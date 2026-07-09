from typing import List, Dict, Any, Optional
from providers import ChatMessage, MessageRole, ToolDefinition, BaseLLMProvider

SYSTEM_PROMPT = """You are a helpful autonomous agent.
You solve tasks step-by-step.
Before using any tool, always think about why you need it and state your reasoning clearly in your text response.
When working with files or code, always run `list_project_files` first to discover the exact workspace layout and file paths. Do not guess filenames or directory structures.
Once you have finished the task or answered the question, summarize your final response to the user.
Do not make unnecessary tool calls. If you get an error from a tool, analyze the error and try to fix your input.
"""

class AgentListener:
    """
    Interface/Observer definition for listening to events in the Agent Loop.
    Allows decoupling UI presentation (Console, Web, GUI, Logs) from the Agent logic.
    """
    def on_step_start(self, step: int, max_steps: int):
        pass

    def on_thought(self, thought: str):
        pass

    def on_tool_call(self, name: str, arguments: Dict[str, Any], call_id: str):
        pass

    def on_tool_output(self, name: str, result: str):
        pass

    def on_error(self, message: str):
        pass

    def on_complete(self):
        pass


class MemoryManager:
    """
    Manages and optimizes conversation history to prevent token overflow
    while preserving context and reasoning quality.
    """
    def __init__(self, max_tool_output_chars: int = 4000, max_full_tool_outputs: int = 3):
        self.max_tool_output_chars = max_tool_output_chars
        self.max_full_tool_outputs = max_full_tool_outputs

    def optimize_before_generation(self, messages: List[ChatMessage]) -> List[ChatMessage]:
        """
        Optimizes history before sending it to the LLM.
        1. Collapses/archives the contents of older TOOL messages to save massive tokens
           while keeping all ASSISTANT thoughts and tool call instructions intact.
        2. Applies a large sliding window as a last-resort safety net for extremely long runs.
        """
        if len(messages) <= 4:
            return messages

        # Find tool output messages that are older than self.max_full_tool_outputs
        tool_output_count = 0
        messages_to_archive_indices = set()
        
        # Iterate backwards to count tool output messages starting from the most recent
        for idx in range(len(messages) - 1, -1, -1):
            msg = messages[idx]
            if msg.role == MessageRole.TOOL:
                tool_output_count += 1
                if tool_output_count > self.max_full_tool_outputs:
                    messages_to_archive_indices.add(idx)

        # Build optimized message list
        optimized = []
        for idx, msg in enumerate(messages):
            if idx in messages_to_archive_indices:
                snippet = msg.content[:80].replace("\n", " ") if msg.content else ""
                archived_content = (
                    f"[Tool output for '{msg.name}' archived to save context tokens. "
                    f"Original size: {len(msg.content or '')} chars. Content snippet: '{snippet}...']"
                )
                optimized.append(
                    ChatMessage(
                        role=msg.role,
                        content=archived_content,
                        tool_call_id=msg.tool_call_id,
                        name=msg.name
                    )
                )
            else:
                optimized.append(msg)

        # Last resort safety net: sliding window if total messages exceed 40
        max_total_messages = 40
        if len(optimized) > max_total_messages:
            preserved_header = []
            conversation_start_idx = 0
            for i, msg in enumerate(optimized):
                if msg.role in (MessageRole.SYSTEM, MessageRole.USER):
                    preserved_header.append(msg)
                    conversation_start_idx = i + 1
                else:
                    break
            
            reasoning_messages = optimized[conversation_start_idx:]
            # Keep only the last 30 messages of reasoning
            if len(reasoning_messages) > 30:
                truncated_reasoning = reasoning_messages[-30:]
                archive_notice = ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="[System Note: Extremely old steps have been removed from context to fit the window limit.]"
                )
                return preserved_header + [archive_notice] + truncated_reasoning

        return optimized

    def optimize_tool_output(self, name: str, result: str) -> str:
        """
        Truncates extremely long tool outputs to prevent them from flooding the context.
        """
        if len(result) > self.max_tool_output_chars:
            truncated_part = result[:self.max_tool_output_chars]
            notice = (
                f"\n\n[... OUTPUT TRUNCATED FROM {len(result)} TO {self.max_tool_output_chars} CHARACTERS TO PRESERVE TOKEN BUDGET. "
                f"If you need to read more, use more specific file line ranges or the relevant parameters ...]"
            )
            return truncated_part + notice
        return result


class Agent:
    """
    Core Agent Loop. Manages conversation history, queries the AI provider,
    and runs tools. Fully decoupled from CLI parsing and terminal output formatting.
    """
    def __init__(
        self,
        provider: BaseLLMProvider,
        tools: List[ToolDefinition],
        tools_map: Dict[str, Any],
        listener: Optional[AgentListener] = None,
        max_steps: int = 25,
        memory_manager: Optional[MemoryManager] = None
    ):
        self.provider = provider
        self.tools = tools
        self.tools_map = tools_map
        self.listener = listener
        self.max_steps = max_steps
        self.memory_manager = memory_manager or MemoryManager()
        self.history: List[ChatMessage] = [
            ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT)
        ]

    def run(self, user_prompt: str):
        self.history.append(ChatMessage(role=MessageRole.USER, content=user_prompt))

        for step in range(1, self.max_steps + 1):
            if self.listener:
                self.listener.on_step_start(step, self.max_steps)
            
            try:
                # Optimize history before sending to provider to prevent token blowup
                optimized_history = self.memory_manager.optimize_before_generation(self.history)
                
                response_msg = self.provider.generate(
                    messages=optimized_history,
                    tools=self.tools,
                    temperature=0.2
                )
            except Exception as e:
                if self.listener:
                    self.listener.on_error(f"Error communicating with provider: {e}")
                break

            if response_msg.content:
                if self.listener:
                    self.listener.on_thought(response_msg.content)
            
            self.history.append(response_msg)

            if response_msg.tool_calls:
                for tool_call in response_msg.tool_calls:
                    tool_name = tool_call.name
                    tool_args = tool_call.arguments
                    tool_id = tool_call.id
                    
                    if self.listener:
                        self.listener.on_tool_call(tool_name, tool_args, tool_id)
                    
                    if tool_name in self.tools_map:
                        try:
                            # Dynamically call the python function mapped to the tool name
                            result = self.tools_map[tool_name](**tool_args)
                        except Exception as e:
                            result = f"Error executing tool '{tool_name}': {e}"
                    else:
                        result = f"Error: Tool '{tool_name}' is not registered/available."

                    # Truncate/Optimize output if it exceeds context limits
                    optimized_result = self.memory_manager.optimize_tool_output(tool_name, result)

                    if self.listener:
                        self.listener.on_tool_output(tool_name, optimized_result)

                    self.history.append(
                        ChatMessage(
                            role=MessageRole.TOOL,
                            content=optimized_result,
                            tool_call_id=tool_id,
                            name=tool_name
                        )
                    )
                continue
            else:
                if self.listener:
                    self.listener.on_complete()
                break
        else:
            if self.listener:
                self.listener.on_error("Reached maximum number of steps without completing.")

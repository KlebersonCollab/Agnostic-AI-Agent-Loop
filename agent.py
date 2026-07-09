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
    def __init__(self, max_tool_output_chars: int = 4000, max_history_steps: int = 8):
        self.max_tool_output_chars = max_tool_output_chars
        self.max_history_steps = max_history_steps

    def optimize_before_generation(self, messages: List[ChatMessage]) -> List[ChatMessage]:
        """
        Optimizes history before sending it to the LLM.
        Applies sliding window to intermediate reasoning steps while preserving system and user prompts.
        """
        if len(messages) <= 4:
            return messages

        # Preserve the very first system instructions and initial user query
        preserved_header = []
        conversation_start_idx = 0
        
        # Identify the initial setup messages (system and first user message)
        for i, msg in enumerate(messages):
            if msg.role in (MessageRole.SYSTEM, MessageRole.USER):
                preserved_header.append(msg)
                conversation_start_idx = i + 1
            else:
                break
                
        # The remaining messages represent the reasoning steps (thoughts, tool calls, tool outputs)
        reasoning_messages = messages[conversation_start_idx:]
        
        # We only keep the last N reasoning messages
        # Note: A single ReAct step usually consists of:
        # - assistant (thought + optional tool call)
        # - tool (output)
        # So we keep the last max_history_steps * 2 messages.
        max_messages_to_keep = self.max_history_steps * 2
        
        if len(reasoning_messages) > max_messages_to_keep:
            # Slice to keep only the recent ones
            truncated_reasoning = reasoning_messages[-max_messages_to_keep:]
            
            # Insert a system message explaining that older steps were archived/truncated
            archive_notice = ChatMessage(
                role=MessageRole.SYSTEM,
                content=f"[System Note: Older reasoning steps and tool interactions have been archived to save context window. Only the last {self.max_history_steps} steps are shown below.]"
            )
            return preserved_header + [archive_notice] + truncated_reasoning
            
        return messages

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
        max_steps: int = 15,
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

import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from providers import ChatMessage, MessageRole, ToolDefinition, BaseLLMProvider
from memory import AgentMemory

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
        write_checkpoint_file: bool = True,
        system_prompt: str = SYSTEM_PROMPT
    ):
        self.provider = provider
        self.tools = tools
        self.tools_map = tools_map
        self.listener = listener
        self.max_steps = max_steps
        self.write_checkpoint_file = write_checkpoint_file
        
        from context_builder import ContextBuilder
        self.context_builder = ContextBuilder(
            base_system_prompt=system_prompt
        )
        
        self.history: List[ChatMessage] = [
            ChatMessage(role=MessageRole.SYSTEM, content=self.context_builder.build_prompt())
        ]
        self.exit_reason: Optional[str] = None
        self.handover_checkpoint: Optional[str] = None

    def run(self, user_prompt: str):
        self.session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        self.memory = AgentMemory()
        self.memory.create_session(self.session_id, user_prompt)

        self.history.append(ChatMessage(role=MessageRole.USER, content=user_prompt))
        self.exit_reason = None
        self.handover_checkpoint = None

        for step in range(1, self.max_steps + 1):
            if self.listener:
                self.listener.on_step_start(step, self.max_steps)
            
            # Dynamically compile the system prompt
            self.history[0].content = self.context_builder.build_prompt()
            
            is_emergency = (self.max_steps > 2) and (step == self.max_steps - 1)
            
            if is_emergency:
                # Force emergency handover checkpoint prompting
                warning_prompt = (
                    "⚠️ SYSTEM WARNING: You are on the pen-ultimate step of this session. "
                    "You must NOT call any tools. Instead, write a detailed handover checkpoint report "
                    "in Markdown summarizing your progress so far. Use the following structure:\n"
                    "- **Progress Achieved**: What has been completed/created so far.\n"
                    "- **Blockers/Delays**: Why the task was not fully completed, and any errors encountered.\n"
                    "- **Backlog**: Detailed list of remaining tasks in order of priority.\n"
                    "- **Next Step**: The exact prompt/instruction for the next agent to resume."
                )
                self.history.append(ChatMessage(role=MessageRole.SYSTEM, content=warning_prompt))
                
                try:
                    response_msg = self.provider.generate(
                        messages=self.history,
                        tools=None,  # Force no tool calling
                        temperature=0.2
                    )
                except Exception as e:
                    if self.listener:
                        self.listener.on_error(f"Error communicating with provider during emergency handover: {e}")
                    break
            else:
                try:
                    response_msg = self.provider.generate(
                        messages=self.history,
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

            # Log assistant thought/response to memory database
            if response_msg.content or response_msg.tool_calls:
                self.memory.add_episode(
                    session_id=self.session_id,
                    step_number=step,
                    role="assistant",
                    content=response_msg.content,
                    tool_calls=[tc.model_dump() for tc in response_msg.tool_calls] if response_msg.tool_calls else None
                )

            if is_emergency:
                self.handover_checkpoint = response_msg.content
                self.exit_reason = "MAX_STEPS_REACHED"
                
                # Save handover report in memory database
                self.memory.update_session_results(
                    session_id=self.session_id,
                    handover_report=self.handover_checkpoint
                )
                
                if self.write_checkpoint_file:
                    checkpoint_data = {
                        "exit_reason": self.exit_reason,
                        "handover_checkpoint": self.handover_checkpoint,
                        "history": [msg.model_dump() for msg in self.history]
                    }
                    try:
                        with open("checkpoint.json", "w", encoding="utf-8") as f:
                            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
                        if self.listener:
                            self.listener.on_error("🚨 Process interrupted preventively. Checkpoint saved to checkpoint.json.")
                    except Exception as e:
                        if self.listener:
                            self.listener.on_error(f"Failed to save checkpoint.json: {e}")
                
                self.memory.close()
                break

            if response_msg.tool_calls:
                for tool_call in response_msg.tool_calls:
                    tool_name = tool_call.name
                    tool_args = tool_call.arguments
                    tool_id = tool_call.id
                    
                    if self.listener:
                        self.listener.on_tool_call(tool_name, tool_args, tool_id)
                    
                    if tool_name == "load_skill":
                        name = tool_args.get("name")
                        if self.context_builder.load_skill(name):
                            result = f"Success: Skill '{name}' has been loaded into your system prompt."
                        else:
                            result = f"Error: Skill '{name}' not found."
                    elif tool_name == "unload_skill":
                        name = tool_args.get("name")
                        if self.context_builder.unload_skill(name):
                            result = f"Success: Skill '{name}' has been unloaded from your system prompt."
                        else:
                            result = f"Error: Skill '{name}' was not loaded."
                    elif tool_name == "search_memory":
                        query = tool_args.get("query")
                        category = tool_args.get("category")
                        try:
                            search_results = self.memory.search(query, category)
                            if not search_results:
                                result = f"No memories found matching '{query}'."
                            else:
                                formatted_results = []
                                for idx, res in enumerate(search_results, 1):
                                    timestamp = res["session_timestamp"] or "Unknown"
                                    step_info = f", Step {res['step_number']}" if res["step_number"] is not None else ""
                                    formatted_results.append(
                                        f"--- Memory Match #{idx} ---\n"
                                        f"Session ID: {res['session_id']}\n"
                                        f"Date: {timestamp}{step_info}\n"
                                        f"Category: {res['category']}\n"
                                        f"Original Task: {res['task_prompt']}\n"
                                        f"Content:\n{res['content']}\n"
                                    )
                                result = "\n".join(formatted_results)
                        except Exception as e:
                            result = f"Error searching memory: {e}"
                    elif tool_name in self.tools_map:
                        try:
                            # Dynamically call the python function mapped to the tool name
                            result = self.tools_map[tool_name](**tool_args)
                        except Exception as e:
                            result = f"Error executing tool '{tool_name}': {e}"
                    else:
                        result = f"Error: Tool '{tool_name}' is not registered/available."

                    if self.listener:
                        self.listener.on_tool_output(tool_name, result)

                    # Log tool output to memory database
                    self.memory.add_episode(
                        session_id=self.session_id,
                        step_number=step,
                        role="tool",
                        content=result
                    )

                    self.history.append(
                        ChatMessage(
                            role=MessageRole.TOOL,
                            content=result,
                            tool_call_id=tool_id,
                            name=tool_name
                        )
                    )
                continue
            else:
                # Log final response summary to memory database
                self.memory.update_session_results(
                    session_id=self.session_id,
                    final_summary=response_msg.content
                )
                
                if self.listener:
                    self.listener.on_complete()
                self.memory.close()
                break
        else:
            if self.listener:
                self.listener.on_error("Reached maximum number of steps without completing.")
            self.memory.close()


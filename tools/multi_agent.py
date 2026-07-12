import json
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from providers import BaseLLMProvider
from agent import Agent, AgentListener, SYSTEM_PROMPT
from .io_tools import list_project_files, read_file, write_file
from .math_tools import calculate

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule
from rich.markup import escape

console = Console()

# Global reference to the active AI Provider
_active_provider = None

def set_active_provider(provider: BaseLLMProvider):
    """Stores the active LLM provider so subagents can reuse it."""
    global _active_provider
    _active_provider = provider


class CollectingAgentListener(AgentListener):
    """
    Agent listener that collects logs of a subagent's execution AND prints them
    to the terminal in real-time with Rich color coding and streaming feedback.
    """
    def __init__(self, role: str, color_code: str):
        self.role = role
        self.color = color_code
        self.logs = []
        self.step = 1
        self.max_steps = 10

    def log_and_print(self, event_icon: str, event_label: str, content: str, content_style: str = ""):
        # Build plain text message to collect in self.logs
        raw_msg = f"{event_icon} {event_label}: {content}"
        self.logs.append(raw_msg)
        
        # Build beautifully aligned console print
        role_part = f"[bold {self.color}]● {self.role:<28}[/]"
        step_part = f"[dim]Step {self.step}/{self.max_steps}[/]"
        divider = "[dim] ⎹ [/dim]"
        event_part = f"{event_icon} [bold {self.color}]{event_label:<8}[/]"
        content_part = f"[{content_style}]{escape(content)}[/{content_style}]" if content_style else escape(content)
        
        console.print(f"{role_part}{divider}{step_part}{divider}{event_part}{divider}{content_part}")

    def on_step_start(self, step: int, max_steps: int):
        self.step = step
        self.max_steps = max_steps
        self.log_and_print("🚀", "Step", f"Starting step {step} of {max_steps}", "dim")

    def on_thought(self, thought: str):
        clean_thought = thought.replace("\n", " ")
        snippet = clean_thought[:120] + "..." if len(clean_thought) > 120 else clean_thought
        self.log_and_print("🤖", "Thought", snippet, "italic dim")

    def on_tool_call(self, name: str, arguments: Dict[str, Any], call_id: str):
        args_str = json.dumps(arguments, ensure_ascii=False)
        if len(args_str) > 80:
            args_str = args_str[:77] + "..."
        self.log_and_print("🛠️", "Call", f"{name}({args_str})", "yellow")

    def on_tool_output(self, name: str, result: str):
        clean_result = result.replace("\n", " ")
        snippet = clean_result[:100] + "..." if len(clean_result) > 100 else clean_result
        self.log_and_print("📥", "Output", snippet, "dim")

    def on_error(self, message: str):
        self.log_and_print("❌", "Error", message, "bold red")

    def on_complete(self):
        self.log_and_print("🏁", "Complete", "Task completed successfully.", "bold green")


def spawn_subagents_parallel(tasks: List[Dict[str, str]]) -> str:
    """
    Spawns multiple specialized subagents in parallel to execute tasks concurrently.
    Each task is a dictionary: {"role_description": "...", "prompt": "..."}
    Returns a JSON string summarizing the final answers of each subagent.
    """
    if not _active_provider:
        return "Error: Active LLM Provider is not set in multi_agent module."

    # Import TOOLS_MAP and TOOLS_METADATA dynamically to avoid circular dependencies during initialization
    from tools import TOOLS_METADATA, TOOLS_MAP
    subagent_tools_map = {k: v for k, v in TOOLS_MAP.items() if k != "spawn_subagents_parallel"}
    subagent_tools_metadata = [t for t in TOOLS_METADATA if t.name != "spawn_subagents_parallel"]

    # Rich styles for distinct subagents
    subagent_colors = [
        'cyan',
        'magenta',
        'yellow',
        'blue',
        'green',
    ]

    console.print()
    console.print(Panel(
        f"[bold magenta]👥 [Multi-Agent Orchestrator][/bold magenta] Spawning [bold cyan]{len(tasks)}[/bold cyan] subagents in parallel...",
        border_style="magenta",
        expand=False
    ))
    for idx, task in enumerate(tasks, 1):
        role = task.get("role_description", "General Specialist")
        prompt = task.get("prompt", "")
        console.print(f"   [bold cyan]➔ Subagent #{idx}[/bold cyan] | [dim]Role:[/dim] '{role}' | [dim]Prompt:[/dim] '{prompt}'")
    
    console.print()
    console.print(Rule("[bold magenta]LIVE SUBAGENT STREAM[/bold magenta]", style="magenta"))
    console.print()

    def run_single_subagent(task_info: Dict[str, str], index: int):
        role = task_info.get("role_description", "General Specialist")
        prompt = task_info.get("prompt", "")
        
        # Assign unique color based on index
        color_code = subagent_colors[(index - 1) % len(subagent_colors)]
        sub_listener = CollectingAgentListener(role, color_code)
        sub_system_prompt = f"You are a specialized subagent. Your role is: {role}\n" + SYSTEM_PROMPT
        
        agent = Agent(
            provider=_active_provider,
            tools=subagent_tools_metadata,
            tools_map=subagent_tools_map,
            listener=sub_listener,
            max_steps=10,
            write_checkpoint_file=False,
            system_prompt=sub_system_prompt
        )
        
        # Run agent loop
        agent.run(prompt)
        
        # Extract final answer
        final_answer = ""
        for msg in reversed(agent.history):
            if msg.role == "assistant" and msg.content and not msg.tool_calls:
                final_answer = msg.content
                break
        if not final_answer and agent.history:
            for msg in reversed(agent.history):
                if msg.role == "assistant" and msg.content:
                    final_answer = msg.content
                    break

        return {
            "index": index,
            "role": role,
            "prompt": prompt,
            "logs": sub_listener.logs,
            "final_answer": final_answer or "No summary response generated."
        }

    # Parallel execution using ThreadPoolExecutor
    task_results = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {
            executor.submit(run_single_subagent, task, idx): idx
            for idx, task in enumerate(tasks)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                res = future.result()
                task_results[idx - 1] = res
            except Exception as e:
                task_results[idx - 1] = {
                    "index": idx,
                    "role": tasks[idx - 1].get("role_description", "General Specialist"),
                    "prompt": tasks[idx - 1].get("prompt", ""),
                    "logs": [f"❌ Execution crashed: {e}"],
                    "final_answer": f"Error: Thread crashed: {e}"
                }

    console.print()
    console.print(Rule("[bold magenta]LIVE STREAM COMPLETED[/bold magenta]", style="magenta"))
    console.print()

    # Print final summary of each subagent inside beautiful Panels
    for res in task_results:
        summary_panel = Panel(
            Markdown(res["final_answer"]),
            title=f"👥 [bold]Subagent Summary: {res['role']}[/bold]",
            border_style="magenta",
            expand=False
        )
        console.print(summary_panel)
        console.print()

    # Construct the JSON report for the parent agent
    report = []
    for res in task_results:
        report.append({
            "role": res["role"],
            "prompt": res["prompt"],
            "result": res["final_answer"]
        })

    return json.dumps(report, indent=2, ensure_ascii=False)

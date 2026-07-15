import time
import re
import json
from typing import Dict, Any

from agent import AgentListener
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text

console = Console()

class ConsoleAgentListener(AgentListener):
    """
    Console/Terminal implementation of the AgentListener using Rich.
    Provides a beautiful, structured CLI dashboard with live status indicators.
    """
    def __init__(self):
        self.status = None
        self.step_start_time = None
        self.current_tool_call_formatted = None
        self.verbose = False

    def _stop_status(self):
        if self.status:
            self.status.stop()
            self.status = None

    def on_step_start(self, step: int, max_steps: int):
        self._stop_status()
        self.step_start_time = time.monotonic()
        self.status = console.status("[bold green]Agent is thinking...", spinner="dots")
        self.status.start()

    def _format_tool_call(self, name: str, arguments: Dict[str, Any]) -> str:
        import os
        suffix = " (/verbose to expand)" if not self.verbose else ""
        
        if name == "list_project_files":
            path = os.path.abspath(arguments.get("path") or ".")
            return f"ListDir({path}){suffix}"
        elif name == "read_file":
            path = os.path.abspath(arguments.get("filename") or "")
            return f"Read({path}){suffix}"
        elif name == "write_file":
            path = os.path.abspath(arguments.get("filename") or "")
            if os.path.exists(path):
                return f"Edit({path}){suffix}"
            return f"Create({path}){suffix}"
        elif name == "patch_file" or name == "patch":
            path = os.path.abspath(arguments.get("filename") or "")
            return f"Edit({path}){suffix}"
        elif name == "run_command":
            cmd = arguments.get("CommandLine") or ""
            return f"Bash({cmd}){suffix}"
        elif name == "calculate":
            expr = arguments.get("expression") or ""
            return f"Calc({expr})"
        elif name == "search_grep":
            pat = arguments.get("Query") or arguments.get("pattern") or ""
            return f"Grep({pat})"
        elif name == "search_memory":
            q = arguments.get("query") or ""
            return f"SearchMemory({q})"
        elif name == "spawn_subagents_parallel":
            tasks = arguments.get("tasks") or []
            return f"Subagents({len(tasks)} tasks){suffix}"
        elif name == "spawn_subagent_async":
            role = arguments.get("role_description") or ""
            return f"SpawnAsync({role}){suffix}"
        elif name == "check_subagents_status":
            sid = arguments.get("subagent_id") or "all"
            return f"CheckStatus({sid}){suffix}"
        elif name == "interrupt_subagent":
            sid = arguments.get("subagent_id") or ""
            return f"Interrupt({sid}){suffix}"
        elif name == "load_skill":
            sk = arguments.get("name") or ""
            return f"LoadSkill({sk})"
        elif name == "unload_skill":
            sk = arguments.get("name") or ""
            return f"UnloadSkill({sk})"
        elif name == "manage_task":
            tid = arguments.get("TaskId") or ""
            return f"ManageTask(Task: {tid}){suffix}"
        elif name == "schedule":
            prompt = arguments.get("Prompt") or ""
            return f"Schedule({prompt}){suffix}"
        else:
            args_str = json.dumps(arguments, ensure_ascii=False)
            return f"{name}({args_str})"

    def on_thought(self, thought: str, is_final: bool = False):
        self._stop_status()
        if is_final:
            console.print(Markdown(thought))
            console.print()
        else:
            elapsed = 1
            if self.step_start_time is not None:
                elapsed = max(1, int(time.monotonic() - self.step_start_time))
            
            tokens = (len(thought) + 3) // 4
            tokens_str = f"{tokens/1000:.1f}k" if tokens >= 1000 else str(tokens)
            
            lines = [line.strip() for line in thought.split("\n") if line.strip()]
            title = lines[0] if lines else "Thinking..."
            title = re.sub(r'^(#+\s*|-\s*|\*\s*|\d+\.\s*)', '', title).strip()
            if len(title) > 80:
                title = title[:77] + "..."
                
            console.print(f"[bold dim]▸ Thought for {elapsed}s, {tokens_str} tokens[/bold dim]")
            console.print(f"  {title}")
            console.print()

    def on_tool_call(self, name: str, arguments: Dict[str, Any], call_id: str):
        self._stop_status()
        formatted = self._format_tool_call(name, arguments)
        self.current_tool_call_formatted = formatted
        console.print(f"[bold yellow]● {formatted}...[/bold yellow]", end="\r")
        import sys
        sys.stdout.flush()

    def on_tool_output(self, name: str, result: str):
        self._stop_status()
        formatted = getattr(self, "current_tool_call_formatted", None) or f"{name}(...)"
        
        is_error = result.strip().startswith("Error") or result.strip().startswith("Warning")
        if is_error:
            console.print(f"[bold red]● {formatted} (failed)[/bold red]                       ")
        else:
            console.print(f"[bold green]● {formatted}[/bold green]                            ")
        self.current_tool_call_formatted = None
        
        if self.verbose:
            try:
                parsed = json.loads(result)
                display_content = Syntax(json.dumps(parsed, indent=2, ensure_ascii=False), "json", theme="monokai", background_color="default")
            except Exception:
                display_content = Text(result)

            panel = Panel(
                display_content,
                title="📥 [bold cyan]Tool Output[/bold cyan]",
                border_style="cyan",
                expand=False
            )
            console.print(panel)

    def on_error(self, message: str):
        self._stop_status()
        console.print(Panel(Text(message), title="❌ Error", border_style="red"))

    def on_complete(self):
        self._stop_status()

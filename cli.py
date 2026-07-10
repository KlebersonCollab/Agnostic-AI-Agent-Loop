import os
import sys
import json
import argparse
import time
import re
from typing import Dict, Any

from providers import get_provider
from agent import Agent, AgentListener
from tools import TOOLS_METADATA, TOOLS_MAP, set_active_provider
from context.builder import ContextBuilder

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.rule import Rule
from rich.align import Align
from rich.text import Text
from rich.markup import escape

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
        import json
        
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
            # Overwrite carriage return with bold red line, then newline
            console.print(f"[bold red]● {formatted} (failed)[/bold red]                       ")
        else:
            # Overwrite carriage return with bold green line, then newline
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


def run_cli():
    parser = argparse.ArgumentParser(description="Agent Loop runner using agnostic AI provider.")
    parser.add_argument(
        "--provider", 
        type=str, 
        default=os.environ.get("AGENT_PROVIDER", "gemini"),
        help="LLM provider: 'openai', 'gemini', 'anthropic', 'openrouter', 'openai_compatible' (Ollama/Groq)"
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default=os.environ.get("AGENT_MODEL", "gemini-2.5-flash"),
        help="LLM model name (e.g. 'gemini-2.5-flash', 'gpt-4o-mini', 'claude-3-5-sonnet-20241022')"
    )
    parser.add_argument(
        "--api-key", 
        type=str, 
        default=None,
        help="API Key for the provider (optional, falls back to env vars)"
    )
    parser.add_argument(
        "--base-url", 
        type=str, 
        default=None,
        help="Custom base URL (for Ollama, Groq, local endpoints)"
    )
    parser.add_argument(
        "--prompt", 
        type=str, 
        default=None,
        help="Prompt/Task for the agent (if not provided, interactive mode starts)"
    )
    parser.add_argument(
        "--max-steps", 
        type=int, 
        default=200,
        help="Maximum loop iterations/steps"
    )

    args = parser.parse_args()

    # Discover skills and rules at startup
    builder = ContextBuilder(
        base_system_prompt=""
    )
    skills_list = list(builder.skills_cache.keys())
    rules_list = list(builder.rules_cache.keys())

    # Welcome Banner in Panel
    welcome_text = """
[bold magenta]🤖 Welcome to the Agnostic AI Agent Loop![/bold magenta]

[dim]Active Provider:[/dim] [bold blue]{provider}[/bold blue] | [dim]Model:[/dim] [bold green]{model}[/bold green]
[dim]Tools available:[/dim] [yellow]{tools}[/yellow]
[dim]Skills available:[/dim] [cyan]{skills}[/cyan]
[dim]Rules active:[/dim] [magenta]{rules}[/magenta]
    """
    welcome_panel = Panel(
        Align.center(welcome_text.format(
            provider=args.provider,
            model=args.model,
            tools=", ".join(TOOLS_MAP.keys()),
            skills=", ".join(skills_list) if skills_list else "None",
            rules=", ".join(rules_list) if rules_list else "None"
        )),
        border_style="magenta"
    )
    console.print(welcome_panel)

    prompt = args.prompt
    checkpoint_file = "checkpoint.json"
    checkpoint_loaded = False
    
    if not prompt and os.path.exists(checkpoint_file):
        console.print(Panel(
            "[yellow]⚠️  Found a checkpoint from a previous session ('checkpoint.json').[/yellow]\n"
            "The previous task reached the execution step limit before completion.",
            title="[bold yellow]Checkpoint Detected[/bold yellow]",
            border_style="yellow"
        ))
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
            
            report = checkpoint_data.get("handover_checkpoint", "")
            if report:
                console.print(Panel(
                    Markdown(report),
                    title="📋 [bold magenta]Handover Checkpoint Report[/bold magenta]",
                    border_style="magenta",
                    expand=False
                ))
                
                try:
                    resume_choice = console.input("[bold cyan]Do you want to resume this task? (y/n, default y): [/bold cyan]").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[bold red]Exiting.[/bold red]")
                    sys.exit(0)
                    
                if resume_choice in ("", "y", "yes"):
                    prompt = (
                        "Please resume the task. Your context has been purified. "
                        "Analyze the progress achieved and the backlog of remaining tasks from the handover report, "
                        "then continue execution by performing the next immediate steps.\n\n"
                        f"### Handover Checkpoint Report\n{report}"
                    )
                    checkpoint_loaded = True
                else:
                    try:
                        os.rename(checkpoint_file, "checkpoint.json.old")
                        console.print("[dim]Renamed old checkpoint to 'checkpoint.json.old' to avoid conflict.[/dim]")
                    except Exception:
                        pass
        except Exception as e:
            console.print(f"[red]Error loading checkpoint: {e}[/red]")

    # Initialize provider
    try:
        provider = get_provider(
            provider_name=args.provider,
            model_name=args.model,
            api_key=args.api_key,
            base_url=args.base_url
        )
    except Exception as e:
        console.print(Panel(f"Initialization Error: {e}", title="❌ Error", border_style="red"))
        sys.exit(1)

    # Set active provider for tools (subagents)
    set_active_provider(provider)

    # Setup listener and core Agent
    listener = ConsoleAgentListener()
    agent = Agent(
        provider=provider,
        tools=TOOLS_METADATA,
        tools_map=TOOLS_MAP,
        listener=listener,
        max_steps=args.max_steps
    )

    is_interactive = (args.prompt is None)

    if not is_interactive:
        # One-shot execution
        console.print()
        console.print(Panel(
            f"[bold cyan]Objective:[/bold cyan] {prompt}", 
            border_style="cyan"
        ))
        agent.run(prompt)
        
        # Clean up checkpoint if completed successfully
        if agent.exit_reason != "MAX_STEPS_REACHED":
            if os.path.exists(checkpoint_file):
                try:
                    os.remove(checkpoint_file)
                    console.print("[dim]✓ Cleaned up checkpoint file.[/dim]")
                except Exception:
                    pass
    else:
        # Continuous interactive session
        first_turn = True
        while True:
            # If a checkpoint was detected and approved at startup, execute it on the first turn
            if first_turn and checkpoint_loaded:
                console.print()
                console.print(Panel(
                    "[bold cyan]Resuming previous task from Handover Checkpoint[/bold cyan]", 
                    border_style="cyan"
                ))
                agent.run(prompt)
                first_turn = False
                
                # Clean up checkpoint if completed successfully
                if agent.exit_reason != "MAX_STEPS_REACHED":
                    if os.path.exists(checkpoint_file):
                        try:
                            os.remove(checkpoint_file)
                            console.print("[dim]✓ Cleaned up checkpoint file.[/dim]")
                        except Exception:
                            pass
                continue

            try:
                console.print()
                user_input = console.input("[bold magenta]Agnostic (or '/context', '/verbose', '/clear', '/exit') > [/bold magenta]").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold red]Exiting.[/bold red]")
                break

            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                console.print("[bold red]Exiting.[/bold red]")
                break

            if user_input.lower() in ("/clear", "/reset", "clear", "reset"):
                from providers import ChatMessage, MessageRole
                # Reset history to clean system prompt
                agent.history = [
                    ChatMessage(role=MessageRole.SYSTEM, content=agent.context_builder.build_prompt())
                ]
                console.print("[dim]✓ Conversation history and active context cleared.[/dim]")
                continue

            if user_input.lower() in ("/verbose", "/outputs", "/v", "verbose", "outputs"):
                listener.verbose = not listener.verbose
                status_str = "ENABLED" if listener.verbose else "DISABLED"
                console.print(f"[dim]✓ Tool output expansion {status_str}.[/dim]")
                continue

            if user_input.lower() in ("/context", "/c", "context"):
                from context.breakdown import calculate_context_breakdown
                bd = calculate_context_breakdown(agent)
                table = Table(title="📊 Context Window Token Usage Breakdown", show_header=True, header_style="bold magenta")
                table.add_column("Category", style="cyan")
                table.add_column("Est. Tokens", justify="right", style="green")
                table.add_column("Percentage", justify="right", style="yellow")
                
                # Assume standard baseline limit
                limit = 128000
                
                table.add_row("Base System Prompt", f"{bd['base_system']:,}", f"{bd['base_system']/limit:.2%}")
                table.add_row("Active Rules", f"{bd['rules']:,}", f"{bd['rules']/limit:.2%}")
                table.add_row("Skills Metadata", f"{bd['skills_metadata']:,}", f"{bd['skills_metadata']/limit:.2%}")
                table.add_row("Active Skills Body", f"{bd['skills_body']:,}", f"{bd['skills_body']/limit:.2%}")
                table.add_row("Tool Schemas", f"{bd['tools']:,}", f"{bd['tools']/limit:.2%}")
                table.add_row("Conversation History", f"{bd['history']:,}", f"{bd['history']/limit:.2%}")
                table.add_section()
                table.add_row("Total Usage", f"{bd['total']:,}", f"{bd['total']/limit:.2%}", style="bold")
                
                console.print()
                console.print(table)
                console.print(f"[dim]Note: Percentages are calculated relative to a standard {limit:,} tokens limit.[/dim]")
                continue

            console.print()
            console.print(Panel(
                f"[bold cyan]Objective:[/bold cyan] {user_input}", 
                border_style="cyan"
            ))
            agent.run(user_input)

            # Clean up checkpoint if completed successfully
            if agent.exit_reason != "MAX_STEPS_REACHED":
                if os.path.exists(checkpoint_file):
                    try:
                        os.remove(checkpoint_file)
                        console.print("[dim]✓ Cleaned up checkpoint file.[/dim]")
                    except Exception:
                        pass
            
            first_turn = False

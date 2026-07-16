import os
import sys
import json
import argparse

from providers import get_provider
from agent import Agent
from tools import (
    set_active_provider,
    get_orchestrator_tools,
    get_classic_tools
)
from context.builder import ContextBuilder

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from tui import (
    ConsoleAgentListener,
    print_welcome_banner,
    run_one_shot,
    run_interactive_loop
)

console = Console()


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
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["orchestrator", "classic"],
        default="classic",
        help="Agent execution mode: 'orchestrator' (strategic leader) or 'classic' (monolithic)"
    )
    parser.add_argument(
        "--front-host",
        type=str,
        default="127.0.0.1",
        help="Host for the Memory Graph frontend server (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--front-port",
        type=int,
        default=8090,
        help="Port for the Memory Graph frontend server (default: 8090)"
    )
    parser.add_argument(
        "--no-front",
        action="store_true",
        help="Do not start the Memory Graph frontend server"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a browser tab for the Memory Graph frontend"
    )

    args = parser.parse_args()

    # Start the Memory Graph frontend server (part of the project, runs alongside the agent)
    if not args.no_front:
        try:
            from front.server import start_server
            _front_server, _front_port = start_server(
                host=args.front_host,
                port=args.front_port,
                open_browser=not args.no_browser,
            )
            console.print(
                f"[dim]🧠 Memory Graph frontend: http://{args.front_host}:{_front_port}/[/dim]"
            )
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not start Memory Graph frontend: {e}[/yellow]")

    # Discover skills and rules at startup
    builder = ContextBuilder(
        base_system_prompt=""
    )
    skills_list = list(builder.skills_cache.keys())
    rules_list = list(builder.rules_cache.keys())

    # Select tools and prompt based on execution mode
    if args.mode == "orchestrator":
        active_tools_metadata, active_tools_map = get_orchestrator_tools()
        from agent import ORCHESTRATOR_SYSTEM_PROMPT
        active_system_prompt = ORCHESTRATOR_SYSTEM_PROMPT
    else:
        active_tools_metadata, active_tools_map = get_classic_tools()
        from agent import SYSTEM_PROMPT
        active_system_prompt = SYSTEM_PROMPT

    # Welcome Banner in Panel
    print_welcome_banner(
        provider_name=args.provider,
        model_name=args.model,
        mode=args.mode,
        tools_list=list(active_tools_map.keys()),
        skills_list=skills_list,
        rules_list=rules_list
    )

    prompt = args.prompt
    is_loop = False
    if prompt and prompt.lower().startswith("/loop"):
        is_loop = True
        prompt = prompt[5:].strip()
        if not prompt:
            console.print("[red]Error: /loop prefix used but no prompt content provided.[/red]")
            sys.exit(1)
            
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
        tools=active_tools_metadata,
        tools_map=active_tools_map,
        listener=listener,
        max_steps=args.max_steps,
        system_prompt=active_system_prompt
    )

    is_interactive = (args.prompt is None)

    if not is_interactive:
        run_one_shot(agent, prompt, is_loop)
    else:
        run_interactive_loop(agent, listener, checkpoint_loaded, prompt)


if __name__ == "__main__":
    run_cli()

import os
import sys
from rich.console import Console
from rich.panel import Panel

from tui.commands import handle_slash_command

console = Console()
checkpoint_file = "checkpoint.json"

def run_one_shot(agent, prompt: str, is_loop: bool):
    """Executes a single task in one-shot mode."""
    if is_loop:
        agent.max_steps = 10000
        border_color = "red"
        title_text = "[bold red]🔄 Loop Mode Objective (10000 Steps max):[/bold red]"
    else:
        border_color = "cyan"
        title_text = "[bold cyan]Objective:[/bold cyan]"
        
    console.print()
    console.print(Panel(
        f"{title_text} {prompt}", 
        border_style=border_color
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


def run_interactive_loop(agent, listener, checkpoint_loaded: bool = False, checkpoint_prompt: str = None):
    """Starts the continuous interactive session loop."""
    first_turn = True
    while True:
        # If a checkpoint was approved at startup, execute it on the first turn
        if first_turn and checkpoint_loaded and checkpoint_prompt:
            console.print()
            console.print(Panel(
                "[bold cyan]Resuming previous task from Handover Checkpoint[/bold cyan]", 
                border_style="cyan"
            ))
            agent.run(checkpoint_prompt)
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
            user_input = console.input("[bold magenta]Agnostic (or '/context', '/verbose', '/clear', '/exit', '/loop') > [/bold magenta]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold red]Exiting.[/bold red]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
            console.print("[bold red]Exiting.[/bold red]")
            break

        # Process standard TUI commands
        if handle_slash_command(user_input, agent, listener):
            continue

        # Process special loop mode
        if user_input.lower().startswith("/loop"):
            prompt_content = user_input[5:].strip()
            if not prompt_content:
                console.print("[yellow]Usage: /loop <your prompt>[/yellow]")
                console.print("[dim]Runs the agent with a large step limit (10000) to execute long tasks without early handover interrupts.[/dim]")
                continue
            
            original_max_steps = agent.max_steps
            agent.max_steps = 10000
            console.print()
            console.print(Panel(
                f"[bold red]🔄 Loop Mode (Step Limit Removed - 10000 Steps max):[/bold red] {prompt_content}", 
                border_style="red"
            ))
            agent.run(prompt_content)
            agent.max_steps = original_max_steps
            
            # Clean up checkpoint if completed successfully
            if agent.exit_reason != "MAX_STEPS_REACHED":
                if os.path.exists(checkpoint_file):
                    try:
                        os.remove(checkpoint_file)
                        console.print("[dim]✓ Cleaned up checkpoint file.[/dim]")
                    except Exception:
                        pass
            first_turn = False
            continue

        # Process standard input
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

from rich.console import Console
from rich.table import Table

console = Console()

def handle_slash_command(user_input: str, agent, listener) -> bool:
    """
    Handles interactive TUI slash commands.
    Returns True if user_input was a command (and was processed), False otherwise.
    """
    cmd = user_input.strip().lower()

    if cmd in ("/clear", "/reset", "clear", "reset"):
        from providers.base import ChatMessage, MessageRole
        # Reset history to clean system prompt
        agent.history = [
            ChatMessage(role=MessageRole.SYSTEM, content=agent.context_builder.build_prompt())
        ]
        agent.hooks.trigger_on_session_clear(agent)
        console.print("[dim]✓ Conversation history and active context cleared.[/dim]")
        return True

    if cmd in ("/verbose", "/outputs", "/v", "verbose", "outputs"):
        listener.verbose = not listener.verbose
        status_str = "ENABLED" if listener.verbose else "DISABLED"
        console.print(f"[dim]✓ Tool output expansion {status_str}.[/dim]")
        return True

    if cmd in ("/context", "/c", "context"):
        from context.breakdown import calculate_context_breakdown
        bd = calculate_context_breakdown(agent)
        table = Table(title="📊 Context Window Token Usage Breakdown", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Est. Tokens", justify="right", style="green")
        table.add_column("Percentage", justify="right", style="yellow")
        
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
        return True

    return False

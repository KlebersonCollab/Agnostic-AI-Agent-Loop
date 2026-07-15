from rich.console import Console
from rich.panel import Panel
from rich.align import Align

console = Console()

def print_welcome_banner(provider_name: str, model_name: str, mode: str, tools_list: list, skills_list: list, rules_list: list):
    """Prints a beautiful formatted welcome banner at startup."""
    welcome_text = """
[bold magenta]🤖 Welcome to the Agnostic AI Agent Loop![/bold magenta]

[dim]Active Provider:[/dim] [bold blue]{provider}[/bold blue] | [dim]Model:[/dim] [bold green]{model}[/bold green] | [dim]Mode:[/dim] [bold yellow]{mode}[/bold yellow]
[dim]Tools available:[/dim] [yellow]{tools}[/yellow]
[dim]Skills available:[/dim] [cyan]{skills}[/cyan]
[dim]Rules active:[/dim] [magenta]{rules}[/magenta]
    """
    
    welcome_panel = Panel(
        Align.center(welcome_text.format(
            provider=provider_name,
            model=model_name,
            mode=mode.upper(),
            tools=", ".join(tools_list),
            skills=", ".join(skills_list) if skills_list else "None",
            rules=", ".join(rules_list) if rules_list else "None"
        )),
        border_style="magenta"
    )
    console.print(welcome_panel)

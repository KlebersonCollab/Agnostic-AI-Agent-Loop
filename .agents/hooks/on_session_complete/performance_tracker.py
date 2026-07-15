import sys
from rich.console import Console
from rich.table import Table

def handler(agent):
    stats = getattr(sys, "_tool_perf_stats", {})
    if not stats:
        return
    
    console = Console()
    table = Table(title="📊 Relatório de Desempenho das Ferramentas", title_style="bold magenta")
    
    table.add_column("Ferramenta", style="cyan", no_wrap=True)
    table.add_column("Chamadas", style="green", justify="right")
    table.add_column("Tempo Total (s)", style="yellow", justify="right")
    table.add_column("Média (s)", style="blue", justify="right")
    table.add_column("Mín (s)", style="dim white", justify="right")
    table.add_column("Máx (s)", style="bold red", justify="right")
    
    # Sort stats by total duration descending
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]["total_time"], reverse=True)
    
    for tool_name, data in sorted_stats:
        calls = data["calls"]
        total = data["total_time"]
        avg = total / calls if calls > 0 else 0
        t_min = data["min_time"]
        t_max = data["max_time"]
        
        table.add_row(
            tool_name,
            f"{calls:,}",
            f"{total:.4f}s",
            f"{avg:.4f}s",
            f"{t_min:.4f}s",
            f"{t_max:.4f}s"
        )
        
    console.print(table)
    
    # Reset stats so next session has a clean slate
    sys._tool_perf_stats = {}
    if hasattr(sys, "_tool_start_times"):
        sys._tool_start_times = {}

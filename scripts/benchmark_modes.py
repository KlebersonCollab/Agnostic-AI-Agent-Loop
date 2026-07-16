#!/usr/bin/env python3
import sys
import os
import time
import json
import traceback
import subprocess

# Insert project root into path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from providers import get_provider
from agent import Agent, SYSTEM_PROMPT, ORCHESTRATOR_SYSTEM_PROMPT
from agent.listener import AgentListener
from tools import get_classic_tools, get_orchestrator_tools, set_active_provider
from memory.core import AgentMemory
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class BenchmarkListener(AgentListener):
    def __init__(self, mode_name):
        self.mode_name = mode_name
        self.step_count = 0
        self.thoughts = []
        self.tool_calls = []

    def on_step_start(self, step, max_steps):
        self.step_count = step
        console.print(f"    [dim][{self.mode_name}][/dim] Step {step}/{max_steps} started...")

    def on_thought(self, thought, is_final=False):
        snippet = thought.replace('\n', ' ')
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        console.print(f"    [dim][{self.mode_name}][/dim] Thought: [italic]{snippet}[/italic]")
        self.thoughts.append(thought)

    def on_tool_call(self, name, arguments, call_id):
        console.print(f"    [dim][{self.mode_name}][/dim] Tool Call: [yellow]{name}[/yellow]")
        self.tool_calls.append((name, arguments))

    def on_tool_output(self, name, result):
        snippet = result.replace('\n', ' ')
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        console.print(f"    [dim][{self.mode_name}][/dim] Tool Output: [green]{snippet}[/green]")

    def on_error(self, message):
        console.print(f"    [bold red][{self.mode_name}] Error: {message}[/bold red]")

    def on_complete(self):
        pass

def run_agent(mode, prompt, provider):
    if mode == "classic":
        metadata, tools_map = get_classic_tools()
        sys_prompt = SYSTEM_PROMPT
    else:
        metadata, tools_map = get_orchestrator_tools()
        sys_prompt = ORCHESTRATOR_SYSTEM_PROMPT

    listener = BenchmarkListener(mode.upper())
    
    # Enable hooks by default when creating Agent (it instantiates HooksManager)
    agent = Agent(
        provider=provider,
        tools=metadata,
        tools_map=tools_map,
        listener=listener,
        max_steps=12,
        system_prompt=sys_prompt,
        write_checkpoint_file=False
    )
    
    start_time = time.monotonic()
    try:
        agent.run(prompt)
    except Exception as e:
        console.print(f"[bold red]Exception running agent ({mode}): {e}[/bold red]")
        traceback.print_exc()
    elapsed = time.monotonic() - start_time

    # Calculate tokens & cost
    total_prompt = 0
    total_completion = 0
    for msg in agent.history:
        if getattr(msg, "response_metadata", None):
            meta = msg.response_metadata
            total_prompt += meta.get("prompt_tokens", 0)
            total_completion += meta.get("completion_tokens", 0)

    final_answer = ""
    for msg in reversed(agent.history):
        if msg.role == "assistant" and msg.content and not getattr(msg, "tool_calls", None):
            final_answer = msg.content
            break
    if not final_answer and agent.history:
        for msg in reversed(agent.history):
            if msg.role == "assistant" and msg.content:
                final_answer = msg.content
                break

    return {
        "steps": listener.step_count,
        "elapsed": elapsed,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "final_answer": final_answer,
        "tool_calls": listener.tool_calls
    }

def main():
    provider_name = os.environ.get("AGENT_PROVIDER", "openrouter")
    model_name = os.environ.get("AGENT_MODEL", "tencent/hy3:free")
    api_key = os.environ.get("OPENROUTER_API_KEY") if provider_name == "openrouter" else os.environ.get(f"{provider_name.upper()}_API_KEY")
    
    if not api_key or "sua_chave" in api_key:
        console.print("[bold red]Error: No valid API key found. Please configure .env properly.[/bold red]")
        sys.exit(1)

    console.print(Panel(
        f"Initializing capability benchmark using:\n"
        f"Provider: [bold cyan]{provider_name}[/bold cyan]\n"
        f"Model: [bold cyan]{model_name}[/bold cyan]",
        title="[bold green]Agent Capability Benchmark[/bold green]"
    ))

    provider = get_provider(provider_name, model_name, api_key=api_key)
    set_active_provider(provider)

    results = []

    # =========================================================================
    # TASK 1: Operational Integration (File IO + Math)
    # =========================================================================
    task1_name = "Task 1: File Read & Calculation"
    task1_prompt = (
        "Leia o arquivo temporário 'temp_benchmark_num.txt' que contém um número decimal, "
        "multiplique esse número por 3, escreva o resultado de volta no mesmo arquivo "
        "'temp_benchmark_num.txt' e retorne apenas 'Sucesso' se der certo."
    )
    
    def setup_task1():
        with open("temp_benchmark_num.txt", "w") as f:
            f.write("21")
            
    def verify_task1():
        if not os.path.exists("temp_benchmark_num.txt"):
            return False, "File missing"
        with open("temp_benchmark_num.txt", "r") as f:
            content = f.read().strip()
        try:
            val = float(content)
            if val == 63.0:
                return True, "Success (63)"
            return False, f"Incorrect value: {content}"
        except ValueError:
            return False, f"Non-numeric: {content}"
            
    def cleanup_task1():
        if os.path.exists("temp_benchmark_num.txt"):
            os.remove("temp_benchmark_num.txt")

    # Run Task 1 - Classic
    console.print(f"\n[bold magenta]=== Running {task1_name} [Classic Mode] ===[/bold magenta]")
    setup_task1()
    classic_t1 = run_agent("classic", task1_prompt, provider)
    t1_classic_ok, t1_classic_reason = verify_task1()
    cleanup_task1()

    # Run Task 1 - Orchestrator
    console.print(f"\n[bold magenta]=== Running {task1_name} [Orchestrator Mode] ===[/bold magenta]")
    setup_task1()
    orch_t1 = run_agent("orchestrator", task1_prompt, provider)
    t1_orch_ok, t1_orch_reason = verify_task1()
    cleanup_task1()
    
    results.append({
        "task": task1_name,
        "classic": {"success": t1_classic_ok, "info": t1_classic_reason, **classic_t1},
        "orchestrator": {"success": t1_orch_ok, "info": t1_orch_reason, **orch_t1}
    })

    # =========================================================================
    # TASK 2: Code Debugging and Validation
    # =========================================================================
    task2_name = "Task 2: Code Bug Fixing & Validation"
    task2_prompt = (
        "Conserte a função no arquivo 'temp_benchmark_code.py'. Ela está retornando 'a - b' "
        "mas deve retornar 'a + b'. Depois de salvar o arquivo corrigido, execute um comando shell "
        "com a ferramenta adequada para verificar se o assert 'import temp_benchmark_code; assert temp_benchmark_code.add(2, 3) == 5' "
        "executa sem erros. Retorne apenas 'Sucesso' ao final."
    )
    
    def setup_task2():
        with open("temp_benchmark_code.py", "w") as f:
            f.write("def add(a, b):\n    return a - b\n")
            
    def verify_task2():
        if not os.path.exists("temp_benchmark_code.py"):
            return False, "File missing"
        try:
            res = subprocess.run(
                ["python3", "-c", "import temp_benchmark_code; assert temp_benchmark_code.add(2, 3) == 5"],
                capture_output=True, text=True
            )
            if res.returncode == 0:
                return True, "Success (Correctly fixed and validated)"
            return False, f"Assert failed: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Exception: {e}"
            
    def cleanup_task2():
        if os.path.exists("temp_benchmark_code.py"):
            os.remove("temp_benchmark_code.py")
        if os.path.exists("__pycache__"):
            import shutil
            shutil.rmtree("__pycache__", ignore_errors=True)

    # Run Task 2 - Classic
    console.print(f"\n[bold magenta]=== Running {task2_name} [Classic Mode] ===[/bold magenta]")
    setup_task2()
    classic_t2 = run_agent("classic", task2_prompt, provider)
    t2_classic_ok, t2_classic_reason = verify_task2()
    cleanup_task2()

    # Run Task 2 - Orchestrator
    console.print(f"\n[bold magenta]=== Running {task2_name} [Orchestrator Mode] ===[/bold magenta]")
    setup_task2()
    orch_t2 = run_agent("orchestrator", task2_prompt, provider)
    t2_orch_ok, t2_orch_reason = verify_task2()
    cleanup_task2()
    
    results.append({
        "task": task2_name,
        "classic": {"success": t2_classic_ok, "info": t2_classic_reason, **classic_t2},
        "orchestrator": {"success": t2_orch_ok, "info": t2_orch_reason, **orch_t2}
    })

    # =========================================================================
    # TASK 3: Memory Query
    # =========================================================================
    task3_name = "Task 3: Memory Database Query"
    task3_prompt = (
        "Busque na memória de histórico do agente a decisão sobre a 'Modularização do Banco de Dados' "
        "e retorne a data exata em que essa decisão ocorreu."
    )
    
    def setup_task3():
        # Seed memory graph index
        db = AgentMemory()
        # Seed test thought with clear details
        try:
            db.create_session("test_seed_session_1", "Test objective for database modularization")
            db.add_episode(
                session_id="test_seed_session_1",
                step_number=1,
                role="assistant",
                content="Decidido em 2026-07-15: Database Modularization - refatorar memory.py para pacote."
            )
        finally:
            db.close()
            
    def verify_task3(answer_text):
        if not answer_text:
            return False, "Empty answer"
        # Validate that the answer contains the year and modularization info
        ans = answer_text.lower()
        if "2026-07-15" in ans:
            return True, "Success (Found 2026-07-15)"
        return False, f"Answer missing date: {answer_text[:100]}..."
        
    def cleanup_task3():
        # Keep DB as is, but we can clean up if desired.
        pass

    # Run Task 3 - Classic
    console.print(f"\n[bold magenta]=== Running {task3_name} [Classic Mode] ===[/bold magenta]")
    setup_task3()
    classic_t3 = run_agent("classic", task3_prompt, provider)
    t3_classic_ok, t3_classic_reason = verify_task3(classic_t3["final_answer"])
    cleanup_task3()

    # Run Task 3 - Orchestrator
    console.print(f"\n[bold magenta]=== Running {task3_name} [Orchestrator Mode] ===[/bold magenta]")
    setup_task3()
    orch_t3 = run_agent("orchestrator", task3_prompt, provider)
    t3_orch_ok, t3_orch_reason = verify_task3(orch_t3["final_answer"])
    cleanup_task3()
    
    results.append({
        "task": task3_name,
        "classic": {"success": t3_classic_ok, "info": t3_classic_reason, **classic_t3},
        "orchestrator": {"success": t3_orch_ok, "info": t3_orch_reason, **orch_t3}
    })

    # =========================================================================
    # PRINT SUMMARY TABLE
    # =========================================================================
    console.print("\n" + "="*80)
    console.print("[bold green]Capability Benchmark Results Summary[/bold green]")
    console.print("="*80 + "\n")

    table = Table(title="Agent Mode Comparison (Classic vs Orchestrator)")
    table.add_column("Task Name", style="cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Classic Mode", style="green")
    table.add_column("Orchestrator Mode", style="magenta")

    for item in results:
        t_name = item["task"]
        c = item["classic"]
        o = item["orchestrator"]
        
        c_status = "[bold green]PASS[/bold green]" if c["success"] else f"[bold red]FAIL[/bold red] ({c['info']})"
        o_status = "[bold green]PASS[/bold green]" if o["success"] else f"[bold red]FAIL[/bold red] ({o['info']})"
        
        table.add_row(t_name, "Outcome", c_status, o_status)
        table.add_row("", "Steps", str(c["steps"]), str(o["steps"]))
        table.add_row("", "Elapsed Time", f"{c['elapsed']:.2f}s", f"{o['elapsed']:.2f}s")
        table.add_row("", "Total Tokens", f"{c['total_tokens']:,}", f"{o['total_tokens']:,}")
        
        # Format tool calls
        c_tc = ", ".join(list(set(tc[0] for tc in c["tool_calls"])))
        o_tc = ", ".join(list(set(tc[0] for tc in o["tool_calls"])))
        table.add_row("", "Tools Executed", c_tc or "None", o_tc or "None")
        table.add_row("", "-" * 15, "-" * 15, "-" * 15)

    console.print(table)
    
    # Output to markdown file in artifacts
    md_content = ["# Benchmark Results: Classic vs Orchestrator\n"]
    md_content.append(f"**Model**: {model_name} ({provider_name})\n")
    md_content.append("| Task | Mode | Success | Steps | Time | Tokens | Tools Used | Info |")
    md_content.append("| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |")
    
    for item in results:
        t_name = item["task"]
        c = item["classic"]
        o = item["orchestrator"]
        
        c_tc = ", ".join(list(set(tc[0] for tc in c["tool_calls"])))
        o_tc = ", ".join(list(set(tc[0] for tc in o["tool_calls"])))
        
        md_content.append(f"| {t_name} | Classic | {c['success']} | {c['steps']} | {c['elapsed']:.2f}s | {c['total_tokens']} | {c_tc} | {c['info']} |")
        md_content.append(f"| {t_name} | Orchestrator | {o['success']} | {o['steps']} | {o['elapsed']:.2f}s | {o['total_tokens']} | {o_tc} | {o['info']} |")

    # Save to file
    with open("benchmark_results.md", "w") as f:
        f.write("\n".join(md_content))
    console.print("\nSaved markdown summary to [bold]benchmark_results.md[/bold]")

if __name__ == "__main__":
    main()

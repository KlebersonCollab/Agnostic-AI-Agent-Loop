import os
import json
import re
from typing import List, Tuple
from providers.base import ChatMessage, MessageRole

def estimate_tokens(messages: list) -> int:
    msg_chars = 0
    for msg in messages:
        if getattr(msg, "content", None):
            msg_chars += len(msg.content)
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                if hasattr(tc, "model_dump"):
                    msg_chars += len(json.dumps(tc.model_dump()))
                else:
                    msg_chars += len(json.dumps(tc))
    return (msg_chars + 3) // 4


def _summarize_pruned_messages(pruned_msgs: list) -> str:
    """
    Extracts key information (objective, subagent invocations, test runs, key files/tools used)
    from pruned messages to preserve crucial architectural and operational state.
    """
    subagent_delegations = []
    tests_summary = []
    files_modified = set()
    tools_used = set()

    for msg in pruned_msgs:
        # Check tool calls
        tool_calls = getattr(msg, "tool_calls", None) or []
        for tc in tool_calls:
            name = getattr(tc, "name", "") if hasattr(tc, "name") else tc.get("name", "")
            args = getattr(tc, "arguments", {}) if hasattr(tc, "arguments") else tc.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}

            tools_used.add(name)

            if name in ("spawn_subagent_async", "spawn_subagents_parallel", "invoke_subagent"):
                role = args.get("role_description") or args.get("role") or args.get("task") or "subagent"
                subagent_delegations.append(str(role)[:60])
            elif name in ("write_file", "patch_file", "replace_file_content"):
                fname = args.get("filename") or args.get("TargetFile") or args.get("file_path")
                if fname:
                    files_modified.add(os.path.basename(fname))

        # Check content for test outputs or command executions
        content = getattr(msg, "content", "") or ""
        if "pytest" in content or "test session" in content or "PASSED" in content or "FAILED" in content:
            # Extract test results summary line if found
            match = re.search(r"(=+\s*\d+ passed.*=+|===.*passed.*===)", content, re.IGNORECASE)
            if match:
                tests_summary.append(match.group(0).strip(" ="))
            elif "PASSED" in content:
                tests_summary.append("Tests executed successfully")

    summary_parts = ["📌 **Resumo Estruturado do Contexto Antigo (Podado)**:"]
    
    if subagent_delegations:
        summary_parts.append(f"- **Subagentes / Delegações**: {', '.join(set(subagent_delegations))}")
    if files_modified:
        summary_parts.append(f"- **Arquivos Modificados**: {', '.join(sorted(files_modified))}")
    if tests_summary:
        summary_parts.append(f"- **Status de Testes**: {', '.join(set(tests_summary))}")
    if tools_used:
        summary_parts.append(f"- **Ferramentas Utilizadas**: {', '.join(sorted(tools_used))}")

    summary_parts.append(
        "- **Nota**: O contexto detalhado anterior foi resumido para economizar janelas de token. "
        "Consulte a memória persistente (`search_memory`) para detalhes históricos de execuções passadas."
    )

    return "\n".join(summary_parts)


def handler(messages: list, tools: list):
    # Fetch threshold from env or default to 40,000 tokens
    limit_str = os.environ.get("CONTEXT_PRUNE_LIMIT", "40000")
    try:
        prune_limit = int(limit_str)
    except ValueError:
        prune_limit = 40000
        
    if prune_limit <= 0:
        return messages, tools
        
    current_tokens = estimate_tokens(messages)
    if current_tokens <= prune_limit:
        return messages, tools
        
    # We need to prune
    if len(messages) <= 12:
        return messages, tools
        
    # Identify indices to keep:
    # 1. System prompt (if index 0 is SYSTEM)
    # 2. First user prompt (objective/task declaration)
    keep_start = []
    if messages[0].role == MessageRole.SYSTEM:
        keep_start.append(messages[0])
        if len(messages) > 1 and messages[1].role == MessageRole.USER:
            keep_start.append(messages[1])
    elif messages[0].role == MessageRole.USER:
        keep_start.append(messages[0])
        
    # 3. Last 10 messages (immediate working memory)
    keep_end = messages[-10:]
    
    # 4. Extract pruned section (between start and end)
    start_offset = len(keep_start)
    end_offset = len(messages) - len(keep_end)
    pruned_slice = messages[start_offset:end_offset]

    # Generate rich structured summary placeholder
    summary_content = _summarize_pruned_messages(pruned_slice)
    placeholder = ChatMessage(
        role=MessageRole.SYSTEM,
        content=summary_content
    )
    
    pruned_messages = keep_start + [placeholder] + keep_end
    
    # Optional console log to alert that pruning happened
    try:
        from rich.console import Console
        console = Console()
        console.print(
            f"[bold yellow]⚠️ [Context Pruner][/bold yellow] Contexto podado e resumido com sucesso! "
            f"Tokens: {current_tokens:,} -> {estimate_tokens(pruned_messages):,}"
        )
    except Exception:
        pass
        
    return pruned_messages, tools

import os
import json
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
        # Too few messages to prune safely (e.g., if one single message is huge,
        # we can't prune the middle because there is no middle). Just return.
        return messages, tools
        
    # Identify indices to keep:
    # 1. System prompt (if index 0 is SYSTEM)
    # 2. First user prompt (usually index 1, or index 0 if no system prompt)
    keep_start = []
    if messages[0].role == MessageRole.SYSTEM:
        keep_start.append(messages[0])
        if len(messages) > 1 and messages[1].role == MessageRole.USER:
            keep_start.append(messages[1])
    elif messages[0].role == MessageRole.USER:
        keep_start.append(messages[0])
        
    # 3. Last 10 messages
    keep_end = messages[-10:]
    
    # 4. Generate placeholder for pruned section
    placeholder = ChatMessage(
        role=MessageRole.SYSTEM,
        content="[System: Older conversation history pruned to conserve context window]"
    )
    
    pruned_messages = keep_start + [placeholder] + keep_end
    
    # Optional console log to alert that pruning happened
    try:
        from rich.console import Console
        console = Console()
        console.print(
            f"[bold yellow]⚠️ [Context Pruner][/bold yellow] Histórico de mensagens podado! "
            f"Tokens originais: {current_tokens:,} -> Estimados após poda: {estimate_tokens(pruned_messages):,}"
        )
    except Exception:
        pass
        
    return pruned_messages, tools

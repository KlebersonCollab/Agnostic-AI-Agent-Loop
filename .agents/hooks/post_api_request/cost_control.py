import os
import sys
from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel

# Initialize standard Rich console
console = Console()

# Global ledger variables for the active session
CUMULATIVE_PROMPT_TOKENS = 0
CUMULATIVE_COMPLETION_TOKENS = 0
CUMULATIVE_TOTAL_TOKENS = 0
CUMULATIVE_LATENCY = 0.0
CUMULATIVE_COST_USD = 0.0

# Pricing per 1M tokens (input, output) in USD
PRICING_PER_1M_TOKENS = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.150, 0.600),
    "o1-preview": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    
    # Anthropic
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3.5-sonnet": (3.00, 15.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    
    # Gemini
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-2.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
}

def normalize_model_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower()
    if "/" in name:
        name = name.split("/")[-1]
    return name

def get_pricing(model_name: str):
    norm_name = normalize_model_name(model_name)
    if not norm_name:
        return 0.150, 0.600  # Default fallback
        
    # Check exact match first
    for key, price in PRICING_PER_1M_TOKENS.items():
        if key == norm_name:
            return price
            
    # Check substring match, prioritizing longer keys first
    sorted_keys = sorted(PRICING_PER_1M_TOKENS.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in norm_name or norm_name in key:
            return PRICING_PER_1M_TOKENS[key]
            
    return 0.150, 0.600  # Default fallback to gpt-4o-mini pricing


def reset_ledger():
    global CUMULATIVE_PROMPT_TOKENS, CUMULATIVE_COMPLETION_TOKENS, CUMULATIVE_TOTAL_TOKENS, CUMULATIVE_LATENCY, CUMULATIVE_COST_USD
    CUMULATIVE_PROMPT_TOKENS = 0
    CUMULATIVE_COMPLETION_TOKENS = 0
    CUMULATIVE_TOTAL_TOKENS = 0
    CUMULATIVE_LATENCY = 0.0
    CUMULATIVE_COST_USD = 0.0

def get_ledger():
    return {
        "prompt_tokens": CUMULATIVE_PROMPT_TOKENS,
        "completion_tokens": CUMULATIVE_COMPLETION_TOKENS,
        "total_tokens": CUMULATIVE_TOTAL_TOKENS,
        "latency": CUMULATIVE_LATENCY,
        "cost_usd": CUMULATIVE_COST_USD,
    }

def handler(response_message):
    global CUMULATIVE_PROMPT_TOKENS, CUMULATIVE_COMPLETION_TOKENS, CUMULATIVE_TOTAL_TOKENS, CUMULATIVE_LATENCY, CUMULATIVE_COST_USD
    
    metadata = getattr(response_message, "response_metadata", None) or {}
    
    # Extract token count
    prompt_tokens = metadata.get("prompt_tokens", 0)
    completion_tokens = metadata.get("completion_tokens", 0)
    total_tokens = metadata.get("total_tokens", prompt_tokens + completion_tokens)
    latency = metadata.get("latency", 0.0)
    model_name = metadata.get("model_name", "")
    
    # Calculate incremental cost
    input_price_1m, output_price_1m = get_pricing(model_name)
    incremental_cost = (prompt_tokens * input_price_1m + completion_tokens * output_price_1m) / 1_000_000.0
    
    # Accumulate values
    CUMULATIVE_PROMPT_TOKENS += prompt_tokens
    CUMULATIVE_COMPLETION_TOKENS += completion_tokens
    CUMULATIVE_TOTAL_TOKENS += total_tokens
    CUMULATIVE_LATENCY += latency
    CUMULATIVE_COST_USD += incremental_cost
    
    # Get limits from environment variables
    cost_limit_env = os.environ.get("SESSION_COST_LIMIT")
    token_limit_env = os.environ.get("SESSION_TOKEN_LIMIT")
    
    session_cost_limit = float(cost_limit_env) if cost_limit_env else 0.50
    session_token_limit = int(token_limit_env) if token_limit_env else 100000
    
    # Alert conditions
    cost_exceeded = session_cost_limit > 0 and CUMULATIVE_COST_USD > session_cost_limit
    tokens_exceeded = session_token_limit > 0 and CUMULATIVE_TOTAL_TOKENS > session_token_limit
    
    if cost_exceeded:
        console.print(Panel(
            f"[bold red]⚠️ COST LIMIT EXCEEDED![/bold red]\n"
            f"Current session cost: [bold]${CUMULATIVE_COST_USD:.4f} USD[/bold] (Limit: ${session_cost_limit:.4f} USD)\n"
            f"Prompt tokens: {CUMULATIVE_PROMPT_TOKENS} | Completion tokens: {CUMULATIVE_COMPLETION_TOKENS}\n"
            f"Total cumulative latency: {CUMULATIVE_LATENCY:.2f}s",
            title="[bold yellow]Cost Warning[/bold yellow]",
            border_style="red"
        ))
        
    if tokens_exceeded:
        console.print(Panel(
            f"[bold red]⚠️ TOKEN LIMIT EXCEEDED![/bold red]\n"
            f"Current session tokens: [bold]{CUMULATIVE_TOTAL_TOKENS}[/bold] (Limit: {session_token_limit})\n"
            f"Prompt tokens: {CUMULATIVE_PROMPT_TOKENS} | Completion tokens: {CUMULATIVE_COMPLETION_TOKENS}\n"
            f"Total cumulative latency: {CUMULATIVE_LATENCY:.2f}s",
            title="[bold yellow]Token Warning[/bold yellow]",
            border_style="red"
        ))
        
    return response_message

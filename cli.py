import os
import sys
import json
import argparse
from typing import Dict, Any

from ai_provider import get_provider
from agent import Agent, AgentListener
from tools import TOOLS_METADATA, TOOLS_MAP, set_active_provider

# --- ANSI escape codes for terminal coloring ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_color(text: str, color: str):
    print(f"{color}{text}{Colors.END}")


class ConsoleAgentListener(AgentListener):
    """
    Console/Terminal implementation of the AgentListener.
    Handles user interaction output with colors.
    """
    def on_step_start(self, step: int, max_steps: int):
        print_color(f"--- Step {step} / {max_steps} ---", Colors.HEADER)

    def on_thought(self, thought: str):
        print_color(f"🤖 Thought: {thought}", Colors.GREEN)

    def on_tool_call(self, name: str, arguments: Dict[str, Any], call_id: str):
        print_color(f"🛠️ Tool Call: {name}({json.dumps(arguments)})", Colors.YELLOW)

    def on_tool_output(self, name: str, result: str):
        print_color(f"📥 Tool Output: {result}", Colors.CYAN)
        print()

    def on_error(self, message: str):
        print_color(f"❌ {message}", Colors.RED)

    def on_complete(self):
        print_color("\n🏁 Task Completed!", Colors.HEADER + Colors.BOLD)


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
        default=15,
        help="Maximum loop iterations/steps"
    )

    args = parser.parse_args()

    # Ask interactively if no prompt is provided
    prompt = args.prompt
    if not prompt:
        print_color("🤖 Welcome to the Agnostic AI Agent Loop!", Colors.HEADER + Colors.BOLD)
        print(f"Active Provider: {args.provider} | Model: {args.model}")
        print(f"Tools available: {', '.join(TOOLS_MAP.keys())}\n")
        try:
            prompt = input("Enter your prompt for the agent: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)
            
    if not prompt.strip():
        print("Empty prompt. Exiting.")
        sys.exit(0)

    # Initialize provider
    try:
        provider = get_provider(
            provider_name=args.provider,
            model_name=args.model,
            api_key=args.api_key,
            base_url=args.base_url
        )
    except Exception as e:
        print_color(f"Initialization Error: {e}", Colors.RED)
        sys.exit(1)

    # Set active provider for tools (subagents)
    set_active_provider(provider)

    print_color(f"\n🚀 Starting Agent Session...", Colors.HEADER + Colors.BOLD)
    print_color(f"Objective: {prompt}\n", Colors.CYAN)

    # Setup listener and core Agent
    listener = ConsoleAgentListener()
    agent = Agent(
        provider=provider,
        tools=TOOLS_METADATA,
        tools_map=TOOLS_MAP,
        listener=listener,
        max_steps=args.max_steps
    )
    
    agent.run(prompt)

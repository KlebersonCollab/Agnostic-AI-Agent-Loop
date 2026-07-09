import os
import time
import pytest
from providers import get_provider
from agent import Agent
from tools import TOOLS_METADATA, TOOLS_MAP

# This benchmark test runs real LLM calls and is skipped if no API key is configured.
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY") or ""
has_key = len(OPENROUTER_KEY) > 0 and not OPENROUTER_KEY.startswith("sua_chave")

@pytest.mark.skipif(not has_key, reason="OpenRouter API Key not configured in environment or .env file.")
def test_real_call_single_agent_reasoning():
    """
    Runs a real single-agent ReAct loop that performs mathematical calculation,
    writes the result to a temporary file, and verifies the file exists and is correct.
    """
    provider_name = os.environ.get("AGENT_PROVIDER", "openrouter")
    model_name = os.environ.get("AGENT_MODEL", "tencent/hy3:free")
    
    provider = get_provider(
        provider_name=provider_name,
        model_name=model_name,
        api_key=OPENROUTER_KEY
    )
    
    agent = Agent(
        provider=provider,
        tools=TOOLS_METADATA,
        tools_map=TOOLS_MAP,
        max_steps=10
    )
    
    test_filename = "benchmark_single_agent_result.txt"
    if os.path.exists(test_filename):
        os.remove(test_filename)
        
    prompt = (
        f"Calculate the math expression: 234 * (12 + 88). "
        f"Then write the exact numeric result to a file named '{test_filename}'. "
        f"Do not write any other text in that file, just the result."
    )
    
    start_time = time.time()
    agent.run(prompt)
    duration = time.time() - start_time
    
    try:
        # Check if agent successfully wrote the file
        assert os.path.exists(test_filename), "Agent failed to create the output file."
        with open(test_filename, "r") as f:
            content = f.read().strip()
            
        # Expected calculation: 234 * 100 = 23400
        assert "23400" in content, f"Expected calculation result '23400' in file, got '{content}'"
        print(f"\n✅ Single-agent benchmark passed in {duration:.2f}s! Content: {content}")
        
    finally:
        if os.path.exists(test_filename):
            os.remove(test_filename)


@pytest.mark.skipif(not has_key, reason="OpenRouter API Key not configured in environment or .env file.")
def test_real_call_multi_agent_parallel_spawning():
    """
    Runs a real multi-agent orchestration test where the parent agent spawns
    2 subagents in parallel to read main.py and pyproject.toml respectively,
    summarizes their descriptions, and writes the summary to a file.
    """
    provider_name = os.environ.get("AGENT_PROVIDER", "openrouter")
    model_name = os.environ.get("AGENT_MODEL", "tencent/hy3:free")
    
    provider = get_provider(
        provider_name=provider_name,
        model_name=model_name,
        api_key=OPENROUTER_KEY
    )
    
    # Associate active provider in multi_agent tool module
    from tools import set_active_provider
    set_active_provider(provider)
    
    agent = Agent(
        provider=provider,
        tools=TOOLS_METADATA,
        tools_map=TOOLS_MAP,
        max_steps=8
    )
    
    test_filename = "benchmark_multi_agent_result.txt"
    if os.path.exists(test_filename):
        os.remove(test_filename)
        
    prompt = (
        f"Use parallel subagents to analyze the project structures: "
        f"Have Subagent A read 'main.py' and Subagent B read 'pyproject.toml'. "
        f"Aggregate their descriptions and write the final summary to '{test_filename}'."
    )
    
    start_time = time.time()
    agent.run(prompt)
    duration = time.time() - start_time
    
    try:
        # Check if agent successfully wrote the summary file
        assert os.path.exists(test_filename), "Agent failed to create the summary file."
        with open(test_filename, "r") as f:
            content = f.read().strip()
            
        assert len(content) > 20, "Summary file is empty or too short."
        # Verify that it contains keywords from main.py and pyproject.toml
        assert "main" in content.lower() or "cli" in content.lower(), "Summary should mention main/cli"
        
        print(f"\n✅ Multi-agent benchmark passed in {duration:.2f}s! Content snippet:\n{content[:150]}...")
        
    finally:
        if os.path.exists(test_filename):
            os.remove(test_filename)

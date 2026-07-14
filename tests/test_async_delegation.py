import json
import time
from unittest.mock import MagicMock, patch
from providers.base import ChatMessage, MessageRole, ToolCall
from memory import AgentMemory
from agent import Agent
from tools import get_orchestrator_tools
from tools.multi_agent import (
    spawn_subagent_async,
    check_subagents_status,
    interrupt_subagent,
    _bg_registry,
    set_active_provider
)
from tests.test_agent import MockProvider


def test_allowed_categories_search():
    # Setup database memory
    memory = AgentMemory(db_path=":memory:")
    
    # Pre-populate memory with different categories
    memory.create_session("session_1", "Objective 1")
    memory.add_episode("session_1", 1, "assistant", "Thought content")
    memory.add_episode("session_1", 2, "tool", "Tool output content")
    
    # Save a file outline (category file_outline)
    memory.save_file_outline("test_file.py", "Outline content")
    
    # Test standard search (returns all matches)
    res_all = memory.search("content")
    assert len(res_all) >= 2
    
    # Test search with category whitelist (MemGuard)
    res_filtered = memory.search("content", allowed_categories=["tool_output"])
    assert len(res_filtered) == 1
    assert res_filtered[0]["category"] == "tool_output"
    
    # Test empty category whitelist
    res_empty = memory.search("content", allowed_categories=[])
    assert len(res_empty) == 0


def test_async_delegation_flow():
    # Create responses for a simple two-step subagent ReAct loop
    responses = [
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="I am performing step 1.",
            tool_calls=[
                ToolCall(id="call_1", name="calculate", arguments={"expression": "1 + 1"})
            ]
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Task completed successfully."
        )
    ]
    provider = MockProvider(responses)
    set_active_provider(provider)
    
    # 1. Spawn subagent asynchronously
    res_spawn = spawn_subagent_async(
        role_description="Test Background Worker",
        prompt="Do background work"
    )
    
    data = json.loads(res_spawn)
    assert "subagent_id" in data
    assert data["status"] == "running"
    
    subagent_id = data["subagent_id"]
    
    # Wait briefly for thread execution
    time.sleep(0.5)
    
    # 2. Check status (should be completed since provider responses are immediate)
    res_status = check_subagents_status(subagent_id)
    status_data = json.loads(res_status)
    
    assert status_data["subagent_id"] == subagent_id
    assert status_data["status"] == "completed"
    assert "Task completed successfully." in status_data["final_answer"]
    assert len(status_data["logs"]) > 0


def test_async_delegation_interruption():
    # Setup subagent that has multiple steps so we can interrupt it
    responses = [
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Step 1 thinking...",
            tool_calls=[
                ToolCall(id="call_1", name="calculate", arguments={"expression": "1 + 1"})
            ]
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Step 2 thinking..."
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Step 3 finished."
        )
    ]
    provider = MockProvider(responses)
    set_active_provider(provider)
    
    # Spawn subagent
    res_spawn = spawn_subagent_async(
        role_description="Interruptible Worker",
        prompt="Run a long loop"
    )
    subagent_id = json.loads(res_spawn)["subagent_id"]
    
    # Immediately interrupt it
    res_interrupt = interrupt_subagent(subagent_id)
    interrupt_data = json.loads(res_interrupt)
    
    assert interrupt_data["subagent_id"] == subagent_id
    assert "Cancellation signal" in interrupt_data["message"]
    
    # Wait for the thread to abort the next step
    time.sleep(0.5)
    
    # Check status (should be cancelled)
    res_status = check_subagents_status(subagent_id)
    status_data = json.loads(res_status)
    
    assert status_data["status"] == "cancelled"

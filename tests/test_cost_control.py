import os
import sys
import importlib.util
import pytest
from unittest.mock import MagicMock, patch
from providers.base import ChatMessage, MessageRole
from hooks.manager import HooksManager

# Dynamically import the hook module
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hook_path = os.path.join(project_root, ".agents", "hooks", "post_api_request", "cost_control.py")

spec = importlib.util.spec_from_file_location("cost_control_hook", hook_path)
cost_control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cost_control)

def setup_function():
    # Reset ledger before each test
    cost_control.reset_ledger()

def test_normalize_model_name():
    assert cost_control.normalize_model_name("google/gemini-2.5-flash") == "gemini-2.5-flash"
    assert cost_control.normalize_model_name("openai/gpt-4o-mini") == "gpt-4o-mini"
    assert cost_control.normalize_model_name("claude-3-5-sonnet") == "claude-3-5-sonnet"
    assert cost_control.normalize_model_name("") == ""
    assert cost_control.normalize_model_name(None) == ""

def test_get_pricing():
    # Exists in mapping
    assert cost_control.get_pricing("google/gemini-2.5-flash") == (0.075, 0.30)
    assert cost_control.get_pricing("gpt-4o-mini") == (0.150, 0.600)
    # Substring match
    assert cost_control.get_pricing("anthropic/claude-3.5-sonnet") == (3.00, 15.00)
    # Unmapped model fallback to gpt-4o-mini pricing
    assert cost_control.get_pricing("unknown-model-xyz") == (0.150, 0.600)

def test_ledger_accumulation():
    # Initial state
    assert cost_control.get_ledger()["total_tokens"] == 0
    assert cost_control.get_ledger()["cost_usd"] == 0.0
    
    # First call
    msg1 = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="hello",
        response_metadata={
            "model_name": "gpt-4o-mini",
            "prompt_tokens": 1000,
            "completion_tokens": 200,
            "latency": 1.5
        }
    )
    cost_control.handler(msg1)
    
    ledger = cost_control.get_ledger()
    assert ledger["prompt_tokens"] == 1000
    assert ledger["completion_tokens"] == 200
    assert ledger["total_tokens"] == 1200
    assert ledger["latency"] == 1.5
    # cost = (1000 * 0.150 + 200 * 0.600) / 1,000,000 = (150 + 120) / 1,000,000 = 0.00027
    assert pytest.approx(ledger["cost_usd"]) == 0.00027

    # Second call (accumulated)
    msg2 = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="world",
        response_metadata={
            "model_name": "google/gemini-2.5-flash",
            "prompt_tokens": 2000,
            "completion_tokens": 500,
            "latency": 2.5
        }
    )
    cost_control.handler(msg2)
    
    ledger = cost_control.get_ledger()
    assert ledger["prompt_tokens"] == 3000
    assert ledger["completion_tokens"] == 700
    assert ledger["total_tokens"] == 3700
    assert ledger["latency"] == 4.0
    # incremental cost = (2000 * 0.075 + 500 * 0.30) / 1,000,000 = (150 + 150) / 1,000,000 = 0.0003
    # total cost = 0.00027 + 0.0003 = 0.00057
    assert pytest.approx(ledger["cost_usd"]) == 0.00057

def test_cost_alert_triggered(monkeypatch):
    # Set low limit to trigger alert
    monkeypatch.setenv("SESSION_COST_LIMIT", "0.0001")
    
    msg = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="hello",
        response_metadata={
            "model_name": "gpt-4o-mini",
            "prompt_tokens": 1000,   # cost: 0.00015
            "completion_tokens": 0,
            "latency": 0.5
        }
    )
    
    with patch.object(cost_control.console, 'print') as mock_print:
        cost_control.handler(msg)
        assert mock_print.called
        # Check if the print was related to cost limit
        panel_arg = mock_print.call_args[0][0]
        assert "COST LIMIT EXCEEDED" in str(panel_arg.renderable)

def test_token_alert_triggered(monkeypatch):
    # Set low limit to trigger alert
    monkeypatch.setenv("SESSION_TOKEN_LIMIT", "1000")
    
    msg = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="hello",
        response_metadata={
            "model_name": "gpt-4o-mini",
            "prompt_tokens": 1001,
            "completion_tokens": 0,
            "latency": 0.5
        }
    )
    
    with patch.object(cost_control.console, 'print') as mock_print:
        cost_control.handler(msg)
        assert mock_print.called
        panel_arg = mock_print.call_args[0][0]
        assert "TOKEN LIMIT EXCEEDED" in str(panel_arg.renderable)


def test_hooks_manager_loads_cost_control():
    # Instantiate HooksManager and check if the cost_control hook is loaded
    manager = HooksManager()
    
    # The cost_control.handler should be in the post_api_request list
    handlers = manager.hooks["post_api_request"]
    assert len(handlers) >= 1
    
    # Execute the handlers with a mock response message
    msg = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="hello",
        response_metadata={
            "model_name": "gpt-4o-mini",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "latency": 0.1
        }
    )
    
    res = manager.trigger_post_api_request(msg)
    assert res == msg

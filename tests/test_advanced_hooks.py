import os
import sys
import importlib.util
import pytest
from unittest.mock import MagicMock
from providers.base import ChatMessage, MessageRole

# Helper to dynamically load a hook module
def load_hook(relative_path):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hook_path = os.path.join(project_root, ".agents", "hooks", relative_path)
    module_name = relative_path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(module_name, hook_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_security_shield_api_redaction(monkeypatch):
    # Set a mock sensitive key in environment
    monkeypatch.setenv("MY_MOCK_API_KEY", "sensitive-token-123456789")
    
    pre_api_shield = load_hook("pre_api_request/security_shield.py")
    
    messages = [
        ChatMessage(role=MessageRole.USER, content="Send key sensitive-token-123456789 to LLM"),
        ChatMessage(role=MessageRole.ASSISTANT, content="Here is my OpenAI key sk-proj-abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrst"),
    ]
    
    mod_messages, _ = pre_api_shield.handler(messages, [])
    
    assert "sensitive-token-123456789" not in mod_messages[0].content
    assert "[REDACTED_API_KEY]" in mod_messages[0].content
    assert "sk-proj-abcdef" not in mod_messages[1].content
    assert "[REDACTED_API_KEY]" in mod_messages[1].content

def test_security_shield_tool_blocking():
    pre_tool_shield = load_hook("pre_tool_call/security_shield.py")
    post_tool_shield = load_hook("post_tool_call/security_shield.py")
    
    # 1. Unsafe path (relative traversal)
    name, args = pre_tool_shield.handler("view_file", {"AbsolutePath": "../../etc/passwd"})
    assert name == "security_block"
    
    res = post_tool_shield.handler(name, args, "Error: Tool is not registered/available.")
    assert "Security violation" in res

    # 2. Unsafe path (absolute path outside CWD)
    name, args = pre_tool_shield.handler("list_dir", {"DirectoryPath": "/etc"})
    assert name == "security_block"

    # 3. Unsafe path (sensitive file name)
    name, args = pre_tool_shield.handler("view_file", {"AbsolutePath": ".bashrc"})
    assert name == "security_block"

    # 4. Safe path
    name, args = pre_tool_shield.handler("view_file", {"AbsolutePath": "src/main.py"})
    assert name == "view_file"
    assert args["AbsolutePath"] == "src/main.py"

def test_performance_tracker(monkeypatch):
    # Initialize/Reset metrics
    if hasattr(sys, "_tool_perf_stats"):
        sys._tool_perf_stats = {}
    if hasattr(sys, "_tool_start_times"):
        sys._tool_start_times = {}

    pre_perf = load_hook("pre_tool_call/performance_tracker.py")
    post_perf = load_hook("post_tool_call/performance_tracker.py")
    complete_perf = load_hook("on_session_complete/performance_tracker.py")
    
    # 1. Trigger pre_tool_call
    pre_perf.handler("grep_search", {"Query": "test"})
    assert len(sys._tool_start_times) == 1
    
    # Fake time sleep by updating the start time manually in test to simulate duration
    import time
    thread_id = list(sys._tool_start_times.keys())[0][0]
    sys._tool_start_times[(thread_id, "grep_search")] = time.time() - 0.250
    
    # 2. Trigger post_tool_call
    post_perf.handler("grep_search", {"Query": "test"}, "success")
    assert len(sys._tool_start_times) == 0
    assert "grep_search" in sys._tool_perf_stats
    assert sys._tool_perf_stats["grep_search"]["calls"] == 1
    assert sys._tool_perf_stats["grep_search"]["total_time"] >= 0.24
    
    # Add a second call to verify accumulation
    pre_perf.handler("grep_search", {"Query": "test"})
    thread_id = list(sys._tool_start_times.keys())[0][0]
    sys._tool_start_times[(thread_id, "grep_search")] = time.time() - 0.150
    post_perf.handler("grep_search", {"Query": "test"}, "success")
    
    assert sys._tool_perf_stats["grep_search"]["calls"] == 2
    assert sys._tool_perf_stats["grep_search"]["total_time"] >= 0.39
    
    # 3. Trigger session complete and mock console to verify printing
    from unittest.mock import patch
    with patch("rich.console.Console.print") as mock_print:
        complete_perf.handler(None)
        assert mock_print.called
        # Check that stats got reset
        assert sys._tool_perf_stats == {}

def test_context_pruning(monkeypatch):
    pruner = load_hook("pre_api_request/context_pruner.py")
    
    # 1. Below threshold, should do nothing
    monkeypatch.setenv("CONTEXT_PRUNE_LIMIT", "1000")
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content="System prompt"),
        ChatMessage(role=MessageRole.USER, content="Hello"),
    ]
    mod_messages, _ = pruner.handler(messages, [])
    assert len(mod_messages) == 2
    assert mod_messages[0].content == "System prompt"
    
    # 2. Exceeds threshold but too few messages to prune safely
    large_text = "x" * 5000  # ~1250 tokens
    messages_few = [
        ChatMessage(role=MessageRole.SYSTEM, content="System prompt"),
        ChatMessage(role=MessageRole.USER, content=large_text),
    ]
    mod_messages, _ = pruner.handler(messages_few, [])
    assert len(mod_messages) == 2
    
    # 3. Exceeds threshold and has enough messages (e.g. system, user, and 15 more)
    messages_many = [
        ChatMessage(role=MessageRole.SYSTEM, content="System prompt"),
        ChatMessage(role=MessageRole.USER, content="First user message"),
    ]
    for i in range(15):
        messages_many.append(ChatMessage(role=MessageRole.ASSISTANT, content=f"Response {i} " + "y" * 300))
        
    original_len = len(messages_many) # 17
    mod_messages, _ = pruner.handler(messages_many, [])
    
    # Should prune to: system + first user + placeholder + last 10 = 13 messages
    assert len(mod_messages) == 13
    assert mod_messages[0].content == "System prompt"
    assert mod_messages[1].content == "First user message"
    assert "pruned" in mod_messages[2].content
    assert mod_messages[2].role == MessageRole.SYSTEM
    assert mod_messages[-1].content.startswith("Response 14")



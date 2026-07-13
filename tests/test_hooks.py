import os
import sys
import pytest
from unittest.mock import MagicMock
from providers.base import ChatMessage, MessageRole
from hooks.manager import HooksManager

def _write_hook(directory, name, content):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_hooks_manager_dynamic_loading(tmp_path):
    # Setup temporary hooks directory structure
    hooks_dir = os.path.join(tmp_path, "hooks")
    
    # 1. on_session_start hook
    start_dir = os.path.join(hooks_dir, "on_session_start")
    _write_hook(start_dir, "init.py", """
calls = []
def handler(agent):
    agent.init_flag = True
""")

    # 2. pre_tool_call hook
    pre_tool_dir = os.path.join(hooks_dir, "pre_tool_call")
    _write_hook(pre_tool_dir, "modify.py", """
def handler(name, args):
    if name == "calc":
        args["expression"] = "2+2"
        return name, args
""")

    # 3. post_tool_call hook
    post_tool_dir = os.path.join(hooks_dir, "post_tool_call")
    _write_hook(post_tool_dir, "append.py", """
def handler(name, args, result):
    return result + " [hooked]"
""")

    # 4. on_tool_error hook
    tool_err_dir = os.path.join(hooks_dir, "on_tool_error")
    _write_hook(tool_err_dir, "recover.py", """
def handler(name, args, exc):
    return "recovered"
""")

    # Instantiate manager
    manager = HooksManager(hooks_dir=hooks_dir)
    
    # Verify loaded hooks count
    assert len(manager.hooks["on_session_start"]) == 1
    assert len(manager.hooks["pre_tool_call"]) == 1
    assert len(manager.hooks["post_tool_call"]) == 1
    assert len(manager.hooks["on_tool_error"]) == 1

    # Test Session Start Trigger
    mock_agent = MagicMock()
    mock_agent.init_flag = False
    manager.trigger_on_session_start(mock_agent)
    assert mock_agent.init_flag is True

    # Test Pre-Tool Call Trigger
    name, args = manager.trigger_pre_tool_call("calc", {"expression": "1+1"})
    assert name == "calc"
    assert args["expression"] == "2+2"

    # Test Post-Tool Call Trigger
    res = manager.trigger_post_tool_call("calc", {"expression": "2+2"}, "4")
    assert res == "4 [hooked]"

    # Test On-Tool Error Trigger
    err_res = manager.trigger_on_tool_error("calc", {}, ValueError("crash"))
    assert err_res == "recovered"


def test_hooks_api_request_triggers(tmp_path):
    hooks_dir = os.path.join(tmp_path, "hooks")
    
    # 5. pre_api_request hook
    pre_api_dir = os.path.join(hooks_dir, "pre_api_request")
    _write_hook(pre_api_dir, "pre_req.py", """
def handler(messages, tools):
    messages.append("added_system")
    return messages, tools
""")

    # 6. post_api_request hook
    post_api_dir = os.path.join(hooks_dir, "post_api_request")
    _write_hook(post_api_dir, "post_req.py", """
def handler(response):
    response.content = "hooked response"
    return response
""")

    manager = HooksManager(hooks_dir=hooks_dir)
    
    # Test Pre API
    msg = ["initial"]
    messages, tools = manager.trigger_pre_api_request(msg, None)
    assert messages == ["initial", "added_system"]

    # Test Post API
    resp = ChatMessage(role=MessageRole.ASSISTANT, content="initial response")
    new_resp = manager.trigger_post_api_request(resp)
    assert new_resp.content == "hooked response"


def test_remaining_triggers(tmp_path):
    hooks_dir = os.path.join(tmp_path, "hooks")
    
    # 7. on_session_complete
    _write_hook(os.path.join(hooks_dir, "on_session_complete"), "h.py", """
def handler(agent):
    agent.completed = True
""")
    # 8. on_session_clear
    _write_hook(os.path.join(hooks_dir, "on_session_clear"), "h.py", """
def handler(agent):
    agent.cleared = True
""")
    # 9. pre_step
    _write_hook(os.path.join(hooks_dir, "pre_step"), "h.py", """
def handler(agent, step):
    agent.steps.append(f"pre_{step}")
""")
    # 10. post_step
    _write_hook(os.path.join(hooks_dir, "post_step"), "h.py", """
def handler(agent, step):
    agent.steps.append(f"post_{step}")
""")
    # 11. on_error
    _write_hook(os.path.join(hooks_dir, "on_error"), "h.py", """
def handler(agent, err):
    agent.last_error = err
""")

    manager = HooksManager(hooks_dir=hooks_dir)
    mock_agent = MagicMock()
    mock_agent.steps = []
    mock_agent.completed = False
    mock_agent.cleared = False
    mock_agent.last_error = None

    manager.trigger_on_session_complete(mock_agent)
    assert mock_agent.completed is True

    manager.trigger_on_session_clear(mock_agent)
    assert mock_agent.cleared is True

    manager.trigger_pre_step(mock_agent, 1)
    assert mock_agent.steps == ["pre_1"]

    manager.trigger_post_step(mock_agent, 1)
    assert mock_agent.steps == ["pre_1", "post_1"]

    manager.trigger_on_error(mock_agent, "fatal issue")
    assert mock_agent.last_error == "fatal issue"

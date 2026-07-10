from context.references import parse_context_references, ContextReference, _is_path_safe, preprocess_context_references
import os
import subprocess
import urllib.request
from unittest.mock import MagicMock, patch

def test_parse_simple_references():
    prompt = "Please look at @diff and @staged"
    refs = parse_context_references(prompt)
    assert len(refs) == 2
    assert refs[0].kind == "diff"
    assert refs[1].kind == "staged"

def test_parse_file_references():
    prompt = "Check @file:agent.py and @file:\"context/builder.py\":10-20"
    refs = parse_context_references(prompt)
    assert len(refs) == 2
    assert refs[0].kind == "file"
    assert refs[0].target == "agent.py"
    assert refs[0].line_start is None
    assert refs[0].line_end is None

    assert refs[1].kind == "file"
    assert refs[1].target == "context/builder.py"
    assert refs[1].line_start == 10
    assert refs[1].line_end == 20

def test_parse_url_references():
    prompt = "Analyze @url:https://example.com/status."
    refs = parse_context_references(prompt)
    assert len(refs) == 1
    assert refs[0].kind == "url"
    assert refs[0].target == "https://example.com/status"

def test_is_path_safe():
    cwd = "/home/user/workspace"
    # Safe paths
    safe, err = _is_path_safe("agent.py", cwd)
    assert safe
    assert err is None

    safe, err = _is_path_safe("context/builder.py", cwd)
    assert safe

    # Traversal unsafe path
    safe, err = _is_path_safe("../../etc/passwd", cwd)
    assert not safe
    assert "Path traversal" in err

    # Absolute unsafe path
    safe, err = _is_path_safe("/etc/passwd", cwd)
    assert not safe
    assert "Path traversal" in err

    # Sensitive files
    safe, err = _is_path_safe(".env", cwd)
    assert not safe
    assert "sensitive blocklist" in err

    safe, err = _is_path_safe("subfolder/.npmrc", cwd)
    assert not safe
    assert "sensitive blocklist" in err

    # Sensitive directories
    safe, err = _is_path_safe(".ssh/id_rsa", cwd)
    assert not safe
    assert "sensitive blocklist" in err

def test_preprocess_file_references(tmp_path):
    cwd = str(tmp_path)
    file_path = tmp_path / "hello.txt"
    file_path.write_text("line 1\nline 2\nline 3\nline 4\n")

    # Full file read
    res = preprocess_context_references("Read this: @file:hello.txt", cwd=cwd)
    assert not res.blocked
    assert res.expanded
    assert "Read this:" in res.message
    assert "### File Reference: hello.txt" in res.message
    assert "line 1\nline 2" in res.message

    # Sliced file read
    res_sliced = preprocess_context_references("Read slice: @file:hello.txt:2-3", cwd=cwd)
    assert not res_sliced.blocked
    assert res_sliced.expanded
    assert "lines 2-3" in res_sliced.message
    assert "line 2\nline 3" in res_sliced.message
    assert "line 1" not in res_sliced.message.split("Context References")[1]

def test_preprocess_blocked_file(tmp_path):
    cwd = str(tmp_path)
    res = preprocess_context_references("Read: @file:.env", cwd=cwd)
    assert not res.blocked
    assert "Warning: Blocked file reference" in res.message

def test_preprocess_git_diff(tmp_path):
    cwd = str(tmp_path)
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "diff content here"
        mock_run.return_value = mock_res

        res = preprocess_context_references("Check @diff", cwd=cwd)
        assert res.expanded
        assert "### Git Diff" in res.message
        assert "diff content here" in res.message

def test_preprocess_url(tmp_path):
    cwd = str(tmp_path)
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"<html><body>Hello from HTML</body></html>"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = preprocess_context_references("Visit @url:https://example.org", cwd=cwd)
        assert res.expanded
        assert "Hello from HTML" in res.message

def test_preprocess_token_limits(tmp_path):
    cwd = str(tmp_path)
    file_path = tmp_path / "big.txt"
    file_path.write_text("A" * 800)  # ~200 tokens

    # Large content relative to small budget (100 tokens context window -> limit 50 tokens)
    res = preprocess_context_references("Read: @file:big.txt", cwd=cwd, context_length=100)
    assert res.blocked
    assert not res.expanded
    assert "@ context injection refused" in res.warnings[0]

def test_agent_integration(tmp_path):
    from providers.base import BaseLLMProvider, ChatMessage, MessageRole
    from agent import Agent
    
    class DummyProvider(BaseLLMProvider):
        def __init__(self):
            super().__init__("dummy-model")
            self.last_messages = None
        def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
            self.last_messages = messages
            return ChatMessage(role=MessageRole.ASSISTANT, content="Done")

    provider = DummyProvider()
    agent = Agent(provider=provider, tools=[], tools_map={})
    
    cwd = str(tmp_path)
    file_path = tmp_path / "info.txt"
    file_path.write_text("Secret context data")
    
    with patch("os.getcwd", return_value=cwd):
        agent.run("Tell me: @file:info.txt")
        
    assert len(agent.history) >= 2
    user_msg = agent.history[1].content
    assert "Secret context data" in user_msg
    assert "### File Reference: info.txt" in user_msg




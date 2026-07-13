import pytest
import os
import json
from unittest.mock import MagicMock, patch, mock_open
from context.mcp import MCPManager
from agent import Agent
from providers.base import BaseLLMProvider, ChatMessage, MessageRole, ToolDefinition
from mcp.types import Tool, TextContent, CallToolResult

class DummyProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__("dummy-model")
    def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
        return ChatMessage(role=MessageRole.ASSISTANT, content="Done")

@pytest.fixture
def agent():
    provider = DummyProvider()
    return Agent(provider=provider, tools=[], tools_map={})

def test_mcp_manager_lifecycle(agent, tmp_path):
    mcp_dir = tmp_path / ".agents" / "mcp"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    
    # Write mock config file
    config_data = {
        "mcpServers": {
            "mock-server": {
                "command": "echo",
                "args": ["hello"]
            }
        }
    }
    config_file = mcp_dir / "mock-server.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    manager = MCPManager(agent=agent, config_dirs=[str(mcp_dir)])
    
    # Define mock tool and call results
    mock_tool = Tool(
        name="hello_tool",
        description="Prints hello",
        inputSchema={"type": "object", "properties": {"name": {"type": "string"}}}
    )
    
    mock_result = CallToolResult(
        content=[TextContent(type="text", text="Hello mock!")],
        is_error=False
    )
    
    # Custom run_sync mock to bypass real subprocess/network stdio connection
    def mock_run_sync(coro):
        import asyncio
        coro_name = str(coro)
        if asyncio.iscoroutine(coro):
            coro.close()
        if "list_tools" in coro_name:
            return [mock_tool]
        elif "call_tool" in coro_name:
            return mock_result
        return None

    manager.run_sync = mock_run_sync

    # Patch Client, and mock builtins.open returning JSON
    m = mock_open(read_data=json.dumps(config_data))
    with patch("context.mcp.Client") as MockClient, \
         patch("os.path.exists", return_value=True), \
         patch("builtins.open", m):
         
         # 1. Load server
         load_res = manager.load_mcp("mock-server")
         assert "loaded successfully" in load_res
         assert "mock-server" in manager.active_clients
         assert "hello_tool" in manager.tools_metadata["mock-server"]
         
         # 2. Load tool
         load_tool_res = manager.load_mcp_tool("mock-server", "hello_tool")
         assert "Exposed tool 'hello_tool'" in load_tool_res
         assert len(agent.tools) == 1
         assert agent.tools[0].name == "hello_tool"
         assert "hello_tool" in agent.tools_map
         
         # 3. Call tool
         call_res = agent.tools_map["hello_tool"](name="World")
         assert call_res == "Hello mock!"
         
         # 4. Unload tool
         unload_tool_res = manager.unload_mcp_tool("mock-server", "hello_tool")
         assert "Unloaded tool 'hello_tool'" in unload_tool_res
         assert len(agent.tools) == 0
         assert "hello_tool" not in agent.tools_map
         
         # 5. Unload server
         unload_res = manager.unload_mcp("mock-server")
         assert "Unloaded MCP server 'mock-server'" in unload_res
         assert "mock-server" not in manager.active_clients
         
         manager.cleanup()

def test_mcp_config_caching_and_invalidation(agent, tmp_path):
    # Setup test config files in tmp_path
    config_a = {"mcpServers": {"server-a": {"command": "echo", "args": ["A"]}}}
    config_b = {"mcpServers": {"server-b": {"command": "echo", "args": ["B"]}}}
    
    file_a = tmp_path / "server-a.json"
    with open(file_a, "w", encoding="utf-8") as f:
        json.dump(config_a, f)
        
    # Initialize manager with custom config directory
    manager = MCPManager(agent=agent, config_dirs=[str(tmp_path)])
    
    try:
        # 1. Startup pre-caching check
        available = manager.get_available_mcp_servers()
        assert "server-a" in available
        assert available["server-a"]["config"]["mcpServers"]["server-a"]["args"] == ["A"]
        
        # 2. Invalidation upon modification
        config_a_updated = {"mcpServers": {"server-a": {"command": "echo", "args": ["A_updated"]}}}
        # Write and force update mtime
        with open(file_a, "w", encoding="utf-8") as f:
            json.dump(config_a_updated, f)
        
        # Modify file mtime forward to ensure mtime change is detected
        curr_mtime = os.path.getmtime(file_a)
        os.utime(file_a, (curr_mtime + 5, curr_mtime + 5))
        
        manager.check_and_update_cache()
        available = manager.get_available_mcp_servers()
        assert available["server-a"]["config"]["mcpServers"]["server-a"]["args"] == ["A_updated"]
        
        # 3. Dynamic addition check
        file_b = tmp_path / "server-b.json"
        with open(file_b, "w", encoding="utf-8") as f:
            json.dump(config_b, f)
            
        manager.check_and_update_cache()
        available = manager.get_available_mcp_servers()
        assert "server-b" in available
        assert available["server-b"]["config"]["mcpServers"]["server-b"]["args"] == ["B"]
        
        # 4. Dynamic removal check
        os.remove(file_a)
        manager.check_and_update_cache()
        available = manager.get_available_mcp_servers()
        assert "server-a" not in available
        assert "server-b" in available
        
    finally:
        manager.cleanup()

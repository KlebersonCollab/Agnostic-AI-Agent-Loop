# SDD Technical Plan: Model Context Protocol (MCP) Client (mcp_client)

This document describes the technical implementation plan for the Model Context Protocol (MCP) client.

---

## 1. Architecture Overview
We will implement the `context/mcp.py` module to manage stdio MCP servers using `fastmcp`. The `Agent` will instantiate this manager and expose tools to control it.

```
context/
├── __init__.py
├── builder.py
├── references.py
├── breakdown.py
└── mcp.py           # New module
```

---

## 2. Technical Design

### Sync/Async execution helper
Since `Agent.run()` is synchronous, and `fastmcp` is asynchronous, we will use a robust thread-safe runner:
```python
import asyncio
import threading
from concurrent.futures import Future

def run_async(coro):
    def target(f: Future):
        try:
            res = asyncio.run(coro)
            f.set_result(res)
        except Exception as e:
            f.set_exception(e)
            
    fut = Future()
    t = threading.Thread(target=target)
    t.start()
    t.join()
    return fut.result()
```

### The `MCPManager` (`context/mcp.py`)
```python
import os
import json
from fastmcp import Client
from providers.base import ToolDefinition

class MCPManager:
    def __init__(self, agent):
        self.agent = agent
        self.active_clients = {}  # server_name -> Client
        self.tools_metadata = {}  # server_name -> Dict[tool_name, mcp.types.Tool]
        self.loaded_tools = {}    # server_name -> Set[tool_name]
        
    def load_mcp(self, server_name: str) -> str:
        if server_name in self.active_clients:
            return f"MCP server '{server_name}' is already loaded."
            
        # Locate config file
        config_path = os.path.join(os.getcwd(), ".agents", "mcp", f"{server_name}.json")
        if not os.path.exists(config_path):
            # Try global fallback
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".agents", "mcp", f"{server_name}.json")
            if not os.path.exists(config_path):
                return f"Error: Configuration file for MCP '{server_name}' not found."
                
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)
            
            client = Client(config_dict)
            # Run connection asynchronously
            run_async(client.__aenter__())
            self.active_clients[server_name] = client
            self.loaded_tools[server_name] = set()
            
            # Fetch tools
            tools = run_async(client.list_tools())
            self.tools_metadata[server_name] = {t.name: t for t in tools}
            
            tool_list_str = "\n".join([f"- {t.name}: {t.description}" for t in tools])
            return (
                f"Success: MCP server '{server_name}' loaded.\n"
                f"Available tools (NOT loaded yet):\n{tool_list_str}\n\n"
                f"To expose a tool to your active set, call `load_mcp_tool('{server_name}', 'tool_name')`."
            )
        except Exception as e:
            return f"Error loading MCP server '{server_name}': {e}"
            
    def load_mcp_tool(self, server_name: str, tool_name: str) -> str:
        if server_name not in self.active_clients:
            return f"Error: MCP server '{server_name}' is not loaded. Call `load_mcp('{server_name}')` first."
            
        mcp_tools = self.tools_metadata.get(server_name, {})
        if tool_name not in mcp_tools:
            return f"Error: Tool '{tool_name}' not found on server '{server_name}'."
            
        if tool_name in self.loaded_tools[server_name]:
            return f"Tool '{tool_name}' is already loaded."
            
        t = mcp_tools[tool_name]
        
        # Build ToolDefinition
        tool_def = ToolDefinition(
            name=t.name,
            description=t.description or "No description available.",
            parameters=t.inputSchema or {"type": "object", "properties": {}}
        )
        
        # Add to agent's tools list
        self.agent.tools.append(tool_def)
        
        # Create execution wrapper
        def make_wrapper(s_name, t_name):
            def wrapper(**kwargs):
                client = self.active_clients[s_name]
                res = run_async(client.call_tool(t_name, kwargs))
                
                # Format output string
                text_results = []
                for item in res.content:
                    if hasattr(item, "text") and item.text:
                        text_results.append(item.text)
                    elif hasattr(item, "data") and item.data:
                        text_results.append(str(item.data))
                    else:
                        text_results.append(str(item))
                
                final_str = "\n".join(text_results)
                if getattr(res, "is_error", False):
                    return f"Error: {final_str}"
                return final_str
            return wrapper
            
        self.agent.tools_map[t.name] = make_wrapper(server_name, t.name)
        self.loaded_tools[server_name].add(t.name)
        
        return f"Success: Exposed tool '{tool_name}' from server '{server_name}' to your active toolset."

    def unload_mcp_tool(self, server_name: str, tool_name: str) -> str:
        if server_name not in self.active_clients:
            return f"Error: MCP server '{server_name}' is not active."
        if tool_name not in self.loaded_tools.get(server_name, set()):
            return f"Error: Tool '{tool_name}' is not loaded."
            
        # Remove from agent tools list
        self.agent.tools = [t for t in self.agent.tools if t.name != tool_name]
        # Remove from tools_map
        if tool_name in self.agent.tools_map:
            del self.agent.tools_map[tool_name]
            
        self.loaded_tools[server_name].remove(tool_name)
        return f"Success: Unloaded tool '{tool_name}' from your active toolset."
        
    def unload_mcp(self, server_name: str) -> str:
        if server_name not in self.active_clients:
            return f"Error: MCP server '{server_name}' is not active."
            
        # Unload all active tools of this server
        for t_name in list(self.loaded_tools.get(server_name, set())):
            self.unload_mcp_tool(server_name, t_name)
            
        client = self.active_clients[server_name]
        try:
            run_async(client.__aexit__(None, None, None))
        except Exception:
            pass
            
        del self.active_clients[server_name]
        del self.loaded_tools[server_name]
        if server_name in self.tools_metadata:
            del self.tools_metadata[server_name]
            
        return f"Success: Unloaded MCP server '{server_name}' and shut down subprocess."
        
    def cleanup(self):
        # Shut down all servers safely
        for name in list(self.active_clients.keys()):
            self.unload_mcp(name)
```

---

## 3. Implementation Strategy

### Interception in `Agent.run`
We will register `load_mcp`, `unload_mcp`, `load_mcp_tool`, `unload_mcp_tool` in `tools/__init__.py` with dummy lambda handlers.
In `agent.py`, we will intercept these calls in the ReAct loop:
```python
                    if tool_name == "load_mcp":
                        s_name = tool_args.get("server_name")
                        result = self.mcp_manager.load_mcp(s_name)
                    elif tool_name == "unload_mcp":
                        s_name = tool_args.get("server_name")
                        result = self.mcp_manager.unload_mcp(s_name)
                    elif tool_name == "load_mcp_tool":
                        s_name = tool_args.get("server_name")
                        t_name = tool_args.get("tool_name")
                        result = self.mcp_manager.load_mcp_tool(s_name, t_name)
                    elif tool_name == "unload_mcp_tool":
                        s_name = tool_args.get("server_name")
                        t_name = tool_args.get("tool_name")
                        result = self.mcp_manager.unload_mcp_tool(s_name, t_name)
```

### Safety: Cleanup in `Agent.run()` finally block
```python
    def run(self, user_prompt: str):
        # Initialize mcp_manager if not present
        if not hasattr(self, "mcp_manager"):
            self.mcp_manager = MCPManager(self)
        try:
            # ... react loop ...
        finally:
            self.mcp_manager.cleanup()
```

---

## 4. Status
- **NEEDS_REVIEW**

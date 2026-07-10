from __future__ import annotations
import asyncio
import os
import json
import threading
from concurrent.futures import Future
from typing import Dict, Any, Set, List
from fastmcp import Client
from providers.base import ToolDefinition

# Thread-safe async runner helper
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

class MCPManager:
    """
    Manages Model Context Protocol (MCP) server lifecycles, subprocess clients,
    and dynamic tool registration/unregistration.
    """
    def __init__(self, agent):
        self.agent = agent
        self.active_clients: Dict[str, Client] = {}
        self.tools_metadata: Dict[str, Dict[str, Any]] = {}
        self.loaded_tools: Dict[str, Set[str]] = {}

    def load_mcp(self, server_name: str) -> str:
        """
        Loads and connects to an MCP server, reading command config from .agents/mcp/{server_name}.json.
        Lists available tools without exposing them to the agent's prompt schema.
        """
        if server_name in self.active_clients:
            return f"MCP server '{server_name}' is already loaded and active."

        # Search for configuration file in workspace `.agents/mcp/`
        config_path = os.path.abspath(os.path.join(os.getcwd(), ".agents", "mcp", f"{server_name}.json"))
        if not os.path.exists(config_path):
            # Fallback to package root
            package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.abspath(os.path.join(package_root, ".agents", "mcp", f"{server_name}.json"))
            if not os.path.exists(config_path):
                return f"Error: MCP configuration file for '{server_name}' not found at {config_path}."

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)

            client = Client(config_dict)
            
            # Start client session asynchronously in a background loop
            run_async(client.__aenter__())
            self.active_clients[server_name] = client
            self.loaded_tools[server_name] = set()

            # Retrieve available tools from server
            tools = run_async(client.list_tools())
            self.tools_metadata[server_name] = {t.name: t for t in tools}

            tool_list_str = "\n".join([f"- {t.name}: {t.description}" for t in tools]) if tools else "No tools available."
            return (
                f"Success: MCP server '{server_name}' loaded successfully.\n"
                f"Available tools (NOT loaded into your context yet):\n{tool_list_str}\n\n"
                f"To expose a tool to your active tools schema, you MUST call `load_mcp_tool('{server_name}', 'tool_name')`."
            )
        except Exception as e:
            # Clean up if failed during initialization
            if server_name in self.active_clients:
                self.unload_mcp(server_name)
            return f"Error connecting to MCP server '{server_name}': {e}"

    def load_mcp_tool(self, server_name: str, tool_name: str) -> str:
        """
        Dynamically registers/exposes a tool from a loaded MCP server into the agent's active tools.
        """
        if server_name not in self.active_clients:
            return f"Error: MCP server '{server_name}' is not loaded. Call `load_mcp('{server_name}')` first."

        server_tools = self.tools_metadata.get(server_name, {})
        if tool_name not in server_tools:
            return f"Error: Tool '{tool_name}' not found on MCP server '{server_name}'."

        if tool_name in self.loaded_tools[server_name]:
            return f"Tool '{tool_name}' from server '{server_name}' is already loaded."

        t = server_tools[tool_name]

        # Construct ToolDefinition schema
        tool_def = ToolDefinition(
            name=t.name,
            description=t.description or "No description available.",
            parameters=t.inputSchema or {"type": "object", "properties": {}}
        )

        # Dynamic injection into the agent
        self.agent.tools.append(tool_def)

        # Mapped wrapper execution handler
        def make_wrapper(s_name, t_name):
            def wrapper(**kwargs):
                client = self.active_clients.get(s_name)
                if not client:
                    return f"Error: MCP server '{s_name}' is not currently running."
                
                # Execute async call
                res = run_async(client.call_tool(t_name, kwargs))
                
                # Format response contents
                text_results = []
                for item in getattr(res, "content", []):
                    if getattr(item, "type", None) == "text" and getattr(item, "text", None):
                        text_results.append(item.text)
                    elif hasattr(item, "text") and item.text:
                        text_results.append(item.text)
                    elif hasattr(item, "data") and item.data:
                        text_results.append(str(item.data))
                    else:
                        text_results.append(str(item))

                final_text = "\n".join(text_results)
                if getattr(res, "is_error", False):
                    return f"Error: {final_text}"
                return final_text
            return wrapper

        self.agent.tools_map[t.name] = make_wrapper(server_name, t.name)
        self.loaded_tools[server_name].add(t.name)

        return f"Success: Exposed tool '{tool_name}' from server '{server_name}' to your active toolset."

    def unload_mcp_tool(self, server_name: str, tool_name: str) -> str:
        """
        Dynamically unregisters/removes a tool from the agent's active tools to budget context space.
        """
        if server_name not in self.active_clients:
            return f"Error: MCP server '{server_name}' is not loaded."

        if tool_name not in self.loaded_tools.get(server_name, set()):
            return f"Error: Tool '{tool_name}' from server '{server_name}' is not loaded."

        # Remove from agent's tools list
        self.agent.tools = [t for t in self.agent.tools if t.name != tool_name]
        
        # Remove from tools_map
        if tool_name in self.agent.tools_map:
            del self.agent.tools_map[tool_name]

        self.loaded_tools[server_name].remove(tool_name)
        return f"Success: Unloaded tool '{tool_name}' from your active toolset."

    def unload_mcp(self, server_name: str) -> str:
        """
        Closes connection, shuts down the server process, and cleans up all active tools of this server.
        """
        if server_name not in self.active_clients:
            return f"Error: MCP server '{server_name}' is not active."

        # Unregister all currently loaded tools of this server
        for t_name in list(self.loaded_tools.get(server_name, set())):
            self.unload_mcp_tool(server_name, t_name)

        client = self.active_clients[server_name]
        try:
            # Terminate subprocess and clean connection context
            run_async(client.__aexit__(None, None, None))
        except Exception:
            pass

        del self.active_clients[server_name]
        del self.loaded_tools[server_name]
        if server_name in self.tools_metadata:
            del self.tools_metadata[server_name]

        return f"Success: Unloaded MCP server '{server_name}' and shut down subprocess cleanly."

    def cleanup(self):
        """
        Clean up all active servers and subprocesses (crucial to prevent process leaks).
        """
        active_names = list(self.active_clients.keys())
        for name in active_names:
            self.unload_mcp(name)

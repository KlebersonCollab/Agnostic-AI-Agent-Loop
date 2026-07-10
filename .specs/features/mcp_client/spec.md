# SDD Specification: Model Context Protocol (MCP) Client (mcp_client)

This specification defines the functional requirements and business logic for the Model Context Protocol (MCP) client integration.

---

## 1. Context & Goals

### Problem Statement
The agent has access to local Python-based tools. However, to interact with modern devtools, browsers (e.g. Playwright), databases, or external APIs, we need a standard, extensible way to integrate third-party tools. The industry standard is the Model Context Protocol (MCP).

### Goal
Implement an MCP client module. The agent will read JSON configs from `.agents/mcp/{server_name}.json` and spawn local stdio MCP servers in the background. To protect the LLM context window from being flooded by dozens of unused tools, the agent will have the ability to load/unload MCP servers and selectively register specific tools from those servers.

### Scope
* **Included:**
  * Reading configs from `.agents/mcp/{server_name}.json`.
  * Background lifecycle management of stdio MCP servers via the `fastmcp` client library.
  * Internal tools:
    * `load_mcp(server_name: str)`: Connects to server and queries available tools.
    * `unload_mcp(server_name: str)`: Disconnects and terminates server.
    * `load_mcp_tool(server_name: str, tool_name: str)`: Exposes a single tool schema to the LLM.
    * `unload_mcp_tool(server_name: str, tool_name: str)`: Removes the tool schema.
  * In-place modification of `Agent.tools` and `Agent.tools_map` to dynamically support loaded MCP tools.
  * Clean termination of all spawned processes upon agent exit or completion.
* **NOT Included:**
  * SSE/HTTP remote server authentication flows. Stdio subprocess execution is the core target.

---

## 2. Requirements (BDD Scenarios)

### Feature: Dynamic MCP Server and Tool Management

**Scenario 1: Loading an MCP server**
- **Given** The server configuration `.agents/mcp/chrome-devtools.json` exists.
- **When** The agent executes `load_mcp("chrome-devtools")`.
- **Then** The subprocess starts, the client connects, and retrieves available tools `['evaluate', 'navigate', 'screenshot']` without exposing them to the prompt.

**Scenario 2: Loading a specific MCP tool**
- **Given** The server `chrome-devtools` is loaded.
- **When** The agent executes `load_mcp_tool("chrome-devtools", "screenshot")`.
- **Then** The tool `screenshot` is appended to `agent.tools` as a `ToolDefinition`, and `agent.tools_map["screenshot"]` maps to the client's call handler.

**Scenario 3: Executing a loaded MCP tool**
- **Given** The tool `screenshot` is loaded.
- **When** The agent executes `screenshot` with parameters `{"url": "..."}`.
- **Then** The client invokes the tool on the subprocess, receives the result, and returns it as a string to the agent loop.

**Scenario 4: Unloading tools and server**
- **Given** The tool `screenshot` and server `chrome-devtools` are active.
- **When** The agent executes `unload_mcp("chrome-devtools")`.
- **Then** The tool `screenshot` is removed from `agent.tools` and `agent.tools_map`, and the subprocess is terminated.

---

## 3. Constraints & Risks
* **Lifecycle Leaks:** If the agent crash-exits, subprocesses could be left orphaned. We must ensure that any active MCP client is closed in a `try...finally` block in `Agent.run` or via destructor `__del__`.
* **Async Execution in Sync Loop:** The `Agent.run()` method is synchronous. `fastmcp` client methods are async. We must execute them safely on a dedicated thread loop to avoid nesting event loop issues.

---

## 4. Status
- **NEEDS_REVIEW**

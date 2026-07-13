# SDD Specification: mcp_cache_and_fixes (spec.md)

This specification defines the functional requirements and business logic for path traversal security validation, MCP client test warnings cleanup, and dynamic pre-caching/reloading of MCP server configurations.

---

## 1. Context & Goals

### Problem Statement
1. **Weak Path Traversal Check**: The path guard in `tools/io_tools.py` checks `abs_path.startswith(cwd)` without a path separator, allowing reads and writes to sibling directories sharing a prefix (e.g. `cwd = /path/to/project`, path `abs_path = /path/to/project_secreto` returns `True`).
2. **Pytest Runtime Warning**: The `tests/test_mcp_client.py` test suite raises warnings because mock coroutines from `Client.__aenter__` and `Client.__aexit__` are discarded without being awaited/closed.
3. **Uncached/Untracked MCP configs**: MCP configuration files under `.agents/mcp/*.json` are not pre-cached or listed in the system prompt. Changing, adding, or deleting a configuration file does not automatically trigger cache invalidation and reloading.

### Scope
- **Included**:
  - Secure check in `tools/io_tools.py` ensuring that requested files are strictly inside `cwd` or its subdirectories.
  - Awaiting/closing coroutines in `tests/test_mcp_client.py`.
  - Directory scanning and pre-caching of all MCP configuration files under `.agents/mcp/` on startup.
  - Cache invalidation and reload checking: detect newly created configs, modified configs, and deleted configs on prompt compilation step, and update the cache dynamically.
  - Including available MCP servers in the compiled system prompt.
- **Excluded**:
  - File watcher libraries (like watchdog): we will use filesystem polling (`os.path.getmtime` and directory listing) on prompt compilation/session check to avoid adding heavy third-party dependencies.

### Success Criteria
- No warnings are thrown by mock coroutines during test execution.
- Path traversal check denies access to sibling directories with shared prefix.
- MCP configurations cache invalidates and updates properly when files are edited, added, or deleted.
- The compiled system prompt displays the currently available MCP servers.

---

## 2. Requirements (BDD Scenarios)

### Feature: Path Traversal Security
**Scenario 1: Reject path outside workspace sharing a prefix**
- **Given** a workspace root `/home/user/project`
- **When** a filesystem tool is called with `/home/user/project_sibling/file.txt`
- **Then** the tool returns an error message denying access.

### Feature: MCP Configuration Pre-caching and Prompt Listing
**Scenario 2: List available MCP servers in system prompt**
- **Given** MCP config files `server1.json` and `server2.json` in `.agents/mcp/`
- **When** the agent compiles the system prompt
- **Then** the prompt contains a list of available MCP servers (`server1`, `server2`).

**Scenario 3: Invalidate and update cache when config is modified**
- **Given** a cached MCP config file `server1.json`
- **When** the `server1.json` file is modified on disk (its `mtime` changes)
- **Then** the next prompt compilation step detects the modification, updates the cache, and reloads the metadata.

**Scenario 4: Detect added/removed MCP configs**
- **Given** the list of `.agents/mcp/` config files
- **When** `new_server.json` is added to `.agents/mcp/` or `server2.json` is deleted
- **Then** the cache updates dynamically to add/remove the corresponding servers from the available list.

---

## 3. Constraints & Risks

- **Security**: The path-traversal check must not break valid paths within the project directory (including subdirectories and standard relative path resolutions).
- **Performance**: Polling files in `.agents/mcp/` should be fast and lightweight, avoiding disk blocking during the agent ReAct loop step.
- **Backward Compatibility**: Existing MCP client lifecycle commands (`load_mcp`, `unload_mcp`) must function normally, but utilize the pre-cached configurations.

---

## 4. Status
- **NEEDS_REVIEW**

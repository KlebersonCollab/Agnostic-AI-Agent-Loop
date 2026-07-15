# Project State & Context

## 🏁 Session Status
- **Current Task**: None. Feature `agent_refactoring` is completed and reviewed.
- **Progress**: 100% complete. Modularized `agent.py` by extracting prompts, observer listener interfaces, and the ReAct execution loop into the new `agent/` package.
- **Next Steps**:
  - Await next instructions from user.

## 💡 Decisions Log
- **2026-07-15 - Agent Modularization**: Refactor `agent.py` into a package structure `agent/` to separate concerns (prompts, listener base interface, core loop execution), improving code readability and modularity. (Completed)
- **2026-07-15 - CLI Modularization & TUI separation**: Extract TUI concerns (`ConsoleAgentListener`, welcome banner, runner loops, slash commands) from `cli.py` to a dedicated `tui/` package to improve modularity and single responsibility. (Completed)
- **2026-07-14 - SQLite Concurrency and Transaction Rollback**: Plan, specify, and implement global DB serialization, a 30s connection timeout, and explicit rollbacks on write failures to prevent deadlocks and lock leaks during multi-agent concurrent writes. (Completed)
- **2026-07-14 - Asynchronous Delegation and MemGuard**: Plan, specify, and implement background subagent threading, cancellation checks, registry tools, and SQLite FTS5 category whitelists for controlled shared memory. (Completed)
- **2026-07-14 - Agent Orchestrator Mode**: Plan, specify, and implement Orchestrator Mode, defining tool sets for Orchestrator and Worker roles and adding a toggle via `--mode` CLI parameter. (Completed)
- **2026-07-13 - Execute Command Tool**: Plan, specify, and implement a sandboxed `execute_command` tool inside the workspace, enforcing safety blacklists, timeouts, and output limits. (Completed)
- **2026-07-13 - Delete File Tool**: Plan, specify, and implement a secure `delete_file` tool inside the workspace, emitting a console warning upon execution. (Completed)
- **2026-07-13 - Hooks System**: Plan, specify, and implement dynamic Hooks loading and execution system supporting package/workspace paths, overrides, and 11 distinct event triggers across agent loop, tool execution, and provider API requests. (Completed)
- **2026-07-13 - MCP Caching & Security Fixes**: Plan and specify security hardening of path checks, caching/monitoring of MCP config files, and resolving mock coroutine warnings. (Completed)
- **2026-07-10 - Context Reference Injection**: Decide to implement prompt-level `@file`, `@url`, `@diff`, `@staged` parsing to match Hermes Agent style context injection. (Completed)
- **2026-07-10 - Context Folder Refactoring**: Decide to organize context modules under a new Python package `context/` (containing `context/builder.py` and `context/references.py`) to keep the codebase modular. (Completed)
- **2026-07-10 - Context Breakdown display**: Decide to implement a `/context` slash command in `cli.py` that calculates and displays the token usage breakdown in a beautiful colored Rich table. (Completed)
- **2026-07-10 - Model Context Protocol Client**: Decide to implement stdio-based MCP client using `fastmcp` programmatically. Keep tools context budgeted by exposing servers and tools dynamically on-demand (`load_mcp`, `load_mcp_tool`). (Completed)
- **2026-07-11 - sdd-memory Evolution**: Evolve the knowledge-graph protocol (SKILL.md) + frontend to close 2026 literature gaps: temporal `state` (current/historical/transition) with `supersede` op to kill ghost memory; functional `role` isolation (MemGuard); `verify_write` checklist + `confidence` field (TrustMem / Manufactured Confidence); `decay`/`consolidate` guidance (FadeMem). All new fields optional/backward-compatible. (Completed)
- **2026-07-11 - Curl Tool**: Implemented a programmatic `curl` tool using standard library `urllib` to handle HTTP requests (GET, POST, PUT, DELETE, PATCH, etc.) with custom headers, body/data, configurable timeouts, and bypassing SSL verification. (Completed)
- **2026-07-12 - Curl Response Truncation**: Decided to add a `max_response_chars` parameter (default 50,000) and response truncation logic to the `curl` tool to prevent context bloating and token exhaustion errors on large HTTP responses. (Completed)
- **2026-07-12 - Loop Command Mode**: Decided to introduce a `/loop <prompt>` prefix in both interactive and one-shot CLI modes. It temporarily increases the `max_steps` to 10000, bypassing standard early handover checkpoints and step limits to let the agent run long-running tasks to completion. (Completed)
- **2026-07-12 - Concurrent Tool Execution**: Decided to run multiple tool calls concurrently in a ThreadPoolExecutor within agent.py to optimize latency, ensuring thread-safe database operations in AgentMemory with reentrant locks. (Completed)
- **2026-07-12 - Subagent UI Enhancement**: Decided to refactor CollectingAgentListener in tools/multi_agent.py to output structured, aligned columns with Rich color coding for step tracking. (Completed)

## 🚧 Active Blockers
- None.

## ❄️ Deferred Ideas / Icebox
- None.

## ⚠️ Known Technical Debts
- Hand-rolled frontmatter parser in `ContextBuilder` (documented in technical map).

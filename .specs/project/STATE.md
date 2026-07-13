# Project State & Context

## 🏁 Session Status
- **Current Task**: None. Feature `hooks_system` is completed and reviewed.
- **Progress**: 100% complete. Implemented HooksManager dynamic loader with package and workspace paths, overrides, 11 event triggers, and integration with Agent loop and CLI. Passed all 6 tests.
- **Next Steps**:
  - Await next instructions from user.

## 💡 Decisions Log
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

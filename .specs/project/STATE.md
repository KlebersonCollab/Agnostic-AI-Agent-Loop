# Project State & Context

## 🏁 Session Status
- **Current Task**: Evolving sdd-memory knowledge graph protocol (feature: sdd_memory_evolution)
- **Progress**: Implementation complete (SKILL.md schema + front/index.html rendering + regression test). Awaiting `uv run pytest` execution (no shell tool in this environment).
- **Next Steps**:
  1. Run `uv run pytest tests/test_memory_graph.py -q` to confirm the regression + new-schema tests pass.
  2. Optionally run `python front/server.py --no-browser` and load `/api/memory.jsonl` to visually confirm state/role badges and ghost indicators.

## 💡 Decisions Log
- **2026-07-10 - Context Reference Injection**: Decide to implement prompt-level `@file`, `@url`, `@diff`, `@staged` parsing to match Hermes Agent style context injection. (Completed)
- **2026-07-10 - Context Folder Refactoring**: Decide to organize context modules under a new Python package `context/` (containing `context/builder.py` and `context/references.py`) to keep the codebase modular. (Completed)
- **2026-07-10 - Context Breakdown display**: Decide to implement a `/context` slash command in `cli.py` that calculates and displays the token usage breakdown in a beautiful colored Rich table. (Completed)
- **2026-07-10 - Model Context Protocol Client**: Decide to implement stdio-based MCP client using `fastmcp` programmatically. Keep tools context budgeted by exposing servers and tools dynamically on-demand (`load_mcp`, `load_mcp_tool`). (Completed)
- **2026-07-11 - sdd-memory Evolution**: Evolve the knowledge-graph protocol (SKILL.md) + frontend to close 2026 literature gaps: temporal `state` (current/historical/transition) with `supersede` op to kill ghost memory; functional `role` isolation (MemGuard); `verify_write` checklist + `confidence` field (TrustMem / Manufactured Confidence); `decay`/`consolidate` guidance (FadeMem). All new fields optional/backward-compatible. (Completed)

## 🚧 Active Blockers
- None.

## ❄️ Deferred Ideas / Icebox
- None.

## ⚠️ Known Technical Debts
- Hand-rolled frontmatter parser in `ContextBuilder` (documented in technical map).

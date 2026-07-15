# SDD Specification: spec.md

This is the source of truth for the functional requirements of the **Advanced Hooks** feature.

---

## 1. Context & Goals
- **Problem Statement**: The agent's environment needs extra guards and automation:
  - Confidential API keys might leak into the LLM context.
  - Dangerous tool calls or path traversals could run.
  - We lack detailed metrics on tool execution performance.
  - Large conversation history leads to context bloat and high costs.
  - Tool execution errors (like permissions/missing files) can stall or crash the agent loop.
- **Scope**: Implementing four distinct hooks:
  - **Security Shield** (`pre_api_request` / `pre_tool_call`): Sanitize outgoing messages for API keys, block malicious paths.
  - **Performance Tracker** (`pre_tool_call` / `post_tool_call` / `on_session_complete`): Profile tool execution metrics and output a summary Rich table.
  - **Context Pruner** (`pre_api_request`): Automatically prune older history in the prompt when near limits.
  - **Self-Healing** (`on_tool_error`): Intercept exceptions and return actionable advice to the agent.
- **Success Criteria**: All hooks are integrated, executed at their designated lifecycles, and verified with 100% test coverage.

---

## 2. Requirements (BDD Scenarios)

### Feature: Security Shield

**Scenario 1: Redact API keys from LLM messages**
- **Given** an outgoing API request containing a message with an API key (e.g. `sk-proj-12345...` or `AIzaSy...`) or any value from active environment variables containing keys (e.g., `GEMINI_API_KEY`).
- **When** `pre_api_request` hook triggers.
- **Then** the key values in the messages are replaced with `[REDACTED_API_KEY]`.

**Scenario 2: Block unsafe path traversal**
- **Given** a tool call trying to access paths outside the workspace or dangerous paths (e.g. `/etc/passwd`, `~/.ssh/`).
- **When** `pre_tool_call` hook triggers.
- **Then** a `ValueError` is raised, preventing the tool from running.

---

### Feature: Performance Tracker

**Scenario 1: Profile and report tool stats**
- **Given** a session executing multiple tools (e.g., `grep_search`, `read_file`).
- **When** `pre_tool_call` and `post_tool_call` profile durations, and the session completes.
- **Then** a clean Rich table with tool stats (call counts, total time, average latency) is displayed in the console.

---

### Feature: Context Pruner

**Scenario 1: Prune middle of the conversation when near threshold**
- **Given** a message history with an estimated token count exceeding a safe threshold (e.g., 40,000 tokens).
- **When** `pre_api_request` triggers.
- **Then** the middle of the conversation is pruned, replacing it with a summary placeholder message, while keeping the system prompt, first user message, and last 10 messages intact.

---

### Feature: Self-Healing

**Scenario 1: Return user-friendly tips on tool exceptions**
- **Given** a tool execution raising a `FileNotFoundError` or `PermissionError`.
- **When** `on_tool_error` triggers.
- **Then** a constructive message guiding the agent (e.g., "Error: File not found. Verify the path exists.") is returned as the tool output.

---

## 3. Constraints & Risks
- **Security**: Security Shield must not block valid workspace operations, only malicious/unsafe paths and key leakage.
- **Performance**: Hooks must execute quickly (<10ms) to avoid lagging the agent loops.
- **Dependencies**: Uses `rich` for formatting, standard library for scheduling, profiling, and sanitization.

---

## 4. Status
- **NEEDS_REVIEW**

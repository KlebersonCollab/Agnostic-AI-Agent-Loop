# SDD Technical Plan: plan.md

This is the **technical blueprint** for implementing the advanced hooks (Security Shield, Performance Tracker, Context Pruner, Self-Healing).

---

## 1. Architecture Overview
We will implement the hooks as modular Python files placed inside the specific directories corresponding to the event triggers defined in `HooksManager` ([manager.py](file:///home/klebersonromero/Projetos/teste/hooks/manager.py)):
- `.agents/hooks/pre_api_request/security_shield.py` & `.agents/hooks/pre_tool_call/security_shield.py`
- `.agents/hooks/pre_tool_call/performance_tracker.py`, `.agents/hooks/post_tool_call/performance_tracker.py`, and `.agents/hooks/on_session_complete/performance_tracker.py`
- `.agents/hooks/pre_api_request/context_pruner.py`
- `.agents/hooks/on_tool_error/self_healing.py`

These modules will be loaded dynamically by `HooksManager` and run during the ReAct loop stages.

---

## 2. Technical Design

### Hook Details & APIs

#### A. Security Shield
- **File**: `pre_api_request/security_shield.py`
  - Reads active environment variables that contain keys (`*_API_KEY`, `*_SECRET`, `*_PASSWORD`).
  - Scans all messages for occurrences of these sensitive string values, as well as common API key patterns (regex patterns for `sk-...`, `AIzaSy...`, etc.).
  - Replaces all matches with `[REDACTED_API_KEY]`.
- **File**: `pre_tool_call/security_shield.py`
  - Intercepts all tool calls.
  - Checks if path-like arguments try to traverse out of the workspace (CWD) or reference sensitive paths (e.g. `/etc/`, `.ssh/`, `.bashrc`, `.env`).
  - Raises a `ValueError("Security violation: path traversal or unauthorized access blocked")` if a match is found.

#### B. Performance Tracker
- **State**: A global dictionary in `performance_tracker.py` storing:
  - `start_times = {}` (keyed by call session ID / thread ID)
  - `metrics = {}` (accumulating counts, total/min/max duration per tool name)
- **File**: `pre_tool_call/performance_tracker.py`
  - Records current time under the current execution key.
- **File**: `post_tool_call/performance_tracker.py`
  - Computes difference, records counts/durations.
- **File**: `on_session_complete/performance_tracker.py`
  - Uses `rich` to print a colored console table summarizing tool performance, sorted by total execution time.

#### C. Context Pruner
- **File**: `pre_api_request/context_pruner.py`
  - Computes approximate token usage.
  - If total estimated token size exceeds a configurable threshold (default `40000` tokens):
    - Retains:
      - System message (first message if role == system).
      - First user message.
      - Last 10 messages of the conversation.
    - Compresses the middle messages into a single system message: `[System: Older conversation history pruned to preserve context window]` to release token usage.

#### D. Self-Healing
- **File**: `on_tool_error/self_healing.py`
  - Catches tool exceptions.
  - Translates `FileNotFoundError` to: `Error: File '<filename>' not found. Verify the path exists and check spelling.`
  - Translates `PermissionError` to: `Error: Permission denied. Make sure you have read/write access to the target path.`
  - Returns the translated error message directly to the agent's context as the tool output so it can correct itself.

---

## 3. Implementation Strategy
- **Isolation**: Only new files inside `.agents/hooks/` will be created. No changes to the core agent loop or existing modules are needed since `HooksManager` loads them dynamically from `.agents/hooks/<event>/`.
- **Testing Strategy**:
  - Implement a suite of unit tests in `tests/test_advanced_hooks.py` using `unittest.mock` to simulate triggers and assert hook actions.
  - Test redaction, path traversal blocks, performance calculation, history pruning, and error translation.
- **Migrations**: No database/schema changes needed.

---

## 4. Status
- **NEEDS_REVIEW**

# SDD Specification: concurrent_tool_execution

This is the source of truth for **functional requirements** and **business logic** for the Concurrent Tool Execution feature.

---

## 1. Context & Goals
- **Problem Statement**: In the current ReAct loop, when the LLM returns multiple parallel tool calls (e.g. reading different files or calling web URLs), they are executed sequentially. This introduces unnecessary step latency because the total execution time is the sum of all tool execution times.
- **Scope**:
  - **In-Scope**:
    - Concurrently execute multiple tool calls generated in the same LLM response.
    - Support both standard registered tools (in `tools_map`) and intercepted agent-level tools (`load_skill`, `unload_skill`, `search_memory`, `load_mcp`, etc.).
    - Maintain consistent ordering in agent history, listeners, and memory logs.
    - **Graceful Error Isolation**: Catch and isolate exceptions raised by individual tools inside threads, returning formatted error messages rather than crashing the agent process.
    - **Context Window Integrity**: Guarantee that concurrent execution does not duplicate, corrupt, or drop parts of the conversation context sent to the LLM.
  - **Out-of-Scope**:
    - Concurrency across different loop steps (the main agent loop remains sequential).
    - Asynchronous event-loop rewrite of the entire codebase (the loop remains synchronous).
- **Success Criteria**:
  - Multiple tool calls within the same step run in parallel.
  - Verification test suite exercises parallel execution and validates correct outputs.
  - A tool failure in one thread does not terminate the agent loop prematurely.

## 2. Requirements (BDD Scenarios)

### Feature: Concurrent Tool Execution

**Scenario 1: Executing multiple tools concurrently**
- **Given** an LLM provider returns multiple tool calls (e.g. two separate `read_file` calls)
- **When** the agent processes the step
- **Then** the tools should run concurrently (e.g., in a thread pool)
- **And** the total execution time should be significantly lower than the sum of their individual sequential execution times
- **And** all tool outputs should be logged to the listener, memory, and history in the correct order.

**Scenario 2: Graceful recovery on tool crash**
- **Given** multiple tools are running concurrently
- **When** one of the tools raises an unexpected exception
- **Then** the thread must catch the exception and convert it to a standard error string (e.g., `Error executing tool...`)
- **And** other concurrent tools must complete their execution normally
- **And** the agent must not crash or exit prematurely.

**Scenario 3: Context and History Preservation**
- **Given** multiple tools execute concurrently and finish out of order
- **When** they return their results
- **Then** they must be logged and appended to the chat history (`self.history`) in the exact order they were requested by the LLM
- **And** the context size and content sent to the LLM in the next turn must remain fully intact and correct.

**Scenario 4: Handling thread safety in database and file system**
- **Given** multiple tools are executing concurrently
- **When** they access shared resources like `AgentMemory` or files
- **Then** access should be properly synchronized to prevent database corruption, transaction conflicts, or file state corruption.

## 3. Constraints & Risks
- **Security**: The current file-system tools use a shared `_file_write_lock` which prevents concurrent write conflicts.
- **Performance**: Use of a bounded `ThreadPoolExecutor` to prevent spawning excessive threads if the model returns many tool calls.
- **Database Thread Safety**: SQLite connections are not fully thread-safe for concurrent query executions across multiple threads. We must synchronize accesses to `AgentMemory` or isolate database logging to the main thread.
- **Dependencies**: Uses Python's standard library `concurrent.futures`. No new third-party packages are required.

---
## 4. Status
- **AGREE**

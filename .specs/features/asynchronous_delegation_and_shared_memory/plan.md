# SDD Technical Plan: asynchronous_delegation_and_shared_memory

This is the technical blueprint for implementing Asynchronous Delegation and Shared Memory (MemGuard) in the Agnostic AI Agent framework.

---

## 1. Architecture Overview

To support multi-agent collaboration with non-blocking delegation and memory access isolation:
1. **Asynchronous Delegation**:
   - Introduce `spawn_subagent_async`, which starts a subagent running in a separate background thread and returns immediately with a unique `subagent_id`.
   - Implement `check_subagents_status` to allow the Orchestrator to inspect progress logs and final outputs of active or completed background subagents.
   - Implement `interrupt_subagent` to abort a running subagent thread by setting a thread-safe `cancelled` flag checked during the agent ReAct loop.
2. **Shared Memory (MemGuard)**:
   - Restrict the `search_memory` tool for subagents to enforce role-based context isolation.
   - The Orchestrator can configure a subagent's allowed memory categories (e.g. only technical tool outputs/thoughts, blocking user prompts and handovers that could contain credentials or private inputs).
   - In `AgentMemory.search`, enforce the category whitelist at the SQL query level.

```
                      ┌────────────────────────┐
                      │  Orchestrator Agent    │
                      └───────────┬────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │ (spawn_subagent_async) │ (check_subagents)      │ (interrupt_subagent)
         ▼                        ▼                        ▼
 ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
 │ Background    │        │ Read progress │        │ Set cancelled │
 │ Thread        │        │ logs / output │        │ flag = True   │
 └───────┬───────┘        └───────────────┘        └───────┬───────┘
         │                                                 │
         ▼                                                 ▼
 ┌───────────────┐                                 ┌───────────────┐
 │  Subagent     │                                 │ Abort ReAct   │
 │  ReAct Loop   │◄────────────────────────────────┤ step loop     │
 └───────┬───────┘                                 └───────────────┘
         │
         │ search_memory()
         ▼
 ┌───────────────┐
 │  MemGuard     │ (Filter FTS5 categories via whitelist)
 └───────────────┘
```

---

## 2. Technical Design

### Asynchronous Delegation System
We will implement a `BackgroundSubagentRegistry` in `tools/multi_agent.py` to keep track of active threads:
- It will hold references to running `Agent` instances, their threads, and their accumulative logs/listeners.
- **Thread Safety**: Access to the registry dictionary will be synchronized using a thread lock.
- **Cancellation**: `Agent` in [agent.py](file:///home/klebersonromero/Projetos/teste/agent.py) will check `self.cancelled` at the beginning of each loop step. If `True`, it exits with `"CANCELLED"`.

### Shared Memory & MemGuard
- In [agent.py](file:///home/klebersonromero/Projetos/teste/agent.py), add `allowed_memory_categories: Optional[List[str]] = None` to the `Agent` constructor.
- When `search_memory` is called by the agent, it passes `self.allowed_memory_categories` to `self.memory.search()`.
- In [memory.py](file:///home/klebersonromero/Projetos/teste/memory.py), update `AgentMemory.search` to support filtering by a list of allowed categories via SQLite's `IN` operator.

### New Tools Registration
Add the following tools to [tools/__init__.py](file:///home/klebersonromero/Projetos/teste/tools/__init__.py):
1. `spawn_subagent_async`:
   - Parameters: `role_description` (str), `prompt` (str), `allowed_categories` (optional list of str).
   - Action: Spawns the subagent in a background thread, returns `subagent_id`.
2. `check_subagents_status`:
   - Parameters: none or optional `subagent_id` (str).
   - Action: Returns a JSON-formatted summary of all subagents or a specific one (status: `running`/`completed`/`cancelled`/`failed`, incremental logs, and final answer).
3. `interrupt_subagent`:
   - Parameters: `subagent_id` (str).
   - Action: Cancels the target subagent.

---

## 3. Implementation Strategy
- **Isolation**:
  - Update [agent.py](file:///home/klebersonromero/Projetos/teste/agent.py) to add `cancelled` flag and memory isolation configuration.
  - Update [memory.py](file:///home/klebersonromero/Projetos/teste/memory.py) to support SQL-level category whitelists.
  - Implement async spawning and registry in [tools/multi_agent.py](file:///home/klebersonromero/Projetos/teste/tools/multi_agent.py).
  - Register new tools in [tools/__init__.py](file:///home/klebersonromero/Projetos/teste/tools/__init__.py).
- **Testing Strategy**:
  - Create [tests/test_async_delegation.py](file:///home/klebersonromero/Projetos/teste/tests/test_async_delegation.py) to verify:
    1. Async subagents start and run in the background.
    2. Orchestrator can retrieve incremental progress logs while the subagent is running.
    3. Interrupting a subagent stops its ReAct loop cleanly.
    4. Memory queries are filtered according to the specified categories.

---

## 4. Status
- **DRAFT**

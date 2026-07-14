# SDD Specification: asynchronous_delegation_and_shared_memory

This is the source of truth for **functional requirements** and **business logic** for the Asynchronous Delegation and Shared Memory (MemGuard) features.

---

## 1. Context & Goals
- **Problem Statement**:
  1. Spawning subagents using `spawn_subagents_parallel` blocks the Orchestrator's execution thread until all subagents finish. This prevents the Orchestrator from making decision updates or stopping long-running tasks early if a blocker or mistake is detected.
  2. Subagents have access to all memory indices by default, which can lead to leaks of sensitive data (like user prompts containing API keys or handover reports containing restricted notes).
- **Goal**:
  1. Build a non-blocking background task system for subagents with progress tracking and interruption.
  2. Implement role-based, category-restricted database access (MemGuard) for subagents.

---

## 2. Requirements (BDD Scenarios)

### Feature: Asynchronous Delegation

**Scenario 1: Spawning a subagent asynchronously**
- **Given** the Orchestrator wants to run a task without blocking its loop
- **When** the Orchestrator calls `spawn_subagent_async`
- **Then** the tool must return a unique `subagent_id` immediately
- **And** the subagent execution loop must start running in a background thread.

**Scenario 2: Checking status of background subagents**
- **Given** one or more subagents are running in the background
- **When** the Orchestrator calls `check_subagents_status`
- **Then** it must receive a JSON containing the state of all subagents
- **And** for each subagent, it must show its status (`running`, `completed`, `failed`, `cancelled`), current execution logs, and final answer (if completed).

**Scenario 3: Interrupting a subagent**
- **Given** a subagent is running in the background
- **When** the Orchestrator calls `interrupt_subagent` with the corresponding `subagent_id`
- **Then** the subagent's execution must stop during its next ReAct loop iteration
- **And** its status in the registry must be updated to `cancelled`.

---

### Feature: Shared Memory with MemGuard

**Scenario 4: Filtered memory search**
- **Given** a subagent is configured with allowed memory categories `['thought', 'tool_output']`
- **When** the subagent calls `search_memory`
- **Then** the query returned by the SQLite memory database must only contain entries matching the specified categories
- **And** entries with categories like `task`, `user_input`, or `handover` must be excluded.

---

## 3. Constraints & Risks
- **Concurrency & SQLite Lock**: Since subagents run concurrently, SQLite operations must be thread-safe. This is already supported by `AgentMemory`'s reentrant lock `self.lock`, but we must ensure connection isolation or thread-safe shared transactions.
- **CPU Overload**: Running too many concurrent subagents can slow down the host machine. We will document that the Orchestrator should limit the number of active background subagents.

---

## 4. Status
- **DRAFT**

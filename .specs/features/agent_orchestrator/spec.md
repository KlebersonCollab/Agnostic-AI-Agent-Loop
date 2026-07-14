# SDD Specification: agent_orchestrator

This is the source of truth for **functional requirements** and **business logic** for the Agent Orchestrator Mode.

---

## 1. Context & Goals
- **Problem Statement**: Running a monolithic ReAct loop where the agent executes all file actions, commands, and calculations directly leads to cluttered context history, making it harder for the agent to follow complex structural rules or maintain high-level strategy.
- **Goal**: Implement a delegated hub-and-spoke multi-agent architecture. By separating the agent's responsibilities, the Orchestrator remains clean, logical, and focused, while delegating atomic technical tasks to specialized subagents.
- **Scope**:
  - **In-Scope**:
    - Separate tools into Orchestrator (strategic) and Worker (operational) sets.
    - Provide a new Orchestrator-specific system prompt emphasizing leadership, planning, and delegation.
    - Support `--mode {orchestrator,classic}` to allow switching between modes.
    - Guarantee that subagents retain access to operational tools to execute delegated work.
  - **Out-of-Scope**:
    - Restructuring `Agent` to be asynchronous.
    - Modifying MCP server communication protocols.
- **Success Criteria**:
  - Running the agent with `--mode orchestrator` configures the agent with only strategic/delegation tools.
  - Running the agent with `--mode classic` registers all tools as before.
  - Subagents spawned from the Orchestrator have access to all operational tools and execute successfully.
  - Test suite passes and validates the tool filtering/delegation behavior.

---

## 2. Requirements (BDD Scenarios)

### Feature: Agent Orchestrator Mode

**Scenario 1: Starting in Orchestrator Mode**
- **Given** the agent is started with `--mode orchestrator` (or default)
- **When** the agent loop is initialized
- **Then** the base system prompt must be `ORCHESTRATOR_SYSTEM_PROMPT`
- **And** the active tool definitions passed to the LLM must contain only orchestrator tools (`spawn_subagents_parallel`, `search_memory`, and skill/mcp management)
- **And** operational tools (like `read_file`, `write_file`, `execute_command`) must NOT be present in the active tool definitions.

**Scenario 2: Starting in Classic Mode**
- **Given** the agent is started with `--mode classic`
- **When** the agent loop is initialized
- **Then** the base system prompt must be `SYSTEM_PROMPT`
- **And** the active tool definitions must include all registered tools (both strategic and operational).

**Scenario 3: Delegating operational tasks**
- **Given** the agent is running in Orchestrator Mode
- **When** the user requests a file modification or shell execution
- **Then** the agent must not execute the action directly
- **And** the agent must call `spawn_subagents_parallel` with a specialized task prompt and role description to perform the work.

**Scenario 4: Subagent tool set preservation**
- **Given** a subagent is spawned from an Orchestrator Agent
- **When** the subagent is initialized in `multi_agent.py`
- **Then** it must receive all operational tools and other registered tools (except `spawn_subagents_parallel` to prevent recursion)
- **And** it must be able to call those operational tools to perform its tasks.

---

## 3. Constraints & Risks
- **Backward Compatibility**: Existing scripts or integrations calling `Agent` or running `pytest` with mock tools must continue to function without changes. We will ensure the `Agent` class constructor remains fully compatible by letting the CLI or caller handle the tool filtering.
- **Recursive Spawning**: Subagents must not have the `spawn_subagents_parallel` tool to prevent infinite loops of subagents spawning subagents.

---

## 4. Status
- **DRAFT**

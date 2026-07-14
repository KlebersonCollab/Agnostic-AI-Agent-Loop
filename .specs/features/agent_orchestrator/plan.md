# SDD Technical Plan: agent_orchestrator

This is the technical blueprint for the Agent Orchestrator Mode implementation.

---

## 1. Architecture Overview
Currently, the `Agent` acts as a monolithic ReAct loop containing all tools. To transition to a hub-and-spoke multi-agent model:
- The main agent will act as a **Strategic Orchestrator**, coordinating tasks, managing planning/context, and delegating execution.
- Operational tools (file operations, command execution, math, curl) will be isolated. The Orchestrator will only use orchestration/delegation tools (`spawn_subagents_parallel`, memory search, and skill/mcp management).
- Worker subagents will retain access to operational tools to execute the delegated tasks, reporting summaries back to the Orchestrator.
- A new CLI flag `--mode {orchestrator,classic}` (default: `orchestrator`) will allow toggling between the new delegated architecture and the classic monolithic execution mode.

```
                  ┌────────────────────────┐
                  │       CLI Runner       │
                  └───────────┬────────────┘
                              │
                    Mode: orchestrator
                              │
                              ▼
                  ┌────────────────────────┐
                  │  Orchestrator Agent    │ (Has: spawn_subagents_parallel,
                  │      (Strategic)       │  search_memory, skills/mcp tools)
                  └───────────┬────────────┘
                              │
                 spawn_subagents_parallel()
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
     ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
     │  Subagent   │   │  Subagent   │   │  Subagent   │ (Has: read/write/patch_file,
     │ (Specialist)│   │ (Specialist)│   │ (Specialist)│  execute_command, curl, etc.)
     └─────────────┘   └─────────────┘   └─────────────┘
```

---

## 2. Technical Design

### Tool Separation
We will divide the tools in [tools/__init__.py](file:///home/klebersonromero/Projetos/teste/tools/__init__.py) into categories:
1. **Orchestrator Tools**:
   - `spawn_subagents_parallel`
   - `search_memory`
   - `load_skill` / `unload_skill`
   - `load_mcp` / `unload_mcp` / `load_mcp_tool` / `unload_mcp_tool`
2. **Operational Tools** (Worker Only):
   - `list_project_files`, `read_file`, `write_file`, `patch_file`, `delete_file`
   - `execute_command`
   - `calculate`
   - `curl`
   - `search_grep`, `get_outline`

### System Prompts
We will create a specialized system prompt for the Orchestrator mode to instruct the model to behave as a leader and plan delegatively:
- **`ORCHESTRATOR_SYSTEM_PROMPT`**: Directs the agent to act as a manager, analyze requests, define strategies, and delegate operational actions (like editing files, running bash commands, or making web requests) to specialized subagents using the `spawn_subagents_parallel` tool.

### CLI Enhancements
Modify [cli.py](file:///home/klebersonromero/Projetos/teste/cli.py) to:
- Add a `--mode` argument (choices: `orchestrator`, `classic`, default: `orchestrator`).
- Filter the toolset passed to the main `Agent` based on the selected mode.
- In `orchestrator` mode, load `ORCHESTRATOR_SYSTEM_PROMPT` as the base system prompt instead of the classic monolithic `SYSTEM_PROMPT`.

---

## 3. Implementation Strategy
- **Isolation**:
  - Update [agent.py](file:///home/klebersonromero/Projetos/teste/agent.py) to declare `ORCHESTRATOR_SYSTEM_PROMPT` and export a clean interface.
  - Update [cli.py](file:///home/klebersonromero/Projetos/teste/cli.py) to add the CLI argument and filter tools.
  - Update [tools/__init__.py](file:///home/klebersonromero/Projetos/teste/tools/__init__.py) to expose filtered lists of tools: `get_orchestrator_tools()` and `get_operational_tools()`.
- **Testing Strategy**:
  - Add [tests/test_agent_orchestrator.py](file:///home/klebersonromero/Projetos/teste/tests/test_agent_orchestrator.py) to verify:
    1. Tool filtering matches expectations in both modes.
    2. Orchestrator properly delegates operational work using `spawn_subagents_parallel`.
- **Migrations**: No database migrations.

---

## 4. Status
- **DRAFT**

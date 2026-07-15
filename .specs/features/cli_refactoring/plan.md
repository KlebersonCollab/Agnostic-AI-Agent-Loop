# SDD Technical Plan: cli_refactoring

This is the technical blueprint for refactoring `cli.py` to extract presentation/UI layer concerns and session management into a separate `tui/` package.

---

## 1. Architecture Overview
Currently, `cli.py` is bloated and contains:
1. Command Line argument parsing.
2. Welcome banner printing logic.
3. Checkpoint loading/resuming logic.
4. Console/TUI event formatting and printing via `ConsoleAgentListener`.
5. The interactive continuous session shell loop.

To adhere to clean code principles and separation of concerns, we will modularize `cli.py` by introducing the `tui/` package:
- `tui/listener.py`: Holds `ConsoleAgentListener` for decoupling TUI event listening/rendering.
- `tui/commands.py`: Holds command/slash commands handlers (such as `/context`, `/verbose`, `/clear`, `/loop`).
- `tui/helpers.py`: Holds TUI helper functions like welcome banner formatting.
- `tui/runner.py`: Coordinates interactive and one-shot execution loops.

`cli.py` will serve solely as the command-line interface entry point: parsing arguments, starting the frontend server (if requested), bootstrapping the provider, and invoking `tui.runner`.

---

## 2. Technical Design

### Package Structure
```
tui/
├── __init__.py
├── commands.py
├── helpers.py
├── listener.py
└── runner.py
```

### Module Responsibilities
1. **`tui/listener.py`**:
   - Class `ConsoleAgentListener` extending `AgentListener`.
   - Thread-safe Rich console helper for thought/tool print outputs.

2. **`tui/commands.py`**:
   - `handle_slash_command(user_input: str, agent: Agent, listener: ConsoleAgentListener) -> bool`: returns `True` if it was a slash command (and processed it), otherwise `False`.

3. **`tui/helpers.py`**:
   - `print_welcome_banner(provider: str, model: str, mode: str, tools_list: list, skills_list: list, rules_list: list)`
   - `load_checkpoint_if_exists() -> Optional[str]`

4. **`tui/runner.py`**:
   - `run_interactive_loop(agent: Agent, listener: ConsoleAgentListener)`
   - `run_one_shot(agent: Agent, prompt: str, is_loop: bool)`

---

## 3. Implementation Strategy
- **Phase 1**: Create `tui/` directory and populate modules.
- **Phase 2**: Refactor `cli.py` to import and call `tui/` components.
- **Phase 3**: Verify correctness by running all unit tests, specifically `tests/test_cli_loop.py`.

---

## 4. Status
- **DRAFT**

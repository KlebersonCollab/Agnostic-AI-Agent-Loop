# SDD Specification: cli_refactoring

This is the source of truth for **functional requirements** and **business logic** for CLI modularization.

---

## 1. Context & Goals
- **Problem**: `cli.py` has too many responsibilities (UI layout, interactive shell loops, arguments parsing, server setup).
- **Goal**: Refactor the codebase to segregate presentation concerns and commands logic into the `tui/` package, leaving `cli.py` clean and minimal.

---

## 2. Requirements (BDD Scenarios)

**Scenario 1: Command line execution still runs identical behavior**
- **Given** the agent is executed with one-shot arguments (e.g. `uv run python cli.py --prompt "test"`)
- **When** the process runs
- **Then** it must invoke the TUI runner and execute identical steps as the monolithic script did.

**Scenario 2: Slash commands in interactive mode are resolved correctly**
- **Given** the agent is in interactive mode
- **When** the user types `/context`, `/verbose`, `/clear`, `/loop`, or `/exit`
- **Then** the modular `handle_slash_command` function must capture, process, and direct the behavior correctly.

**Scenario 3: Zero regressions in CLI tests**
- **Given** tests mock `cli.Agent` and others
- **When** `pytest` is executed
- **Then** `tests/test_cli_loop.py` must pass cleanly without modification or with minimal compatible updates.

---

## 3. Constraints & Risks
- Ensure that `cli.py` still contains the `run_cli` entry point so we do not break external scripts or pyproject run targets.

---

## 4. Status
- **DRAFT**

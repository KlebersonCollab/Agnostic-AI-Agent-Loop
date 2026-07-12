# SDD Specification: loop_command

This is the source of truth for the functional requirements of the `/loop` command feature.

---

## 1. Context & Goals
- **Problem Statement**: For complex, long-running task sessions, the agent's default step limit (usually 15-200 steps) can interrupt the execution prematurely, forcing the agent to write a handover checkpoint and requiring the user to manually resume it. The user needs a way to run the agent in a "loop" mode where the step limit is effectively removed (set to a very high limit like 10,000 steps) so the agent can execute until completion without interruption.
- **Scope**:
  - Add support for a `/loop <prompt>` prefix/command in interactive mode.
  - Add support for a `/loop <prompt>` prefix in command-line one-shot mode (`--prompt "/loop ..."`).
  - When `/loop` is used, temporarily set the maximum steps to `10000` to allow uninterrupted execution.
  - Display a distinct status banner (in red) to warn that loop mode is active.
- **Success Criteria**:
  - Typing `/loop` without arguments in interactive mode prints usage instructions.
  - Typing `/loop <prompt>` runs the prompt with a maximum of 10,000 steps.
  - The step limit is restored to the default once the loop execution completes.
  - Extensive unit tests verify the `/loop` parsing and command execution in both interactive and one-shot modes.

## 2. Requirements (BDD Scenarios)

### Feature: /loop Command Mode

**Scenario 1: Interactive /loop command with prompt**
- **Given** the interactive agent console is running
- **When** the user types `/loop make a full refactoring of file x`
- **Then** the agent's maximum steps is temporarily set to 10,000, a red status panel is shown, and the agent executes the task until completion. After completion, the step limit is restored to its original value.

**Scenario 3: Interactive /loop command usage help**
- **Given** the interactive agent console is running
- **When** the user types `/loop` with no prompt content
- **Then** the console prints a help message explaining the usage and does not start the agent.

## 3. Constraints & Risks
- **Dependencies**: None. Purely CLI and Agent wrapper logic.
- **Performance/Safety**: To prevent runaway billing or infinite loops, we enforce a large but finite safety cap of 10,000 steps instead of an actual infinite loop.

---

## 4. Status
- **AGREE**

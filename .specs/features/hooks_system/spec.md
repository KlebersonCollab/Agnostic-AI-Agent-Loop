# SDD Specification: hooks_system (spec.md)

Functional requirements and business logic for the Hooks System.

---

## 1. Context & Goals
- **Problem Statement**: The agent loop, tool calls, and API request cycles need extensibility points (hooks) so that custom scripts can run before, during, or after operations.
- **Scope**:
  - Expose 11 distinct hook event triggers.
  - Dynamically load Python files (`*.py`) from two directories:
    1. Built-in package hooks location (`.agents/hooks/` in the project root directory).
    2. Local workspace hooks location (`.agents/hooks/` in the current working directory).
  - Resolve conflicts by letting CWD hooks override package-level hooks with the same file name.
  - Maintain alphabetical ordering of hook execution.
  - Fail-safe execution: Errors inside hooks must be caught and logged to stderr without crashing the main agent execution.

- **Success Criteria**:
  - The `HooksManager` successfully initializes and scans the specified folders.
  - All 11 triggers work correctly, passing the correct arguments and receiving return values when necessary.
  - Core agent loop, tool execution, and provider API requests invoke the appropriate hooks.
  - 100% of unit tests pass.

---

## 2. Requirements (BDD Scenarios)

### Feature: Dynamic Hooks Loading and Execution

**Scenario 1: Load hooks from package and local workspace with overrides**
- **Given** a built-in hook file named `git_autocommit.py` in `.agents/hooks/post_step/`
- **And** a local workspace hook file named `git_autocommit.py` in the current working directory's `.agents/hooks/post_step/`
- **When** the HooksManager initializes
- **Then** only the local workspace version of `git_autocommit.py` is loaded and executed.

**Scenario 2: Triggering pre-tool-call and post-tool-call hooks**
- **Given** a registered tool named `calculate` and hook handlers in `pre_tool_call` and `post_tool_call`
- **When** the agent executes `calculate`
- **Then** the `pre_tool_call` hooks execute first, potentially modifying the tool arguments
- **And** the tool runs with modified arguments
- **And** the `post_tool_call` hooks execute last, potentially modifying the result.

**Scenario 3: Fail-safe hook execution**
- **Given** a hook handler that raises an unhandled exception
- **When** the hook trigger is fired
- **Then** the exception is captured, printed to standard error, and the agent loop continues unaffected.

---

## 3. Constraints & Risks
- **Security**: Hooks are local Python files. We assume files in `.agents/hooks` are trusted since they are created by the user or part of the package.
- **Performance**: Hook loading using `importlib` is performed once at startup. Thread-safe execution is required because tools can run concurrently.
- **Dependencies**: None beyond Python standard library (`importlib`, `os`, `sys`).

---

## 4. Status
- **MODIFIED** - Automatically aligned with user prompt requirements.

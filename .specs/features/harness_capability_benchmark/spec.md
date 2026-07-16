# SDD Specification: spec.md

This specification defines the functional requirements for comparing the capabilities of the Agnostic Agent in Classic (single-agent) vs. Orchestrator (coordinator-worker) modes.

---

## 1. Context & Goals
- **Problem Statement**: Users observe that transitioning from a single monolithic agent (Classic mode) to a coordinator-worker architecture (Orchestrator mode) may result in reduced task performance, higher latency, and failure to solve complex logical tasks due to context dilution and tool restrictions on the leader.
- **Scope**:
  - Implement a Python script/test harness in `scripts/benchmark_modes.py`.
  - Load the real OpenRouter provider configuration from `.env`.
  - Compare both modes against 3 distinct tasks:
    1. Operational Integration (File Read + Math Multiplication).
    2. Code Repair and Shell Verification (Read -> Write -> Run Pytest/Assert).
    3. Memory Database retrieval.
  - Measure: Completion success, step count, token consumption, cost, and elapsed time.
- **Success Criteria**: 
  - The script executes successfully and outputs a clear comparative markdown table of metrics.
  - Both modes are evaluated under identical conditions.

## 2. Requirements (BDD Scenarios)

### Feature: Mode Capability Comparison

**Scenario 1: Operational Integration (File IO and Math)**
- **Given** a target file `temp_benchmark_num.txt` containing a numeric value.
- **When** the agent is tasked to read the file, multiply the value by 3, and write the new value back.
- **Then** the file should contain the correct multiplied value upon agent completion, and the metrics are logged.

**Scenario 2: Code Debugging and Validation**
- **Given** a python file `temp_benchmark_code.py` containing a function with a bug (e.g. subtracting instead of adding).
- **When** the agent is tasked to fix the function so it passes a simple assert test, and run a bash validation command.
- **Then** the function must be corrected, the command must execute successfully, and the metrics are logged.

**Scenario 3: Memory Query**
- **Given** a specific decision or fact exists in the agent's SQLite memory.
- **When** the agent is asked to retrieve the date of a specific database decision.
- **Then** the final response must contain the correct date, and the metrics are logged.

## 3. Constraints & Risks
- **API Cost**: Running real LLM calls consumes credits. The benchmark must be concise.
- **LLM Flakiness**: Use a model with consistent behavior (loaded from `.env`).
- **Cleanliness**: The script must clean up all temporary benchmark files (`temp_*`) after completion to avoid polluting the workspace.

---

## 4. Status
- **AGREE** - Agree with the specification plan

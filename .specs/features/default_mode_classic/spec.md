# SDD Specification: spec.md

This specification defines the functional requirement to change the default agent execution mode from "orchestrator" to "classic".

---

## 1. Context & Goals
- **Problem Statement**: The current default mode is `orchestrator`, which limits the agent's tool access and leads to sub-optimal operational performance (latency, telephone game context dilution) for typical development tasks.
- **Scope**:
  - Update `cli.py` to default `--mode` to `classic`.
  - Ensure the agent retains the capability to execute tasks directly and delegate if needed.
  - Verify that all unit and integration tests continue to pass.
- **Success Criteria**: 
  - Executing `agnostic-agent` or running the CLI without `--mode` defaults to `classic` mode.
  - The test suite executes successfully.

## 2. Requirements (BDD Scenarios)

### Feature: Default Mode Selection

**Scenario 1: Default execution mode without arguments**
- **Given** the CLI configuration parser in `cli.py`.
- **When** the user runs the CLI without passing the `--mode` argument.
- **Then** the parsed argument `args.mode` must equal `"classic"`.

## 3. Constraints & Risks
- **Backward Compatibility**: Ensure that explicit passing of `--mode orchestrator` still functions perfectly.

---

## 4. Status
- **AGREE** - Agree with the specification plan

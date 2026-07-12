# SDD Specification: subagent_ui_enhancement

This is the source of truth for **functional requirements** and **business logic** for the Subagent UI Enhancement.

---

## 1. Context & Goals
- **Problem Statement**: When multiple subagents run in parallel, their console logs interleave. The current format is simple and verbose:
  `[Subagent: Role] --- Step 1 / 10 ---`
  `[Subagent: Role] 🤖 Thought: ...`
  This lacks structure, alignment, and alignment between columns, making concurrent execution hard to follow visually.
- **Scope**:
  - **In-Scope**:
    - Enhance [CollectingAgentListener](file:///home/klebersonromero/Projetos/teste/tools/multi_agent.py#L27) to output beautifully aligned, structured logs.
    - Format components (Role tag, Step progress, Event type, Content) into clear columns.
    - Utilize Rich colors and styles to distinguish events (Thoughts, Tool Calls, Outputs, Completion).
  - **Out-of-Scope**:
    - Rewriting the CLI listener of the main agent ([ConsoleAgentListener](file:///home/klebersonromero/Projetos/teste/cli.py#L26)).
- **Success Criteria**:
  - Log output columns are aligned and easily scannable.
  - Subagent roles are clearly color-coded.
  - All test suites still pass.

## 2. Requirements (BDD Scenarios)

### Feature: Subagent UI Enhancement

**Scenario 1: Aligned columns on step execution**
- **Given** multiple subagents with roles of different lengths (e.g. "Backend Data Layer Auditor" and "Test Suite Auditor")
- **When** they emit events (Thought, Tool Call, Output)
- **Then** the role column must be padded to a fixed width to keep logs aligned.
- **And** the step info must be formatted as `Step X/Y` in a dimmed style.
- **And** each event type must be preceded by a distinct badge/emoji.

---
## 3. Status
- **AGREE**

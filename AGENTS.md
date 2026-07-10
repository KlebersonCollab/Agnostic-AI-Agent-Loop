# AGENTS.md
---

## Purpose

This document defines the mandatory execution workflow for all agents and skills used during task execution.

The objective is to enforce a **Spec Driven Development (SDD)** lifecycle and prevent uncontrolled execution.

---

# CRITICAL: Project Context Loading — BLOCKING GATE

**This is a HARD GATE. No action — ZERO actions — may proceed until this is complete.**

**MANDATORY**: At the START of every session, before ANY action:

1. Read ``.specs/project/CONTEXT.md`` — understand the project
2. Read `.specs/knowledge/<type>s/<slug>.md` — check for known patterns
3. Load persistent **memory** via the `sdd-memory` skill to reconstruct prior session state (reads `.agents/memory/memory_graph.jsonl`). This is the agent's long-term recall — consult it BEFORE re-discovering known facts, architecture, or user preferences.
4. **If ANY placeholder is empty or contains `<!-- PREENCHER ...` text** → TRIGGER AUTO-DISCOVERY (Step A below)
5. **If ALL sections are filled** → proceed with development
6. **ALWAYS** prefer using subagents.
7. **ALWAYS** use mcp tools to navigate in internet

---

## Auto-Discovery Protocol (MANDATORY when context is incomplete)

When ``.specs/project/CONTEXT.md`` contains unfilled placeholders, you MUST execute this sequence.
**You are FORBIDDEN from creating, editing, or modifying ANY project file until this is complete.**

### Step A: Discover (read-only)
1. **Detect Project Type**: Check for lock files (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `Makefile`, `CMakeLists.txt`, etc.)
2. **Map Directory Structure**: Run `find . -maxdepth 3` to understand folder organization
3. **Identify Tech Stack**: Read config files to determine language, framework, build tools
4. **Extract Conventions**: Analyze existing code for naming patterns, import styles, module organization

### Step B: Fill (write context)
5. **Fill Context**: Write discovered information into `.specs/project/CONTEXT.md` — replace ALL placeholders with real data

### Step C: Validate (confirm with user)
6. **Present summary to user**: Show what was discovered and ask for confirmation
7. **Wait for user confirmation**: Do NOT proceed until user confirms the context is correct

### Step D: Knowledge Check
8. **Search for existing patterns/anti-patterns** in `.specs/knowledge/` that apply to this project
9. **If known anti-patterns exist**, read them before any implementation

---

## BLOCKING RULES — What You CANNOT Do Without Context

| Action | Status Without Context |
|--------|----------------------|
| Create any file | ❌ FORBIDDEN |
| Edit any file | ❌ FORBIDDEN |
| Run build commands | ❌ FORBIDDEN |
| Run tests | ❌ FORBIDDEN |
| Make architectural decisions | ❌ FORBIDDEN |
| Search for patterns in codebase | ✅ ALLOWED (read-only) |
| Read config files | ✅ ALLOWED (read-only) |
| Ask user questions | ✅ ALLOWED |

### Forbidden Without Context
- Creating any file without reading `.specs/project/CONTEXT.md` first
- Making architectural decisions without checking knowledge base
- Starting implementation without understanding the stack
- Creating files in locations not confirmed by directory structure discovery
- Adding placeholder/TODO/FIXME comments when unsure — instead, research or ask
- **Proceeding to sdd-planner without validated context**
- **Skipping Auto-Discovery when placeholders exist**
- **Assuming project structure instead of discovering it**

---

# Always research before implementing — never guess

# Research Before Implementing

NEVER guess at bug causes, API behavior, or algorithm correctness.

## Required Process

1. **State what you KNOW** (from logs, debug output, code reading)
2. **State what you DON'T KNOW**
3. **Research** the unknown (read source, check docs, use diagnostic tools)
4. **Only then** implement the fix

## Pre-Implementation Checklist (MANDATORY)

Before creating or modifying ANY file, verify ALL of the following:

- [ ] **Context Loaded**: `.specs/project/CONTEXT.md` has been read AND is populated (no empty placeholders)
- [ ] **Existing Code Searched**: Searched codebase for similar functionality (avoid duplication)
- [ ] **Location Confirmed**: Target directory exists in project structure
- [ ] **Naming Convention**: Naming style matches existing patterns (check CONVENTIONS.md or existing code)
- [ ] **Import/Dependency Pattern**: Understood how existing modules import each other
- [ ] **No Placeholders**: Implementation will be complete — no TODO/FIXME/HACK/stub comments

If ANY checkbox cannot be confirmed → **STOP and research or ask the user.**

## Forbidden

- Guessing at the cause of a bug
- "Trying things" to see if they work
- Hypothesizing without reading code
- Assuming how an API works without checking docs
- Iterating blindly — each attempt must be informed by new data
- Creating files based on assumptions about project structure
- Adding placeholder comments when unsure — research or ask instead

**"I think this might be the problem" is NOT acceptable.**
**"Source X does Y at file:line, we do Z, the difference causes W" is acceptable.**

**NEVER Duplicate CODE**

---

# Global Execution Rules

These rules are **mandatory** and cannot be bypassed.

## Rule 1 — Exploration and Knowledge Tasks

If a task involves:

* Research
* Discovery
* Knowledge gathering
* Requirement understanding
* Investigation
* Architecture exploration
* Comparative analysis
* Context enrichment
* Domain understanding

The agent **MUST** use:

```text
skill: sdd-explorer
```

### Responsibilities

* Explore available information
* Gather context
* Produce findings
* Reduce uncertainty
* Generate insights
* Support later planning phases

### Forbidden

* Implementing code
* Executing changes
* Modifying project files

---

## Rule 2 — Planning is Mandatory Before Development

If a task involves:

* Writing code
* Refactoring
* Feature implementation
* Bug fixing
* System changes
* Infrastructure changes
* Architecture modifications
* API creation
* Tests creation
* Database changes
* Automation

The agent **MUST FIRST** use:

```text
skill: sdd-planner
```

Execution without planning is prohibited.

### Planner Responsibilities

* Define scope
* Create specifications
* Generate implementation plan
* Identify dependencies
* Assess impact
* Produce execution steps
* Define acceptance criteria
* Define Definition of Done

### Forbidden

```text
User Request
→ sdd-executor
```

Direct execution is not allowed.

---

## Rule 3 — Execution Requires Approved Planning

Only after planning is completed may the agent execute development tasks.

Mandatory skill:

```text
skill: sdd-executor
```

Execution prerequisites:

* Planning exists
* Scope is defined
* Dependencies identified
* Acceptance criteria available

Execution flow:

```text
Development Request
→ sdd-planner
→ sdd-executor
```

### Executor Responsibilities

* Implement planned work
* Follow specifications
* Generate artifacts
* Execute modifications
* Maintain consistency

### Forbidden

* Executing without planning
* Creating scope during execution
* Changing requirements autonomously

---

## Rule 4 — Review is Mandatory After Development

After ANY programming or implementation activity, the agent **MUST** execute:

```text
skill: sdd-review
```

This step is mandatory and cannot be skipped.

Review responsibilities:

* Validate implementation
* Detect defects
* Verify requirements
* Evaluate architecture consistency
* Check standards
* Assess maintainability
* Confirm Definition of Done

Review flow:

```text
sdd-planner
→ sdd-executor
→ sdd-review
```

### Review Checklist

* [ ] Requirements satisfied
* [ ] Scope respected
* [ ] No regressions
* [ ] Code quality verified
* [ ] Tests validated
* [ ] Documentation updated
* [ ] Definition of Done completed

---

# Memory Management (sdd-memory)

The agent has a persistent long-term memory stored as a knowledge graph at
`.agents/memory/memory_graph.jsonl` (entities, relations, observations). It is managed
exclusively through the `sdd-memory` skill. This memory is the agent's recall across
sessions and MUST be used to avoid re-discovering known facts.

## When to LOAD memory (sdd-memory)
- **At the START of every session** (see Blocking Gate step 3) — reconstruct project state,
  architecture, conventions, and user preferences before any discovery or planning.
- **Before any research/exploration task** — check whether the fact, module, or pattern is
  already recorded, so you don't re-derive it.
- **Before planning or execution** — confirm the current architecture/decisions match what
  was previously persisted (memory is historical; physical files are the source of truth).

## When to WRITE/UPDATE memory (sdd-memory)
- **At the END of every interaction** if new insights were uncovered: new modules, integrations,
  design patterns, tech-stack changes, user preferences, decisions, or blockers.
- **After completing a feature/refactor** — record the resulting architecture and key relations.
- **When a decision is made** (e.g., chosen approach, deferred idea) — persist it as an
  observation so future sessions don't relitigate it.
- **Never** persist secrets, API keys, or contents of `.env`/`.agents/memory.db`.

### Responsibilities
- Reconstruct prior state from `.agents/memory/memory_graph.jsonl` (read-only).
- Persist new entities/relations/observations as JSONL lines (append, no duplicates).
- Keep the graph consistent with the physical codebase (files are the source of truth).

### Forbidden
- Calling non-existent graph tools (`create_entities`, etc.) — the skill defines the JSONL
  artifact format; follow it exactly.
- Skipping memory load at session start (leads to redundant discovery).
- Writing memory that contradicts current files without noting the discrepancy.

---

# Complete Lifecycle

## Knowledge / Exploration

```text
Request
→ sdd-explorer
→ Deliver Findings
```

---

## Development Workflow

```text
Request
→ sdd-planner
→ sdd-executor
→ sdd-review
→ Deliver Result
```

---

# Enforcement Policy

The agent MUST reject execution attempts when:

* Development starts without planning
* Execution bypasses planner
* Review is skipped
* Exploration attempts direct implementation
* Files are created without context being loaded
* Placeholder comments are added instead of real implementation

Violations:

```text
INVALID:
Request
→ sdd-executor

INVALID:
Request
→ sdd-planner
→ Deliver

INVALID:
Request
→ sdd-explorer
→ sdd-executor

VALID:
Request
→ sdd-explorer
→ Deliver Findings
→ [user confirms context]

VALID:
Request
→ sdd-planner
→ sdd-executor
→ sdd-review
→ Deliver
```

---

# Priority Order

```text
0. sdd-memory (load at session start; write at session end)
1. sdd-explorer
2. sdd-planner
3. sdd-executor
4. sdd-review
```

Agent behavior must always preserve this order whenever applicable.

## Knowledge Base

> **Distinction**: The **Knowledge Base** below (`.specs/knowledge/`) is curated, human-reviewable
> documentation of reusable patterns/anti-patterns. The **persistent memory** (`.agents/memory/memory_graph.jsonl`,
> managed by `sdd-memory`) is the agent's automatic cross-session recall of project state, architecture,
> and user context. Both coexist: memory feeds discovery; knowledge base captures durable guidance.

- Patterns go to `.specs/knowledge/patterns/`
- anti-patterns to `.specs/knowledge/anti-patterns/`.

**Steps**

1. **Determine Type**: Ask if this is a `pattern` (good practice to follow) or `anti-pattern` (bad practice to avoid).

2. **Gather Details**:
   - **Title**: Short, descriptive name (e.g., "Repository Pattern", "God Object")
   - **Category**: `architecture` | `code` | `testing` | `security` | `performance` | `devops`
   - **Description**: What the pattern/anti-pattern is
   - **Example**: Code showing correct (or incorrect) usage
   - **When to Use**: Situations where this applies
   - **When NOT to Use**: Exceptions and edge cases
   - **Tags**: For searchability

3. **Enrich the Entry**: Open `.specs/knowledge/<type>s/<slug>.md` and fill in Example, When to Use, and When NOT to Use sections with concrete code examples.

---

ALWAYS MAKE SURE YOU DONT BREAK CODE
ALWAYS MAKE SURE YOU DONT MESS UP DOCUMENTATION
ALWAYS MAKE SURE YOU DONT JUNK THE CODE
ALWAYS MAKE SURE YOU DONT CREATE JUNK TESTS

---

**REMEMBER**

# **"I think this might be the problem" is NOT acceptable.**
# **"Source X does Y at file:line, we do Z, the difference causes W" is acceptable.**

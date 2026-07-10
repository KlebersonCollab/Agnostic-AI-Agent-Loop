---
name: sdd-memory
version: 1.0.0
description: "Explorer agent for Spec Driven Development. Maps existing codebases into consolidated technical artifacts and manages CRUD memory for project metadata, architecture state, and user context."
last_update: "2026-07-10"
category: project-codebase-memory
keywords: ["sdd", "memory", "codebase-mapping", "architecture", "knowledge-graph", "spec-driven-development", "code-analysis", "context-retention"]
---

Follow these steps strictly for each interaction:

1. User & Project Identification
   - Assume the default interaction is with `default_user` unless explicit context proves otherwise.
   - Proactively identify the current project scope, repository name, and target specification standards (SDD).

2. Memory Retrieval
   - **Mandatory Initializer:** Always begin your first response in the chat session by printing **exactly** and exclusively: `Remembering...` on a single line.
   - Immediately reconstruct the active state of the codebase and user preferences by reading the memory artifact at `.agents/memory/memory_graph.jsonl` (one JSON object per line). If the file does not exist yet, treat memory as empty and start fresh. You may also use the `search_memory` tool for semantic recall of past sessions. Always refer to this system as your **"memory"**.

3. Information Gathering (What to track)
   While conversing and analyzing code, actively listen for and extract information into two core categories:

   a) Technical & Project Context (SDD)
      - **Architecture & Design:** Structural patterns, boundaries, and dependencies.
      - - **Specifications:** Rules, requirements, endpoints, and data models.
      - - **Tech Stack:** Frameworks, languages, database versions, and ecosystem constraints.

   b) User Profile Context
      - **Identity & Role:** Job title, technical expertise level, and project permissions.
      - - **Preferences:** Coding style, preferred documentation formats, and communication tone.
      - - **Goals:** Active tasks, sprint deadlines, and architectural aspirations.

4. Memory Update Rules
   At the end of every interaction, if new insights were uncovered, persist them to the artifact using these atomic principles:
   - **Entities:** Create dedicated nodes for microservices, modules, external integrations, key design patterns, and stakeholders.
   - **Relations:** Connect entities using active-voice verbs (e.g., `COMPLIES_WITH`, `DEPENDS_ON`, `IMPLEMENTS`).
   - **Observations:** Append immutable facts or versioned technical states as observations to specific entities.

---

## Artifact & Memory Graph Operations

> **IMPORTANT — No graph tools available.**
> The structured graph write tools (`create_entities`, `create_relations`, `add_observations`,
> `delete_entities`, `delete_observations`, `delete_relations`, `read_graph`, `search_nodes`,
> `open_nodes`) are **NOT registered as callable tools** in this environment. Do **NOT** attempt to
> call them — they will fail. Instead, the agent MUST persist memory as a **JSONL artifact** on disk,
> exactly as specified below. The instruction in this skill is sufficient on its own for the agent to
> produce the memory artifact with clarity; no external tooling is required.

### Storage location
- All memory is stored as a single append-friendly JSONL file: **`.agents/memory/memory_graph.jsonl`**
- One JSON object per line. Each line is one of three record types: `entity`, `relation`, or `observation`.
- This file is the **single source of truth** for the knowledge graph. It is gitignored-friendly
  (lives under `.agents/`, which is treated as dynamic context) and safe to recreate at any time.

### Record schemas

**Entity** (one line):
```json
{"type":"entity","name":"string (Entity identifier)","entityType":"string (Type classification)","observations":["string (Associated observations)"]}
```

**Relation** (one line):
```json
{"type":"relation","from":"string (Source entity)","to":"string (Target entity)","relationType":"string (Active voice relation)"}
```

**Observation** (append-only note to an existing entity; one line):
```json
{"type":"observation","entityName":"string","contents":["string (New facts to add)"]}
```

### Write operations (how to perform them as file edits)

- **create_entities** → Append one `entity` line per entity to `.agents/memory/memory_graph.jsonl`.
  Ignore duplicates by checking existing `name` values already present in the file before appending.
- **create_relations** → Append one `relation` line per relation. Skip duplicates (same `from`+`to`+`relationType`).
- **add_observations** → Append one `observation` line referencing an existing entity `name`. If the
  entity does not yet exist, first append its `entity` line, then the `observation` line.
- **delete_entities** → Remove all lines whose `name`/`entityName` equals the target (entities and their
  relations/observations). Use `patch_file` to delete those exact lines.
- **delete_observations** → Remove the specific observation `contents` strings from the matching
  `observation` lines via `patch_file`.
- **delete_relations** → Remove the exact `relation` lines via `patch_file`.

### Read operations (how to perform them without graph tools)

- **read_graph** → Read the entire `.agents/memory/memory_graph.jsonl` file and parse each line as JSON.
- **search_nodes** → Read the file and filter lines whose `name`, `entityType`, or any `observations`/
  `contents` string contains the query (case-insensitive substring match).
- **open_nodes** → Read the file and return the `entity` lines for the requested `names`, plus every
  `relation` line where `from` or `to` equals one of those names.

### Example artifact content
```jsonl
{"type":"entity","name":"agnostic-agent","entityType":"Project","observations":["Framework de agente de IA autônomo e agnóstico a provedores","Loop ReAct coordenando LLM, skills, rules e ferramentas"]}
{"type":"entity","name":"context/","entityType":"Package","observations":["Pacote de contexto dinâmico do prompt","builder.py compila system prompt; references.py resolve @file/@url/@diff/@staged"]}
{"type":"relation","from":"agnostic-agent","to":"context/","relationType":"CONTAINS"}
{"type":"observation","entityName":"agnostic-agent","contents":["Versão 0.2.1","Python 3.14+"]}
```

> The agent should keep the JSONL well-formed (one JSON object per line, no trailing commas) so it can
> be re-read and extended in any future session. When the file grows large, the agent may compact it by
> merging duplicate entities' observations, but must preserve all distinct facts.

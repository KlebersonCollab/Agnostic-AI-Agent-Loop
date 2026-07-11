---
name: sdd-memory
version: 1.1.0
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

> **Evolution note (2026):** The schema below is backward compatible. Every field beyond the
> original core (`type`, `name`/`from`/`to`, `entityType`, `relationType`, `observations`/`contents`)
> is **OPTIONAL** and defaults safely when absent. This closes the gaps identified against the 2026
> agent-memory literature: temporal state & supersession (A-TMA 2607.01935, Supersede 2606.27472),
> functional-role isolation (MemGuard 2605.28009), write verification (TrustMem 2606.25161), and
> decay/consolidation (FadeMem 2601.18642, Manufactured Confidence 2606.29279).

**Entity** (one line):
```json
{"type":"entity","name":"string (Entity identifier)","entityType":"string (Type classification)","observations":["string (Associated observations)"],"role":"architecture|user_profile|episodic|rule|decision|preference|project_state|feedback","state":"current|historical|transition","confidence":"high|medium|low|tentative","access_count":0,"last_accessed":"ISO8601|null"}
```
- `role` *(optional, default `architecture`)*: functional classification used to prevent heterogeneous
  memory contamination (MemGuard). Keep stable facts, episodic events, rules, and decisions in separate
  roles so retrieval can be scoped to a single role.
- `state` *(optional, default `current`)*: temporal status. `historical` = superseded/obsolete;
  `transition` = in-flight change not yet finalized. Prevents *ghost memory* (A-TMA).
- `confidence` *(optional, default `high`)*: `tentative` preserves hedged phrasing ("might prefer X")
  and MUST NOT be upgraded to a flat assertion on write (Manufactured Confidence). `low` flags
  weakly-supported claims.
- `access_count` / `last_accessed` *(optional)*: maintenance signals for decay/consolidation.

**Relation** (one line):
```json
{"type":"relation","from":"string (Source entity)","to":"string (Target entity)","relationType":"string (Active voice relation)","state":"current|historical|transition","superseded_by":"<relation signature>|null"}
```
- `state` *(optional, default `current`)*: same temporal semantics as entities.
- `superseded_by` *(optional)*: links a `historical` relation to the relation that replaced it.

**Observation** (append-only note to an existing entity; one line):
```json
{"type":"observation","entityName":"string","contents":["string (New facts to add)"],"state":"current|historical|transition","confidence":"high|medium|low|tentative"}
```
- `state` / `confidence` *(optional, defaults `current` / `high`)*: same semantics as above.

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
- **supersede** → When a fact changes (user moves, plan revised, decision reversed), NEVER blind-overwrite.
  Instead: (1) patch the old record's line to `"state":"historical"`; (2) append the new record with
  `"state":"current"`; (3) link them with a relation
  `{"type":"relation","from":"<old name>","to":"<new name>","relationType":"SUPERSEDED_BY","state":"historical"}`
  (or, for an observation, append a marker observation
  `{"type":"observation","entityName":"<old name>","contents":["<fact> (superseded by: <new fact>)"],"state":"historical"}`).
  This keeps the audit trail and prevents stale facts from being served as truth (Supersede 2606.27472).

### verify_write — pre-append checklist (TrustMem 2606.25161)
Before appending ANY record, evaluate three signals and encode the result in `confidence`:
- **coverage**: Did we capture the load-bearing fact? If a key fact is missing, still append but note the gap.
- **preservation**: Did we avoid deleting/overwriting prior distinct facts? Use `supersede`, never blind overwrite.
- **faithfulness**: Is the content grounded in observed text / tool output / user statement? If unsupported
  or invented → set `confidence:"low"` or drop the record. **NEVER persist secrets, API keys, or `.env`
  contents** (reinforces the existing AGENTS.md rule). A hedged user remark is stored `confidence:"tentative"`,
  keeping the hedge — it is NOT upgraded to a confident assertion.

### decay & consolidate — maintenance guidance (FadeMem 2601.18642)
- On every read/retrieval of a record, increment its `access_count` and refresh `last_accessed`.
- **consolidate** (agent-triggered, not a daemon): merge duplicate/near-duplicate observations into one;
  fade (`state:"historical"`) records with low `access_count` + low relevance + old `last_accessed`;
  keep ALL distinct facts. `historical` records remain linked for audit. This bounds graph growth without
  the binary "keep everything or lose it" failure mode of naive memory.

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

# SDD Technical Plan: sdd-memory Evolution (sdd_memory_evolution)

Technical blueprint for evolving the `sdd-memory` protocol and its `front/` viewer.

---

## 1. Architecture Overview
`sdd-memory` is a **skill** (markdown instructions in `.agents/skills/memory/SKILL.md`) that governs
how the agent persists a knowledge graph as a JSONL artifact at `.agents/memory/memory_graph.jsonl`.
A lightweight web viewer (`front/server.py` + `front/index.html`) reads that file over HTTP and
renders it with vis-network. There is **no Python graph library** — the schema lives in the SKILL.md
and is consumed by the frontend parser.

The evolution is therefore: (a) extend the schema documented in SKILL.md with optional fields and new
operations; (b) make the frontend parser + renderer aware of those fields (defaulting safely); (c)
add a regression test that loads the *current* graph.

```
.agents/skills/memory/SKILL.md   # protocol: schemas + operations + verify_write + decay  (EDIT)
front/index.html                 # parser + renderer: state badge, role filter/color, ghost flag (EDIT)
tests/test_memory_graph.py       # NEW: regression test loading existing graph + new-field records
```

---

## 2. Technical Design

### 2.1 Extended Record Schemas (all fields OPTIONAL, default-safe)

**Entity** (one line):
```json
{"type":"entity","name":"string","entityType":"string",
 "role":"architecture|user_profile|episodic|rule|decision|preference|project_state|feedback",
 "state":"current|historical|transition",
 "confidence":"high|medium|low|tentative",
 "access_count":0, "last_accessed":"ISO8601|null",
 "observations":["string"]}
```
Defaults when absent: `role="architecture"`, `state="current"`, `confidence="high"`.

**Relation** (one line):
```json
{"type":"relation","from":"string","to":"string","relationType":"string",
 "state":"current|historical|transition",
 "superseded_by":"<relation signature>|null"}
```
Defaults: `state="current"`.

**Observation** (one line):
```json
{"type":"observation","entityName":"string","contents":["string"],
 "state":"current|historical|transition","confidence":"high|medium|low|tentative"}
```
Defaults: `state="current"`, `confidence="high"`.

### 2.2 New Operation: `supersede`
- Mark target record `state="historical"` (patch its line).
- Add a `superseded_by` link: a relation `{"from":<target name>,"to":<new name>,"relationType":"SUPERSEDED_BY","state":"historical"}` OR, for an observation, append a marker observation `{"entityName":<target>,"contents":["<fact> (superseded by: <new fact>)"],"state":"historical"}`.
- The superseding record keeps `state="current"`.

### 2.3 New Guidance: `verify_write` (TrustMem 2606.25161)
Before any append, the agent evaluates three signals and records them implicitly via `confidence`:
- **coverage**: did we capture the load-bearing fact? (missing → still append, but note gap)
- **preservation**: did we avoid deleting/overwriting prior distinct facts? (use `supersede`, never blind overwrite)
- **faithfulness**: is the content grounded in observed text/tool output? (unsupported → `confidence:"low"` or drop; NEVER persist secrets/.env)

### 2.4 New Guidance: `decay` / `consolidate` (FadeMem 2601.18642)
- Track `access_count` / `last_accessed` when a record is retrieved (agent increments on read).
- Compaction procedure (agent-triggered, documented): merge duplicate observations into one; fade
  (`state="historical"`) records with low access_count + low relevance + old age; keep all distinct facts.
- Preserve tentative phrasing: a `confidence:"tentative"` record is NEVER upgraded to a flat assertion on write.

### 2.5 Frontend Changes (`front/index.html`)
- `parseJSONL`: default missing `state`→`current`, `role`→`architecture`, `confidence`→`high`.
- Stats: add a "Stale/Ghost" counter = records with `state="historical"` or `state="transition"`.
- Entity card: show `state` badge (current=green, historical=secondary, transition=warning) and `role` badge.
- Type filter: extend to also filter by `role` (add a second select or merge into existing filter with a prefix).
- Graph node title: include `state` + `role` + `confidence`.
- Color: add `ROLE_COLORS` mapping so role is visually distinguishable; `historical` nodes get a dashed border.
- Ghost indicator: nodes that have both a `current` and a `historical` version of the same `name` (or linked via SUPERSEDED_BY) get a subtle warning ring.

### 2.6 Regression Test (`tests/test_memory_graph.py`)
- Loads the **actual** `.agents/memory/memory_graph.jsonl` from disk (if present) and asserts it parses
  with zero errors and that every entity has a defaulted `state`/`role`/`confidence`.
- Builds a small in-memory JSONL with the new fields and asserts the parser assigns them correctly and
  that `supersede` logic marks the old record `historical`.
- No network, no browser: pure `json` parsing mirroring the frontend logic (kept in sync by contract).

---

## 3. Implementation Strategy

### Isolation
- Only `.agents/skills/memory/SKILL.md`, `front/index.html`, and a new `tests/test_memory_graph.py` are touched.
- `memory.py`, `agent.py`, `cli.py` are NOT modified (separate "Agent Memory" system).

### Testing Strategy
- Unit/regression: `tests/test_memory_graph.py` parses both the live graph and synthetic new-schema records.
- Manual: `python front/server.py --no-browser` then load `/api/memory.jsonl` and confirm badges/filters.

### Migrations
- None required. Existing graph is valid as-is (all new fields optional).

---

## 4. Status
- **NEEDS_REVIEW**

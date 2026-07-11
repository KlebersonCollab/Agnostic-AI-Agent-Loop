# SDD Specification: sdd-memory Evolution (sdd_memory_evolution)

This specification defines the functional requirements and business logic for evolving the
`sdd-memory` skill — the persistent cross-session knowledge graph stored at
`.agents/memory/memory_graph.jsonl` — to close the gaps identified against the 2026 agent-memory
literature (graph-based memory surveys, MAGMA, MemGuard, A-TMA, Supersede, TrustMem, FadeMem).

---

## 1. Context & Goals

### Problem Statement
The current `sdd-memory` protocol stores a flat knowledge graph of `entity` / `relation` /
`observation` records. It works, but the literature shows four structural gaps that cause real
failures in long-horizon agents:

1. **No temporal state / supersession (Ghost Memory — A-TMA 2607.01935; Supersede 2606.27472).**
   Facts that change over time (user moves, plan revised, decision reversed) coexist with current
   facts and contaminate retrieval. The graph cannot distinguish *current* from *historical* or
   *transition* state, so stale facts are served as truth.
2. **No functional role / type isolation (MemGuard 2605.28009).**
   Stable user facts, episodic events, behavioral rules, and project architecture are collapsed into
   one undifferentiated space, enabling heterogeneous memory contamination.
3. **No write verification (TrustMem 2606.25161).**
   Appends can omit important info, corrupt existing memory, or introduce unsupported/hallucinated
   content. Once stored, errors become persistent system-state failures.
4. **No decay / consolidation (FadeMem 2601.18642; Manufactured Confidence 2606.29279).**
   The graph only grows; there is no mechanism to fade irrelevant details, consolidate duplicates, or
   preserve tentative phrasing instead of "upgrading" hedges into confident assertions.

### Goal
Evolve the `sdd-memory` protocol (SKILL.md) and the `front/` viewer so the knowledge graph gains:
- **Temporal state** (`current` / `historical` / `transition`) with supersession semantics.
- **Functional role** per memory record (`architecture`, `user_profile`, `episodic`, `rule`, `decision`, `preference`, `project_state`, `feedback`).
- **A write-time verifier** (coverage / preservation / faithfulness) that the agent runs before
  persisting, plus a `confidence` field that preserves tentative phrasing.
- **Decay / consolidation guidance** (access-frequency + relevance + age) and a compaction procedure.

All changes MUST remain **backward compatible**: the existing `memory_graph.jsonl` (and any future
minimal records) must continue to load, render, and be queryable without modification.

### Scope
* **Included:**
  * Extended record schemas for `entity`, `relation`, `observation` (optional new fields, all default-safe).
  * New `supersede` operation (mark a record as `historical` and link the superseding record).
  * New `verify_write` guidance + `confidence` field semantics.
  * New `decay` / `consolidate` maintenance guidance.
  * Frontend rendering of `state` (badge + styling) and `role` (filter + color), plus a "stale/ghost" indicator.
  * Updated SKILL.md with the full evolved protocol, examples, and a verification checklist.
  * A regression test that loads the *existing* graph and asserts it still parses and renders.
* **NOT Included:**
  * Changing `memory.py` (the SQLite FTS5 episodic store) — that is a separate system ("Agent Memory").
  * Building a separate Python library for the graph (the JSONL-as-artifact approach is retained).
  * Automated background compaction daemon (guidance only; agent-triggered compaction).

---

## 2. Requirements (BDD Scenarios)

### Feature: Temporal State & Supersession

**Scenario 1: Recording a changing fact with state**
- **Given** The user says "I moved to Lisbon" after a prior memory "user lives in Porto".
- **When** The agent persists the new fact as an `observation`/`entity` with `"state":"current"` and calls `supersede` on the Porto record.
- **Then** The Porto record is marked `"state":"historical"` with a `superseded_by` link to the Lisbon record, and retrieval for "where does the user live" returns the Lisbon (current) record, not Porto.

**Scenario 2: Transition state during change**
- **Given** A plan is being revised but not yet finalized.
- **When** The agent records the in-flight revision as `"state":"transition"`.
- **Then** The record is retrievable but visually flagged as provisional in the frontend, and does not overwrite the still-current plan.

### Feature: Functional Role Isolation

**Scenario 3: Tagging memory by role**
- **Given** The agent stores a stable user preference and a one-off episodic event.
- **When** It tags the preference `"role":"preference"` and the event `"role":"episodic"`.
- **Then** The frontend offers a role filter, and retrieval can be scoped to a single role to avoid cross-role contamination (MemGuard).

### Feature: Write Verification & Confidence

**Scenario 4: Verifying before write**
- **Given** The agent is about to append a new observation to an entity.
- **When** It runs the `verify_write` checklist (coverage: did we capture the key fact? preservation: did we avoid deleting prior facts? faithfulness: is it grounded in observed text, not invented?).
- **Then** If faithfulness fails (unsupported claim), the agent either drops the record or marks `"confidence":"low"` rather than storing a confident assertion.

**Scenario 5: Preserving tentative phrasing**
- **Given** A user remark is hedged ("I might prefer X").
- **When** The agent stores it.
- **Then** It is stored with `"confidence":"tentative"` keeping the hedge, NOT upgraded to a flat confident fact (Manufactured Confidence 2606.29279).

### Feature: Decay & Consolidation

**Scenario 6: Compaction preserves distinct facts**
- **Given** The graph has grown with duplicate/near-duplicate observations.
- **When** The agent runs the documented `consolidate` procedure (merge duplicates, fade low-access low-relevance old records, keep all distinct facts).
- **Then** The resulting graph is smaller, no distinct fact is lost, and `historical` records remain linked for audit.

### Feature: Backward Compatibility

**Scenario 7: Existing graph still loads**
- **Given** The current `.agents/memory/memory_graph.jsonl` (flat records, no `state`/`role`/`confidence`).
- **When** The evolved frontend and parser load it.
- **Then** All entities/relations/observations render; missing fields default to `current` / `architecture` / `high` without error.

---

## 3. Constraints & Risks
* **Backward Compatibility (HARD):** Every new field is optional. Parsers MUST default missing fields.
* **No graph tools:** The protocol still persists via JSONL file edits (append/patch), never calling
  non-existent graph tools.
* **Security:** The existing rule "never persist secrets / .env contents" is preserved and reinforced
  under `verify_write` (faithfulness excludes secrets).
* **Frontend:** Pure stdlib server + CDN libs; no new build step. New fields rendered without breaking
  the existing vis-network graph.

---

## 4. Status
- **NEEDS_REVIEW**

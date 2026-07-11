# SDD Tasks: sdd-memory Evolution (sdd_memory_evolution)

Atomic task list for implementation tracking.
*Mandatory: Each [x] must correspond to at least one atomic Git commit and valid evidence.*
*Only the Executor can mark with the [x] a Task, Planners are prohibited*

---

## 📊 Phase Progress Monitoring

| Phase | Task | Status | Evidence (Commit/Log) |
| :--- | :--- | :---: | :--- |
| **1. PREP** | [T1] Extend SKILL.md schemas with state/role/confidence + supersede/verify_write/decay ops | [x] | SKILL.md patched: optional fields + supersede/verify_write/decay documented |
| **2. CORE** | [T2] Update front/index.html parser to default new fields + render state/role/ghost | [x] | index.html parseJSONL + buildDatasets + entity cards updated |
| **2. CORE** | [T3] Add role filter + ROLE_COLORS + historical dashed border in frontend | [x] | role-filter select + ROLE_COLORS + dashed border + ghost ring added |
| **3. FINAL** | [T4] Create tests/test_memory_graph.py regression + new-schema parsing test | [x] | tests/test_memory_graph.py created (5 tests, mirrors frontend contract) |
| **3. FINAL** | [T5] Run pytest; verify existing graph loads; update STATE.md + memory graph | [~] | STATE.md + memory_graph.jsonl updated. Pytest NOT executed: no shell tool in this env. Run `uv run pytest tests/test_memory_graph.py -q` to confirm. |

---

### T1 — Extend SKILL.md protocol
Edit `.agents/skills/memory/SKILL.md`: add optional `role`, `state`, `confidence`, `access_count`,
`last_accessed` to entity/relation/observation schemas (with defaults); document `supersede`,
`verify_write` (coverage/preservation/faithfulness), and `decay`/`consolidate` procedures; add
worked examples. Keep all existing text valid. Evidence: file edit + grep for new fields.

### T2 — Frontend parser + rendering of new fields
Edit `front/index.html` `parseJSONL` to default `state="current"`, `role="architecture"`,
`confidence="high"`; add a "Stale/Ghost" stat counter; show `state` + `role` badges on entity cards;
include state/role/confidence in node `title`. Evidence: file edit.

### T3 — Role filter + colors + ghost indicator
In `front/index.html`, add `ROLE_COLORS`, extend the type filter (or add a role select) to filter by
`role`; render `historical` nodes with dashed border; flag entities that have a `current`+`historical`
pair (or SUPERSEDED_BY link) with a warning ring. Evidence: file edit.

### T4 — Regression + new-schema test
Create `tests/test_memory_graph.py`: (a) load the live `.agents/memory/memory_graph.jsonl` and assert
it parses with defaults; (b) parse synthetic records with new fields and assert correct assignment;
(c) assert `supersede` marks old record `historical`. Pure stdlib `json`, mirrors frontend contract.
Evidence: new file + pytest pass.

### T5 — Verify + document
Run `uv run pytest tests/test_memory_graph.py -q`; confirm existing graph still loads (no errors);
update `.specs/project/STATE.md` (new decision: sdd-memory evolution) and append the evolution to the
memory graph as entities/observations. Evidence: pytest output + STATE.md edit + graph append.

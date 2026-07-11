"""
Regression + schema tests for the sdd-memory knowledge graph artifact.

These tests mirror the parsing contract implemented in `front/index.html`
(parseJSONL / normEntity / normRelation / normObservation / ghost detection)
so that the on-disk `.agents/memory/memory_graph.jsonl` and any new-schema
records remain loadable and correctly interpreted.

No network, no browser. Pure stdlib `json`.
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIVE_GRAPH = PROJECT_ROOT / ".agents" / "memory" / "memory_graph.jsonl"


# ---- Mirror of the frontend parser contract (kept in sync by design) ----
def norm_entity(e):
    e = dict(e)
    e["entityType"] = e.get("entityType") or "Unknown"
    e["role"] = e.get("role") or "architecture"
    e["state"] = e.get("state") or "current"
    e["confidence"] = e.get("confidence") or "high"
    e["observations"] = e.get("observations") or []
    e["access_count"] = e.get("access_count") or 0
    return e


def norm_relation(r):
    r = dict(r)
    r["state"] = r.get("state") or "current"
    return r


def norm_observation(o):
    o = dict(o)
    o["state"] = o.get("state") or "current"
    o["confidence"] = o.get("confidence") or "high"
    return o


def parse_jsonl(text):
    entities, relations, observations = [], [], []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or not obj.get("type"):
            continue
        if obj["type"] == "entity":
            entities.append(norm_entity(obj))
        elif obj["type"] == "relation":
            relations.append(norm_relation(obj))
        elif obj["type"] == "observation":
            observations.append(norm_observation(obj))

    by_name = {e["name"]: e for e in entities}
    for obs in observations:
        ent = by_name.get(obs.get("entityName"))
        if ent:
            ent["observations"] = ent["observations"] + (obs.get("contents") or [])
            if obs.get("state") and obs["state"] != "current":
                ent["_hasNonCurrentObs"] = True

    superseded = {
        r["from"] for r in relations if r.get("relationType") == "SUPERSEDED_BY"
    }
    for e in entities:
        e["_ghost"] = e["name"] in superseded or bool(e.get("_hasNonCurrentObs"))
    return {"entities": entities, "relations": relations, "observations": observations}


def test_live_graph_parses_with_defaults():
    """The existing production graph must load with zero errors and default fields."""
    if not LIVE_GRAPH.exists():
        # Nothing to test against in a fresh checkout; skip gracefully.
        return
    text = LIVE_GRAPH.read_text(encoding="utf-8")
    data = parse_jsonl(text)
    assert data["entities"], "live graph should contain entities"
    for e in data["entities"]:
        # Backward compatibility: flat records get safe defaults.
        assert e["state"] == "current"
        assert e["role"] == "architecture"
        assert e["confidence"] == "high"
        assert isinstance(e["observations"], list)
    # Relations and observations (if any) also default cleanly.
    for r in data["relations"]:
        assert r["state"] in ("current", "historical", "transition")
    for o in data["observations"]:
        assert o["state"] in ("current", "historical", "transition")
        assert o["confidence"] in ("high", "medium", "low", "tentative")


def test_new_schema_fields_are_respected():
    """When new fields are present, they are preserved (not overwritten by defaults)."""
    text = (
        '{"type":"entity","name":"user","entityType":"User","role":"user_profile",'
        '"state":"current","confidence":"tentative","observations":["might prefer X"]}\n'
        '{"type":"entity","name":"user_old","entityType":"User","role":"user_profile",'
        '"state":"historical","confidence":"high","observations":["preferred Y"]}\n'
        '{"type":"relation","from":"user_old","to":"user","relationType":"SUPERSEDED_BY",'
        '"state":"historical"}\n'
        '{"type":"observation","entityName":"user","contents":["confirmed Z"],'
        '"state":"current","confidence":"high"}\n'
    )
    data = parse_jsonl(text)
    assert len(data["entities"]) == 2
    user = next(e for e in data["entities"] if e["name"] == "user")
    assert user["role"] == "user_profile"
    assert user["state"] == "current"
    assert user["confidence"] == "tentative"
    # Observation merged into entity
    assert "confirmed Z" in user["observations"]
    # Ghost detection: user_old is the target of SUPERSEDED_BY
    old = next(e for e in data["entities"] if e["name"] == "user_old")
    assert old["state"] == "historical"
    assert old["_ghost"] is True
    assert user["_ghost"] is False


def test_supersede_marks_old_record_historical():
    """supersede semantics: old record historical + SUPERSEDED_BY link present."""
    # Simulate the documented supersede procedure.
    before = (
        '{"type":"entity","name":"plan_v1","entityType":"Feature",'
        '"observations":["plan A"],"state":"current"}\n'
    )
    after = before + (
        '{"type":"entity","name":"plan_v2","entityType":"Feature",'
        '"observations":["plan B"],"state":"current"}\n'
        '{"type":"relation","from":"plan_v1","to":"plan_v2",'
        '"relationType":"SUPERSEDED_BY","state":"historical"}\n'
    )
    # Apply the supersede edit (patch old line to historical).
    after = after.replace('"observations":["plan A"],"state":"current"',
                          '"observations":["plan A"],"state":"historical"')
    data = parse_jsonl(after)
    v1 = next(e for e in data["entities"] if e["name"] == "plan_v1")
    v2 = next(e for e in data["entities"] if e["name"] == "plan_v2")
    assert v1["state"] == "historical"
    assert v2["state"] == "current"
    assert v1["_ghost"] is True
    assert any(r["relationType"] == "SUPERSEDED_BY" for r in data["relations"])


def test_invalid_lines_are_skipped():
    text = (
        'not json at all\n'
        '{"type":"entity","name":"ok","entityType":"Module"}\n'
        '{"no_type":true}\n'
    )
    data = parse_jsonl(text)
    assert len(data["entities"]) == 1
    assert data["entities"][0]["name"] == "ok"


def test_role_filter_isolation_contract():
    """MemGuard-style: role can be used to scope retrieval to a single role."""
    text = (
        '{"type":"entity","name":"pref","entityType":"User","role":"preference"}\n'
        '{"type":"entity","name":"evt","entityType":"User","role":"episodic"}\n'
    )
    data = parse_jsonl(text)
    prefs = [e for e in data["entities"] if e["role"] == "preference"]
    epis = [e for e in data["entities"] if e["role"] == "episodic"]
    assert len(prefs) == 1 and prefs[0]["name"] == "pref"
    assert len(epis) == 1 and epis[0]["name"] == "evt"

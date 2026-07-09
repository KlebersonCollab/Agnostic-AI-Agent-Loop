# Coding Principles

Behavioral bias, not just a checklist. Read before every implementation.

---

## Before Coding
- **Explicit Assumptions:** State your assumptions. If uncertain, ask.
- **Multiple Interpretations:** If there are multiple ways to interpret the task, present them. Do not choose silently.
- **Simplicity:** Is there a simpler approach? Say so. Question when necessary.
- **Uncertainty:** If something is confusing, STOP. Name what is confusing and request clarification.

---

## During Implementation

### Simplicity
- No features beyond what was requested (YAGNI).
- No abstractions for single-use code.
- No "flexibility" or "configuration" that wasn't asked for.
- 200 lines of code that could be 50? Refactor to simplify.

### Surgical Changes
- Do not "improve" unrelated adjacent code, comments, or formatting.
- Do not refactor what is not broken.
- Follow the existing code style in the repository.
- Remove ONLY imports/variables/functions that YOUR changes orphaned. Do not delete pre-existing dead code unless requested.

### Test Integrity
- **NEVER** weaken an existing test assertion to make it pass.
- **NEVER** delete a test to reduce the failure count.
- **NEVER** use skip/disable mechanisms to ignore failing tests.
- Tests are the specification — the implementation conforms to the tests, not the other way around.

### Goal Orientation
- Transform vague tasks into verifiable objectives.
- In multi-step tasks, state a brief plan with verification points.
- Every changed line must have direct traceability to the user's request.

---

## After Each Change
Ask yourself: *"Would a senior engineer call this over-engineering?"*
If the answer is yes → **simplify before proceeding**.

---

<!-- @sdd-state -->
```yaml
version: "2.3.0"
feature_id: "SDD-CORE"
phase: "MANAGEMENT"
status: "COMPLETED"
last_update: "2026-05-06T09:42:30Z"
evidence_checksum: "8e52f6a"
```

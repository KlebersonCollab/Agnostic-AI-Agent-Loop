# Grilling Session: Terminology & Architecture Challenge

This reference defines the **Grilling Session (Sabatina)** process, designed to sharpen terminology, enforce domain model consistency, and register critical architectural decisions before any code or specifications are written.

---

## 🏁 Objectives
- **Sharpen Vague Language**: Identify and replace overloaded or ambiguous terms with precise domain-specific nouns.
- **Relentless Plan Challenge**: Probe edge cases and stress-test assumptions with concrete scenarios.
- **Lazy Artifact Creation**: Maintain `CONTEXT.md` (Domain Glossary) and `ADRs` (Architectural Decision Records) inline as decisions crystallize.

---

## 🔄 The Grilling Protocol (During Phase 0: ALIGN)

### 1. Glossary Enforcement
When a term conflicts with the existing language in `CONTEXT.md` or is used vaguely (e.g., saying "account" instead of clarifying between "Customer" or "User"):
- **Action**: Stop and challenge immediately: *"You used term X, but the glossary defines X as Y. Do you mean Y or a new concept?"*
- **Resolution**: Update the central `CONTEXT.md` immediately with the correct definition and aliases to avoid.

### 2. Scenario-Driven Stress Testing
Propose edge-case scenarios that test the boundaries of the design tree one-by-one. Ask targeted questions, and for each question, provide a recommended answer based on domain best practices.
- Ask questions **one at a time**, waiting for explicit user feedback before moving to the next.
- If a question can be answered by exploring the codebase, prioritize exploration over asking the user.

---

## 📖 CONTEXT.md Format (Domain Glossary)

`CONTEXT.md` resides in the project root or `.specs/project/`. It must be **totally devoid of implementation details** (it is a glossary and nothing else).

### Structure

```markdown
# {Context Name}

{One or two sentence description of what this context is and why it exists.}

## Language

**{Term}**:
{A one or two sentence description of the term defining what it IS, not what it does.}
_Avoid_: {Comma-separated list of vague or forbidden aliases}

**Order**:
A formal request from a customer to purchase one or more products.
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request
```

### Rules
1. **Be Opinionated**: Pick the absolute best term when multiple choices exist, and explicitly flag aliases to avoid.
2. **Cardinality & Relationships**: Express relationships clearly between bold terms.
3. **No General Code Concepts**: Only include unique terms specific to the project's domain context. General programming concepts (timeouts, error types, utility helpers) do NOT belong here.
4. **Example Dialogue**: Include a brief conversation demonstrating how terms interact naturally.

---

## 🏛️ ADR Format (Architectural Decision Records)

ADRs reside in `.specs/project/ADRs/` and use sequential numbering: `0001-slug.md`, `0002-slug.md`, etc.

### When to Create an ADR
Only offer to create an ADR if **all three** criteria are true:
1. **Hard to Reverse**: The cost of changing your mind later is meaningful.
2. **Surprising Without Context**: A future reader will look at the code and wonder "why on earth did they do it this way?".
3. **The Result of a Real Trade-Off**: There were genuine alternatives, and you picked one for specific reasons.

### Template

```markdown
# {Short title of the decision}

{1-3 sentences: what is the context, what did we decide, and why.}

## Status
Accepted | Superseded by ADR-NNNN | Deprecated

## Consequences (Optional)
{Downstream effects or limitations resulting from this decision}
```

---

<!-- @sdd-state -->
```yaml
version: "2.3.0"
feature_id: "SDD-GRILL-INTEGRATION"
phase: "VERIFY"
status: "COMPLETED"
last_update: "2026-05-22T14:22:00Z"
evidence_checksum: "make-audit-success"
```

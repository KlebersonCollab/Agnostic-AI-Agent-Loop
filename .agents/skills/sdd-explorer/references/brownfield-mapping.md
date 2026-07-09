# Brownfield Mapping (TECHNICAL-MAP)

**Trigger:** "Map codebase", "Analyze existing code", "Document current architecture"

**Purpose:** Understand the existing project structure and identify risks before planning features.

## The Output: Granular Codebase Mapping

Instead of a single large file, the Explorer generates a set of targeted artifacts in `.specs/codebase/` to keep the context clean and modular.

### 1. STACK.md (Tech Stack & Ecosystem)
- **Core:** Languages, frameworks, and runtimes with versions.
- **Tools:** Package managers, build tools, and CLI utilities.
- **Testing:** Unit, Integration, and E2E frameworks.

### 2. ARCHITECTURE.md (Structure & Patterns)
- **High-Level Structure:** Directory organization and layer definitions.
- **Observed Patterns:** Concrete examples of how logic is decoupled (e.g., Services, Repositories, Hooks).
- **Data Flow:** Mermaid diagram of primary request/response cycles.

### 3. CONVENTIONS.md (Core Conventions)
- **Naming:** Files, functions, and variables based on codebase evidence.
- **Style:** Error handling patterns, type safety approach, and commenting style.

### 4. CONCERNS.md (Critical Risks)
*This is the most important section for the Safety Valve protocol.*
- **Technical Debt:** Shortcuts that impact maintainability.
- **Fragile Areas:** Components that break easily or have low test coverage.
- **Security & Performance:** Known bottlenecks or exposed patterns.
- **Mandatory:** Every concern must include file paths as evidence.

### 5. TECHNICAL-MAP.md (Consolidated View)
- A high-level summary and index that links to the granular files above.

---

## Analysis Protocol

1. **Systematic Scan:** Use `ls -R` and dependency manifests to build `STACK.md`.
2. **Architecture Trace:** Follow a primary request to map the `ARCHITECTURE.md`.
3. **Pattern Extraction:** Analyze 5-10 representative files to define `CONVENTIONS.md`.
4. **Risk Discovery:** Search for "TODO", "FIXME", "HACK", or complex legacy structures for `CONCERNS.md`.

## Quality Rules
- **Evidence-Based:** Reference specific file paths for every claim.
- **Current State Only:** Document what IS, not what you think it should be.
- **Granularity:** Keep information in the correct file to avoid context bloat.

---

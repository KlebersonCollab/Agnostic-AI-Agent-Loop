# SDD Specification: memory_refactoring

This is the source of truth for **functional requirements** and **business logic** for Memory modularization.

---

## 1. Context & Goals
- **Problem**: `memory.py` mixes SQL schema creation statements with operational queries.
- **Goal**: Refactor the codebase to isolate the SQL schema logic into a dedicated schema file.

---

## 2. Requirements (BDD Scenarios)

**Scenario 1: Imports are backwards compatible**
- **Given** client code imports `AgentMemory` from `memory` (e.g. `from memory import AgentMemory`)
- **When** the code is executed
- **Then** the `memory/__init__.py` file must resolve and provide the class seamlessly.

**Scenario 2: Database writes and search run identical behavior**
- **Given** the agent runs and creates sessions/episodes or searches memory
- **When** executing database calls
- **Then** it must execute identical operations as before.

---

## 3. Constraints & Risks
- Avoid breaking the concurrency protections (global lock, timeouts, rollbacks) we recently implemented in the database loop.

---

## 4. Status
- **DRAFT**

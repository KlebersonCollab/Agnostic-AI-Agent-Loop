# SDD Specification: memory_lock_fix

This is the source of truth for **functional requirements** and **business logic** for the SQLite Memory Lock Fix.

---

## 1. Context & Goals
- **Problem**: Concurrent database writes from background subagents and the orchestrator using instance-level RLocks resulted in `database is locked` errors. If an exception occurred during a write, the connection's transaction stayed open, blocking the database file permanently in a deadlock/silent hang.
- **Goal**: Implement thread-safe database serialization and robust exception/rollback handling to ensure SQLite transactions are never left uncommitted under failures.

---

## 2. Requirements (BDD Scenarios)

**Scenario 1: Thread-safe serialization of database writes**
- **Given** multiple threads have separate `AgentMemory` instances connected to the same database file
- **When** they execute writes concurrently
- **Then** the class-level `_global_lock` must serialize their access
- **And** no `database is locked` error should occur.

**Scenario 2: Rollback on database write failure**
- **Given** a write operation fails (e.g. invalid SQL or constraint violation)
- **When** the exception is raised
- **Then** the transaction must be explicitly rolled back
- **And** the SQLite database lock must be released immediately.

---

## 3. Constraints & Risks
- **Performance**: Serializing all database accesses in memory introduces minimal overhead because writes are extremely fast, but it guarantees absolute data consistency and prevents file locks.

---

## 4. Status
- **DRAFT**

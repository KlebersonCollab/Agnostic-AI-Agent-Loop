# SDD Technical Plan: memory_lock_fix

This is the technical blueprint for fixing the SQLite transaction lock / race condition bug.

---

## 1. Architecture Overview
When multiple threads (such as the Orchestrator and background Subagents) instantiate separate `AgentMemory` objects and write to the shared SQLite database file concurrently:
1. The previous `self.lock` was an **instance-level** `threading.RLock()`, meaning different instances on different threads did not share the same lock, allowing concurrent writes.
2. Concurrent writes on separate SQLite connections without WAL mode or proper timeout settings lead to `sqlite3.OperationalError: database is locked`.
3. If any database write operation fails with an exception, the `sqlite3` transaction remains open/uncommitted. This locks the database indefinitely for that connection, causing subsequent queries across the entire process to hang or fail silently.

To resolve this:
- **Global Lock**: Share a single class-level lock `_global_lock = threading.RLock()` across all `AgentMemory` instances to serialize all SQLite operations.
- **Resilient Transactions**: Ensure that if any SQLite operation raises an exception, we explicitly call `self.conn.rollback()` to close the transaction and release locks.
- **Connection Timeout**: Increase the default SQLite connection timeout from 5.0 to 30.0 seconds to prevent immediate errors on temporary disk locks.

---

## 2. Technical Design

### Class-Level Lock
```python
class AgentMemory:
    _global_lock = threading.RLock()

    def __init__(self, db_path: str = None):
        self.lock = self._global_lock
```

### Transaction Rollbacks
Wrap all write operations in a try-except block:
```python
try:
    # database operations
    self.conn.commit()
except Exception:
    self.conn.rollback()
    raise
```

---

## 3. Implementation Strategy
- **Isolation**:
  - Touch [memory.py](file:///home/klebersonromero/Projetos/teste/memory.py) to implement the global lock, timeout parameter, and rollback blocks.
- **Testing**:
  - Run the existing test suite (`uv run pytest`) to ensure all tests (including concurrent/parallel test suites) pass cleanly.

---

## 4. Status
- **DRAFT**

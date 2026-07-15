# SDD Technical Plan: memory_refactoring

This is the technical blueprint for refactoring `memory.py` to extract database schema definition (DDL) and database init concerns.

---

## 1. Architecture Overview
Currently, `memory.py` contains:
1. SQL commands to set up tables (`CREATE TABLE IF NOT EXISTS...`).
2. Main `AgentMemory` execution methods.

To separate concerns, we will modularize `memory.py` into a package structure `memory/`:
- `memory/schema.py`: Holds database SQL templates and schema initialization functions.
- `memory/core.py`: Holds the main `AgentMemory` class.
- `memory/__init__.py`: Re-exports `AgentMemory` to maintain complete backwards compatibility.

---

## 2. Technical Design

### Package Structure
```
memory/
├── __init__.py
├── core.py
└── schema.py
```

---

## 3. Implementation Strategy
- **Phase 1**: Populate modular files under `memory/`.
- **Phase 2**: Remove the monolithic `memory.py` file.
- **Phase 3**: Verify correctness by running all unit tests.

---

## 4. Status
- **DRAFT**

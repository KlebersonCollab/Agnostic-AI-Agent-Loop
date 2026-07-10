# SDD Technical Plan: Context References (context_references)

This document describes the technical implementation plan for context reference injection and the creation of the `context` package.

---

## 1. Architecture Overview
We will create a new Python package folder `context/` in the project root. This package will contain:
1. `context/__init__.py`: Initializes the context package.
2. `context/builder.py`: Refactored and moved version of `context_builder.py` (previously in the root).
3. `context/references.py`: Resolves context references (`@file:`, `@url:`, `@diff`, `@staged`) concurrently, enforcing security blocklists and path resolution checks, as well as context-window token budgeting.

```
context/
├── __init__.py
├── builder.py       # (formerly context_builder.py)
└── references.py    # (formerly context_references.py)
```

Imports across the project (in `cli.py`, `agent.py`, and `tests/test_context_builder.py`) will be updated to load from `context.builder`.

---

## 2. Technical Design

### Data Models / Schemas
Inside `context/references.py`:
```python
@dataclass(frozen=True)
class ContextReference:
    raw: str          # e.g., '@file:agent.py:10-30'
    kind: str         # 'file', 'url', 'diff', 'staged'
    target: str       # e.g., 'agent.py'
    start: int        # string index start in prompt
    end: int          # string index end in prompt
    line_start: Optional[int] = None
    line_end: Optional[int] = None

@dataclass
class ContextReferenceResult:
    message: str                        # final prompt with references stripped and appended
    original_message: str               # original prompt
    references: List[ContextReference]
    warnings: List[str]
    injected_tokens: int
    expanded: bool
    blocked: bool
```

### Path Location Adjustments in `context/builder.py`
Since `builder.py` is moving into a subfolder `context/`, package root detection in `__init__` must adjust:
```python
# Package root directory (where context/builder.py is located)
package_root = os.path.dirname(os.path.abspath(__file__))
# Project root directory (one level up from package_root)
project_root = os.path.dirname(package_root)

# builtin agents will be relative to project root
builtin_agents = os.path.join(project_root, ".agents")
```

### Integration Point (Agent.run)
In [agent.py](file:///home/klebersonromero/Projetos/teste/agent.py):
```python
    def run(self, user_prompt: str):
        # Resolve references
        result = preprocess_context_references(user_prompt, cwd=os.getcwd(), context_length=128000)
        
        # Log/display warnings if any
        if result.warnings and self.listener:
            for warning in result.warnings:
                self.listener.on_error(f"⚠️ Context reference warning: {warning}")
        
        # Use final message
        final_prompt = result.message
```

---

## 3. Implementation Strategy

### Isolation
* **Files to be created:**
  * `context/__init__.py`
  * `context/references.py`
  * `tests/test_context_references.py`
* **Files to be moved/modified:**
  * `context_builder.py` → Move to `context/builder.py`, modify `.agents` pathing.
  * `agent.py`: Update import from `context_builder` to `context.builder`. Import and run `preprocess_context_references` from `context.references`.
  * `cli.py`: Update import from `context_builder` to `context.builder`.
  * `tests/test_context_builder.py`: Update imports and test mocks.

### Testing Strategy
* **Unit Tests:**
  * Test `test_context_builder.py` runs and passes successfully after movement and import updates.
  * Implement unit tests in `tests/test_context_references.py` for parsing regexes, path safety resolution, token estimation, and git execution.

---

## 4. Status
- **NEEDS_REVIEW**

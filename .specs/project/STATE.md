# Project State & Context

## 🏁 Session Status
- **Current Task**: Planning and implementing Context References and Folder Refactoring
- **Progress**: 30% (Planning artifacts updated, awaiting review/approval)
- **Next Steps**:
  1. Ask the user to review the updated structure (moving context_builder to context/builder.py).
  2. Transition to Approved and In Progress.
  3. Start sdd-executor to run implementation steps.

## 💡 Decisions Log
- **2026-07-10 - Context Reference Injection**: Decide to implement prompt-level `@file`, `@url`, `@diff`, `@staged` parsing to match Hermes Agent style context injection.
- **2026-07-10 - Context Folder Refactoring**: Decide to organize context modules under a new Python package `context/` (containing `context/builder.py` and `context/references.py`) to keep the codebase modular.

## 🚧 Active Blockers
- None.

## ❄️ Deferred Ideas / Icebox
- None.

## ⚠️ Known Technical Debts
- Hand-rolled frontmatter parser in `ContextBuilder` (documented in technical map).

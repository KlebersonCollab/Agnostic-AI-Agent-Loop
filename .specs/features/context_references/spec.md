# SDD Specification: Context References (context_references)

This specification defines the functional requirements and business logic for the context reference injection system.

---

## 1. Context & Goals

### Problem Statement
Currently, users of the Agnostic Agent CLI must manually copy and paste file contents, git diffs, or URL text into their prompt to provide context to the agent. This is slow, tedious, and error-prone.

### Goal
Implement a prompt-level reference parsing and injection system. The system will detect special syntax in the user's prompt (e.g. `@file:filename`, `@url:http...`, `@staged`, `@diff`) and automatically expand those references, fetching and appending their contents to the prompt before the Agent begins execution.

### Scope
* **Included:**
  * Support for `@file:path` references with optional line numbers (e.g., `@file:agent.py` or `@file:agent.py:10-30`).
  * Support for `@url:http...` references to fetch external webpage content.
  * Support for `@diff` and `@staged` to inject the current git diff or staged files diff.
  * Security sandbox: prevent path traversal (e.g. `@file:../../../etc/passwd` or `@file:~/.ssh/id_rsa`) and block a predefined list of sensitive files/folders.
  * Context size safety limits: Warning and hard refusal thresholds based on token estimates to avoid context-window crashes.
* **NOT Included:**
  * Auto-fetching large binary assets (e.g. PDFs, images). Only text content is supported.
  * Recursive file/folder expansion (e.g. `@folder:src`).

### Success Criteria
* The user can use `@file`, `@url`, `@diff`, and `@staged` in interactive and one-shot prompts.
* Selected references are expanded and appended to the prompt in a structured section.
* Path traversal attempts are blocked, returning a warning block instead of the file content.
* Token budgets are calculated and respected (25% soft warning, 50% hard limit of total model context length).

---

## 2. Requirements (BDD Scenarios)

### Feature: Context References Injection

**Scenario 1: Parse and expand multiple valid context references**
- **Given** The workspace contains a file `hello.txt` with content "Hello World"
- **When** The user prompt is "Summarize this: @file:hello.txt"
- **Then** The prompt is expanded to include a "Context References" block containing the content of `hello.txt`

**Scenario 2: Block unauthorized path traversal**
- **Given** The user attempts to reference a file outside the workspace root, such as `@file:../../other.txt` or a sensitive file like `@file:.env`
- **When** The prompt is processed
- **Then** An error/warning is generated, the expansion is blocked, and the file content is not read.

**Scenario 3: Gracefully handle URL extraction**
- **Given** The user references a URL `@url:https://example.com`
- **When** The prompt is processed
- **Then** The content is retrieved (mocked in tests) and formatted as Markdown in the injected prompt context.

---

## 3. Constraints & Risks

### Security
* **Access Control:** All file references must resolve inside the workspace root (the current working directory). Directory traversal using `..` or absolute paths pointing outside the workspace must be rejected.
* **Sensitive File Blocklist:** Explicitly block access to files like `.env`, `.env.local`, `.git`, `.ssh/*`, `.npmrc`, `.pypirc`.

### Performance
* **Concurrence:** Multiple references should be fetched concurrently using an async task pool to avoid blocking the main thread sequentially.
* **Token Budget:** Since total context window size varies per model, the system must read the active provider's capacity (or fallback default) and warn or block if context injection is too large.

---

## 4. Status
- **NEEDS_REVIEW**

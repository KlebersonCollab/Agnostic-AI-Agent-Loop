# SDD Specification: Context Breakdown (context_breakdown)

This specification defines the functional requirements and business logic for the context breakdown display system.

---

## 1. Context & Goals

### Problem Statement
As the agent loop runs through multiple steps, loading rules, active skills, and accumulating message history, the context window fills up. Currently, the user has no visibility into what is consuming the context window tokens (e.g. system prompt vs. rules vs. tools vs. chat history), making it hard to debug token limits or optimize prompt usage.

### Goal
Implement a context breakdown module under the `context` package. This module will analyze the agent's active prompt, history, and tools, estimating the token usage of each component. We will expose this breakdown to the user via a `/context` slash command in the interactive CLI, formatted in a beautiful terminal table.

### Scope
* **Included:**
  * Estimation of token usage using a characters/4 rough heuristic.
  * Separation of usage into categories: Base System Prompt, Active Rules, Loaded Skills, Tool Schemas, and Conversation History.
  * Implementation of a `/context` command in the interactive CLI loop ([cli.py](file:///home/klebersonromero/Projetos/teste/cli.py)) using `rich` to render a detailed, colored table.
* **NOT Included:**
  * Live tokenizer counts (e.g. Tiktoken or Llama tokenizer). Rough estimation is sufficient and performs instantly.
  * Real-time charts or GUI elements. A text-based `rich` table in the console is the target.

### Success Criteria
* The user can type `/context` in the interactive CLI loop.
* The CLI displays a clean, colored breakdown table detailing token usage and percentage of the total context window.
* Individual categories (system, rules, skills, tools, history) show correct relative token sizes.

---

## 2. Requirements (BDD Scenarios)

### Feature: Context Breakdown Command

**Scenario 1: User requests context breakdown in interactive mode**
- **Given** The agent is initialized with 2 rules, 1 active skill, 5 tools, and a conversation history of 3 messages.
- **When** The user inputs `/context` (or `/c`) in the CLI.
- **Then** The CLI halts normal prompt execution, calculates token sizes, and prints a formatted `rich` table showing the breakdown.

**Scenario 2: Breakdown estimates match physical content lengths**
- **Given** An agent state with known character sizes for system prompt, rules, tools, and history.
- **When** The breakdown is computed.
- **Then** The estimated token values correspond exactly to `(character_length + 3) // 4` for each category.

---

## 3. Constraints & Risks

### Performance
* **Zero Overhead:** The calculation must run instantly without performing any network requests or heavy CPU-bound tokenization. Heuristics must be calculated in memory.

---

## 4. Status
- **NEEDS_REVIEW**

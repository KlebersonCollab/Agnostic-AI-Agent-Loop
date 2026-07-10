# Domain Glossary (CONTEXT.md)

This glossary defines the core concepts and terms used within our Agnostic Agent framework.

## Core Concepts

### Agent
The main execution unit that runs a ReAct (Reasoning and Action) loop, coordinating interactions between the LLM provider, active skills, rules, and registered tools.

### Provider
An abstraction layer that maps generic LLM requests to specific model client libraries (such as OpenAI, Anthropic, and Google GenAI) and handles transient error retries.

### Tool
An executable function that the agent can call to interact with the environment (e.g., reading/writing files, performing math operations, or querying memory).

### Skill
A set of loadable guidelines and instructions stored in markdown files that can be dynamically loaded or unloaded from the agent's active system prompt to guide its behavior for specific tasks.

### Rule
An active, structural constraint that is always present in the agent's system prompt (e.g., prohibition rules, formatting rules).

### Handover Checkpoint
A markdown report generated when the agent approaches its step limit, detailing progress, blockers, backlog, and next steps to allow a subsequent agent session to resume cleanly.

### Agent Memory
A persistent SQLite database with FTS5 search index that records the history of thoughts, tool actions, and results across agent sessions to allow semantic retrieval of past knowledge.

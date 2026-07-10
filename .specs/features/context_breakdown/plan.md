# SDD Technical Plan: Context Breakdown (context_breakdown)

This document describes the technical implementation plan for the context breakdown display system.

---

## 1. Architecture Overview
We will implement a new module `context/breakdown.py` which will calculate the token usage breakdown from the agent's current state.

We will then modify [cli.py](file:///home/klebersonromero/Projetos/teste/cli.py) to support the `/context` (and `/c`) command in interactive mode, displaying a colored Rich table representing this breakdown.

```
context/
├── __init__.py
├── builder.py
├── references.py
└── breakdown.py     # New module
```

---

## 2. Technical Design

### Data Models / Schemas
The breakdown output dictionary structure:
```python
{
    "base_system": int,       # Base prompt tokens
    "rules": int,             # Active rules tokens
    "skills_metadata": int,   # Available skills metadata list tokens
    "skills_body": int,       # Loaded/active skills details tokens
    "tools": int,             # Registered tools schemas tokens
    "history": int,           # Chat history tokens (excluding system prompt)
    "total": int              # Sum of all above
}
```

### Breakdown Calculation Logic (`context/breakdown.py`)
```python
def _chars_to_tokens(text: str) -> int:
    return (len(text) + 3) // 4

def calculate_context_breakdown(agent) -> dict:
    builder = agent.context_builder
    
    # 1. Base System Prompt
    base_sys = _chars_to_tokens(builder.base_system_prompt)
    
    # 2. Active Rules
    rules_size = 0
    for r in builder.active_rules:
        if r in builder.rules_cache:
            rules_size += len(builder.rules_cache[r])
    rules_tokens = _chars_to_tokens(rules_size)
    
    # 3. Skills Metadata
    skills_meta_size = 0
    for name, data in builder.skills_cache.items():
        meta = data["metadata"]
        desc = meta.get("description", "")
        kws = str(meta.get("keywords", []))
        skills_meta_size += len(name) + len(desc) + len(kws)
    skills_meta_tokens = _chars_to_tokens(skills_meta_size)
    
    # 4. Loaded Skills Body
    skills_body_size = 0
    for s in builder.active_skills:
        if s in builder.skills_cache:
            skills_body_size += len(builder.skills_cache[s]["body"])
    skills_body_tokens = _chars_to_tokens(skills_body_size)
    
    # 5. Tools schemas
    import json
    tools_size = 0
    for tool_def in agent.tools:
        # tool_def is a Pydantic model
        tools_size += len(json.dumps(tool_def.model_dump()))
    tools_tokens = _chars_to_tokens(tools_size)
    
    # 6. Conversation History (excluding the first system prompt message)
    history_size = 0
    for msg in agent.history[1:]:
        if msg.content:
            history_size += len(msg.content)
        # Count tool calls if present
        if msg.tool_calls:
            for tc in msg.tool_calls:
                history_size += len(tc.name) + len(json.dumps(tc.arguments))
    history_tokens = _chars_to_tokens(history_size)
    
    total = base_sys + rules_tokens + skills_meta_tokens + skills_body_tokens + tools_tokens + history_tokens
    
    return {
        "base_system": base_sys,
        "rules": rules_tokens,
        "skills_metadata": skills_meta_tokens,
        "skills_body": skills_body_tokens,
        "tools": tools_tokens,
        "history": history_tokens,
        "total": total
    }
```

---

## 3. Implementation Strategy

### Isolation
* **Files to be created:**
  * `context/breakdown.py`
  * `tests/test_context_breakdown.py`
* **Files to be modified:**
  * `cli.py`: Intercept `/context` and `/c` commands, import `calculate_context_breakdown` and render the table.

### CLI Rendering Design
Using Rich table:
```python
from rich.table import Table

def display_context_breakdown(agent):
    bd = calculate_context_breakdown(agent)
    table = Table(title="📊 Context Window Token Usage Breakdown", show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan")
    table.add_column("Est. Tokens", justify="right", style="green")
    table.add_column("Percentage", justify="right", style="yellow")
    
    # Total context window length limit (can assume 128k as standard baseline for gemini/openai)
    limit = 128000
    
    table.add_row("Base System Prompt", f"{bd['base_system']:,}", f"{bd['base_system']/limit:.2%}")
    table.add_row("Active Rules", f"{bd['rules']:,}", f"{bd['rules']/limit:.2%}")
    table.add_row("Skills Metadata", f"{bd['skills_metadata']:,}", f"{bd['skills_metadata']/limit:.2%}")
    table.add_row("Active Skills Body", f"{bd['skills_body']:,}", f"{bd['skills_body']/limit:.2%}")
    table.add_row("Tool Schemas", f"{bd['tools']:,}", f"{bd['tools']/limit:.2%}")
    table.add_row("Conversation History", f"{bd['history']:,}", f"{bd['history']/limit:.2%}")
    table.add_section()
    table.add_row("Total Usage", f"{bd['total']:,}", f"{bd['total']/limit:.2%}", style="bold")
    console.print(table)
```

---

## 4. Status
- **NEEDS_REVIEW**

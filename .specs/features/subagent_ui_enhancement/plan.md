# SDD Technical Plan: subagent_ui_enhancement

This is the technical blueprint for the Subagent UI Enhancement.

---

## 1. Architecture Overview
We will refactor [CollectingAgentListener](file:///home/klebersonromero/Projetos/teste/tools/multi_agent.py#L27) in [tools/multi_agent.py](file:///home/klebersonromero/Projetos/teste/tools/multi_agent.py) to structure console prints using aligned, color-coded columns using Rich markup formatting.

## 2. Technical Design

### Structured Log Signature
We will update `log_and_print` to accept structured event metadata:
```python
def log_and_print(self, event_icon: str, event_label: str, content: str, content_style: str = ""):
    # 1. Store plain text in logs
    self.logs.append(f"{event_icon} {event_label}: {content}")
    # 2. Print beautiful columns
    ...
```

### Alignment Columns Layout
```
● Backend Data Layer Auditor     ⎹ Step 1/10 ⎹ 🛠️ Call     ⎹ list_project_files()
● Test Suite Auditor             ⎹ Step 1/10 ⎹ 🤖 Thought  ⎹ I need to check the tests...
```

Columns format:
- **Role**: `[bold {self.color}]● {self.role:<28}[/]` (length 28 padding)
- **Step**: `[dim]Step {self.step}/{self.max_steps}[/]`
- **Event**: `{event_icon} [bold {self.color}]{event_label:<8}[/]`
- **Content**: `[{content_style}]{content}[/{content_style}]`

---

## 3. Implementation Strategy
- **Isolation**: Only [tools/multi_agent.py](file:///home/klebersonromero/Projetos/teste/tools/multi_agent.py) will be modified.
- **Testing Strategy**: Ensure the python syntax compiles and runs, and all existing tests pass.

---

## 4. Status
- **AGREE**

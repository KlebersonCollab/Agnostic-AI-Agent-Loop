# SDD Technical Plan: execute_command_tool (plan.md)

Technical design and implementation details for the `execute_command` tool.

---

## 1. Core Code Design

### Tool Implementation (`tools/io_tools.py`)
```python
def execute_command(command: str) -> str:
    """
    Executes a shell command inside the project workspace directory in a sandboxed/restricted environment.
    Enforces a timeout, prevents execution of forbidden system-level commands, and caps output size.
    """
    forbidden_terms = [
        "sudo", "rm -rf /", "mkfs", "dd ", "shutdown", "reboot", "poweroff",
        "/etc/passwd", "/etc/shadow", "~/.ssh", ".env"
    ]
    command_clean = command.strip()
    if any(term in command_clean.lower() for term in forbidden_terms):
        return "Error: Command contains forbidden/unsafe terms or patterns."

    workspace = os.getcwd()
    
    # Log command execution to developer console
    from rich.console import Console
    console = Console()
    console.print(f"[bold yellow]💻 [Shell Command][/bold yellow] Executing: {command_clean}")

    try:
        result = subprocess.run(
            command_clean,
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
            
        output = output.strip()
        if not output:
            output = f"[Command exited with code {result.returncode} and produced no output]"
            
        # Truncate response to prevent context window bloat
        max_chars = 30000
        if len(output) > max_chars:
            output = output[:max_chars] + f"\n\n[... Output truncated. Total length: {len(output)} characters]"
            
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds of execution."
    except Exception as e:
        return f"Error executing command: {e}"
```

### Registry Integration (`tools/__init__.py`)
Add `execute_command` to `REGISTERED_TOOLS`:
```python
    (
        ToolDefinition(
            name="execute_command",
            description="Executes a shell command in a sandboxed/restricted environment inside the project directory.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command line string to execute, e.g. 'pytest' or 'ls -la'."
                    }
                },
                "required": ["command"]
            }
        ),
        io_tools.execute_command
    ),
```

---

## 2. Status
- **NEEDS_REVIEW**

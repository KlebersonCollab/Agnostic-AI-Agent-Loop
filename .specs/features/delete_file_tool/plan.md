# SDD Technical Plan: delete_file_tool (plan.md)

Technical design and implementation details for the `delete_file` tool.

---

## 1. Core Code Design

### Tool Implementation (`tools/io_tools.py`)
```python
def delete_file(filename: str) -> str:
    """
    Permanently deletes a file inside the project workspace directory.
    Prints a warning to the console to ensure responsibility.
    """
    try:
        if not _is_safe_path(filename):
            return "Error: Access denied. Cannot delete files outside the project directory."
        abs_path = os.path.abspath(filename)

        if not os.path.exists(abs_path):
            return f"Error: File '{filename}' does not exist."
            
        if os.path.isdir(abs_path):
            return f"Error: Target '{filename}' is a directory. delete_file only supports files."

        with _file_write_lock:
            os.remove(abs_path)
            
        # Log responsible warning to the developer console
        from rich.console import Console
        console = Console()
        console.print(f"[bold red]⚠️  [File Deletion][/bold red] File '{filename}' has been permanently deleted.")
        
        return (
            f"Success: File '{filename}' was successfully deleted. "
            "[WARNING: This action is permanent and cannot be undone. "
            "Ensure that this deletion does not break dependencies or leave orphan imports in the codebase.]"
        )
    except Exception as e:
        return f"Error deleting file '{filename}': {e}"
```

### Registry Integration (`tools/__init__.py`)
Add `delete_file` to `REGISTERED_TOOLS`:
```python
    (
        ToolDefinition(
            name="delete_file",
            description="Permanently deletes a file inside the project directory. Warns of deletion responsibly.",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The path of the file to delete (must be inside the project directory)."
                    }
                },
                "required": ["filename"]
            }
        ),
        delete_file
    ),
```

---

## 2. Status
- **NEEDS_REVIEW**

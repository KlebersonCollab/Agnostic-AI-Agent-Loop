import os
from typing import Dict, Any, List
from ai_provider import ToolDefinition

def list_project_files(path: str = ".") -> str:
    """Lists files and folders in the specified directory recursively, ignoring virtual environments and git folders."""
    try:
        ignored = {".git", ".venv", "__pycache__", ".pytest_cache", ".idea", ".vscode"}
        output = []
        for root, dirs, files in os.walk(path):
            # Modify dirs in-place to avoid traversing ignored directories
            dirs[:] = [d for d in dirs if d not in ignored]
            
            # Get relative path for root
            rel_root = os.path.relpath(root, path)
            if rel_root == ".":
                rel_root = ""
                
            for d in dirs:
                dir_path = os.path.join(rel_root, d) if rel_root else d
                output.append(f"[DIR]  {dir_path}")
            for f in files:
                file_path = os.path.join(rel_root, f) if rel_root else f
                output.append(f"[FILE] {file_path}")
                
        if not output:
            return "No files found."
        # Sort files and directories alphabetically
        output.sort()
        return "\n".join(output)
    except Exception as e:
        return f"Error listing files: {e}"

def read_file(filename: str) -> str:
    """Reads the entire content of a file."""
    try:
        # Resolve real path to ensure it's in the workspace
        abs_path = os.path.abspath(filename)
        cwd = os.getcwd()
        if not abs_path.startswith(cwd):
            return "Error: Access denied. Cannot read files outside the project directory."
            
        if not os.path.exists(abs_path):
            return f"Error: File '{filename}' does not exist."
            
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{filename}': {e}"

def write_file(filename: str, content: str) -> str:
    """Writes content to a file. Overwrites if the file already exists."""
    try:
        # Resolve real path to ensure it's in the workspace
        abs_path = os.path.abspath(filename)
        cwd = os.getcwd()
        if not abs_path.startswith(cwd):
            return "Error: Access denied. Cannot write files outside the project directory."

        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: File '{filename}' written successfully."
    except Exception as e:
        return f"Error writing file '{filename}': {e}"

def calculate(expression: str) -> str:
    """Evaluates a basic math expression safely."""
    allowed_chars = "0123456789+-*/(). "
    if not all(c in allowed_chars for c in expression):
        return "Error: Invalid characters. Only numbers and basic math operators are allowed."
    try:
        # Safe evaluation
        result = eval(expression, {"__builtins__": None})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression '{expression}': {e}"


# Standardized descriptions for the LLM
TOOLS_METADATA = [
    ToolDefinition(
        name="list_project_files",
        description="Lists all files and directories recursively in the project workspace, ignoring standard build/git/.venv directories. Use this to discover the workspace files.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to list, defaults to the project root '.'",
                    "default": "."
                }
            }
        }
    ),
    ToolDefinition(
        name="read_file",
        description="Read the textual content of any file in the workspace. Useful for discovering file content or code details.",
        parameters={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The relative path to the file to read, e.g., 'pyproject.toml' or 'main.py'"
                }
            },
            "required": ["filename"]
        }
    ),
    ToolDefinition(
        name="write_file",
        description="Create a new file or overwrite an existing file with text content in the workspace.",
        parameters={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The relative path of the file to create or overwrite, e.g., 'README.md'"
                },
                "content": {
                    "type": "string",
                    "description": "The full text content to write to the file."
                }
            },
            "required": ["filename", "content"]
        }
    ),
    ToolDefinition(
        name="calculate",
        description="Evaluate a mathematical expression. Supports basic operations (+, -, *, /, parentheses).",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate, e.g. '3 * (4 + 5)'"
                }
            },
            "required": ["expression"]
        }
    )
]

# Mapping tool names to executable Python functions
TOOLS_MAP = {
    "list_project_files": list_project_files,
    "read_file": read_file,
    "write_file": write_file,
    "calculate": calculate
}

from providers import ToolDefinition
from . import io_tools
from . import math_tools
from . import multi_agent

# Expose provider setup method for main CLI bootstrap
set_active_provider = multi_agent.set_active_provider

# Standardized tool metadata signatures for the AI Provider
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
        description="Read the textual content of any file in the workspace. Supports reading specific segments via optional start_line and end_line parameters (1-indexed, inclusive).",
        parameters={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The relative path to the file to read, e.g., 'pyproject.toml' or 'main.py'"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Optional line number to start reading from (1-indexed, inclusive)."
                },
                "end_line": {
                    "type": "integer",
                    "description": "Optional line number to end reading at (1-indexed, inclusive)."
                }
            },
            "required": ["filename"]
        }
    ),
    ToolDefinition(
        name="write_file",
        description="Create a new file or overwrite an existing file with text content in the workspace (Thread Safe).",
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
    ),
    ToolDefinition(
        name="spawn_subagents_parallel",
        description="Spawns multiple specialized subagents in parallel to execute tasks concurrently. "
                    "Use this tool when you want to divide a large task (like reading multiple files or analyzing multiple structures) "
                    "into smaller tasks that can run in parallel. This keeps your parent context clean, concise, and focused. "
                    "Returns a JSON summary of the results of each subagent.",
        parameters={
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "description": "List of tasks to perform in parallel.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role_description": {
                                "type": "string",
                                "description": "The expertise/role of the subagent, e.g. 'File Reader Specialist' or 'Document Structuring Expert'."
                            },
                            "prompt": {
                                "type": "string",
                                "description": "The specific query, task, or file analyzing prompt for this subagent."
                            }
                        },
                        "required": ["role_description", "prompt"]
                    }
                }
            },
            "required": ["tasks"]
        }
    )
]

# Mapping tool names to executable Python functions
TOOLS_MAP = {
    "list_project_files": io_tools.list_project_files,
    "read_file": io_tools.read_file,
    "write_file": io_tools.write_file,
    "calculate": math_tools.calculate,
    "spawn_subagents_parallel": multi_agent.spawn_subagents_parallel
}

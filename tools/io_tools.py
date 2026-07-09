import os
import re
import ast
import threading
from typing import Optional

# Thread safety lock for writing/modifying operations
_file_write_lock = threading.Lock()

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


def read_file(filename: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """Reads the content of a file, supporting optional start_line and end_line parameters (1-indexed, inclusive)."""
    try:
        # Resolve real path to ensure it's in the workspace
        abs_path = os.path.abspath(filename)
        cwd = os.getcwd()
        if not abs_path.startswith(cwd):
            return "Error: Access denied. Cannot read files outside the project directory."
            
        if not os.path.exists(abs_path):
            return f"Error: File '{filename}' does not exist."
            
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Apply line range if provided
        if start_line is not None or end_line is not None:
            # 1-indexed, inclusive to 0-indexed, exclusive slice conversion
            s = (start_line - 1) if start_line is not None else 0
            s = max(0, min(s, len(lines)))
            
            e = end_line if end_line is not None else len(lines)
            e = max(s, min(e, len(lines)))
            
            selected_lines = lines[s:e]
            if not selected_lines:
                return f"Notice: No lines found in the requested range [{start_line or 1}:{end_line or 'end'}]."
            return "".join(selected_lines)
            
        return "".join(lines)
    except Exception as e:
        return f"Error reading file '{filename}': {e}"


def write_file(filename: str, content: str) -> str:
    """Writes content to a file. Overwrites if the file already exists (Thread Safe)."""
    try:
        # Resolve real path to ensure it's in the workspace
        abs_path = os.path.abspath(filename)
        cwd = os.getcwd()
        if not abs_path.startswith(cwd):
            return "Error: Access denied. Cannot write files outside the project directory."

        with _file_write_lock:
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
        return f"Success: File '{filename}' written successfully."
    except Exception as e:
        return f"Error writing file '{filename}': {e}"


def patch_file(filename: str, target_block: str, replacement_block: str) -> str:
    """
    Safely edits a file by replacing an exact, unique target block of text with a replacement block.
    This avoids rewriting the entire file and is thread-safe.
    """
    try:
        # Resolve real path to ensure it's in the workspace
        abs_path = os.path.abspath(filename)
        cwd = os.getcwd()
        if not abs_path.startswith(cwd):
            return "Error: Access denied. Cannot write files outside the project directory."

        if not os.path.exists(abs_path):
            return f"Error: File '{filename}' does not exist."

        with _file_write_lock:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify target block exists
            occurrences = content.count(target_block)
            if occurrences == 0:
                return (
                    f"Error: Target block was not found in '{filename}'. "
                    f"Make sure you specify the exact characters, spacing, and indentations."
                )
            if occurrences > 1:
                return (
                    f"Error: Target block was found {occurrences} times in '{filename}'. "
                    f"Please provide a more unique target block to avoid replacing wrong segments."
                )

            # Apply replacement
            new_content = content.replace(target_block, replacement_block, 1)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        return f"Success: File '{filename}' patched successfully."
    except Exception as e:
        return f"Error patching file '{filename}': {e}"


def search_grep(query: str, path: str = ".", is_regex: bool = False, case_insensitive: bool = True) -> str:
    """
    Searches for a query string or regex pattern recursively in the workspace files.
    """
    try:
        ignored = {".git", ".venv", "__pycache__", ".pytest_cache", ".idea", ".vscode"}
        flags = re.IGNORECASE if case_insensitive else 0
        
        # Compile pattern
        if is_regex:
            pattern = re.compile(query, flags)
        else:
            pattern = re.compile(re.escape(query), flags)
            
        results = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ignored]
            
            for f in files:
                # Search source/text files only
                if f.endswith((".py", ".toml", ".md", ".txt", ".json", ".yaml", ".yml", ".ini", ".env", ".example")):
                    file_path = os.path.relpath(os.path.join(root, f), path)
                    
                    try:
                        with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as file_handle:
                            for line_num, line in enumerate(file_handle, 1):
                                if pattern.search(line):
                                    results.append(f"{file_path}:{line_num}: {line.strip()}")
                    except Exception:
                        pass
                        
        if not results:
            return f"No matches found for '{query}'."
        return "\n".join(results[:100]) # Cap at 100 results to avoid context bloating
    except Exception as e:
        return f"Error executing search: {e}"


def get_outline(filename: str) -> str:
    """
    Parses a Python file and returns a high-level outline of its structure,
    including classes, methods, functions, and imports. This helps the agent
    understand the module layout without reading the entire source code.
    """
    try:
        # Resolve real path to ensure it's in the workspace
        abs_path = os.path.abspath(filename)
        cwd = os.getcwd()
        if not abs_path.startswith(cwd):
            return "Error: Access denied. Cannot access files outside the project directory."

        if not os.path.exists(abs_path):
            return f"Error: File '{filename}' does not exist."

        if not filename.endswith(".py"):
            return "Error: AST parsing is only supported for Python (.py) files."

        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=filename)
        
        outline = []
        outline.append(f"Structure outline for '{filename}':")
        
        for node in tree.body:
            if isinstance(node, ast.Import):
                for name in node.names:
                    outline.append(f"  [IMPORT] import {name.name}")
            elif isinstance(node, ast.ImportFrom):
                names = ", ".join(n.name for n in node.names)
                outline.append(f"  [IMPORT] from {node.module or ''} import {names}")
            elif isinstance(node, ast.FunctionDef):
                args = ", ".join(arg.arg for arg in node.args.args)
                doc = f" - \"{ast.get_docstring(node).splitlines()[0]}\"" if ast.get_docstring(node) else ""
                outline.append(f"  [FUNCTION] def {node.name}({args}){doc}")
            elif isinstance(node, ast.ClassDef):
                doc = f" - \"{ast.get_docstring(node).splitlines()[0]}\"" if ast.get_docstring(node) else ""
                outline.append(f"  [CLASS] class {node.name}{doc}")
                
                # Walk the class body to find methods
                for subnode in node.body:
                    if isinstance(subnode, ast.FunctionDef):
                        sub_args = ", ".join(arg.arg for arg in subnode.args.args)
                        sub_doc = f" - \"{ast.get_docstring(subnode).splitlines()[0]}\"" if ast.get_docstring(subnode) else ""
                        outline.append(f"    [METHOD] def {subnode.name}({sub_args}){sub_doc}")
                        
        if len(outline) == 1:
            return f"Notice: No classes, functions, or imports found in '{filename}'."
            
        return "\n".join(outline)
    except SyntaxError as se:
        return f"Error parsing Python syntax in '{filename}': {se}"
    except Exception as e:
        return f"Error getting outline for '{filename}': {e}"

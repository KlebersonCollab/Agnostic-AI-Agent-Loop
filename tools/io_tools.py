import os
import re
import ast
import threading
import subprocess
import fnmatch
from typing import Optional, Set, List

# Thread safety lock for writing/modifying operations
_file_write_lock = threading.Lock()

DEFAULT_IGNORED_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".idea", ".vscode", "node_modules", "dist", "build", ".next",
    ".nuxt", "target", "vendor", ".cache", "coverage", ".turbo"
}

def _is_safe_path(filename: str) -> bool:
    """Verifies that the absolute path of the file resides strictly within the current working directory."""
    try:
        abs_path = os.path.abspath(filename)
        cwd = os.getcwd()
        common = os.path.commonpath([cwd, abs_path])
        return common == cwd
    except (ValueError, Exception):
        return False


def _load_ignore_patterns(base_path: str = ".") -> List[str]:
    """
    Reads .gitignore and .dockerignore from the base_path directory (and parent dirs up to cwd)
    and returns a list of glob patterns to ignore.
    """
    patterns = []
    ignore_filenames = [".gitignore", ".dockerignore"]
    
    for filename in ignore_filenames:
        filepath = os.path.join(base_path, filename)
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        # Ignore comments and empty lines
                        if line and not line.startswith("#"):
                            # Normalize pattern leading slash if present
                            pattern = line.rstrip("/")
                            if pattern.startswith("/"):
                                pattern = pattern[1:]
                            patterns.append(pattern)
            except Exception:
                pass
    return patterns


def _is_ignored(rel_path: str, is_dir: bool, ignore_patterns: List[str]) -> bool:
    """Checks if a relative path matches any ignore patterns from .gitignore / .dockerignore."""
    path_parts = rel_path.split(os.sep)
    basename = path_parts[-1]
    
    for pattern in ignore_patterns:
        # Match basename or full relative path or any parent segment
        if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(rel_path, pattern):
            return True
        for part in path_parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def list_project_files(path: str = ".") -> str:
    """Lists files and folders in the specified directory recursively, ignoring default virtual environments, build dirs, and rules in .gitignore / .dockerignore."""
    try:
        if not _is_safe_path(path):
            return "Error: Access denied. Cannot list files outside the project directory."
        
        ignored_dirs = set(DEFAULT_IGNORED_DIRS)
        custom_patterns = _load_ignore_patterns(path)

        output = []
        for root, dirs, files in os.walk(path):
            rel_root = os.path.relpath(root, path)
            if rel_root == ".":
                rel_root = ""
                
            # Filter dirs in-place to prevent traversing ignored directories
            dirs[:] = [
                d for d in dirs 
                if d not in ignored_dirs and not _is_ignored(
                    os.path.join(rel_root, d) if rel_root else d, 
                    is_dir=True, 
                    ignore_patterns=custom_patterns
                )
            ]
            
            for d in dirs:
                dir_path = os.path.join(rel_root, d) if rel_root else d
                output.append(f"[DIR]  {dir_path}")
                
            for f in files:
                file_path = os.path.join(rel_root, f) if rel_root else f
                if not _is_ignored(file_path, is_dir=False, ignore_patterns=custom_patterns):
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
        if not _is_safe_path(filename):
            return "Error: Access denied. Cannot read files outside the project directory."
        abs_path = os.path.abspath(filename)
            
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
        if not _is_safe_path(filename):
            return "Error: Access denied. Cannot write files outside the project directory."
        abs_path = os.path.abspath(filename)

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
        if not _is_safe_path(filename):
            return "Error: Access denied. Cannot write files outside the project directory."
        abs_path = os.path.abspath(filename)

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
        if not _is_safe_path(path):
            return "Error: Access denied. Cannot search outside the project directory."
        
        ignored_dirs = set(DEFAULT_IGNORED_DIRS)
        custom_patterns = _load_ignore_patterns(path)
        flags = re.IGNORECASE if case_insensitive else 0
        
        # Compile pattern
        if is_regex:
            pattern = re.compile(query, flags)
        else:
            pattern = re.compile(re.escape(query), flags)
            
        results = []
        for root, dirs, files in os.walk(path):
            rel_root = os.path.relpath(root, path)
            if rel_root == ".":
                rel_root = ""

            dirs[:] = [
                d for d in dirs 
                if d not in ignored_dirs and not _is_ignored(
                    os.path.join(rel_root, d) if rel_root else d, 
                    is_dir=True, 
                    ignore_patterns=custom_patterns
                )
            ]
            
            for f in files:
                file_path = os.path.join(rel_root, f) if rel_root else f
                if _is_ignored(file_path, is_dir=False, ignore_patterns=custom_patterns):
                    continue

                # Search source/text files only
                if f.endswith((".py", ".toml", ".md", ".txt", ".json", ".yaml", ".yml", ".ini", ".env", ".example", ".ts", ".js", ".vue", ".jsx", ".tsx", ".css", ".html")):
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
        if not _is_safe_path(filename):
            return "Error: Access denied. Cannot access files outside the project directory."
        abs_path = os.path.abspath(filename)

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

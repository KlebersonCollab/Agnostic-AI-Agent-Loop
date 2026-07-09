import os
import threading

# Thread safety lock for writing operations
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

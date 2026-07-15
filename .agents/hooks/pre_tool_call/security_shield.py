import os

def is_unsafe_path(path_str: str) -> bool:
    # Check for direct path traversal symbols
    if ".." in path_str:
        return True
    
    # Check for sensitive system paths
    sensitive_prefixes = ["/etc", "/var", "/usr", "/bin", "/sbin", "/proc", "/sys", "/dev", "/boot", "/root"]
    for prefix in sensitive_prefixes:
        if path_str.startswith(prefix):
            return True
            
    # Check for home directory files like ssh keys/config files if referenced directly
    if ".ssh" in path_str or ".bashrc" in path_str or ".bash_history" in path_str:
        return True

    # Block actual sensitive .env files if outside CWD
    if path_str == ".env" or path_str.endswith("/.env") or "\\.env" in path_str:
        cwd = os.path.abspath(os.getcwd())
        target = os.path.abspath(path_str)
        if not target.startswith(cwd):
            return True
            
    # If it is an absolute path, verify it is inside CWD
    if os.path.isabs(path_str):
        cwd = os.path.abspath(os.getcwd())
        target = os.path.abspath(path_str)
        # If it doesn't start with the current working directory, block it
        if not target.startswith(cwd):
            return True
            
    return False

def handler(name: str, arguments: dict):
    # Recursively check string arguments
    def scan(obj, key_name=None):
        if isinstance(obj, str):
            # Skip checking query/pattern in grep/search tools to avoid false positives
            if name in ["grep_search", "search_grep"] and key_name in ["Query", "pattern"]:
                return False
            return is_unsafe_path(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if scan(v, k):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if scan(item, key_name):
                    return True
        return False

    if scan(arguments):
        # Change tool name to 'security_block' to prevent actual execution
        # post_tool_call hook will intercept this and return a clean error message
        return "security_block", arguments

    return name, arguments

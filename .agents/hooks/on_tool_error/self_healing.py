import sys

def handler(name: str, arguments: dict, exception: Exception) -> str:
    # Get exception type name and message
    exc_type = type(exception)
    exc_msg = str(exception)
    
    if exc_type is FileNotFoundError:
        return (
            f"Error: The target file/path specified in tool '{name}' was not found.\n"
            f"Action: Verify if the file path is correct, check spelling, or check if the file was deleted."
        )
    elif exc_type is PermissionError:
        return (
            f"Error: Permission denied when calling tool '{name}'.\n"
            f"Action: Ensure you have read/write permissions to the target path and that it is not locked by another process."
        )
    elif exc_type in [ModuleNotFoundError, ImportError]:
        return (
            f"Error: Missing required Python module or package during tool '{name}' execution: {exc_msg}\n"
            f"Action: Check if the package is installed in the current environment or run 'uv pip install <package>'."
        )
    elif exc_type is TypeError:
        return (
            f"Error: Invalid argument type or mismatched signature for tool '{name}': {exc_msg}\n"
            f"Action: Check the tool specification and verify the types and names of keys in arguments: {arguments}."
        )
    elif exc_type is ValueError:
        return f"Error executing tool '{name}' due to invalid value: {exc_msg}"
        
    # Return None to fallback to standard agent error message
    return None

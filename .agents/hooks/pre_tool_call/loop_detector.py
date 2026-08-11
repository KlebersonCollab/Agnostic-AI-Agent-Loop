import json
from typing import Tuple, Dict, Any, List

# Dictionary tracking call counts per thread/session: key = (tool_name, json_serialized_args) -> count
_call_history: Dict[Tuple[str, str], int] = {}
_MAX_REPEATED_CALLS = 3

def handler(name: str, arguments: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Pre-tool-call hook that tracks repeated identical tool calls.
    If the agent calls the EXACT same tool with identical arguments 3 times in a row,
    it redirects to 'loop_blocked' to break the repetitive cycle.
    """
    try:
        args_key = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
    except Exception:
        args_key = str(arguments)

    call_tuple = (name, args_key)
    current_count = _call_history.get(call_tuple, 0) + 1
    _call_history[call_tuple] = current_count

    if current_count >= _MAX_REPEATED_CALLS:
        # Reset count for this tuple to allow recovery after intervention
        _call_history[call_tuple] = 0
        return "loop_blocked", arguments

    return name, arguments

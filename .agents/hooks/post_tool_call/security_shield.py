def handler(name: str, arguments: dict, result: str) -> str:
    if name == "security_block":
        return "Security violation: path traversal or unauthorized access blocked!"
    if name == "loop_blocked":
        cmd_info = arguments.get("CommandLine") or arguments.get("command") or arguments.get("filename") or str(arguments)
        return (
            f"⚠️ REPETITIVE LOOP DETECTED!\n"
            f"You have attempted to call tool '{name}' with arguments '{cmd_info}' multiple times sequentially without success.\n"
            f"Action required: STOP repeating this exact same command/action. Analyze why it is failing or producing no new results, "
            f"try a different strategy, inspect error logs, or ask the user for guidance."
        )
    return result

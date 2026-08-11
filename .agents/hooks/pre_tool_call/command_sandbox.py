import re

# Blacklisted command patterns that present high destructive risks or unauthorized access
DANGEROUS_PATTERNS = [
    r"\brm\s+-[rRfF]*\s+[/~*]",       # Destructive file removal at root/home/all
    r"\bmkfs\b",                      # File system creation
    r"\bdd\s+if=",                     # Disk overwriting
    r"\bchmod\s+-[rRfF]*\s+777\s+/",   # Unsafe permissions changes on system
    r">:?\s*/dev/sd[a-z]",             # Writing directly to raw storage devices
    r"\b(nc|netcat|ncat)\s+.*-e",      # Netcat reverse shell execution
]

def handler(name: str, arguments: dict):
    """
    Pre-tool-call hook that inspects command lines executed via execute_command or bash
    and blocks dangerous system commands.
    """
    if name in ("execute_command", "run_command", "bash"):
        cmd = arguments.get("CommandLine") or arguments.get("command") or arguments.get("cmd") or ""
        if isinstance(cmd, str) and cmd:
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    return "security_block", arguments

    return name, arguments

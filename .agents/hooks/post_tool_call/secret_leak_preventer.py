import re

# Regex patterns for common sensitive credentials
SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{16,})['\"]?", "[REDACTED_SECRET]"),
    (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_SECRET]"),
    (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
    (r"xox[baprs]-[a-zA-Z0-9]{10,}", "[REDACTED_SLACK_TOKEN]"),
    (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
    (r"-----BEGIN (RSA|OPENSSH|PRIVATE) KEY-----", "[REDACTED_PRIVATE_KEY]"),
]

def handler(name: str, arguments: dict, result: str) -> str:
    """
    Post-tool-call hook that inspects tool outputs (e.g. read_file, execute_command)
    and redacts sensitive credentials/keys before they enter conversation history.
    """
    if not isinstance(result, str) or not result:
        return result

    redacted = result
    for pattern, replacement in SECRET_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted)

    return redacted

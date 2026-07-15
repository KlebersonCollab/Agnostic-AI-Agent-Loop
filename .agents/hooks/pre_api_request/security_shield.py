import os
import re

# Common patterns for API keys
API_KEY_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{48,256}"),  # OpenAI style keys
    re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"),   # Google Gemini style keys
]

def handler(messages: list, tools: list):
    # Fetch values of active API keys/secrets/tokens from environment
    env_keys = []
    for k, v in os.environ.items():
        if any(substring in k.upper() for substring in ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]):
            # Avoid redacting short strings to prevent false positives
            if v and len(v) > 8:
                env_keys.append(v)

    for msg in messages:
        if not getattr(msg, "content", None):
            continue
        
        # 1. Redact environmental keys
        for val in env_keys:
            if val in msg.content:
                msg.content = msg.content.replace(val, "[REDACTED_API_KEY]")
        
        # 2. Redact patterns
        for pattern in API_KEY_PATTERNS:
            msg.content = pattern.sub("[REDACTED_API_KEY]", msg.content)
            
    return messages, tools

from __future__ import annotations
import json

def _chars_to_tokens(text: str) -> int:
    return (len(text) + 3) // 4

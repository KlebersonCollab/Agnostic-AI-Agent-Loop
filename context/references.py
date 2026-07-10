from __future__ import annotations
import re
import os
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path

_QUOTED_REFERENCE_VALUE = r'(?:`[^`\n]+`|"[^"\n]+"|\'[^\'\n]+\')'
REFERENCE_PATTERN = re.compile(
    rf"(?<![\w/])@(?:(?P<simple>diff|staged)\b|(?P<kind>file|folder|git|url):(?P<value>{_QUOTED_REFERENCE_VALUE}(?::\d+(?:-\d+)?)?|\S+))"
)
TRAILING_PUNCTUATION = ",.;!?"

@dataclass(frozen=True)
class ContextReference:
    raw: str
    kind: str
    target: str
    start: int
    end: int
    line_start: int | None = None
    line_end: int | None = None

@dataclass
class ContextReferenceResult:
    message: str
    original_message: str
    references: List[ContextReference] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    injected_tokens: int = 0
    expanded: bool = False
    blocked: bool = False

def _strip_trailing_punctuation(value: str) -> str:
    return value.rstrip(TRAILING_PUNCTUATION)

def _strip_reference_wrappers(value: str) -> str:
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")) or \
       (value.startswith("`") and value.endswith("`")):
        return value[1:-1]
    return value

def _parse_file_reference_value(value: str) -> tuple[str, int | None, int | None]:
    val = _strip_reference_wrappers(value)
    match = re.search(r":(\d+)(?:-(\d+))?$", val)
    if match:
        line_start = int(match.group(1))
        line_end = int(match.group(2)) if match.group(2) else line_start
        target = val[:match.start()]
        return _strip_reference_wrappers(target), line_start, line_end
    return val, None, None

def parse_context_references(message: str) -> list[ContextReference]:
    refs: list[ContextReference] = []
    if not message:
        return refs

    for match in REFERENCE_PATTERN.finditer(message):
        simple = match.group("simple")
        if simple:
            refs.append(
                ContextReference(
                    raw=match.group(0),
                    kind=simple,
                    target="",
                    start=match.start(),
                    end=match.end(),
                )
            )
            continue

        kind = match.group("kind")
        value = _strip_trailing_punctuation(match.group("value") or "")
        line_start = None
        line_end = None
        target = _strip_reference_wrappers(value)

        if kind == "file":
            target, line_start, line_end = _parse_file_reference_value(value)

        refs.append(
            ContextReference(
                raw=match.group(0),
                kind=kind,
                target=target,
                start=match.start(),
                end=match.end(),
                line_start=line_start,
                line_end=line_end,
            )
        )

    return refs

_SENSITIVE_DIRS = {".ssh", ".aws", ".gnupg", ".kube", ".docker", ".azure", ".git"}
_SENSITIVE_FILES = {
    ".netrc",
    ".pgpass",
    ".npmrc",
    ".pypirc",
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.staging",
    ".git-credentials"
}

def _is_path_safe(target: str, cwd: str) -> tuple[bool, str | None]:
    cwd_path = Path(cwd).expanduser().resolve()
    try:
        raw_path = Path(target)
        if raw_path.is_absolute():
            resolved_path = raw_path.resolve()
        else:
            resolved_path = (cwd_path / raw_path).resolve()
    except Exception as e:
        return False, f"Invalid path resolution: {e}"

    try:
        resolved_path.relative_to(cwd_path)
    except ValueError:
        return False, "Path traversal detected: target is outside the workspace."

    for part in resolved_path.parts:
        if part in _SENSITIVE_DIRS:
            return False, f"Access denied: directory '{part}' is on the sensitive blocklist."

    if resolved_path.name in _SENSITIVE_FILES:
        return False, f"Access denied: file '{resolved_path.name}' is on the sensitive blocklist."

    return True, None


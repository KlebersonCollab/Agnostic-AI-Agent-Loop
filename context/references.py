from __future__ import annotations
import re
import os
import asyncio
import concurrent.futures
import subprocess
import urllib.request
import urllib.error
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

def _read_file_reference(target: str, line_start: int | None, line_end: int | None, cwd: str) -> str:
    safe, err = _is_path_safe(target, cwd)
    if not safe:
        return f"Warning: Blocked file reference '{target}': {err}"
    
    abs_path = os.path.abspath(os.path.join(cwd, target))
    if not os.path.exists(abs_path):
        return f"Warning: File not found '{target}'"
    if os.path.isdir(abs_path):
        return f"Warning: Target '{target}' is a directory, not a file."
        
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        if line_start is not None:
            start = max(1, line_start) - 1
            end = len(lines) if line_end is None else min(len(lines), line_end)
            sliced_lines = lines[start:end]
            content = "".join(sliced_lines)
            header = f"### File Reference: {target} (lines {line_start}-{line_end or ''})\n"
        else:
            content = "".join(lines)
            header = f"### File Reference: {target}\n"
            
        return f"{header}```\n{content}\n```\n"
    except Exception as e:
        return f"Warning: Error reading file '{target}': {e}"

def _fetch_url_reference(url: str) -> str:
    if not (url.startswith("http://") or url.startswith("https://")):
        return f"Warning: Invalid URL reference '{url}': must start with http:// or https://"
        
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8', errors='replace')
        
        if "<body" in html_content.lower() or "<html" in html_content.lower():
            text = re.sub(r'<(script|style).*?>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]*>', ' ', text)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)
        else:
            text = html_content
            
        max_chars = 40000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[Web content truncated to save space]..."
            
        return f"### URL Reference: {url}\n```\n{text}\n```\n"
    except Exception as e:
        return f"Warning: Error fetching URL '{url}': {e}"

def _get_git_diff(staged: bool = False) -> str:
    try:
        cmd = ["git", "diff", "--staged"] if staged else ["git", "diff"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode != 0:
            return f"Warning: Git diff command returned exit code {res.returncode}: {res.stderr}"
        diff_text = res.stdout.strip()
        if not diff_text:
            return "### Git Diff: No changes found."
        label = "Git Staged Diff" if staged else "Git Diff"
        return f"### {label}\n```diff\n{diff_text}\n```\n"
    except Exception as e:
        return f"Warning: Error executing git diff: {e}"

def _chars_to_tokens(text: str) -> int:
    return (len(text) + 3) // 4

async def _expand_reference(ref: ContextReference, cwd: str) -> tuple[str | None, str | None]:
    loop = asyncio.get_running_loop()
    
    if ref.kind == "file":
        content = await loop.run_in_executor(None, _read_file_reference, ref.target, ref.line_start, ref.line_end, cwd)
        if content.startswith("Warning:"):
            return content, None
        return None, content
        
    elif ref.kind == "url":
        content = await loop.run_in_executor(None, _fetch_url_reference, ref.target)
        if content.startswith("Warning:"):
            return content, None
        return None, content
        
    elif ref.kind == "diff":
        content = await loop.run_in_executor(None, _get_git_diff, False)
        if content.startswith("Warning:"):
            return content, None
        return None, content
        
    elif ref.kind == "staged":
        content = await loop.run_in_executor(None, _get_git_diff, True)
        if content.startswith("Warning:"):
            return content, None
        return None, content
        
    return f"Warning: Unknown reference kind '{ref.kind}'", None

def _remove_reference_tokens(message: str, refs: list[ContextReference]) -> str:
    sorted_refs = sorted(refs, key=lambda r: r.start, reverse=True)
    chars = list(message)
    for ref in sorted_refs:
        chars[ref.start:ref.end] = []
    
    clean_msg = "".join(chars)
    clean_msg = re.sub(r' +', ' ', clean_msg).strip()
    return clean_msg

async def preprocess_context_references_async(
    message: str,
    *,
    cwd: str,
    context_length: int = 128000
) -> ContextReferenceResult:
    refs = parse_context_references(message)
    if not refs:
        return ContextReferenceResult(message=message, original_message=message)
        
    warnings: List[str] = []
    blocks: List[str] = []
    injected_tokens = 0
    
    expanded = await asyncio.gather(*(_expand_reference(ref, cwd) for ref in refs))
    
    for warning, block in expanded:
        if warning:
            warnings.append(warning)
        if block:
            blocks.append(block)
            injected_tokens += _chars_to_tokens(block)
            
    soft_limit = int(context_length * 0.25)
    hard_limit = int(context_length * 0.50)
    
    if injected_tokens > hard_limit:
        warnings.append(
            f"@ context injection refused: {injected_tokens} tokens exceeds the 50% hard limit ({hard_limit})."
        )
        return ContextReferenceResult(
            message=message,
            original_message=message,
            references=refs,
            warnings=warnings,
            injected_tokens=injected_tokens,
            expanded=False,
            blocked=True
        )
        
    if injected_tokens > soft_limit:
        warnings.append(
            f"@ context injection warning: {injected_tokens} tokens exceeds the 25% soft limit ({soft_limit})."
        )
        
    stripped = _remove_reference_tokens(message, refs)
    final_message_parts = [stripped]
    
    if warnings:
        final_message_parts.append("\n--- Context Warnings ---\n" + "\n".join(f"- {w}" for w in warnings))
        
    if blocks:
        final_message_parts.append("\n--- Context References ---\n" + "\n".join(blocks))
        
    return ContextReferenceResult(
        message="\n\n".join(final_message_parts).strip(),
        original_message=message,
        references=refs,
        warnings=warnings,
        injected_tokens=injected_tokens,
        expanded=True,
        blocked=False
    )

def preprocess_context_references(
    message: str,
    *,
    cwd: str,
    context_length: int = 128000
) -> ContextReferenceResult:
    coro = preprocess_context_references_async(message, cwd=cwd, context_length=context_length)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
            
    return asyncio.run(coro)



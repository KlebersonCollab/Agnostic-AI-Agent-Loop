import os
import re
import json
from datetime import datetime, timezone

def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug)
    return slug[:40] or "extracted_pattern"

def handler(agent):
    """
    On-session-complete hook that automatically extracts reusable patterns and key solution steps
    from successful agent sessions into .specs/knowledge/patterns/ for continuous learning.
    """
    if not agent:
        return

    exit_reason = getattr(agent, "exit_reason", None)
    # Only extract patterns from clean, successful completions
    if exit_reason and exit_reason != "SUCCESS":
        return

    history = getattr(agent, "history", [])
    if not history:
        return

    user_objective = ""
    for msg in history:
        role = str(getattr(msg, "role", "") or "")
        content = getattr(msg, "content", "") or ""
        if ("user" in role.lower()) and content:
            user_objective = content.strip()
            break

    if not user_objective:
        return

    files_modified = set()
    tools_used = set()
    key_steps = []

    for msg in history:
        tool_calls = getattr(msg, "tool_calls", None) or []
        for tc in tool_calls:
            if hasattr(tc, "name"):
                name = str(tc.name)
            elif isinstance(tc, dict):
                name = str(tc.get("name", ""))
            else:
                name = str(tc)

            args = {}
            if hasattr(tc, "arguments"):
                args = tc.arguments
            elif isinstance(tc, dict):
                args = tc.get("arguments", {})

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            elif hasattr(args, "get"):
                pass
            else:
                args = {}

            if name:
                tools_used.add(name)

            if name in ("write_file", "patch_file", "replace_file_content"):
                fname = args.get("filename") or args.get("TargetFile")
                if fname:
                    files_modified.add(str(os.path.basename(str(fname))))
                    key_steps.append(f"Modify/create `{os.path.basename(str(fname))}` via `{name}`")
            elif name in ("execute_command", "run_command", "bash"):
                cmd = args.get("CommandLine") or args.get("command") or args.get("cmd") or ""
                if cmd:
                    key_steps.append(f"Execute `{str(cmd)[:60]}`")

    # Only extract pattern if meaningful file modifications or commands occurred
    if not files_modified and not key_steps:
        return

    slug = _slugify(user_objective)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    pattern_content = (
        f"# Pattern: {user_objective[:80]}\n\n"
        f"**Extracted Date**: {timestamp}\n"
        f"**Category**: Auto-Learned Pattern\n\n"
        f"## Objective\n"
        f"{user_objective}\n\n"
        f"## Solution Workflow & Steps\n"
    )
    for idx, step in enumerate(key_steps[:10], 1):
        pattern_content += f"{idx}. {step}\n"

    pattern_content += (
        f"\n## Artifacts & Dependencies\n"
        f"- **Files Changed**: {', '.join(sorted(files_modified)) if files_modified else 'None'}\n"
        f"- **Tools Used**: {', '.join(sorted(tools_used))}\n"
    )

    try:
        patterns_dir = os.path.join(os.getcwd(), ".specs", "knowledge", "patterns")
        os.makedirs(patterns_dir, exist_ok=True)
        pattern_file = os.path.join(patterns_dir, f"{slug}.md")
        with open(pattern_file, "w", encoding="utf-8") as f:
            f.write(pattern_content)
    except Exception:
        pass

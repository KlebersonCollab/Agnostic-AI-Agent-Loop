import os
import json
from datetime import datetime, timezone

def handler(agent):
    """
    On-session-complete hook that logs a concise Markdown summary (Session Digest)
    of the completed session to .agents/session_digests.log for audit and review.
    """
    if not agent:
        return

    session_id = getattr(agent, "session_id", "unknown")
    exit_reason = getattr(agent, "exit_reason", "SUCCESS") or "SUCCESS"
    history = getattr(agent, "history", [])

    files_written = set()
    tools_called = set()
    steps_count = 0

    for msg in history:
        if getattr(msg, "role", "") == "assistant":
            steps_count += 1
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
                tools_called.add(name)
            if name in ("write_file", "patch_file", "replace_file_content"):
                fname = args.get("filename") or args.get("TargetFile")
                if fname:
                    files_written.add(os.path.basename(str(fname)))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    digest_entry = (
        f"### 📋 Session Digest [{timestamp}]\n"
        f"- **Session ID**: `{session_id}`\n"
        f"- **Exit Reason**: `{exit_reason}`\n"
        f"- **Total Steps**: {steps_count}\n"
        f"- **Tools Used**: {', '.join(sorted(tools_called)) if tools_called else 'None'}\n"
        f"- **Files Modified**: {', '.join(sorted(files_written)) if files_written else 'None'}\n\n"
    )

    try:
        log_dir = os.path.join(os.getcwd(), ".agents")
        os.makedirs(log_dir, exist_ok=True)
        digest_file = os.path.join(log_dir, "session_digests.log")
        with open(digest_file, "a", encoding="utf-8") as f:
            f.write(digest_entry)
    except Exception:
        pass

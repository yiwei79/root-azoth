from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_REMINDER = (
    "[scope-gate] Write/Edit blocked — no approved scope card found.\n"
    "\n"
    "Before building, run /next to declare your intent and receive an approved scope card. "
    "This moves the confirm-before-building rule from memory to mechanical enforcement (D43/D50).\n"
    "\n"
    "To unblock: run /next, confirm the scope card, then retry your tool call."
)


def _deny(reason: str) -> None:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def _allow() -> None:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "",
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Fail-open: Claude Code guarantees valid JSON on stdin.
        # If stdin is empty or malformed (e.g. during testing), allow through.
        _allow()
        return

    tool_name = payload.get("tool_name", "")

    if tool_name not in {"Write", "Edit"}:
        _allow()
        return

    gate_path_env = os.environ.get("AZOTH_SCOPE_GATE_PATH")
    if gate_path_env:
        gate_path = Path(gate_path_env)
    else:
        gate_path = REPO_ROOT / ".azoth" / "scope-gate.json"

    # Exception: always allow writes to scope-gate.json itself.
    # /next writes this file after human approval — blocking it would be circular.
    file_path_str = payload.get("tool_input", {}).get("file_path", "")
    if file_path_str:
        try:
            if Path(file_path_str).resolve() == gate_path.resolve():
                _allow()
                return
        except (OSError, ValueError):
            pass

    if not gate_path.exists():
        _deny(_REMINDER)
        return

    try:
        data = json.loads(gate_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _deny("scope-gate.json is malformed")
        return

    if data.get("approved") is not True:
        _deny(_REMINDER)
        return

    expires_at_raw = data.get("expires_at", "")
    try:
        # fromisoformat() does not accept the Z suffix on Python < 3.11.
        # Normalize it to +00:00 before parsing.
        normalized = expires_at_raw.replace("Z", "+00:00") if expires_at_raw.endswith("Z") else expires_at_raw
        expires_at = datetime.fromisoformat(normalized)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expires_at:
            _deny(_REMINDER)
            return
    except (ValueError, TypeError):
        _deny("scope-gate.json expires_at is invalid ISO 8601")
        return

    _allow()


if __name__ == "__main__":
    main()

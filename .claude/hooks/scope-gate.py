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

_GOVERNED_REMINDER = (
    "[pipeline-gate] Write/Edit blocked — governed scope requires pipeline gate.\n"
    "\n"
    "Your scope-gate.json indicates M1 or delivery_pipeline: governed. You must run one of "
    "`/deliver-full`, `/auto`, or `/deliver` and execute **Stage 0 — Pipeline gate** first: "
    "Write `.azoth/pipeline-gate.json` with `session_id` matching scope-gate and the correct "
    "`pipeline` key. The PreToolUse hook enforces this (D51 mechanical layer).\n"
    "\n"
    "Do not implement governed backlog work inline without the delivery pipeline + subagent routing. "
    "After Stage 0, Write/Edit to other paths is allowed until scope expires."
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


def _parse_expires_at(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _is_governed_scope(data: dict) -> bool:
    return data.get("delivery_pipeline") == "governed" or data.get("target_layer") == "M1"


def _pipeline_gate_path() -> Path:
    env = os.environ.get("AZOTH_PIPELINE_GATE_PATH")
    if env:
        return Path(env)
    return REPO_ROOT / ".azoth" / "pipeline-gate.json"


def _pipeline_gate_ok(pg_path: Path, scope_data: dict) -> bool:
    sid = scope_data.get("session_id")
    if not sid or not pg_path.is_file():
        return False
    try:
        pg = json.loads(pg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if pg.get("approved") is not True:
        return False
    if pg.get("session_id") != sid:
        return False
    exp = _parse_expires_at(str(pg.get("expires_at", "")))
    if exp is None:
        return False
    if datetime.now(timezone.utc) >= exp:
        return False
    return True


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
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

    pg_path = _pipeline_gate_path()

    file_path_str = payload.get("tool_input", {}).get("file_path", "")

    def _resolved_target() -> Path | None:
        if not file_path_str:
            return None
        try:
            p = Path(file_path_str)
            if not p.is_absolute():
                p = (REPO_ROOT / p).resolve()
            else:
                p = p.resolve()
            return p
        except (OSError, ValueError):
            return None

    target = _resolved_target()

    # Bootstrap: allow writing scope-gate.json when absent / updating after /next.
    if target is not None:
        try:
            if target == gate_path.resolve():
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

    exp_scope = _parse_expires_at(str(data.get("expires_at", "")))
    if exp_scope is None:
        _deny("scope-gate.json expires_at is invalid ISO 8601")
        return
    if datetime.now(timezone.utc) >= exp_scope:
        _deny(_REMINDER)
        return

    if _is_governed_scope(data):
        is_pg_write = False
        if target is not None:
            try:
                is_pg_write = target == pg_path.resolve()
            except (OSError, ValueError):
                pass
        if not is_pg_write and not _pipeline_gate_ok(pg_path, data):
            _deny(_GOVERNED_REMINDER)
            return

    _allow()


if __name__ == "__main__":
    main()

"""
Append-only session telemetry for P5-004 / D14 (GOVERNANCE §6).

Writes JSON lines to `.azoth/telemetry/session-log.jsonl` (gitignored).
Must never raise — failures are swallowed so hooks cannot break PreToolUse.

Canonical ``outcome`` values (for log consumers):
  - ``record_pretooluse_write_edit``: ``allowed`` | ``denied`` (PreToolUse gate result).
  - ``record_session_lifecycle``: ``success`` (non-tool session events).

Other common keys: ``session_id``, ``turn``, ``timestamp``, ``source`` (``pretooluse`` | ``session``),
``tool_name``, ``action``, ``target``, ``denial_stage``, ``reason``, optional ``entropy_*``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def telemetry_dir(repo_root: Path) -> Path:
    env = os.environ.get("AZOTH_TELEMETRY_DIR")
    if env:
        return Path(env)
    return repo_root / ".azoth" / "telemetry"


def _safe_seq(raw: object) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _read_seq_state(seq_path: Path) -> dict:
    if not seq_path.is_file():
        return {}
    try:
        data = json.loads(seq_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _next_turn(seq_path: Path, session_id: str) -> int:
    """Monotonic turn per session_id; never raises (fail closed to 0)."""
    if not session_id:
        return 0
    try:
        data = _read_seq_state(seq_path)
        if data.get("session_id") != session_id:
            n = 1
        else:
            n = _safe_seq(data.get("seq", 0)) + 1
        seq_path.parent.mkdir(parents=True, exist_ok=True)
        seq_path.write_text(
            json.dumps({"session_id": session_id, "seq": n}, sort_keys=True),
            encoding="utf-8",
        )
        return n
    except Exception:
        return 0


def append_session_event(repo_root: Path, record: dict) -> None:
    """Append one JSON object as a line to session-log.jsonl."""
    try:
        root = telemetry_dir(repo_root)
        root.mkdir(parents=True, exist_ok=True)
        log_path = root / "session-log.jsonl"
        sid = str(record.get("session_id", "") or "")
        turn = _next_turn(root / "telemetry_seq.json", sid) if sid else 0
        line = {
            **record,
            "turn": turn if sid else record.get("turn", 0),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
    except Exception:
        pass


def record_pretooluse_write_edit(
    repo_root: Path,
    *,
    payload: dict,
    session_id: str,
    outcome: str,
    denial_stage: str | None = None,
    reason: str = "",
    entropy_delta: float | None = None,
    cumulative_entropy: float | None = None,
    entropy_zone: str | None = None,
) -> None:
    """Log one PreToolUse Write/Edit decision (P5-004)."""
    tool_name = str(payload.get("tool_name", "") or "")
    raw_input = payload.get("tool_input")
    tool_input = raw_input if isinstance(raw_input, dict) else {}
    target = str(tool_input.get("file_path", "") or "")
    if tool_name == "Write":
        action = "write"
    elif tool_name == "Edit":
        action = "edit"
    else:
        action = tool_name.lower()
    rec: dict = {
        "session_id": session_id,
        "source": "pretooluse",
        "agent": "unknown",
        "tool_name": tool_name,
        "action": action,
        "target": target,
        "outcome": outcome,
        "denial_stage": denial_stage or "",
        "reason": (reason or "")[:2000],
    }
    if entropy_delta is not None:
        rec["entropy_delta"] = round(entropy_delta, 6)
    if cumulative_entropy is not None:
        rec["cumulative_entropy"] = round(cumulative_entropy, 6)
    if entropy_zone:
        rec["entropy_zone"] = entropy_zone
    append_session_event(repo_root, rec)


def record_session_lifecycle(
    repo_root: Path,
    *,
    event: str,
    session_id: str = "",
    detail: str = "",
) -> None:
    """Optional: session_start, session_orientation, etc."""
    append_session_event(
        repo_root,
        {
            "session_id": session_id,
            "source": "session",
            "agent": "unknown",
            "tool_name": "",
            "action": event,
            "target": "",
            "outcome": "success",
            "denial_stage": "",
            "reason": (detail or "")[:2000],
        },
    )

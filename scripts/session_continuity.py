#!/usr/bin/env python3
"""Shared scope/session continuity helpers for resume and workflow routing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _parse_expires_at(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def active_scope(root: Path) -> dict[str, Any]:
    scope = load_json(root / ".azoth" / "scope-gate.json")
    if scope.get("approved") is not True:
        return {}
    expires_at = _parse_expires_at(str(scope.get("expires_at") or ""))
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        return {}
    return scope


def scope_conflict_message(
    root: Path,
    *,
    command_name: str,
    command_args: str = "",
    requested_session_id: str | None = None,
) -> str | None:
    """Return a hard-stop message when an explicit workflow conflicts with live scope."""
    scope = active_scope(root)
    active_session_id = str(scope.get("session_id") or "").strip()
    if not active_session_id:
        return None

    if requested_session_id and requested_session_id != active_session_id:
        return (
            f"Active scope '{active_session_id}' is still live. "
            f"Do not reopen '{requested_session_id}' until you `/park`, `/session-closeout`, or abort the current scope."
        )

    args = command_args.strip()
    if command_name == "next":
        return (
            f"Active scope '{active_session_id}' is still live for "
            f"{str(scope.get('goal') or 'the current goal')!r}. "
            "Use `resume`, `/park`, or `/session-closeout` before selecting a new task."
        )

    if command_name in {"auto", "dynamic-full-auto", "deliver", "deliver-full"} and args:
        return (
            f"Active scope '{active_session_id}' is still live for "
            f"{str(scope.get('goal') or 'the current goal')!r}. "
            f"Do not start a new `/{command_name}` goal until you `/park`, `/session-closeout`, or abort the current scope."
        )

    return None

#!/usr/bin/env python3
"""Shared helpers for Azoth's lightweight session-gate control plane."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SESSION_MODES = frozenset({"exploratory", "delivery"})
SESSION_GATE_RELATIVE_PATH = Path(".azoth") / "session-gate.json"
_ALLOWED_EXPLORATORY_PATHS = (
    Path(".azoth") / "session-gate.json",
    Path(".azoth") / "run-ledger.local.yaml",
    Path(".azoth") / "session-state.md",
    Path(".azoth") / "bootloader-state.md",
    Path(".azoth") / "memory" / "episodes.jsonl",
)
_DELIVERY_PREFIXES = (
    "implement",
    "fix",
    "add",
    "update",
    "patch",
    "refactor",
    "wire",
    "migrate",
    "edit",
    "change",
    "write code",
    "make the change",
)
_EXPLORATORY_PREFIXES = (
    "explore",
    "research",
    "brainstorm",
    "plan",
    "explain",
    "diagnose",
    "compare",
    "think through",
    "let's think through",
    "lets think through",
    "walk through",
)


def utc_now_iso(*, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def session_gate_path(root: Path) -> Path:
    return root / SESSION_GATE_RELATIVE_PATH


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def normalized_session_mode(data: dict[str, Any] | None) -> str:
    mode = str((data or {}).get("session_mode") or "").strip().lower()
    return mode if mode in SESSION_MODES else "delivery"


def session_gate_is_active(data: dict[str, Any] | None) -> bool:
    if not isinstance(data, dict):
        return False
    if str(data.get("status") or "").strip() != "active":
        return False
    return bool(str(data.get("session_id") or "").strip())


def active_session_gate(root: Path) -> dict[str, Any]:
    gate = load_json(session_gate_path(root))
    return gate if session_gate_is_active(gate) else {}


def matching_exploratory_session(root: Path, goal: str) -> dict[str, Any]:
    gate = active_session_gate(root)
    if (
        gate
        and normalized_session_mode(gate) == "exploratory"
        and str(gate.get("goal") or "").strip() == goal.strip()
    ):
        return gate
    return {}


def classify_goal_intent(prompt: str) -> str:
    lowered = prompt.strip().lower()
    if any(lowered.startswith(prefix) for prefix in _DELIVERY_PREFIXES):
        return "delivery"
    if any(lowered.startswith(prefix) for prefix in _EXPLORATORY_PREFIXES):
        return "exploratory"
    return "exploratory"


def _slugify_goal(goal: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", goal.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:48] or "adhoc-session"


def default_session_id(goal: str, *, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return f"{current.strftime('%Y-%m-%d')}-adhoc-{_slugify_goal(goal)}"


def _upsert_session_registry_entry(
    root: Path,
    *,
    session_id: str,
    goal: str,
    session_mode: str,
    status: str,
    ide: str,
    next_action: str,
    updated_at: str,
    backlog_id: str = "AD-HOC",
    closed_at: str | None = None,
) -> None:
    ledger_path = root / ".azoth" / "run-ledger.local.yaml"
    ledger = load_yaml(ledger_path)
    if not ledger:
        ledger = {"schema_version": 1, "runs": []}
    sessions = ledger.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
        ledger["sessions"] = sessions
    entry = next(
        (
            item
            for item in sessions
            if isinstance(item, dict) and str(item.get("session_id") or "") == session_id
        ),
        None,
    )
    if entry is None:
        entry = {"session_id": session_id}
        sessions.append(entry)
    entry.update(
        {
            "session_id": session_id,
            "backlog_id": backlog_id,
            "goal": goal,
            "status": status,
            "ide": ide,
            "next_action": next_action,
            "updated_at": updated_at,
            "session_mode": session_mode,
        }
    )
    if closed_at:
        entry["closed_at"] = closed_at
    elif status == "closed":
        entry["closed_at"] = updated_at
    else:
        entry.pop("closed_at", None)
    write_yaml(ledger_path, ledger)


def _write_exploratory_session_state(
    root: Path,
    *,
    session_id: str,
    goal: str,
    timestamp: str,
    state: str,
    next_action: str,
    ide: str,
) -> None:
    session_state = {
        "session_id": session_id,
        "session_mode": "exploratory",
        "state": state,
        "last_ide": ide,
        "timestamp": timestamp,
        "active_task": (
            f"Exploratory — {goal}" if state == "active" else f"Closed exploratory — {goal}"
        ),
        "active_files": [],
        "pending_decisions": [],
        "approved_scope": "Exploratory session (no write scope)",
        "next_action": next_action,
    }
    write_yaml(root / ".azoth" / "session-state.md", session_state)


def ensure_exploratory_session(
    root: Path,
    *,
    goal: str,
    ide: str = "codex",
    now: datetime | None = None,
) -> dict[str, Any]:
    timestamp = utc_now_iso(now=now)
    existing = matching_exploratory_session(root, goal)
    if existing:
        session_id = str(existing.get("session_id") or default_session_id(goal, now=now))
        opened_at = str(existing.get("opened_at") or timestamp)
    else:
        session_id = default_session_id(goal, now=now)
        opened_at = timestamp

    gate = {
        "session_id": session_id,
        "goal": goal,
        "session_mode": "exploratory",
        "opened_at": opened_at,
        "updated_at": timestamp,
        "status": "active",
        "approved_by": "system",
    }
    scope_gate = root / ".azoth" / "scope-gate.json"
    if not scope_gate.exists():
        write_json(scope_gate, {})
    write_json(session_gate_path(root), gate)

    next_action = "Continue the exploratory session or escalate into /auto before repo edits."
    _upsert_session_registry_entry(
        root,
        session_id=session_id,
        goal=goal,
        session_mode="exploratory",
        status="active",
        ide=ide,
        next_action=next_action,
        updated_at=timestamp,
    )
    _write_exploratory_session_state(
        root,
        session_id=session_id,
        goal=goal,
        timestamp=timestamp,
        state="active",
        next_action=next_action,
        ide=ide,
    )
    return gate


def close_session_gate(
    root: Path,
    *,
    timestamp: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    gate_path = session_gate_path(root)
    gate = load_json(gate_path)
    if not gate:
        return {}
    if session_id and str(gate.get("session_id") or "") != session_id:
        return {}
    gate["status"] = "closed"
    gate["updated_at"] = timestamp
    gate["closed_at"] = timestamp
    write_json(gate_path, gate)
    return gate


def is_exploratory_write_target(root: Path, target: Path) -> bool:
    try:
        resolved = target.resolve()
    except (OSError, ValueError):
        return False
    for rel_path in _ALLOWED_EXPLORATORY_PATHS:
        try:
            if resolved == (root / rel_path).resolve():
                return True
        except (OSError, ValueError):
            continue
    return False

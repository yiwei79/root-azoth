#!/usr/bin/env python3
"""Shared scope/session continuity helpers for resume and workflow routing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from session_gate import active_session_gate


PIPELINE_COMMANDS = {"auto", "autonomous-auto", "dynamic-full-auto", "deliver", "deliver-full"}
_EXTEND_THRESHOLD_SECONDS = 30 * 60
_WORK_ITEM_RE = re.compile(r"\b(?:[A-Z]{1,6}-\d{1,6}|P\d+-\d+|D\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TransitionDecision:
    """Resolved session transition for a new user request."""

    action: str
    reason: str
    active_session_id: str = ""
    active_goal: str = ""


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
    if str(scope.get("scope_status") or "active").strip() not in {"", "active"}:
        return {}
    expires_at = _parse_expires_at(str(scope.get("expires_at") or ""))
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        return {}
    return scope


def session_registry_entry_is_resumable(
    root: Path,
    entry: dict[str, Any],
    *,
    scope: dict[str, Any] | None = None,
) -> bool:
    """Return True only for session records backed by a real resume signal.

    `status: parked` is resumable by itself. `status: active` is resumable only when
    the repo still has a matching live approved scope for the same session.
    """
    status = str(entry.get("status") or "").strip()
    if status == "parked":
        return True
    if status != "active":
        return False

    live_scope = scope if scope is not None else active_scope(root)
    if not live_scope:
        return False
    return (
        str(live_scope.get("session_id") or "").strip()
        == str(entry.get("session_id") or "").strip()
    )


def governance_mode(scope: dict[str, Any]) -> str:
    """Return the normalized governance mode for a scope gate."""
    mode = str(scope.get("governance_mode") or "").strip()
    if mode in {"standard", "governed"}:
        return mode
    legacy = str(scope.get("delivery_pipeline") or "").strip()
    if legacy == "governed":
        return "governed"
    if legacy == "standard":
        return "standard"
    if str(scope.get("target_layer") or "").strip() == "M1":
        return "governed"
    return "standard"


def selected_pipeline_command(
    scope: dict[str, Any], pipeline_gate: dict[str, Any] | None = None
) -> str:
    """Return the selected delivery pipeline command when known."""
    if isinstance(pipeline_gate, dict):
        candidate = str(
            pipeline_gate.get("pipeline_command") or pipeline_gate.get("pipeline") or ""
        ).strip()
        if candidate:
            return candidate

    candidate = str(scope.get("pipeline_command") or "").strip()
    if candidate:
        return candidate

    legacy = str(scope.get("delivery_pipeline") or "").strip()
    if legacy in PIPELINE_COMMANDS:
        return legacy
    return ""


def _looks_like_same_goal(requested_goal: str, active_goal: str) -> bool:
    left = requested_goal.strip()
    right = active_goal.strip()
    if not left or not right:
        return False
    if left.lower() == right.lower():
        return True

    left_work_item = _WORK_ITEM_RE.search(left)
    right_work_item = _WORK_ITEM_RE.search(right)
    if left_work_item and right_work_item:
        return left_work_item.group(0).lower() == right_work_item.group(0).lower()
    if left_work_item or right_work_item:
        return False

    def _normalize(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.lower()))

    return _normalize(left) == _normalize(right)


def resolve_transition(
    root: Path,
    *,
    command_name: str = "",
    command_args: str = "",
    prompt_goal: str = "",
    requested_session_id: str | None = None,
    now: datetime | None = None,
) -> TransitionDecision:
    """Resolve whether a request should open, resume, extend, or replace a session."""
    if now is None:
        now = datetime.now(timezone.utc)

    scope = active_scope(root)
    active_session = scope or active_session_gate(root)
    active_session_id = str(active_session.get("session_id") or "").strip()
    active_goal = str(active_session.get("goal") or "").strip()
    if not active_session_id:
        return TransitionDecision(action="new", reason="no-active-session")

    if requested_session_id:
        if requested_session_id == active_session_id:
            return TransitionDecision(
                action="resume",
                reason="requested-active-session",
                active_session_id=active_session_id,
                active_goal=active_goal,
            )
        return TransitionDecision(
            action="conflict",
            reason="different-live-session",
            active_session_id=active_session_id,
            active_goal=active_goal,
        )

    requested_goal = command_args.strip() or prompt_goal.strip()
    expires_at = _parse_expires_at(str(scope.get("expires_at") or ""))
    ttl_low = False
    if expires_at is not None:
        ttl_low = int((expires_at - now).total_seconds()) <= _EXTEND_THRESHOLD_SECONDS

    if command_name == "next":
        return TransitionDecision(
            action="replace",
            reason="next-with-live-scope",
            active_session_id=active_session_id,
            active_goal=active_goal,
        )

    if not scope:
        if requested_goal and _looks_like_same_goal(requested_goal, active_goal):
            return TransitionDecision(
                action="resume",
                reason="matching-exploratory-goal",
                active_session_id=active_session_id,
                active_goal=active_goal,
            )
        if requested_goal:
            return TransitionDecision(
                action="replace",
                reason="different-exploratory-goal",
                active_session_id=active_session_id,
                active_goal=active_goal,
            )
        return TransitionDecision(
            action="resume",
            reason="active-exploratory-session",
            active_session_id=active_session_id,
            active_goal=active_goal,
        )

    if command_name in PIPELINE_COMMANDS:
        if requested_goal and not _looks_like_same_goal(requested_goal, active_goal):
            return TransitionDecision(
                action="replace",
                reason="different-pipeline-goal",
                active_session_id=active_session_id,
                active_goal=active_goal,
            )
        if ttl_low:
            return TransitionDecision(
                action="extend",
                reason="matching-goal-low-ttl",
                active_session_id=active_session_id,
                active_goal=active_goal,
            )
        return TransitionDecision(
            action="resume",
            reason="matching-pipeline-goal",
            active_session_id=active_session_id,
            active_goal=active_goal,
        )

    if requested_goal:
        if _looks_like_same_goal(requested_goal, active_goal):
            if ttl_low:
                return TransitionDecision(
                    action="extend",
                    reason="matching-freeform-goal-low-ttl",
                    active_session_id=active_session_id,
                    active_goal=active_goal,
                )
            return TransitionDecision(
                action="resume",
                reason="matching-freeform-goal",
                active_session_id=active_session_id,
                active_goal=active_goal,
            )
        return TransitionDecision(
            action="replace",
            reason="different-freeform-goal",
            active_session_id=active_session_id,
            active_goal=active_goal,
        )

    if ttl_low:
        return TransitionDecision(
            action="extend",
            reason="live-scope-low-ttl",
            active_session_id=active_session_id,
            active_goal=active_goal,
        )
    return TransitionDecision(
        action="resume",
        reason="live-scope",
        active_session_id=active_session_id,
        active_goal=active_goal,
    )


def scope_conflict_message(
    root: Path,
    *,
    command_name: str,
    command_args: str = "",
    requested_session_id: str | None = None,
) -> str | None:
    """Return a hard-stop message when an explicit workflow conflicts with live scope."""
    decision = resolve_transition(
        root,
        command_name=command_name,
        command_args=command_args,
        requested_session_id=requested_session_id,
    )
    active_session_id = decision.active_session_id
    if not active_session_id:
        return None

    if decision.action in {"resume", "extend"}:
        return None

    if decision.action == "conflict":
        return (
            f"Active scope '{active_session_id}' is still live. "
            f"Do not reopen '{requested_session_id}' until you `/park`, `/session-closeout`, or abort the current scope."
        )

    if decision.action == "replace" and command_name == "next":
        return (
            f"Active scope '{active_session_id}' is still live for "
            f"{decision.active_goal or 'the current goal'!r}. "
            "Treat a new `/next` request as a replace decision: resume or extend the current scope, "
            "or park/close it before selecting new work."
        )

    if decision.action == "replace" and command_name in PIPELINE_COMMANDS and command_args.strip():
        return (
            f"Active scope '{active_session_id}' is still live for "
            f"{decision.active_goal or 'the current goal'!r}. "
            f"Treat a new `/{command_name}` request as a replace decision: park or close the "
            "current scope, then open the new pipeline deliberately."
        )

    return None

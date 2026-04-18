#!/usr/bin/env python3
"""UserPromptSubmit hook for Azoth workflow token routing in Codex."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

COMMAND_DIR = ROOT / ".claude" / "commands"
LEADING_COMMAND_RE = re.compile(r"^\s*/([a-z][a-z0-9-]*)\b(.*)$", re.DOTALL)

PIPELINE_COMMANDS = {"auto", "dynamic-full-auto", "deliver", "deliver-full"}


def _emit(additional_context: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": additional_context,
                }
            }
        )
    )


def _looks_like_actionable_freeform(prompt: str) -> bool:
    stripped = prompt.strip().lower()
    prefixes = (
        "continue",
        "resume",
        "keep going",
        "let's continue",
        "work on",
        "implement",
        "fix",
        "add",
        "update",
        "refactor",
        "change",
    )
    return stripped.startswith(prefixes)


def _parse_iso_datetime(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _load_active_scope() -> dict[str, str] | None:
    scope_path = ROOT / ".azoth" / "scope-gate.json"
    if not scope_path.is_file():
        return None

    try:
        gate = json.loads(scope_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not gate.get("approved"):
        return None

    expires_at = gate.get("expires_at")
    if isinstance(expires_at, str) and expires_at.strip():
        try:
            if _parse_iso_datetime(expires_at) <= datetime.now(timezone.utc):
                return None
        except ValueError:
            return None

    return gate


def _transition_guidance(prompt: str, *, command_name: str = "", command_args: str = "") -> str:
    gate = _load_active_scope()
    if not gate:
        return ""

    active_session_id = str(gate.get("session_id") or "").strip()
    active_goal = str(gate.get("goal") or "").strip()
    backlog_id = str(gate.get("backlog_id") or "").strip()
    request_text = (command_args if command_name else prompt).strip().lower()
    active_goal_lc = active_goal.lower()
    backlog_id_lc = backlog_id.lower()

    if not active_session_id:
        return ""

    if (
        not request_text
        or request_text.startswith(("continue", "resume", "keep going", "let's continue"))
        or (active_goal_lc and active_goal_lc in request_text)
        or (active_goal_lc and request_text in active_goal_lc)
        or (backlog_id_lc and backlog_id_lc in request_text)
    ):
        return (
            f"Active scope `{active_session_id}` matches this request. "
            "Treat it as a resume/continue decision, not as a brand-new scope."
        )

    if command_name or _looks_like_actionable_freeform(prompt):
        return (
            f"Active scope `{active_session_id}` is live for "
            f"`{active_goal or 'the current goal'}`. "
            "Treat this request as a replace decision: park or close the current scope before opening a new one."
        )

    return ""


def _governed_write_reminder() -> str:
    return (
        "Continuity guidance classifies the session transition only; it does not authorize writes. "
        "Governed edits still require a valid scope-gate and, when applicable, pipeline-gate."
    )


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return 0

    match = LEADING_COMMAND_RE.match(prompt)
    if match is None:
        if not _looks_like_actionable_freeform(prompt):
            return 0
        transition = _transition_guidance(prompt)
        if transition:
            _emit(transition)
        return 0

    name = match.group(1)
    command_args = match.group(2).strip()
    command_path = COMMAND_DIR / f"{name}.md"
    if not command_path.is_file():
        return 0

    guidance = [
        f"Azoth workflow token detected: `/{name}`.",
        f"Read `{command_path.relative_to(ROOT).as_posix()}` and follow that repository command contract instead of improvising.",
    ]

    if name in PIPELINE_COMMANDS:
        guidance.extend(
            [
                "Keep the orchestrator in the main thread.",
                "Use staged subagents when the command or `skills/subagent-router/SKILL.md` requires isolation.",
                "For write-enabled or governed stages, follow the gate procedure in the command doc before editing.",
            ]
        )
    elif name == "session-closeout":
        guidance.append(
            "During closeout, treat W1/W2/W4 under `.azoth/` as authoritative, attempt W3, and log `W3 deferred` if blocked."
        )
    elif name in {"start", "next"}:
        guidance.append(
            "Honor the existing scope/pipeline state under `.azoth/` before proposing new work."
        )

    transition = _transition_guidance(prompt, command_name=name, command_args=command_args)
    if transition:
        guidance.append(transition)
        guidance.append(_governed_write_reminder())

    _emit(" ".join(guidance))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""UserPromptSubmit hook for Azoth workflow token routing in Codex."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from session_continuity import resolve_transition  # noqa: E402

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


def _transition_guidance(prompt: str, *, command_name: str = "", command_args: str = "") -> str:
    decision = resolve_transition(
        ROOT,
        command_name=command_name,
        command_args=command_args,
        prompt_goal="" if command_name else prompt,
    )
    if not decision.active_session_id or decision.action == "new":
        return ""

    if decision.action == "resume":
        return (
            f"Active scope `{decision.active_session_id}` matches this request. "
            "Treat it as a resume/continue decision, not as a brand-new scope."
        )
    if decision.action == "extend":
        return (
            f"Active scope `{decision.active_session_id}` is still the right session but TTL is low. "
            "Offer extend/checkpoint/abort rather than reopening scope from scratch."
        )
    if decision.action == "replace":
        return (
            f"Active scope `{decision.active_session_id}` is live for "
            f"`{decision.active_goal or 'the current goal'}`. "
            "Treat this request as a replace decision: park or close the current scope before opening a new one."
        )
    if decision.action == "conflict":
        return (
            f"A different live scope `{decision.active_session_id}` already exists. "
            "Do not silently retarget it."
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
                f"Prefer the staged Codex entry path: use `/skills` or type `$azoth-{name}` so Codex executes the generated Azoth wrapper skill instead of relying on literal token fallback alone.",
                "Keep the orchestrator in the main thread.",
                "Use staged subagents when the command or `skills/subagent-router/SKILL.md` requires isolation.",
                "An explicit pipeline token is a request for staged pipeline execution and staged delegation, not permission to improvise the work inline.",
                "If staged delegation is unavailable, STOP and ask the human whether to authorize delegation, adjust the pipeline, or switch platforms.",
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

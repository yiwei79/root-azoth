#!/usr/bin/env python3
"""UserPromptSubmit hook for Azoth workflow token routing in Codex."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMAND_DIR = ROOT / ".claude" / "commands"
LEADING_COMMAND_RE = re.compile(r"^\s*/([a-z][a-z0-9-]*)\b")

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
        return 0

    name = match.group(1)
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

    _emit(" ".join(guidance))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

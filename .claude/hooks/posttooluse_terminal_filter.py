#!/usr/bin/env python3
"""Filter verbose terminal PostToolUse output for Claude and VS Code hook payloads.

JSON payloads use the VS Code/Copilot-style `tool_response` field and emit
`hookSpecificOutput.additionalContext`. Raw stdin falls back to the legacy
Claude shell-filter behavior so existing PostToolUse flows keep working.
"""

from __future__ import annotations

import json
import re
import sys

_MAX_LINES = 100
_MAX_EMITTED_LINES = 150
_ERROR_RE = re.compile(r"(error|fail|exception|traceback|assert|warning:)", re.IGNORECASE)


def _looks_like_terminal_payload(payload: dict) -> bool:
    tool_name = str(payload.get("tool_name", "") or "").replace("-", "_").lower()
    if tool_name in {"bash", "terminal", "run_in_terminal", "terminal_command", "execute"}:
        return True
    tool_input = payload.get("tool_input")
    return isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str)


def _response_text(payload: dict) -> str:
    response = payload.get("tool_response")
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        for key in ("stdout", "stderr", "output", "content", "text", "message"):
            value = response.get(key)
            if isinstance(value, str) and value:
                return value
        return json.dumps(response, sort_keys=True)
    if isinstance(response, list):
        parts = [item for item in response if isinstance(item, str) and item]
        return "\n".join(parts)
    return ""


def _filter_output(text: str) -> str:
    lines = text.splitlines()
    line_count = len(lines)
    if line_count <= _MAX_LINES:
        return ""

    selected: list[str] = []
    seen: set[int] = set()
    for idx, line in enumerate(lines):
        if not _ERROR_RE.search(line):
            continue
        start = max(0, idx - 1)
        end = min(line_count, idx + 6)
        for pos in range(start, end):
            if pos in seen:
                continue
            seen.add(pos)
            selected.append(lines[pos])
            if len(selected) >= _MAX_EMITTED_LINES:
                break
        if len(selected) >= _MAX_EMITTED_LINES:
            break

    if selected:
        return f"[Output filtered: {line_count} lines -> errors/warnings only]\n" + "\n".join(
            selected[:_MAX_EMITTED_LINES]
        )

    tail = "\n".join(lines[-10:])
    return (
        f"[Output filtered: {line_count} lines, {len(text)} chars -> no errors detected]\n"
        "Last 10 lines:\n"
        f"{tail}"
    )


def _emit_json(additional_context: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": additional_context,
                }
            }
        )
    )


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        filtered = _filter_output(raw)
        sys.stdout.write(filtered or raw)
        return

    if not isinstance(payload, dict) or not _looks_like_terminal_payload(payload):
        _emit_json("")
        return

    filtered = _filter_output(_response_text(payload))
    _emit_json(filtered)


if __name__ == "__main__":
    main()

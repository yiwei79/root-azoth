#!/usr/bin/env python3
"""PreToolUse scope gate only (thin CLI). Production Write/Edit path: edit_pretooluse_orchestrator.py."""

from __future__ import annotations

import json
import sys

from scope_gate_core import emit_hook_response, evaluate_scope_gate


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        emit_hook_response(allow=True)
        return
    tool_name = payload.get("tool_name", "")
    if tool_name not in {"Write", "Edit"}:
        emit_hook_response(allow=True)
        return
    result = evaluate_scope_gate(payload)
    if not result.allowed:
        emit_hook_response(allow=False, reason=result.deny_reason)
        return
    emit_hook_response(allow=True)


if __name__ == "__main__":
    main()

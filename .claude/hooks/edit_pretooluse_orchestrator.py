#!/usr/bin/env python3
"""
PreToolUse orchestrator: scope gate (D43/D50) then entropy check (TRUST_CONTRACT §1, P5-002).

Normative: kernel/TRUST_CONTRACT.md §1; behavioral alignment: skills/entropy-guard/SKILL.md
"""

from __future__ import annotations

import json
import sys

from entropy_check import evaluate_entropy
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
    if result.skip_entropy:
        emit_hook_response(allow=True)
        return
    if result.scope_data is None:
        emit_hook_response(allow=True)
        return
    ent = evaluate_entropy(payload, result.scope_data)
    if not ent.allowed:
        emit_hook_response(allow=False, reason=ent.reason)
        return
    if ent.yellow_advisory:
        emit_hook_response(allow=True, reason=ent.reason)
        return
    emit_hook_response(allow=True)


if __name__ == "__main__":
    main()

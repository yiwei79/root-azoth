#!/usr/bin/env python3
"""Combined scope-gate and pipeline-gate validator for Azoth pipelines.

Superset of scope_gate_check.py — validates both gate files and their
cross-consistency. Used by orchestrator post-approval gate-write (S1/S4)
and cross-platform gate enforcement (Cursor parity, Copilot instructions).

Usage:
    python3 scripts/check_gates.py [--session-id SESSION_ID] [--require-pipeline-gate]

Exit codes:
    0  all checked gates are valid
    1  any gate is invalid, missing, or inconsistent
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Tuple

from scope_gate_check import check_scope_gate, find_scope_gate


SCOPE_GATE_REQUIRED_FIELDS = frozenset({
    "session_id",
    "goal",
    "approved",
    "approved_by",
    "expires_at",
    "backlog_id",
    "delivery_pipeline",
    "target_layer",
})

PIPELINE_GATE_REQUIRED_FIELDS = frozenset({
    "session_id",
    "pipeline",
    "approved",
    "expires_at",
    "opened_at",
})


def find_pipeline_gate() -> Path:
    """Locate .azoth/pipeline-gate.json relative to the repo root."""
    here = Path(__file__).resolve().parent.parent
    return here / ".azoth" / "pipeline-gate.json"


def check_scope_gate_fields(session_id: Optional[str] = None) -> Tuple[bool, str]:
    """Validate scope-gate.json exists, is approved, unexpired, and has all 8 fields."""
    valid, message = check_scope_gate(session_id)
    if not valid:
        return valid, message

    gate_path = find_scope_gate()
    try:
        with open(gate_path, encoding="utf-8") as f:
            gate = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"❌ BLOCKED — scope-gate.json is malformed: {e}"

    missing = SCOPE_GATE_REQUIRED_FIELDS - set(gate.keys())
    if missing:
        return False, f"❌ BLOCKED — scope-gate.json missing fields: {sorted(missing)}"

    return True, message


def check_pipeline_gate(
    session_id: Optional[str] = None,
    require: bool = False,
) -> Tuple[bool, str]:
    """Validate pipeline-gate.json if present or required."""
    gate_path = find_pipeline_gate()

    if not gate_path.exists():
        if require:
            return False, "❌ BLOCKED — pipeline-gate.json required but not found."
        return True, "ℹ️  pipeline-gate.json not present (not required)."

    try:
        with open(gate_path, encoding="utf-8") as f:
            gate = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"❌ BLOCKED — pipeline-gate.json is malformed: {e}"

    missing = PIPELINE_GATE_REQUIRED_FIELDS - set(gate.keys())
    if missing:
        return False, f"❌ BLOCKED — pipeline-gate.json missing fields: {sorted(missing)}"

    if not gate.get("approved"):
        return False, "❌ BLOCKED — pipeline-gate.json is not approved."

    # Validate session_id consistency with scope-gate
    scope_path = find_scope_gate()
    if scope_path.exists():
        try:
            with open(scope_path, encoding="utf-8") as f:
                scope = json.load(f)
            if gate.get("session_id") != scope.get("session_id"):
                return (
                    False,
                    f"❌ BLOCKED — session_id mismatch: scope-gate has "
                    f"'{scope.get('session_id')}', pipeline-gate has "
                    f"'{gate.get('session_id')}'.",
                )
        except (json.JSONDecodeError, OSError):
            pass

    if session_id and gate.get("session_id") != session_id:
        return (
            False,
            f"❌ BLOCKED — pipeline-gate session_id mismatch: expected '{session_id}', "
            f"gate has '{gate.get('session_id')}'.",
        )

    pipeline_name = gate.get("pipeline", "(unknown)")
    return True, f"✅ Pipeline gate valid — pipeline: {pipeline_name}"


def check_all_gates(
    session_id: Optional[str] = None,
    require_pipeline_gate: bool = False,
) -> Tuple[bool, list[str]]:
    """Validate all gate files. Returns (all_valid, list_of_messages)."""
    messages: list[str] = []
    all_valid = True

    scope_valid, scope_msg = check_scope_gate_fields(session_id)
    messages.append(scope_msg)
    if not scope_valid:
        all_valid = False

    pipe_valid, pipe_msg = check_pipeline_gate(session_id, require_pipeline_gate)
    messages.append(pipe_msg)
    if not pipe_valid:
        all_valid = False

    return all_valid, messages


def main():
    parser = argparse.ArgumentParser(
        description="Validate .azoth/scope-gate.json and .azoth/pipeline-gate.json"
    )
    parser.add_argument(
        "--session-id",
        help="Optional session ID to match against both gates",
        default=None,
    )
    parser.add_argument(
        "--require-pipeline-gate",
        action="store_true",
        help="Fail if pipeline-gate.json is not present",
    )
    args = parser.parse_args()

    all_valid, messages = check_all_gates(args.session_id, args.require_pipeline_gate)
    for msg in messages:
        print(msg)
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()

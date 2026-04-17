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

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from scope_gate_check import check_scope_gate, find_scope_gate


SCOPE_GATE_CORE_REQUIRED_FIELDS = frozenset(
    {
        "session_id",
        "goal",
        "approved",
        "approved_by",
        "expires_at",
        "backlog_id",
        "target_layer",
    }
)

SCOPE_GATE_MODE_FIELDS = frozenset({"delivery_pipeline", "governance_mode"})

PIPELINE_GATE_CORE_REQUIRED_FIELDS = frozenset(
    {
        "session_id",
        "approved",
        "expires_at",
        "opened_at",
    }
)

PIPELINE_GATE_MODE_FIELDS = frozenset({"pipeline", "pipeline_command"})
PIPELINE_COMMANDS = frozenset({"auto", "dynamic-full-auto", "deliver", "deliver-full"})


def find_pipeline_gate(root: Path | None = None) -> Path:
    """Locate .azoth/pipeline-gate.json relative to the repo root."""
    here = root or Path(__file__).resolve().parent.parent
    return here / ".azoth" / "pipeline-gate.json"


def _parse_iso(raw: str) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00") if text.endswith("Z") else text
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pipeline_command(pipeline_gate: dict) -> str:
    return str(pipeline_gate.get("pipeline_command") or pipeline_gate.get("pipeline") or "").strip()


def _scope_requires_pipeline_gate(scope_gate: dict) -> bool:
    governance_mode = str(scope_gate.get("governance_mode") or "").strip()
    if governance_mode == "governed":
        return True
    legacy = str(scope_gate.get("delivery_pipeline") or "").strip()
    if legacy == "governed":
        return True
    return str(scope_gate.get("target_layer") or "").strip() == "M1"


def _scope_selected_pipeline(scope_gate: dict) -> str:
    candidate = str(scope_gate.get("pipeline_command") or "").strip()
    if candidate:
        return candidate
    legacy = str(scope_gate.get("delivery_pipeline") or "").strip()
    if legacy in PIPELINE_COMMANDS:
        return legacy
    return ""


def check_scope_gate_fields(
    session_id: Optional[str] = None,
    root: Path | None = None,
) -> Tuple[bool, str]:
    """Validate scope-gate.json exists, is approved, unexpired, and has bridge-required fields."""
    valid, message = check_scope_gate(session_id, root=root)
    if not valid:
        return valid, message

    gate_path = find_scope_gate(root)
    try:
        with open(gate_path, encoding="utf-8") as f:
            gate = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"❌ BLOCKED — scope-gate.json is malformed: {e}"

    missing = SCOPE_GATE_CORE_REQUIRED_FIELDS - set(gate.keys())
    if missing:
        return False, f"❌ BLOCKED — scope-gate.json missing fields: {sorted(missing)}"
    if not (SCOPE_GATE_MODE_FIELDS & set(gate.keys())):
        return (
            False,
            "❌ BLOCKED — scope-gate.json missing mode field: require one of "
            "['delivery_pipeline', 'governance_mode']",
        )

    return True, message


def check_pipeline_gate(
    session_id: Optional[str] = None,
    require: bool = False,
    root: Path | None = None,
) -> Tuple[bool, str]:
    """Validate pipeline-gate.json if present or required."""
    gate_path = find_pipeline_gate(root)
    scope_path = find_scope_gate(root)
    if scope_path.exists():
        try:
            with open(scope_path, encoding="utf-8") as f:
                scope = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            return False, f"❌ BLOCKED — scope-gate.json is malformed during pipeline cross-check: {exc}"
        require = require or _scope_requires_pipeline_gate(scope)
    else:
        scope = None

    if not gate_path.exists():
        if require:
            return False, "❌ BLOCKED — pipeline-gate.json required but not found."
        return True, "ℹ️  pipeline-gate.json not present (not required)."

    try:
        with open(gate_path, encoding="utf-8") as f:
            gate = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"❌ BLOCKED — pipeline-gate.json is malformed: {e}"

    missing = PIPELINE_GATE_CORE_REQUIRED_FIELDS - set(gate.keys())
    if missing:
        return False, f"❌ BLOCKED — pipeline-gate.json missing fields: {sorted(missing)}"
    if not (PIPELINE_GATE_MODE_FIELDS & set(gate.keys())):
        return (
            False,
            "❌ BLOCKED — pipeline-gate.json missing mode field: require one of "
            "['pipeline', 'pipeline_command']",
        )

    if not gate.get("approved"):
        return False, "❌ BLOCKED — pipeline-gate.json is not approved."

    opened_at = _parse_iso(str(gate.get("opened_at") or ""))
    if opened_at is None:
        return False, "❌ BLOCKED — pipeline-gate.json opened_at is invalid ISO 8601."

    expires_at = _parse_iso(str(gate.get("expires_at") or ""))
    if expires_at is None:
        return False, "❌ BLOCKED — pipeline-gate.json expires_at is invalid ISO 8601."
    if datetime.now(timezone.utc) >= expires_at:
        return False, "❌ BLOCKED — pipeline-gate.json is expired."
    if opened_at > expires_at:
        return False, "❌ BLOCKED — pipeline-gate.json opened_at is after expires_at."

    pipeline_name = _pipeline_command(gate)
    if pipeline_name not in PIPELINE_COMMANDS:
        return (
            False,
            "❌ BLOCKED — pipeline-gate.json pipeline must be one of "
            f"{sorted(PIPELINE_COMMANDS)}, got {pipeline_name!r}.",
        )

    # Validate session_id consistency with scope-gate
    if scope is not None:
        if gate.get("session_id") != scope.get("session_id"):
            return (
                False,
                f"❌ BLOCKED — session_id mismatch: scope-gate has "
                f"'{scope.get('session_id')}', pipeline-gate has "
                f"'{gate.get('session_id')}'.",
            )
        scope_expires = _parse_iso(str(scope.get("expires_at") or ""))
        if scope_expires is not None and scope_expires != expires_at:
            return (
                False,
                "❌ BLOCKED — expires_at mismatch between scope-gate.json and "
                "pipeline-gate.json.",
            )
        selected_pipeline = _scope_selected_pipeline(scope)
        if selected_pipeline and selected_pipeline != pipeline_name:
            return (
                False,
                "❌ BLOCKED — pipeline-gate command does not match the selected "
                "pipeline recorded in scope-gate.json.",
            )

    if session_id and gate.get("session_id") != session_id:
        return (
            False,
            f"❌ BLOCKED — pipeline-gate session_id mismatch: expected '{session_id}', "
            f"gate has '{gate.get('session_id')}'.",
        )

    return True, f"✅ Pipeline gate valid — pipeline: {pipeline_name}"


def check_all_gates(
    session_id: Optional[str] = None,
    require_pipeline_gate: bool = False,
    root: Path | None = None,
) -> Tuple[bool, list[str]]:
    """Validate all gate files. Returns (all_valid, list_of_messages)."""
    messages: list[str] = []
    all_valid = True

    scope_valid, scope_msg = check_scope_gate_fields(session_id, root=root)
    messages.append(scope_msg)
    if not scope_valid:
        all_valid = False

    pipe_valid, pipe_msg = check_pipeline_gate(session_id, require_pipeline_gate, root=root)
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
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Optional repo root containing .azoth/ (for tests and relocated worktrees).",
    )
    args = parser.parse_args()

    all_valid, messages = check_all_gates(
        args.session_id,
        args.require_pipeline_gate,
        root=args.root,
    )
    for msg in messages:
        print(msg)
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()

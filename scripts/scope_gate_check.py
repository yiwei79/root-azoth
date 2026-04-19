#!/usr/bin/env python3
"""Scope-gate validation helper for Antigravity workflow preconditions.

Usage:
    python3 scripts/scope_gate_check.py [--session-id SESSION_ID]

Exit codes:
    0  scope gate is valid (approved, unexpired)
    1  scope gate is invalid, missing, or expired

Prints a human-readable status line suitable for embedding in workflow output.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple


def find_scope_gate(root: Path | None = None) -> Path:
    """Locate .azoth/scope-gate.json relative to the repo root."""
    here = root or Path(__file__).resolve().parent.parent
    return here / ".azoth" / "scope-gate.json"


def parse_iso_datetime(s: str) -> datetime:
    """Parse ISO-8601 datetime string, handling +00:00 and Z suffixes."""
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def check_scope_gate(
    session_id: Optional[str] = None, root: Path | None = None
) -> Tuple[bool, str]:
    """Validate the scope gate and return (valid, message)."""
    gate_path = find_scope_gate(root)

    if not gate_path.exists():
        return False, "❌ BLOCKED — scope-gate.json not found. Run /next to open scope."

    try:
        with open(gate_path, encoding="utf-8") as f:
            gate = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"❌ BLOCKED — scope-gate.json is malformed: {e}"

    # Check approved
    if not gate.get("approved"):
        close_reason = gate.get("close_reason", "")
        if close_reason:
            return (
                False,
                f"❌ BLOCKED — scope gate is closed (reason: {close_reason}). "
                f"Run /next to open a new scope.",
            )
        return False, "❌ BLOCKED — scope gate is not approved. Run /next to open scope."

    # Check expires_at
    expires_at_str = gate.get("expires_at")
    if not expires_at_str:
        # No expiry — treat as valid (some gates omit TTL)
        pass
    else:
        try:
            expires_at = parse_iso_datetime(expires_at_str)
            now = datetime.now(timezone.utc)
            if expires_at <= now:
                return (
                    False,
                    f"❌ BLOCKED — scope gate expired at {expires_at_str}. "
                    f"Run /next to refresh scope.",
                )
        except (ValueError, TypeError):
            return False, f"❌ BLOCKED — scope-gate expires_at is unparseable: {expires_at_str}"

    # Check session_id if provided
    if session_id:
        gate_session = gate.get("session_id", "")
        if gate_session != session_id:
            return (
                False,
                f"❌ BLOCKED — session_id mismatch: expected '{session_id}', "
                f"gate has '{gate_session}'.",
            )

    # Valid
    goal = gate.get("goal", "(unknown)")
    gate_session = gate.get("session_id", "(unknown)")
    expires_msg = ""
    if expires_at_str:
        try:
            expires_at = parse_iso_datetime(expires_at_str)
            remaining = expires_at - datetime.now(timezone.utc)
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes = remainder // 60
            expires_msg = f" | TTL: {hours}h{minutes:02d}m remaining"
        except (ValueError, TypeError):
            pass

    return (
        True,
        f"✅ Scope gate valid — session: {gate_session} | goal: {goal}{expires_msg}",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Validate .azoth/scope-gate.json for workflow preconditions"
    )
    parser.add_argument(
        "--session-id",
        help="Optional session ID to match against the gate",
        default=None,
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Optional repo root containing .azoth/ (for tests and relocated worktrees).",
    )
    args = parser.parse_args()

    valid, message = check_scope_gate(args.session_id, root=args.root)
    print(message)
    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()

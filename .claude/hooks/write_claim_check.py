#!/usr/bin/env python3
"""
write_claim_check.py — P1-015 write-claim gate for PreToolUse orchestrator.

Evaluates whether the requesting session may write. Enforces the coarse
repo-wide write lease stored in run-ledger.local.yaml.

Usage (programmatic):
    from write_claim_check import evaluate_write_claim
    result = evaluate_write_claim(root, requesting_session="sess-id")
    if not result.allowed:
        # deny the write

Reads the ledger path from AZOTH_LEDGER_PATH env var; if unset, derives it
as <root>/.azoth/run-ledger.local.yaml.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class WriteClaimResult:
    """Result of write-claim evaluation. Compatible with ScopeGateResult interface."""

    allowed: bool
    deny_reason: str = ""


def evaluate_write_claim(root: Path, requesting_session: str) -> WriteClaimResult:
    """Evaluate whether requesting_session may write under the current write claim.

    Returns WriteClaimResult(allowed=True) when:
      - No write claim exists in the ledger, OR
      - The claim is held by requesting_session (same session), OR
      - The claim has expired (stale; caller should run resolve_stale_claims).

    Returns WriteClaimResult(allowed=False, deny_reason=...) when:
      - An unexpired claim is held by a different session, OR
      - The write-claim ledger cannot be loaded or validated safely.
    """
    if not str(requesting_session or "").strip():
        # Bootstrap/admin writes may not yet carry a scope session. Those writes are
        # gated upstream by scope_gate_core exemptions and must not be blocked by the
        # repo write lease.
        return WriteClaimResult(allowed=True)

    # Import run_ledger — try the canonical scripts/ dir relative to this hook file
    # first (repo install), then scripts/ relative to the provided root (test override).
    _this_file = Path(__file__).resolve()
    _repo_scripts = str(_this_file.parent.parent.parent / "scripts")
    _root_scripts = str(root / "scripts")
    for _sd in (_repo_scripts, _root_scripts):
        if _sd not in sys.path:
            sys.path.insert(0, _sd)

    try:
        from run_ledger import load_write_claim  # type: ignore[import]
    except ImportError as exc:
        return WriteClaimResult(
            allowed=False,
            deny_reason=f"[write-claim] BLOCKED — could not import run_ledger: {exc}",
        )

    # Derive the effective root: if AZOTH_LEDGER_PATH is set (test override), derive root
    # from the ledger path so load_write_claim reads the correct ledger.
    _ledger_env = os.environ.get("AZOTH_LEDGER_PATH")
    if _ledger_env:
        # Derive root from ledger path: <root>/.azoth/run-ledger.local.yaml
        effective_root = Path(_ledger_env).parent.parent
    else:
        effective_root = root

    try:
        claim = load_write_claim(effective_root)
    except Exception as exc:
        return WriteClaimResult(
            allowed=False,
            deny_reason=f"[write-claim] BLOCKED — could not load write claim: {exc}",
        )

    if claim is None:
        return WriteClaimResult(allowed=True)

    holder = claim.get("session_id", "")
    if not str(holder or "").strip():
        return WriteClaimResult(
            allowed=False,
            deny_reason="[write-claim] BLOCKED — write claim is malformed: missing session_id.",
        )
    if holder == requesting_session:
        return WriteClaimResult(allowed=True)

    # Check expiry
    raw_exp = claim.get("expires_at", "")
    try:
        normalized = raw_exp.replace("Z", "+00:00") if raw_exp.endswith("Z") else raw_exp
        exp_dt = datetime.fromisoformat(normalized)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return WriteClaimResult(
            allowed=False,
            deny_reason="[write-claim] BLOCKED — write claim is malformed: invalid expires_at.",
        )

    if datetime.now(timezone.utc) >= exp_dt:
        # Claim has expired — allow, but caller should call resolve_stale_claims
        return WriteClaimResult(allowed=True)

    # Unexpired foreign claim — deny
    deny_reason = (
        f"[write-claim] Write blocked — write claim held by '{holder}' until {raw_exp}. "
        f"Ask session '{holder}' to release the claim, or wait for expiry and run "
        f"`python3 scripts/run_ledger.py resolve-stale`."
    )
    return WriteClaimResult(allowed=False, deny_reason=deny_reason)

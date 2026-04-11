#!/usr/bin/env python3
"""
PreToolUse orchestrator: scope gate (D43/D50), alignment-summary (BL-012, P5-003),
write-claim gate (P1-015), then entropy (P5-002).

Order: scope → alignment handoff validation → write-claim gate → entropy.
Normative: kernel/TRUST_CONTRACT.md §1–§2; skills/entropy-guard/SKILL.md
Telemetry: P5-004 — append to `.azoth/telemetry/session-log.jsonl` (D14).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from alignment_summary_gate import evaluate_alignment_handoff, resolve_repo_root
from entropy_check import evaluate_entropy
from scope_gate_core import emit_hook_response, evaluate_scope_gate, normalized_write_action
from session_telemetry import record_pretooluse_write_edit


def _session_id(scope_data: dict | None) -> str:
    if not scope_data:
        return ""
    return str(scope_data.get("session_id", "") or "")


def main() -> None:
    raw = sys.stdin.read()
    repo_root = resolve_repo_root()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        emit_hook_response(allow=True)
        return
    if normalized_write_action(payload) is None:
        emit_hook_response(allow=True)
        return
    result = evaluate_scope_gate(payload, repo_root=repo_root)
    if not result.allowed:
        record_pretooluse_write_edit(
            repo_root,
            payload=payload,
            session_id=_session_id(result.scope_data),
            outcome="denied",
            denial_stage="scope",
            reason=result.deny_reason,
        )
        emit_hook_response(allow=False, reason=result.deny_reason)
        return
    align = evaluate_alignment_handoff(payload, repo_root=repo_root)
    if not align.allowed:
        record_pretooluse_write_edit(
            repo_root,
            payload=payload,
            session_id=_session_id(result.scope_data),
            outcome="denied",
            denial_stage="alignment",
            reason=align.deny_reason,
        )
        emit_hook_response(allow=False, reason=align.deny_reason)
        return

    # Write-claim gate (P1-015): after alignment, before entropy skip.
    # Derive ledger root from AZOTH_LEDGER_PATH env (test override) or scope-gate path.
    _ledger_env = os.environ.get("AZOTH_LEDGER_PATH")
    if _ledger_env:
        _claim_root = Path(_ledger_env).parent.parent
    else:
        _claim_root = repo_root
    try:
        hooks_dir = str(Path(__file__).parent)
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        from write_claim_check import evaluate_write_claim  # type: ignore[import]

        _requesting_session = _session_id(result.scope_data)
        _claim_result = evaluate_write_claim(_claim_root, _requesting_session)
        if not _claim_result.allowed:
            record_pretooluse_write_edit(
                repo_root,
                payload=payload,
                session_id=_requesting_session,
                outcome="denied",
                denial_stage="write_claim",
                reason=_claim_result.deny_reason,
            )
            emit_hook_response(allow=False, reason=_claim_result.deny_reason)
            return
    except Exception as _wc_exc:
        # Write-claim check must not crash the orchestrator; fail open.
        # Record the warning so silent failures are visible in telemetry.
        print(f"[write-claim] WARNING: unexpected error in write_claim_check: {_wc_exc}", file=sys.stderr)

    if result.skip_entropy:
        record_pretooluse_write_edit(
            repo_root,
            payload=payload,
            session_id=_session_id(result.scope_data),
            outcome="allowed",
            denial_stage="",
            reason="skip_entropy",
        )
        emit_hook_response(allow=True)
        return
    if result.scope_data is None:
        record_pretooluse_write_edit(
            repo_root,
            payload=payload,
            session_id="",
            outcome="allowed",
            denial_stage="",
            reason="scope_data_none",
        )
        emit_hook_response(allow=True)
        return
    ent = evaluate_entropy(payload, result.scope_data, repo_root=repo_root)
    sid = _session_id(result.scope_data)
    if not ent.allowed:
        record_pretooluse_write_edit(
            repo_root,
            payload=payload,
            session_id=sid,
            outcome="denied",
            denial_stage="entropy",
            reason=ent.reason,
            entropy_delta=ent.entropy_delta,
            cumulative_entropy=ent.cumulative_entropy,
            entropy_zone=ent.entropy_zone,
        )
        emit_hook_response(allow=False, reason=ent.reason)
        return
    if ent.yellow_advisory:
        record_pretooluse_write_edit(
            repo_root,
            payload=payload,
            session_id=sid,
            outcome="allowed",
            denial_stage="",
            reason=ent.reason,
            entropy_delta=ent.entropy_delta,
            cumulative_entropy=ent.cumulative_entropy,
            entropy_zone=ent.entropy_zone,
        )
        emit_hook_response(allow=True, reason=ent.reason)
        return
    record_pretooluse_write_edit(
        repo_root,
        payload=payload,
        session_id=sid,
        outcome="allowed",
        denial_stage="",
        reason="",
        entropy_delta=ent.entropy_delta,
        cumulative_entropy=ent.cumulative_entropy,
        entropy_zone=ent.entropy_zone,
    )
    emit_hook_response(allow=True)


if __name__ == "__main__":
    main()

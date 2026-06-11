#!/usr/bin/env python3
"""FD-003 guard — subagent isolation.

A pipeline that names multiple stage kinds (context-recovery, planning-bank,
validation, run-ledger) but reports zero spawned subagents is the FD-003
failure mode: stage narration happens inline, isolation is fake. This guard
refuses to mark such a run complete.

Rule:
  - If the run plan declares >=2 side-effectful stages with zero spawned
    subagents, the guard fails.
  - Side-effectful stage kinds: planning_bank, run_ledger_update,
    context_recovery, validation, hydration.

Input: JSON payload with a "stages" list. Each stage is a dict with at least
"name" and "kind". "spawned_subagent" (bool) and "subagent_type" (str|None)
are honored when present.

Invoked by scripts/azoth_guards.py (the runner). Standalone CLI removed —
operators debugging a guard should run the test suite or invoke the runner
with a single-section payload.
"""

from __future__ import annotations

from typing import Any


SIDE_EFFECT_STAGE_KINDS = {
    "planning_bank",
    "run_ledger_update",
    "context_recovery",
    "validation",
    "hydration",
}


def check(payload: dict[str, Any]) -> dict[str, Any]:
    stages = payload.get("stages")
    if stages is None:
        return {"ok": True, "violations": [], "reason": "no stages provided"}
    if not isinstance(stages, list):
        return {
            "ok": False,
            "violations": [
                {
                    "rule": "fd_003_invalid_payload",
                    "message": "payload.stages must be a list",
                }
            ],
        }

    side_effect_stages = [
        s
        for s in stages
        if isinstance(s, dict) and str(s.get("kind", "")).strip() in SIDE_EFFECT_STAGE_KINDS
    ]
    spawned = [
        s for s in side_effect_stages if isinstance(s, dict) and bool(s.get("spawned_subagent"))
    ]

    if len(side_effect_stages) >= 2 and not spawned:
        return {
            "ok": False,
            "violations": [
                {
                    "rule": "fd_003_no_spawned_subagent",
                    "message": (
                        "Pipeline declares multiple side-effectful stages with zero "
                        "spawned subagents. Stage narration would happen inline. "
                        "Either spawn a real subagent or mark stages as advisory."
                    ),
                    "stages": [str(s.get("kind")) for s in side_effect_stages],
                }
            ],
        }

    return {
        "ok": True,
        "violations": [],
        "spawned_count": len(spawned),
        "side_effect_stage_count": len(side_effect_stages),
    }

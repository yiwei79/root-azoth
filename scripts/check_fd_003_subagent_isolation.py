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

Exit codes:
  0 — guard passes
  1 — guard blocks (violation)
  2 — usage error (bad input)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SIDE_EFFECT_STAGE_KINDS = {
    "planning_bank",
    "run_ledger_update",
    "context_recovery",
    "validation",
    "hydration",
}


def check(payload: dict[str, object]) -> dict[str, object]:
    stages = payload.get("stages")
    if stages is None:
        return {"ok": True, "violations": [], "reason": "no stages provided"}
    if not isinstance(stages, list):
        return {
            "ok": False,
            "violations": [{
                "rule": "fd_003_invalid_payload",
                "message": "payload.stages must be a list",
            }],
        }

    side_effect_stages = [
        s for s in stages
        if isinstance(s, dict) and str(s.get("kind", "")).strip() in SIDE_EFFECT_STAGE_KINDS
    ]
    spawned = [
        s for s in side_effect_stages
        if isinstance(s, dict) and bool(s.get("spawned_subagent"))
    ]

    if len(side_effect_stages) >= 2 and not spawned:
        return {
            "ok": False,
            "violations": [{
                "rule": "fd_003_no_spawned_subagent",
                "message": (
                    "Pipeline declares multiple side-effectful stages with zero "
                    "spawned subagents. Stage narration would happen inline. "
                    "Either spawn a real subagent or mark stages as advisory."
                ),
                "stages": [str(s.get("kind")) for s in side_effect_stages],
            }],
        }

    return {
        "ok": True,
        "violations": [],
        "spawned_count": len(spawned),
        "side_effect_stage_count": len(side_effect_stages),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: --input {args.input} not found", file=__import__("sys").stderr)
        return 2

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = check(payload)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["ok"]:
            print("FD-003: OK")
        else:
            print("FD-003: FAIL")
            for v in result["violations"]:
                print(f"  - {v['rule']}: {v['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""FD-005 guard — completion semantics.

Hydration is planning-state work, not delivery. Marking a persistent goal
"complete" because hydration succeeded is the FD-005 failure mode: roadmap
truth has to be repaired afterwards. This guard distinguishes administrative
closeout from implementation acceptance.

Rule:
  - To mark a persistent goal "complete" or "done", achieved_states must
    include implementation_accepted AND tests_pass AND receipt_written.
  - "hydrated" alone is insufficient.
  - States that count as "admin-only" (hydrated, planned, scoped) trigger
    a specific rule: fd_005_admin_complete_pretends_delivery.

Input: JSON payload with:
  - marking (str): "complete", "done", "in_progress", etc.
  - achieved_states (list[str]): the states the run has reached.
  - missing_states (list[str], optional): explicit missing-states list.

Exit codes:
  0 — guard passes
  1 — guard blocks
  2 — usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_FOR_COMPLETION = (
    "implementation_accepted",
    "tests_pass",
    "receipt_written",
)

ADMIN_ONLY_STATES = frozenset({"hydrated", "planned", "scoped"})


def check(payload: dict[str, object]) -> dict[str, object]:
    marking = str(payload.get("marking") or "").lower().strip()
    if marking not in ("complete", "done"):
        return {
            "ok": True,
            "violations": [],
            "reason": "non-completion marking",
        }

    achieved = {str(s) for s in (payload.get("achieved_states") or [])}
    missing = [r for r in REQUIRED_FOR_COMPLETION if r not in achieved]

    if not missing:
        return {"ok": True, "violations": []}

    # Distinguish: admin-only completion vs partial-delivery completion.
    is_admin_only = achieved.issubset(ADMIN_ONLY_STATES) and bool(achieved)
    rule = (
        "fd_005_admin_complete_pretends_delivery"
        if is_admin_only
        else "fd_005_incomplete_state"
    )
    return {
        "ok": False,
        "violations": [{
            "rule": rule,
            "message": (
                f"Cannot mark '{marking}'. Missing required states: {missing}. "
                "Hydration alone does not prove delivery acceptance."
            ),
            "missing": missing,
            "achieved": sorted(achieved),
        }],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: --input {args.input} not found", file=sys.stderr)
        return 2

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = check(payload)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["ok"]:
            print("FD-005: OK")
        else:
            print("FD-005: FAIL")
            for v in result["violations"]:
                print(f"  - {v['rule']}: {v['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

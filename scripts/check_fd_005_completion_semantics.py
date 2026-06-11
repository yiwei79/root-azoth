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

Invoked by scripts/azoth_guards.py (the runner).
"""

from __future__ import annotations

from typing import Any


REQUIRED_FOR_COMPLETION = (
    "implementation_accepted",
    "tests_pass",
    "receipt_written",
)

ADMIN_ONLY_STATES = frozenset({"hydrated", "planned", "scoped"})


def check(payload: dict[str, Any]) -> dict[str, Any]:
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
    rule = "fd_005_admin_complete_pretends_delivery" if is_admin_only else "fd_005_incomplete_state"
    return {
        "ok": False,
        "violations": [
            {
                "rule": rule,
                "message": (
                    f"Cannot mark '{marking}'. Missing required states: {missing}. "
                    "Hydration alone does not prove delivery acceptance."
                ),
                "missing": missing,
                "achieved": sorted(achieved),
            }
        ],
    }

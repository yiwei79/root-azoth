#!/usr/bin/env python3
"""FD-008 guard — subagent contract for governed pipelines.

For governed pipelines (`/deliver-full`, `/dynamic-full-auto` governed mode,
`/auto` governed mode), named roles must be spawned as real subagents. The
FD-008 failure mode is when the orchestrator drafts the architect brief
inline, breaking isolation.

Rule:
  - If pipeline is governed (deliver_full, dynamic_full_auto_governed,
    auto_governed):
    - Stage "architect_brief" must have spawned=True and
      subagent_type="architect".
    - Stage "governance_review" (if present) must have spawned=True and
      subagent_type="reviewer".

Input: JSON payload with:
  - pipeline (str): the pipeline identifier.
  - stages (list[dict]): the stage plans, each with name, spawned, subagent_type.

Invoked by scripts/azoth_guards.py (the runner).
"""

from __future__ import annotations

from typing import Any


GOVERNED_PIPELINES = frozenset(
    {
        "deliver_full",
        "dynamic_full_auto_governed",
        "auto_governed",
    }
)

REQUIRED_SPAWNS = {
    "architect_brief": "architect",
    "governance_review": "reviewer",
}


def check(payload: dict[str, Any]) -> dict[str, Any]:
    pipeline = str(payload.get("pipeline") or "").strip()
    if pipeline not in GOVERNED_PIPELINES:
        return {
            "ok": True,
            "violations": [],
            "reason": "non-governed pipeline",
            "pipeline": pipeline,
        }

    stages = payload.get("stages")
    if stages is None:
        return {
            "ok": False,
            "violations": [
                {
                    "rule": "fd_008_invalid_payload",
                    "message": "stages must be provided for governed pipelines",
                }
            ],
        }
    if not isinstance(stages, list):
        return {
            "ok": False,
            "violations": [
                {
                    "rule": "fd_008_invalid_payload",
                    "message": "stages must be a list",
                }
            ],
        }

    by_name: dict[str, dict[str, Any]] = {}
    for stage in stages:
        if isinstance(stage, dict) and stage.get("name") in REQUIRED_SPAWNS:
            by_name[str(stage["name"])] = stage

    violations: list[dict[str, Any]] = []
    for name, expected_type in REQUIRED_SPAWNS.items():
        if name not in by_name:
            continue  # not part of this run; not a violation
        stage = by_name[name]
        if not bool(stage.get("spawned")):
            violations.append(
                {
                    "rule": f"fd_008_inline_{name}",
                    "message": (
                        f"Governed pipeline {pipeline!r} requires stage "
                        f"{name!r} to be a spawned subagent. The orchestrator "
                        f"must not draft {name!r} inline."
                    ),
                }
            )
        elif stage.get("subagent_type") != expected_type:
            violations.append(
                {
                    "rule": f"fd_008_wrong_subagent_type_{name}",
                    "message": (
                        f"Stage {name!r} must be spawned as {expected_type!r}, "
                        f"got {stage.get('subagent_type')!r}."
                    ),
                }
            )

    return {
        "ok": not violations,
        "violations": violations,
        "pipeline": pipeline,
    }

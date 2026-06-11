#!/usr/bin/env python3
"""FD-004 guard — hydration scope.

Any action that mutates governed state under the umbrella of "hydration"
(roadmap.yaml, backlog.yaml, roadmap spec, initiative state) requires an
open, approved scope-gate. This guard refuses hydration without one.

Rule:
  - If action matches /^hydrate/ AND planned_paths include any governed-state
    path (under .azoth/, .claude/, .codex/, .opencode/, kernel/, agents/),
    then scope_gate.session_id must be present and non-empty.

Input: JSON payload with:
  - action (str): the action name
  - planned_paths (list[str]): paths the action intends to mutate
  - scope_gate (dict|None): an open scope-gate with at least session_id

Invoked by scripts/azoth_guards.py (the runner).
"""

from __future__ import annotations

import re
from typing import Any


GOVERNED_PATH_PREFIXES = (
    ".azoth/",
    ".claude/",
    ".codex/",
    ".opencode/",
    "kernel/",
    "agents/",
)


def _is_governed_path(path: str) -> bool:
    return any(path.startswith(p) for p in GOVERNED_PATH_PREFIXES)


def check(payload: dict[str, Any]) -> dict[str, Any]:
    action = str(payload.get("action") or "")
    if not re.match(r"^hydrate", action):
        return {"ok": True, "violations": [], "reason": "non-hydration action"}

    paths = payload.get("planned_paths") or []
    if not isinstance(paths, list):
        return {
            "ok": False,
            "violations": [
                {
                    "rule": "fd_004_invalid_payload",
                    "message": "planned_paths must be a list",
                }
            ],
        }

    touches_governed = any(_is_governed_path(str(p)) for p in paths)
    if not touches_governed:
        return {"ok": True, "violations": [], "reason": "no governed paths"}

    scope = payload.get("scope_gate")
    if not isinstance(scope, dict) or not str(scope.get("session_id") or "").strip():
        return {
            "ok": False,
            "violations": [
                {
                    "rule": "fd_004_no_scope",
                    "message": (
                        "Hydration action touches governed state but no scope gate "
                        "is open. Open a fresh scope-gate via /next or /auto before "
                        "hydrating planning state."
                    ),
                }
            ],
        }

    return {
        "ok": True,
        "violations": [],
        "scope_session_id": str(scope.get("session_id")),
    }

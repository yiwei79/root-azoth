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

Exit codes:
  0 — guard passes
  1 — guard blocks (no scope-gate for hydration touching governed state)
  2 — usage error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


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


def check(payload: dict[str, object]) -> dict[str, object]:
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
            print("FD-004: OK")
        else:
            print("FD-004: FAIL")
            for v in result["violations"]:
                print(f"  - {v['rule']}: {v['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

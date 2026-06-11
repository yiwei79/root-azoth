#!/usr/bin/env python3
"""Azoth guards runner — combines all friction-event guards into one report.

This is the entry point the orchestrator calls as a single subprocess.
Each guard is also callable individually for fine-grained testing.

Input payload is a dict with optional keys per guard:
  friction_check          → FD-003 (subagent isolation)
  hydration_check         → FD-004 (hydration scope)
  completion_check        → FD-005 (completion semantics)
  subagent_contract_check → FD-008 (subagent contract)

Exit code 0 iff all guards pass.

Each guard module exposes a `check(payload: dict) -> dict` function that
returns a dict with at least `ok` (bool) and `violations` (list[dict]).
The runner loads each module by file path (not import name) so the guard
scripts remain independent and individually invokable.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent

GUARD_MODULES = {
    "fd_003": "check_fd_003_subagent_isolation",
    "fd_004": "check_fd_004_hydration_scope",
    "fd_005": "check_fd_005_completion_semantics",
    "fd_008": "check_fd_008_subagent_contract",
}

# Maps each guard id to the payload-section key that feeds it. Hoisted out
# of the run() loop so the dict is built once, not on every iteration.
GUARD_TO_SECTION_KEY = {
    "fd_003": "friction_check",
    "fd_004": "hydration_check",
    "fd_005": "completion_check",
    "fd_008": "subagent_contract_check",
}


def _load_guard(module_file: str):
    path = SCRIPTS_DIR / f"{module_file}.py"
    spec = importlib.util.spec_from_file_location(module_file, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _check_guard(name: str, payload: dict[str, object]) -> dict[str, object]:
    try:
        module = _load_guard(GUARD_MODULES[name])
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "violations": [
                {
                    "rule": f"{name}_load_error",
                    "message": f"guard module not found: {exc}",
                }
            ],
        }
    except Exception as exc:  # noqa: BLE001 — guard load may raise arbitrary errors
        return {
            "ok": False,
            "violations": [
                {
                    "rule": f"{name}_load_error",
                    "message": str(exc),
                }
            ],
        }
    try:
        return module.check(payload)
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors as violations
        return {
            "ok": False,
            "violations": [
                {
                    "rule": f"{name}_check_error",
                    "message": str(exc),
                }
            ],
        }


def run(payload: dict[str, object]) -> dict[str, object]:
    guards: dict[str, dict[str, object]] = {}
    total_violations = 0
    for guard_id, module_name in GUARD_MODULES.items():
        section_payload = payload.get(GUARD_TO_SECTION_KEY[guard_id]) or {}
        result = _check_guard(guard_id, section_payload)
        guards[guard_id] = result
        total_violations += len(result.get("violations") or [])
    ok = all(g.get("ok") for g in guards.values())
    return {
        "ok": ok,
        "violation_count": total_violations,
        "guards": guards,
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
    result = run(payload)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for name, guard in result["guards"].items():
            mark = "OK  " if guard.get("ok") else "FAIL"
            print(f"[{mark}] {name}")
        print()
        print(f"violations: {result['violation_count']}")
        print(f"overall: {'OK' if result['ok'] else 'FAIL'}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

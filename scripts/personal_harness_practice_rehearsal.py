#!/usr/bin/env python3
"""Run no-write Personal Harness OS practice scenarios."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

import yaml

from personal_harness_context import build_personal_harness_context


DEFAULT_CASES = Path("tests/fixtures/personal_harness_practice_cases.yaml")


def run_practice_rehearsal(
    *,
    repo_root: Path,
    cases_path: Path = DEFAULT_CASES,
    personal_root: Path | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Run fixture-backed practice cases and return a JSON-ready report."""
    root = repo_root.resolve()
    status_before = _git_status(root)
    cases = _load_cases(cases_path)
    results = [
        _run_case(case, repo_root=root, personal_root=personal_root, as_of=as_of)
        for case in cases
    ]
    status_after = _git_status(root)
    return {
        "schema_version": 1,
        "packet_type": "personal_harness_practice_rehearsal",
        "ok": all(result["status"] == "pass" for result in results)
        and status_before == status_after,
        "case_count": len(results),
        "cases": results,
        "no_write_contract": {
            "repo_status_before": status_before,
            "repo_status_after": status_after,
            "repo_mutated": status_before != status_after,
        },
    }


def _load_cases(path: Path) -> list[dict[str, Any]]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema_version") != 1:
        raise ValueError(f"{path}: expected schema_version 1")
    cases = doc.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path}: expected non-empty cases list")
    return [case for case in cases if isinstance(case, dict)]


def _run_case(
    case: Mapping[str, Any],
    *,
    repo_root: Path,
    personal_root: Path | None,
    as_of: str | None,
) -> dict[str, Any]:
    packet = build_personal_harness_context(
        goal=str(case.get("goal") or ""),
        requested_actions=_strings(case.get("requested_actions")),
        planned_paths=_strings(case.get("planned_paths")),
        query_tags=_strings(case.get("query_tags")),
        repo_root=repo_root,
        personal_root=personal_root,
        project_readback=_mapping(case.get("project_readback")),
        as_of=as_of,
    )
    checks = _checks(case, packet)
    return {
        "id": str(case.get("id") or "unknown"),
        "domain": str(case.get("domain") or "unknown"),
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "checks": checks,
        "profile": packet["context_view"].get("harness_profile"),
        "route_state": packet["context_view"].get("route_capsule", {}).get("route_state"),
        "authority_plane": packet["context_view"].get("route_capsule", {}).get("authority_plane"),
        "authority_required": packet["context_view"].get("route_capsule", {}).get("authority_required"),
        "warnings": packet.get("warnings", []),
    }


def _checks(case: Mapping[str, Any], packet: Mapping[str, Any]) -> list[dict[str, str]]:
    expected = _mapping(case.get("expected")) or {}
    context = _mapping(packet.get("context_view")) or {}
    route = _mapping(context.get("route_capsule")) or {}
    project = _mapping(context.get("project_context")) or {}
    return [
        _check("profile", context.get("harness_profile") == expected.get("profile")),
        _check("route_state", route.get("route_state") == expected.get("route_state")),
        _check("authority_required", route.get("authority_required") is expected.get("authority_required")),
        _check("authority_plane", route.get("authority_plane") == expected.get("authority_plane")),
        _check("warnings_empty", packet.get("warnings") == []),
        _check(
            "project_context",
            not expected.get("project") or project.get("project") == expected.get("project"),
        ),
    ]


def _check(check_id: str, passed: bool) -> dict[str, str]:
    return {"id": check_id, "status": "pass" if passed else "fail"}


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _mapping(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, Mapping) else None


def _git_status(root: Path) -> str:
    if not (root / ".git").exists():
        return "not a git repo"
    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unavailable").strip()
        return f"unavailable ({detail})"
    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--personal-root", type=Path)
    parser.add_argument("--as-of")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.json:
        parser.error("practice rehearsal output requires --json")

    report = run_practice_rehearsal(
        repo_root=args.repo_root,
        cases_path=args.cases,
        personal_root=args.personal_root,
        as_of=args.as_of,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

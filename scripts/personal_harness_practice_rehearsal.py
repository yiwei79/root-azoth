#!/usr/bin/env python3
"""Run no-write Personal Harness OS practice scenarios."""

from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
from typing import Any, Mapping

import yaml

from context_view import build_context_view
from harness_profile import HarnessRequest, classify_harness_request


DEFAULT_CASES = Path("examples/personal-harness/rehearsal-cases.yaml")


def run_practice_rehearsal(
    *,
    repo_root: Path,
    cases_path: Path = DEFAULT_CASES,
) -> dict[str, Any]:
    """Run fixture-backed practice cases and return a JSON-ready report."""
    root = repo_root.resolve()
    tree_before = _tree_fingerprint(root)
    cases = _load_cases(cases_path)
    results = [_run_case(case) for case in cases]
    tree_after = _tree_fingerprint(root)
    return {
        "schema_version": 1,
        "packet_type": "personal_harness_practice_rehearsal",
        "ok": all(result["status"] == "pass" for result in results) and tree_before == tree_after,
        "case_count": len(results),
        "cases": results,
        "no_write_contract": {
            "tree_sha256_before": tree_before,
            "tree_sha256_after": tree_after,
            "repo_mutated": tree_before != tree_after,
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
) -> dict[str, Any]:
    request = HarnessRequest.from_mapping(case)
    decision = classify_harness_request(request)
    context = build_context_view(
        goal=request.goal,
        harness_decision=decision,
        project_receipt=_mapping(case.get("project_readback")),
    )
    checks = _checks(case, context)
    return {
        "id": str(case.get("id") or "unknown"),
        "domain": str(case.get("domain") or "unknown"),
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "checks": checks,
        "profile": context.get("harness_profile"),
        "side_effect_class": decision.side_effect_class,
        "route_state": context.get("route_capsule", {}).get("route_state"),
        "authority_plane": context.get("route_capsule", {}).get("authority_plane"),
        "authority_required": context.get("route_capsule", {}).get("authority_required"),
    }


def _checks(case: Mapping[str, Any], context: Mapping[str, Any]) -> list[dict[str, str]]:
    expected = _mapping(case.get("expected")) or {}
    route = _mapping(context.get("route_capsule")) or {}
    project = _mapping(context.get("project_context")) or {}
    return [
        _check("profile", context.get("harness_profile") == expected.get("profile")),
        _check(
            "side_effect_class",
            route.get("side_effect_class") == expected.get("side_effect_class"),
        ),
        _check("route_state", route.get("route_state") == expected.get("route_state")),
        _check(
            "authority_required",
            route.get("authority_required") is expected.get("authority_required"),
        ),
        _check("authority_plane", route.get("authority_plane") == expected.get("authority_plane")),
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


def _tree_fingerprint(root: Path) -> str:
    """Hash file paths and contents so rehearsal proves it made no repository writes."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.json:
        parser.error("practice rehearsal output requires --json")

    report = run_practice_rehearsal(
        repo_root=args.repo_root,
        cases_path=args.cases,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

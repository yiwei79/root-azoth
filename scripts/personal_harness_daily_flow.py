#!/usr/bin/env python3
"""Verify the Personal Harness OS daily cockpit + context flow without writes."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from cockpit_menu import check_cockpit, load_cockpit, render_menu
from personal_harness_context import build_personal_harness_context


def run_daily_flow(
    *,
    cockpit_root: Path,
    repo_root: Path,
    project_id: str,
    goal: str,
    requested_actions: Sequence[str] = (),
    planned_paths: Sequence[str] = (),
    query_tags: Sequence[str] = (),
    personal_root: Path | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Run a no-write daily flow verification and return a JSON-ready report."""
    cockpit_path = cockpit_root.resolve()
    repo_path = repo_root.resolve()
    cockpit_status_before = _git_status(cockpit_path)
    state = load_cockpit(cockpit_path, include_status=True)
    project = _selected_project(state, project_id)
    project_path = Path(str(project.get("repo_path") or "")) if project else None
    project_status_before = _git_status(project_path) if project_path else "missing project"
    menu = render_menu(state, project_id=project_id)
    context_packet = build_personal_harness_context(
        goal=goal,
        requested_actions=requested_actions,
        planned_paths=planned_paths,
        query_tags=query_tags,
        repo_root=repo_path,
        personal_root=personal_root,
        as_of=as_of,
    )
    cockpit_errors = check_cockpit(load_cockpit(cockpit_path, include_status=False))
    cockpit_status_after = _git_status(cockpit_path)
    project_status_after = _git_status(project_path) if project_path else "missing project"
    checks = _checks(
        cockpit_errors=cockpit_errors,
        project=project,
        menu=menu,
        context_packet=context_packet,
        cockpit_status_before=cockpit_status_before,
        cockpit_status_after=cockpit_status_after,
        project_status_before=project_status_before,
        project_status_after=project_status_after,
    )
    return {
        "schema_version": 1,
        "packet_type": "personal_harness_daily_flow",
        "ok": all(check["status"] == "pass" for check in checks),
        "goal": goal,
        "cockpit": {
            "root": str(cockpit_path),
            "project_id": project_id,
            "selected_mode": str(project.get("selected_mode") or "") if project else "",
            "readiness_state": str(project.get("readiness_state") or "") if project else "",
            "authority_plane": str(project.get("authority_plane") or "") if project else "",
            "menu_has_context_command": "personal_harness_context.py --goal" in menu,
            "check_errors": cockpit_errors,
        },
        "context_packet": context_packet,
        "checks": checks,
        "no_write_contract": {
            "cockpit_repo_mutated": cockpit_status_before != cockpit_status_after,
            "project_repo_mutated": project_status_before != project_status_after,
            "project_context_imported": False,
        },
    }


def _selected_project(state: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    for project in state.get("projects", []):
        if isinstance(project, dict) and project.get("project_id") == project_id:
            return project
    return None


def _checks(
    *,
    cockpit_errors: list[str],
    project: dict[str, Any] | None,
    menu: str,
    context_packet: dict[str, Any],
    cockpit_status_before: str,
    cockpit_status_after: str,
    project_status_before: str,
    project_status_after: str,
) -> list[dict[str, str]]:
    context_profile = str(context_packet["context_view"].get("harness_profile") or "")
    cockpit_mode = str(project.get("selected_mode") or "") if project else ""
    checks = [
        _check("cockpit_metadata", not cockpit_errors, "; ".join(cockpit_errors) or "cockpit check OK"),
        _check("project_pointer", project is not None, "project pointer found" if project else "missing project pointer"),
        _check(
            "context_command_visible",
            "personal_harness_context.py --goal" in menu,
            "daily context command visible in cockpit menu",
        ),
        _check(
            "mode_consistency",
            bool(context_profile and cockpit_mode and context_profile == cockpit_mode),
            f"context profile {context_profile!r}; cockpit mode {cockpit_mode!r}",
        ),
        _check(
            "memory_context_loaded",
            bool(context_packet["context_view"].get("memory_context")),
            "memory context present",
        ),
        _check(
            "no_cockpit_write",
            cockpit_status_before == cockpit_status_after,
            "cockpit git status unchanged",
        ),
        _check(
            "no_project_write",
            project_status_before == project_status_after,
            "project git status unchanged",
        ),
    ]
    return checks


def _check(check_id: str, passed: bool, summary: str) -> dict[str, str]:
    return {"id": check_id, "status": "pass" if passed else "fail", "summary": summary}


def _git_status(path: Path | None) -> str:
    if path is None or not path.is_dir() or not (path / ".git").exists():
        return "not a git repo"
    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=path,
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
    parser.add_argument("--cockpit-root", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--project", default="ras-or-ray")
    parser.add_argument("--goal", required=True)
    parser.add_argument("--action", action="append", default=[])
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--personal-root", type=Path)
    parser.add_argument("--as-of")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.json:
        parser.error("personal harness daily flow output requires --json")

    report = run_daily_flow(
        cockpit_root=args.cockpit_root,
        repo_root=args.repo_root,
        project_id=args.project,
        goal=args.goal,
        requested_actions=args.action,
        planned_paths=args.path,
        query_tags=args.tag,
        personal_root=args.personal_root,
        as_of=args.as_of,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify the Personal Harness OS daily cockpit + context flow without writes."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence

from cockpit_menu import check_cockpit, load_cockpit, render_menu
from personal_harness_context import build_personal_harness_context
from personal_knowledge_recall import PersonalKnowledgeRecallError
from personal_knowledge_review import build_review_packet


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
    personal_path = (
        personal_root if personal_root is not None else _default_personal_root(cockpit_path)
    )
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
        personal_root=personal_path,
        project_readback=_project_readback(project),
        as_of=as_of,
    )
    personal_review = _personal_knowledge_review(
        personal_path=personal_path,
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
        personal_root_available=personal_path is not None,
        cockpit_status_before=cockpit_status_before,
        cockpit_status_after=cockpit_status_after,
        project_status_before=project_status_before,
        project_status_after=project_status_after,
    )
    return {
        "schema_version": 1,
        "packet_type": "personal_harness_daily_flow",
        "ok": all(check["status"] != "fail" for check in checks),
        "goal": goal,
        "cockpit": {
            "root": str(cockpit_path),
            "project_id": project_id,
            "selected_mode": str(project.get("selected_mode") or "") if project else "",
            "readiness_state": str(project.get("readiness_state") or "") if project else "",
            "authority_plane": str(project.get("authority_plane") or "") if project else "",
            "menu_has_context_command": _menu_has_context_command(menu),
            "personal_knowledge_root": str(personal_path) if personal_path is not None else "",
            "check_errors": cockpit_errors,
        },
        "context_packet": context_packet,
        "personal_knowledge_review": personal_review,
        "checks": checks,
        "no_write_contract": {
            "cockpit_repo_mutated": cockpit_status_before != cockpit_status_after,
            "project_repo_mutated": project_status_before != project_status_after,
            "project_context_imported": False,
        },
    }


def _personal_knowledge_review(
    *,
    personal_path: Path | None,
    as_of: str | None,
) -> dict[str, Any]:
    if personal_path is None:
        return {
            "schema_version": 1,
            "packet_type": "personal_knowledge_review",
            "summary": {
                "total_cards": 0,
                "current_cards": 0,
                "review_due_cards": 0,
                "requires_operator_review": False,
                "overall_status": "skipped",
            },
            "due_cards": [],
            "next_safe_action": "personal knowledge root not present; skipped",
            "advisory_authority": "advisory_context_not_governing_instruction",
        }
    try:
        return build_review_packet(
            personal_path,
            as_of=_date_from_value(as_of),
        )
    except PersonalKnowledgeRecallError as exc:
        return {
            "schema_version": 1,
            "packet_type": "personal_knowledge_review",
            "summary": {
                "total_cards": 0,
                "current_cards": 0,
                "review_due_cards": 0,
                "requires_operator_review": True,
                "overall_status": "review_error",
            },
            "due_cards": [],
            "next_safe_action": f"fix personal knowledge review error: {exc}",
            "advisory_authority": "advisory_context_not_governing_instruction",
        }


def _date_from_value(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return date.fromisoformat(text)
    except ValueError:
        return None


def _selected_project(state: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    for project in state.get("projects", []):
        if isinstance(project, dict) and project.get("project_id") == project_id:
            return project
    return None


def _project_readback(project: dict[str, Any] | None) -> dict[str, str] | None:
    if project is None:
        return None
    return {
        "project": str(project.get("project_id") or "").strip(),
        "selected_mode": str(project.get("selected_mode") or "").strip(),
        "freshness": str(project.get("freshness_status") or "").strip(),
        "receipt_ref": str(project.get("handoff_receipt_ref") or "").strip(),
    }


def _default_personal_root(cockpit_path: Path) -> Path | None:
    card_dir = cockpit_path / ".azoth" / "knowledge" / "cards" / "root-azoth"
    return cockpit_path if card_dir.is_dir() else None


def _checks(
    *,
    cockpit_errors: list[str],
    project: dict[str, Any] | None,
    menu: str,
    context_packet: dict[str, Any],
    personal_root_available: bool,
    cockpit_status_before: str,
    cockpit_status_after: str,
    project_status_before: str,
    project_status_after: str,
) -> list[dict[str, str]]:
    context_profile = str(context_packet["context_view"].get("harness_profile") or "")
    cockpit_mode = str(project.get("selected_mode") or "") if project else ""
    checks = [
        _check(
            "cockpit_metadata", not cockpit_errors, "; ".join(cockpit_errors) or "cockpit check OK"
        ),
        _check(
            "project_pointer",
            project is not None,
            "project pointer found" if project else "missing project pointer",
        ),
        _check(
            "context_command_visible",
            _menu_has_context_command(menu),
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
            "personal_context_loaded",
            (not personal_root_available)
            or bool(context_packet["context_view"].get("personal_context")),
            (
                "personal context present"
                if personal_root_available
                else "personal knowledge root not present; skipped"
            ),
        ),
        _personal_context_freshness_check(
            context_packet=context_packet,
            personal_root_available=personal_root_available,
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


def _personal_context_freshness_check(
    *,
    context_packet: dict[str, Any],
    personal_root_available: bool,
) -> dict[str, str]:
    if not personal_root_available:
        return _check(
            "personal_context_freshness",
            True,
            "personal knowledge root not present; skipped",
        )
    personal_context = context_packet["context_view"].get("personal_context")
    if not isinstance(personal_context, list) or not personal_context:
        return _check("personal_context_freshness", False, "personal context absent")
    due_summary = _personal_review_due_summary(context_packet)
    if due_summary:
        return {
            "id": "personal_context_freshness",
            "status": "warn",
            "summary": due_summary,
        }
    return _check("personal_context_freshness", True, "personal context current")


def _personal_review_due_summary(context_packet: dict[str, Any]) -> str:
    warnings = context_packet.get("warnings")
    if not isinstance(warnings, list):
        return ""
    for warning in warnings:
        text = str(warning).strip()
        if text.startswith("personal knowledge review due: "):
            return text
    return ""


def _menu_has_context_command(menu: str) -> bool:
    return all(
        snippet in menu for snippet in ("personal_harness_daily_flow.py", "--goal", "--summary")
    )


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


def format_daily_summary(report: dict[str, Any]) -> str:
    """Render a compact operator-facing summary from the JSON report."""
    context_view = report["context_packet"]["context_view"]
    route_capsule = context_view.get("route_capsule", {})
    review = report.get("personal_knowledge_review", {})
    review_summary = review.get("summary", {})
    checks = report.get("checks", [])
    no_write = report.get("no_write_contract", {})
    lines = [
        "# Personal Harness Daily Flow",
        "",
        f"Status: {_daily_status(report)}",
        f"Goal: {report.get('goal', '')}",
        "",
        "## Route",
        f"- Harness profile: {context_view.get('harness_profile', '')}",
        f"- Route state: {route_capsule.get('route_state', '')}",
        f"- Authority plane: {route_capsule.get('authority_plane', '')}",
        f"- Next safe action: {route_capsule.get('next_safe_action', '')}",
        "",
        "## Project",
        f"- Project: {report['cockpit'].get('project_id', '')}",
        f"- Cockpit mode: {report['cockpit'].get('selected_mode', '')}",
        f"- Readiness: {report['cockpit'].get('readiness_state', '')}",
        f"- Personal knowledge root: {report['cockpit'].get('personal_knowledge_root') or 'not present'}",
        "",
        "## Context",
        f"- Memory items: {len(context_view.get('memory_context', []))}",
        f"- Personal context items: {len(context_view.get('personal_context', []))}",
        f"- Personal review status: {review_summary.get('overall_status', 'unknown')}",
        f"- Personal cards due: {review_summary.get('review_due_cards', 0)}",
    ]
    due_cards = review.get("due_cards")
    if isinstance(due_cards, list) and due_cards:
        lines.extend(["", "## Personal Review Due"])
        for card in due_cards:
            if not isinstance(card, dict):
                continue
            lines.append(
                "- "
                f"{card.get('card_id', '')}: {card.get('title', '')} "
                f"({card.get('review_reason', '')}; source: {_first_source_path(card)})"
            )
    lines.extend(
        [
            "",
            "## Checks",
            *_format_checks(checks),
            "",
            "## No-Write Contract",
            f"- Cockpit mutated: {str(no_write.get('cockpit_repo_mutated', '')).lower()}",
            f"- Project mutated: {str(no_write.get('project_repo_mutated', '')).lower()}",
            f"- Project context imported: {str(no_write.get('project_context_imported', '')).lower()}",
            "",
            f"Next: {review.get('next_safe_action') or route_capsule.get('next_safe_action', '')}",
        ]
    )
    return "\n".join(lines)


def _daily_status(report: dict[str, Any]) -> str:
    if not report.get("ok"):
        return "FAIL"
    checks = report.get("checks")
    if isinstance(checks, list) and any(
        isinstance(check, dict) and check.get("status") == "warn" for check in checks
    ):
        return "OK with warnings"
    return "OK"


def _format_checks(checks: Any) -> list[str]:
    if not isinstance(checks, list):
        return ["- unavailable"]
    return [
        f"- {check.get('id', '')}: {check.get('status', '')} - {check.get('summary', '')}"
        for check in checks
        if isinstance(check, dict)
    ]


def _first_source_path(card: dict[str, Any]) -> str:
    refs = card.get("source_refs")
    if not isinstance(refs, list):
        return ""
    for ref in refs:
        if isinstance(ref, dict) and ref.get("path"):
            return str(ref["path"]).strip()
    return ""


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
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    if not args.json and not args.summary:
        parser.error("personal harness daily flow output requires --json or --summary")

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
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    if args.summary:
        print(format_daily_summary(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

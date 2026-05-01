#!/usr/bin/env python3
"""Safe-open terminal menu for the Yiwei Azoth cockpit."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard.
    raise SystemExit("PyYAML is required to run cockpit_menu.py") from exc


FORBIDDEN_PROJECT_CONTEXT_FIELDS = {
    "source_files",
    "code_summaries",
    "dependency_inventory",
    "secrets",
    "retrieval_index",
}
REQUIRED_PROJECT_FIELDS = {
    "project_id",
    "title",
    "repo_path",
    "default_branch",
    "tracking_ref",
    "privacy_class",
    "profile_mode",
    "handoff_receipt_ref",
    "validation_commands",
}


def _default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unavailable").strip()
        return f"unavailable ({detail})"
    return (result.stdout or "").strip() or "clean"


def _latest_public_azoth_release(releases: dict[str, Any]) -> dict[str, Any] | None:
    applied = releases.get("applied_releases")
    if not isinstance(applied, list):
        return None
    for item in reversed(applied):
        if isinstance(item, dict) and item.get("product") == "azoth":
            return item
    return None


def load_cockpit(root: Path | None = None, *, include_status: bool = True) -> dict[str, Any]:
    cockpit_root = (root or _default_root()).resolve()
    manifest = _load_yaml(cockpit_root / "azoth.yaml")
    releases = _load_yaml(cockpit_root / ".azoth" / "releases" / "applied.yaml")
    projects_index = _load_yaml(cockpit_root / ".azoth" / "projects" / "index.yaml")
    projects = projects_index.get("projects")
    if not isinstance(projects, list):
        projects = []

    project_statuses: dict[str, str] = {}
    if include_status:
        for project in projects:
            if not isinstance(project, dict):
                continue
            project_id = str(project.get("project_id") or "unknown")
            path = Path(str(project.get("repo_path") or ""))
            if path.is_dir():
                project_statuses[project_id] = _run_git(["status", "--short", "--branch"], path)
            else:
                project_statuses[project_id] = "missing path"

    return {
        "root": cockpit_root,
        "manifest": manifest,
        "releases": releases,
        "release": _latest_public_azoth_release(releases),
        "projects_index": projects_index,
        "projects": projects,
        "cockpit_status": (
            _run_git(["status", "--short", "--branch"], cockpit_root)
            if include_status and (cockpit_root / ".git").exists()
            else "not checked"
        ),
        "project_statuses": project_statuses,
    }


def _release_sync_line(state: dict[str, Any]) -> str:
    release = state.get("release")
    manifest = state.get("manifest") if isinstance(state.get("manifest"), dict) else {}
    manifest_version = str(manifest.get("version") or "unknown")
    if not isinstance(release, dict):
        return f"Release sync: BLOCKED - no public azoth release in ledger; manifest {manifest_version}"
    version = str(release.get("version") or "unknown")
    commit = str(release.get("commit") or "unknown")
    short_commit = commit[:8] if commit != "unknown" else commit
    status = "OK" if version != "unknown" and commit != "unknown" else "BLOCKED"
    return (
        f"Release sync: {status} - public azoth {version} @ {short_commit}; "
        f"manifest {manifest_version}"
    )


def _project_handoff(project: dict[str, Any]) -> list[str]:
    project_id = str(project.get("project_id") or "unknown")
    path = str(project.get("repo_path") or "")
    quoted_path = shlex.quote(path)
    return [
        f"  Switch command: cd {quoted_path}",
        "  Project-session prompt:",
        f"    You are in project panel `{project_id}` at `{path}`.",
        "    Project-local context is authoritative.",
        "    Do not paste cockpit memory into project-local guidance.",
        "    Start by checking project git status and local project guidance.",
        "    Any project write requires a fresh project-scoped gate.",
    ]


def render_menu(state: dict[str, Any], *, project_id: str | None = None) -> str:
    root = Path(state["root"])
    manifest = state.get("manifest") if isinstance(state.get("manifest"), dict) else {}
    projects = [item for item in state.get("projects", []) if isinstance(item, dict)]
    if project_id:
        projects = [item for item in projects if item.get("project_id") == project_id]

    lines = [
        "# Yiwei Azoth Cockpit",
        "",
        f"Cockpit: {manifest.get('project') or root.name}",
        f"Path: {root}",
        f"Repo status: {state.get('cockpit_status') or 'not checked'}",
        _release_sync_line(state),
        "Sync authority: latest approved public/installable azoth release; root-azoth workshop drift is advisory only.",
        "Mode: safe-open terminal menu; this command writes no files and starts no hidden work.",
        "",
        "## Registered Projects",
    ]

    if not projects:
        lines.append("- No matching project pointers found.")
    for project in projects:
        pid = str(project.get("project_id") or "unknown")
        title = str(project.get("title") or pid)
        status = state.get("project_statuses", {}).get(pid, "not checked")
        lines.extend(
            [
                f"- {pid}: {title}",
                f"  Path: {project.get('repo_path') or '?'}",
                f"  Profile: {project.get('profile_mode') or '?'}",
                f"  Status: {status}",
                f"  Receipt: {project.get('handoff_receipt_ref') or '?'}",
            ]
        )
        lines.extend(_project_handoff(project))

    lines.extend(
        [
            "",
            "## Safe Actions",
            "- Validate cockpit: python3 scripts/cockpit_menu.py --check",
            "- Open project session: use the switch command and project-session prompt above.",
            "- Add project pointer: open an explicit cockpit-owned project-pointer lane.",
            "- Project code/source work: switch to that project repo and open a project-scoped gate.",
            "- Backup/source onboarding/release work: open a separate named lane before writes.",
            "",
            "## Context Firewall",
            "- Cockpit-owned: project pointers, global preferences, release ledger, receipts, routing.",
            "- Project-owned: code, project memory, project-local guidance, project-local gates.",
            "- Handoff execution: the cockpit routes; the project repo owns project context.",
        ]
    )
    return "\n".join(lines)


def check_cockpit(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    root = Path(state["root"])
    manifest = state.get("manifest") if isinstance(state.get("manifest"), dict) else {}
    release = state.get("release")
    projects = [item for item in state.get("projects", []) if isinstance(item, dict)]

    if manifest.get("deployment_role") != "personal-cockpit":
        errors.append("azoth.yaml: deployment_role must be personal-cockpit")
    if not manifest.get("version"):
        errors.append("azoth.yaml: version is required")
    if not isinstance(release, dict):
        errors.append(".azoth/releases/applied.yaml: public azoth release is required")
    else:
        if not release.get("version"):
            errors.append("public azoth release: version is required")
        if not release.get("commit"):
            errors.append("public azoth release: commit is required")

    if not projects:
        errors.append(".azoth/projects/index.yaml: at least one project pointer is required")

    for index, project in enumerate(projects):
        label = str(project.get("project_id") or f"projects[{index}]")
        missing = sorted(field for field in REQUIRED_PROJECT_FIELDS if field not in project)
        for field in missing:
            errors.append(f"{label}: missing required field {field}")
        if project.get("profile_mode") != "pointer_only":
            errors.append(f"{label}: profile_mode must be pointer_only")
        for field in sorted(FORBIDDEN_PROJECT_CONTEXT_FIELDS):
            if field in project:
                errors.append(f"{label}: forbidden context field {field}")
        receipt_ref = str(project.get("handoff_receipt_ref") or "")
        if receipt_ref and not (root / receipt_ref).is_file():
            errors.append(f"{label}: missing handoff receipt {receipt_ref}")
        repo_path = str(project.get("repo_path") or "")
        if repo_path and not Path(repo_path).is_dir():
            errors.append(f"{label}: repo_path does not exist {repo_path}")
        commands = project.get("validation_commands")
        if not isinstance(commands, list):
            errors.append(f"{label}: validation_commands must be a list")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--plain", action="store_true", help="Print deterministic plain text.")
    parser.add_argument("--project", help="Render one project handoff by project_id.")
    parser.add_argument("--check", action="store_true", help="Validate cockpit menu metadata.")
    args = parser.parse_args(argv)

    state = load_cockpit(args.root, include_status=not args.check)
    if args.check:
        errors = check_cockpit(state)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("cockpit menu check OK")
        return 0

    print(render_menu(state, project_id=args.project))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify the deployed Yiwei Azoth cockpit bootstrap contract."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from cockpit_menu import check_cockpit, load_cockpit, render_menu
except ModuleNotFoundError:  # pragma: no cover - defensive direct execution path.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cockpit_menu import check_cockpit, load_cockpit, render_menu

try:
    from yaml_helpers import safe_load_yaml_path
except ModuleNotFoundError:  # pragma: no cover - defensive fallback.
    YAML_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

    def safe_load_yaml_path(path: Path) -> Any:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=YAML_SAFE_LOADER)


DEFAULT_COCKPIT_ROOT = Path("/Users/yiwei/GithubRepos/yiwei-azoth-cockpit")

REQUIRED_FILES = (
    "azoth.yaml",
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/ONBOARDING.md",
    "scripts/cockpit_menu.py",
    ".azoth/releases/applied.yaml",
    ".azoth/projects/index.yaml",
)

STARTUP_FILES = ("AGENTS.md", "CLAUDE.md")
STARTUP_REQUIRED_TEXT = (
    "Yiwei Azoth Cockpit",
    "python3 scripts/cockpit_menu.py --check",
    "python3 scripts/cockpit_menu.py",
    "Context Firewall",
    "Do not import project source",
)
HANDBOOK_REQUIRED_TEXT = (
    "Start cockpit.",
    "## Command Reference",
    "python3 scripts/cockpit_menu.py --check",
    "python3 scripts/cockpit_menu.py --plain",
    "python3 scripts/cockpit_menu.py --project ras-or-ray",
    "python3 scripts/cockpit_menu.py --project <project_id>",
    "personal_knowledge_validate.py --root /Users/yiwei/GithubRepos/yiwei-azoth-cockpit",
)
STALE_STARTUP_PATTERNS = (
    "# personal-azoth-root",
    "Name**: personal-azoth-root",
    "Name: personal-azoth-root",
)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = safe_load_yaml_path(path)
    return loaded if isinstance(loaded, dict) else {}


def _run_command(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _git_status_lines(path: Path) -> list[str]:
    result = _run_command(["git", "status", "--short", "--branch"], cwd=path)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unavailable").strip()
        return [f"ERROR: git status unavailable: {detail}"]
    return (result.stdout or "").splitlines()


def _repo_is_clean(status_lines: list[str]) -> bool:
    return bool(status_lines) and all(line.startswith("## ") for line in status_lines)


def _project_ids(root: Path) -> set[str]:
    index = _load_yaml_mapping(root / ".azoth" / "projects" / "index.yaml")
    projects = index.get("projects")
    if not isinstance(projects, list):
        return set()
    return {
        str(project.get("project_id"))
        for project in projects
        if isinstance(project, dict) and project.get("project_id")
    }


def _check_required_files(root: Path, errors: list[str]) -> None:
    for rel_path in REQUIRED_FILES:
        if not (root / rel_path).is_file():
            errors.append(f"{rel_path}: required cockpit bootstrap file is missing")


def _check_startup_files(root: Path, errors: list[str]) -> None:
    for rel_path in STARTUP_FILES:
        path = root / rel_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if any(pattern in text for pattern in STALE_STARTUP_PATTERNS):
            errors.append(f"{rel_path}: stale personal-azoth-root startup identity")
        for snippet in STARTUP_REQUIRED_TEXT:
            if snippet not in text:
                errors.append(f"{rel_path}: missing required startup text {snippet!r}")


def _check_handbook(root: Path, errors: list[str]) -> None:
    path = root / "docs" / "ONBOARDING.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for snippet in HANDBOOK_REQUIRED_TEXT:
        if snippet not in text:
            errors.append(f"docs/ONBOARDING.md: missing handbook command text {snippet!r}")


def _check_deployment_receipt(root: Path, errors: list[str]) -> None:
    releases = _load_yaml_mapping(root / ".azoth" / "releases" / "applied.yaml")
    deployments = releases.get("personal_deployments")
    if not isinstance(deployments, list):
        errors.append(".azoth/releases/applied.yaml: personal_deployments list is required")
        return

    root_text = str(root.resolve())
    for item in deployments:
        if not isinstance(item, dict):
            continue
        deployment_id = str(item.get("deployment_id") or "")
        if not deployment_id.startswith("t-052-personal-cockpit-deployment"):
            continue
        if str(Path(str(item.get("target_repo") or "")).resolve()) != root_text:
            continue
        if item.get("target_panel") != "yiwei-azoth-cockpit":
            continue
        return
    errors.append(".azoth/releases/applied.yaml: missing T-052 cockpit deployment receipt")


def _check_first_use_receipt(root: Path, errors: list[str]) -> None:
    receipt_dir = root / ".azoth" / "projects" / "handoffs"
    candidates = sorted(receipt_dir.glob("t-055-first-use-*.yaml"))
    if not candidates:
        errors.append(".azoth/projects/handoffs: missing T-055 first-use onboarding receipt")
        return

    project_ids = _project_ids(root)
    for path in candidates:
        doc = _load_yaml_mapping(path)
        contract = doc.get("safe_open_contract")
        pilot = doc.get("pilot_project")
        if doc.get("operation") != "first_use_onboarding_and_no_write_handoff_pilot":
            continue
        if doc.get("source_panel") != "yiwei-azoth-cockpit":
            continue
        if not isinstance(contract, dict) or not isinstance(pilot, dict):
            continue
        if contract.get("cockpit_menu_writes_files") is not False:
            continue
        if contract.get("cockpit_imports_project_context") is not False:
            continue
        if contract.get("project_session_required_for_project_writes") is not True:
            continue
        if str(pilot.get("project_id") or "") not in project_ids:
            continue
        return
    errors.append(".azoth/projects/handoffs: T-055 first-use receipt contract is invalid")


def _check_rendered_menu(root: Path, errors: list[str]) -> None:
    state = load_cockpit(root, include_status=False)
    text = render_menu(state)
    required = (
        "Release sync: OK",
        "Mode: safe-open terminal menu; this command writes no files",
        "## Context Firewall",
        "ras-or-ray",
    )
    for snippet in required:
        if snippet not in text:
            errors.append(f"cockpit menu render: missing {snippet!r}")


def _check_deployed_menu(root: Path, errors: list[str]) -> None:
    script = root / "scripts" / "cockpit_menu.py"
    if not script.is_file():
        return
    result = _run_command(
        [sys.executable, "scripts/cockpit_menu.py", "--check"],
        cwd=root,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        errors.append(f"deployed cockpit menu --check failed: {detail}")


def verify_cockpit_bootstrap(
    root: Path,
    *,
    include_git_status: bool = True,
    run_deployed_menu_check: bool = True,
) -> list[str]:
    """Return fail-closed bootstrap errors for a deployed cockpit root."""
    cockpit_root = root.resolve()
    errors: list[str] = []

    if not cockpit_root.is_dir():
        return [f"{cockpit_root}: cockpit root does not exist"]

    _check_required_files(cockpit_root, errors)
    _check_startup_files(cockpit_root, errors)
    _check_handbook(cockpit_root, errors)
    _check_deployment_receipt(cockpit_root, errors)
    _check_first_use_receipt(cockpit_root, errors)

    state = load_cockpit(cockpit_root, include_status=False)
    errors.extend(check_cockpit(state))
    _check_rendered_menu(cockpit_root, errors)

    if run_deployed_menu_check:
        _check_deployed_menu(cockpit_root, errors)

    if include_git_status:
        if not (cockpit_root / ".git").exists():
            errors.append(f"{cockpit_root}: cockpit root must be a git repository")
        else:
            status_lines = _git_status_lines(cockpit_root)
            if any(line.startswith("ERROR:") for line in status_lines):
                errors.extend(status_lines)
            elif not _repo_is_clean(status_lines):
                errors.append(
                    "cockpit repo must be clean for bootstrap verification: "
                    + " | ".join(status_lines)
                )

    return errors


def format_report(root: Path, errors: list[str]) -> str:
    cockpit_root = root.resolve()
    if not errors:
        return f"cockpit bootstrap verify OK: {cockpit_root}"
    lines = [f"cockpit bootstrap verify FAILED: {cockpit_root}"]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_COCKPIT_ROOT)
    parser.add_argument("--json", action="store_true", help="Emit JSON result.")
    parser.add_argument(
        "--skip-git-status",
        action="store_true",
        help="Do not require the cockpit git repo to be clean.",
    )
    parser.add_argument(
        "--skip-deployed-menu-check",
        action="store_true",
        help="Do not execute the deployed cockpit menu --check command.",
    )
    args = parser.parse_args(argv)

    errors = verify_cockpit_bootstrap(
        args.root,
        include_git_status=not args.skip_git_status,
        run_deployed_menu_check=not args.skip_deployed_menu_check,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "root": str(args.root.resolve()),
                    "status": "passed" if not errors else "failed",
                    "errors": errors,
                },
                indent=2,
            )
        )
    else:
        print(format_report(args.root, errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

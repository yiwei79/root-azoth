#!/usr/bin/env python3
"""Run a no-write UX simulation for the Yiwei Azoth cockpit."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from cockpit_bootstrap_verify import format_report, verify_cockpit_bootstrap
    from cockpit_menu import check_cockpit, load_cockpit, render_menu
except ModuleNotFoundError:  # pragma: no cover - defensive direct execution path.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cockpit_bootstrap_verify import format_report, verify_cockpit_bootstrap
    from cockpit_menu import check_cockpit, load_cockpit, render_menu


DEFAULT_COCKPIT_ROOT = Path("/Users/yiwei/GithubRepos/yiwei-azoth-cockpit")
FORBIDDEN_OUTPUT_SNIPPETS = (
    "source_files",
    "code_summaries",
    "dependency_inventory",
    "secrets",
    "retrieval_index",
    "project instructions",
)


@dataclass(frozen=True)
class SimulationResult:
    output: str
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def _git_status(path: Path) -> str:
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


def _project_path(root: Path, project_id: str) -> Path | None:
    state = load_cockpit(root, include_status=False)
    for project in state.get("projects", []):
        if isinstance(project, dict) and project.get("project_id") == project_id:
            return Path(str(project.get("repo_path") or ""))
    return None


def _onboarding_help(root: Path) -> str:
    path = root / "docs" / "ONBOARDING.md"
    if not path.is_file():
        return "docs/ONBOARDING.md is missing."
    text = path.read_text(encoding="utf-8")
    start = text.find("## Cockpit Command Surface")
    if start == -1:
        start = text.find("## Command Reference")
    end = text.find("## First Pilot", start)
    if start == -1:
        return text.strip()
    if end == -1:
        return text[start:].strip()
    return text[start:end].strip()


def _check_required_output(combined: str, project_id: str) -> list[str]:
    errors: list[str] = []
    required = (
        "Release sync: OK",
        project_id,
        "pointer_only",
        "Project-local context is authoritative",
        "/cockpit",
        "$azoth-cockpit",
    )
    for snippet in required:
        if snippet not in combined:
            errors.append(f"simulation output missing {snippet!r}")
    lowered = combined.lower()
    for forbidden in FORBIDDEN_OUTPUT_SNIPPETS:
        if forbidden in lowered:
            errors.append(f"simulation output leaked forbidden snippet {forbidden!r}")
    return errors


def simulate_cockpit_ux(
    root: Path,
    *,
    project_id: str = "ras-or-ray",
    include_bootstrap_verify: bool = True,
) -> SimulationResult:
    cockpit_root = root.resolve()
    project_path = _project_path(cockpit_root, project_id)
    project_status_before = _git_status(project_path) if project_path else "missing project"
    cockpit_status_before = _git_status(cockpit_root)

    state = load_cockpit(cockpit_root, include_status=True)
    menu = render_menu(state)
    project_handoff = render_menu(state, project_id=project_id)
    cockpit_errors = check_cockpit(load_cockpit(cockpit_root, include_status=False))
    bootstrap_errors = (
        verify_cockpit_bootstrap(
            cockpit_root,
            include_git_status=False,
            run_deployed_menu_check=True,
        )
        if include_bootstrap_verify
        else []
    )

    sections = [
        "# Cockpit UX Simulation",
        "",
        "## Start cockpit",
        "Start cockpit.",
        menu,
        "",
        "## /cockpit",
        menu,
        "",
        "## /cockpit-check",
        "cockpit menu check OK" if not cockpit_errors else "\n".join(cockpit_errors),
        format_report(cockpit_root, bootstrap_errors),
        "",
        f"## /cockpit-project {project_id}",
        project_handoff,
        "",
        "## /cockpit-help",
        _onboarding_help(cockpit_root),
        "",
        "## /cockpit-ux-simulate",
        "This command runs this no-write UX simulation; nested execution is intentionally skipped.",
    ]
    output = "\n".join(sections)

    cockpit_status_after = _git_status(cockpit_root)
    project_status_after = _git_status(project_path) if project_path else "missing project"
    errors = []
    errors.extend(cockpit_errors)
    errors.extend(bootstrap_errors)
    errors.extend(_check_required_output(output, project_id))
    if cockpit_status_before != cockpit_status_after:
        errors.append("cockpit git status changed during simulation")
    if project_status_before != project_status_after:
        errors.append(f"{project_id} git status changed during simulation")

    return SimulationResult(output=output, errors=errors)


def format_result(result: SimulationResult) -> str:
    if result.ok:
        return result.output + "\n\ncockpit UX simulation OK"
    return (
        result.output
        + "\n\ncockpit UX simulation FAILED\n"
        + "\n".join(f"- {error}" for error in result.errors)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_COCKPIT_ROOT)
    parser.add_argument("--project", default="ras-or-ray")
    parser.add_argument(
        "--skip-bootstrap-verify",
        action="store_true",
        help="Skip root bootstrap verification inside the simulation.",
    )
    args = parser.parse_args(argv)

    result = simulate_cockpit_ux(
        args.root,
        project_id=args.project,
        include_bootstrap_verify=not args.skip_bootstrap_verify,
    )
    print(format_result(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

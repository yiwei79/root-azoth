#!/usr/bin/env python3
"""Deploy/check the minimal Codex-visible Yiwei cockpit command surface."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


DEFAULT_COCKPIT_ROOT = Path("/Users/yiwei/GithubRepos/yiwei-azoth-cockpit")


@dataclass(frozen=True)
class CockpitCommand:
    name: str
    display_name: str
    description: str
    summary: str
    execution_steps: tuple[str, ...]
    default_prompt_suffix: str = " "

    @property
    def skill_name(self) -> str:
        return f"azoth-{self.name}"

    @property
    def skill_dir(self) -> Path:
        return Path(".agents") / "skills" / self.skill_name


COCKPIT_COMMANDS: tuple[CockpitCommand, ...] = (
    CockpitCommand(
        name="cockpit",
        display_name="/cockpit",
        description="Open the safe Yiwei Azoth cockpit menu.",
        summary="Run cockpit validation, then show the main safe-open cockpit menu.",
        execution_steps=(
            "Run `python3 scripts/cockpit_menu.py --check`.",
            "Run `python3 scripts/cockpit_menu.py`.",
            "Summarize release sync, registered project pointers, and safe next actions.",
        ),
    ),
    CockpitCommand(
        name="cockpit-check",
        display_name="/cockpit-check",
        description="Validate the Yiwei Azoth cockpit bootstrap and menu metadata.",
        summary="Check that the deployed cockpit has the minimum deterministic bootstrap surface.",
        execution_steps=(
            "Run `python3 scripts/cockpit_menu.py --check`.",
            "If available, run `python3 /Users/yiwei/GithubRepos/root-azoth/scripts/cockpit_bootstrap_verify.py --root /Users/yiwei/GithubRepos/yiwei-azoth-cockpit`.",
            "Report pass/fail and the first actionable missing surface.",
        ),
    ),
    CockpitCommand(
        name="cockpit-project",
        display_name="/cockpit-project",
        description="Render a pointer-only project handoff from the cockpit.",
        summary="Show the selected project path and safe project-session prompt.",
        execution_steps=(
            "Use `$ARGUMENTS` as the project id; default to `ras-or-ray` when empty.",
            "Run `python3 scripts/cockpit_menu.py --project <project_id>`.",
            "Do not load project source or project-local guidance in the cockpit session.",
        ),
        default_prompt_suffix=" ras-or-ray",
    ),
    CockpitCommand(
        name="cockpit-help",
        display_name="/cockpit-help",
        description="Show the cockpit onboarding handbook and command reference.",
        summary="Surface `docs/ONBOARDING.md` and the cockpit safe write-lane rules.",
        execution_steps=(
            "Read `docs/ONBOARDING.md`.",
            "Summarize the Command Reference and Safe Write Lanes sections.",
            "Do not start work; this command is lookup-only.",
        ),
    ),
    CockpitCommand(
        name="cockpit-ux-simulate",
        display_name="/cockpit-ux-simulate",
        description="Run the no-write cockpit UX simulation.",
        summary="Verify the cockpit command experience against the UX anchors without writes.",
        execution_steps=(
            "Run `python3 /Users/yiwei/GithubRepos/root-azoth/scripts/cockpit_ux_simulate.py --root /Users/yiwei/GithubRepos/yiwei-azoth-cockpit --project ras-or-ray`.",
            "Confirm cockpit and project git states are unchanged.",
            "Report any UX anchor mismatch as a blocker.",
        ),
    ),
)


SAFE_OPEN_LINES = (
    "This is a safe-open cockpit command.",
    "It must not write cockpit files, write project files, import project source, "
    "expand retrieval, onboard sources, or start hidden background work.",
)


def command_by_name(name: str) -> CockpitCommand | None:
    return next((command for command in COCKPIT_COMMANDS if command.name == name), None)


def render_skill(command: CockpitCommand) -> str:
    frontmatter = {
        "name": command.skill_name,
        "description": (
            f"Codex-visible cockpit command for `{command.display_name}`. "
            f"Use when the user wants to operate the Yiwei Azoth cockpit via "
            f"`/skills` or `${command.skill_name}`."
        ),
    }
    body = [
        f"Use this skill as the Codex-visible entrypoint for `{command.display_name}`.",
        "",
        command.summary,
        "",
        *SAFE_OPEN_LINES,
        "",
        "Execution contract:",
        *[f"- {step}" for step in command.execution_steps],
        f"- Treat the rest of the user's prompt after `${command.skill_name}` as `$ARGUMENTS`.",
        "- Preserve the cockpit context firewall: the cockpit routes; project repos own project context.",
        "- If the user typed the literal slash command in prompt text, apply the same workflow contract.",
        "",
        "Command metadata:",
        f"- Display name: `{command.display_name}`",
        f"- Skill name: `{command.skill_name}`",
        f"- Description: {command.description}",
    ]
    return (
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n" + "\n".join(body) + "\n"
    )


def render_openai_metadata(command: CockpitCommand) -> str:
    data = {
        "interface": {
            "display_name": command.display_name,
            "short_description": command.description,
            "default_prompt": f"${command.skill_name}{command.default_prompt_suffix}",
        },
        "policy": {"allow_implicit_invocation": False},
    }
    return yaml.safe_dump(data, sort_keys=False)


def expected_files(root: Path) -> dict[Path, str]:
    files: dict[Path, str] = {}
    for command in COCKPIT_COMMANDS:
        skill_dir = root / command.skill_dir
        files[skill_dir / "SKILL.md"] = render_skill(command)
        files[skill_dir / "agents" / "openai.yaml"] = render_openai_metadata(command)
    return files


def deploy_cockpit_command_surface(root: Path, *, check: bool = False) -> list[str]:
    errors: list[str] = []
    for path, expected in expected_files(root).items():
        if check:
            if not path.is_file():
                errors.append(f"{path.relative_to(root)}: missing")
                continue
            actual = path.read_text(encoding="utf-8")
            if actual != expected:
                errors.append(f"{path.relative_to(root)}: stale")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8")
    return errors


def check_cockpit_command_docs(root: Path) -> list[str]:
    errors: list[str] = []
    required = [
        "Start cockpit.",
        "## Cockpit Command Surface",
        *[command.display_name for command in COCKPIT_COMMANDS],
        *[f"${command.skill_name}" for command in COCKPIT_COMMANDS],
    ]
    for rel_path in ("docs/ONBOARDING.md", "AGENTS.md", "CLAUDE.md"):
        path = root / rel_path
        if not path.is_file():
            errors.append(f"{rel_path}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in required:
            if snippet not in text:
                errors.append(f"{rel_path}: missing command-surface text {snippet!r}")
    return errors


def check_cockpit_command_surface(root: Path) -> list[str]:
    return deploy_cockpit_command_surface(root, check=True) + check_cockpit_command_docs(root)


def format_errors(errors: Iterable[str]) -> str:
    items = list(errors)
    if not items:
        return "cockpit command surface OK"
    return "cockpit command surface FAILED\n" + "\n".join(f"- {error}" for error in items)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_COCKPIT_ROOT)
    parser.add_argument("--check", action="store_true", help="Check without writing.")
    args = parser.parse_args(argv)

    errors = (
        check_cockpit_command_surface(args.root)
        if args.check
        else deploy_cockpit_command_surface(args.root)
    )
    print(format_errors(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

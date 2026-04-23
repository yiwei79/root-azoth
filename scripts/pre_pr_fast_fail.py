#!/usr/bin/env python3
"""Run the lightweight pre-PR checks that catch predictable Azoth drift early."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path


PYTHON = sys.executable
REPO_ROOT = Path(__file__).resolve().parent.parent

PARITY_SENSITIVE_PREFIXES = (
    "agents/",
    "commands/",
    "skills/",
    ".claude/commands/",
    "kernel/templates/platform-adapters/",
    ".agents/skills/",
    ".agents/workflows/",
    ".agents/rules/",
    ".claude/agents/",
    ".codex/",
    ".cursor/rules/",
    ".gemini/",
    ".github/agents/",
    ".github/prompts/",
    ".github/skills/",
    ".opencode/",
)
PARITY_SENSITIVE_FILES = (
    "AGENTS.md",
    "GEMINI.md",
)

CONTRACT_TESTS = (
    "tests/test_install_proposals_gitignore.py",
    "tests/test_v020_roadmap_spec_decision_ref_parity.py",
)

CommandRunner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


def _run(cmd: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=repo_root, check=False, text=True)


def _lines(stdout: str) -> list[str]:
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def changed_files_since_head(repo_root: Path) -> list[str]:
    """Return tracked and untracked paths that would matter before opening a PR."""
    changed = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if changed.returncode != 0:
        raise RuntimeError(changed.stderr.strip() or "git diff failed")

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if untracked.returncode != 0:
        raise RuntimeError(untracked.stderr.strip() or "git ls-files failed")

    return _lines(changed.stdout) + _lines(untracked.stdout)


def is_parity_sensitive(path: str) -> bool:
    return path in PARITY_SENSITIVE_FILES or any(
        path.startswith(prefix) for prefix in PARITY_SENSITIVE_PREFIXES
    )


def _commands_for(changed_files: Iterable[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    if any(is_parity_sensitive(path) for path in changed_files):
        commands.append([PYTHON, "scripts/azoth-deploy.py"])
    commands.extend(
        [
            [PYTHON, "scripts/azoth-deploy.py", "--check"],
            [PYTHON, "-m", "ruff", "format", "--check", "."],
            [PYTHON, "-m", "ruff", "check", "."],
            [PYTHON, "-m", "pytest", "-q", *CONTRACT_TESTS],
        ]
    )
    return commands


def main(
    *,
    repo_root: Path = REPO_ROOT,
    run: CommandRunner = _run,
) -> int:
    try:
        changed_files = changed_files_since_head(repo_root)
    except RuntimeError as exc:
        print(f"pre-pr fast-fail: {exc}", file=sys.stderr)
        return 1

    for cmd in _commands_for(changed_files):
        print("+ " + " ".join(cmd))
        result = run(cmd, repo_root)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

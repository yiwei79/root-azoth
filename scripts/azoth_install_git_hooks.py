#!/usr/bin/env python3
"""Install Azoth git hooks using ``core.hooksPath`` (idempotent).

Run from the repository root (or any path inside the work tree):

    python3 scripts/azoth_install_git_hooks.py

Sets ``git config core.hooksPath scripts/git-hooks`` relative to the work tree
so the versioned ``commit-msg`` hook in this repo is used. Does nothing useful
outside a git repository (prints a message and exits 0).

See docs/DAY0_TUTORIAL.md (Phase 5) and D43.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _git_top_level(cwd: Path) -> Path | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(r.stdout.strip())


def main() -> int:
    cwd = Path.cwd()
    git_root = _git_top_level(cwd)
    if git_root is None:
        print("azoth: not a git repository — skipped git hooks install", file=sys.stderr)
        return 0

    hooks_rel = "scripts/git-hooks"
    commit_msg = git_root / hooks_rel / "commit-msg"
    if not commit_msg.is_file():
        print(
            f"azoth: expected hook at {commit_msg} — skipped",
            file=sys.stderr,
        )
        return 1

    subprocess.run(
        ["git", "-C", str(git_root), "config", "core.hooksPath", hooks_rel],
        check=True,
    )
    print(f"azoth: core.hooksPath={hooks_rel} (repo: {git_root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

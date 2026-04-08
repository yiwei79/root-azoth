#!/usr/bin/env python3
"""Mechanical git checkpoints for TRUST_CONTRACT §4 (P5-005).

Run from inside a git work tree. Does not run from PreToolUse hooks — humans or agents
invoke this explicitly before high-entropy work (yellow/red zones).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

_TAG_PREFIX = "azoth/checkpoint/"


def _git_top(cwd: Path) -> Path | None:
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


def _run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def cmd_create(repo: Path) -> int:
    """Stash uncommitted work with message azoth-checkpoint-<unix epoch>."""
    ts = int(time.time())
    msg = f"azoth-checkpoint-{ts}"
    r = _run_git(repo, "stash", "push", "-m", msg, check=False)
    if r.returncode == 0:
        print(f"azoth-checkpoint: stash created ({msg})")
        return 0
    err = (r.stderr or "") + (r.stdout or "")
    if "No local changes to save" in err or "nothing to stash" in err.lower():
        print("azoth-checkpoint: no local changes to stash", file=sys.stderr)
        return 0
    print(r.stderr or r.stdout or "git stash failed", file=sys.stderr)
    return 1


def cmd_tag(repo: Path) -> int:
    """Lightweight tag on HEAD: azoth/checkpoint/<unix epoch> (see git-tag(1))."""
    ts = int(time.time())
    name = f"{_TAG_PREFIX}{ts}"
    _run_git(repo, "tag", name)
    print(f"azoth-checkpoint: tag {name}")
    return 0


def cmd_list(repo: Path) -> int:
    r = _run_git(repo, "stash", "list", check=False)
    lines = [ln for ln in (r.stdout or "").splitlines() if "azoth-checkpoint-" in ln]
    print("--- stash (azoth) ---")
    if lines:
        print("\n".join(lines))
    else:
        print("(none)")
    r2 = _run_git(repo, "tag", "-l", f"{_TAG_PREFIX}*", check=False)
    tags = [ln for ln in (r2.stdout or "").splitlines() if ln.strip()]
    print("--- tags (azoth/checkpoint/*) ---")
    if tags:
        print("\n".join(tags))
    else:
        print("(none)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Create or list Azoth git checkpoints (TRUST_CONTRACT §4).",
        epilog=(
            "Recovery: for stash entries, `git stash apply stash@{n}` keeps the stash "
            "on the stack (safer if conflicts); `git stash pop` applies and removes the "
            "stash. For tags, `git checkout <tag>` detaches HEAD — create a branch if "
            "you need to continue work."
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp_c = sub.add_parser("create", help="git stash push with azoth-checkpoint-<epoch> message")
    sp_c.set_defaults(func=lambda args: cmd_create(args.repo))

    sp_t = sub.add_parser(
        "tag",
        help="lightweight git tag azoth/checkpoint/<epoch> on HEAD",
        description=(
            "Lightweight tag at HEAD: refs/tags/azoth/checkpoint/<epoch> "
            "(plain `git tag`, not `git tag -a`)."
        ),
    )
    sp_t.set_defaults(func=lambda args: cmd_tag(args.repo))

    sp_l = sub.add_parser("list", help="list azoth stash lines and checkpoint tags")
    sp_l.set_defaults(func=lambda args: cmd_list(args.repo))

    for sp in (sp_c, sp_t, sp_l):
        sp.add_argument(
            "--repo",
            type=Path,
            default=Path.cwd(),
            help="git repository root (default: cwd)",
        )

    args = p.parse_args(argv)
    repo = args.repo.resolve()
    root = _git_top(repo)
    if root is None:
        print("azoth-checkpoint: not a git repository", file=sys.stderr)
        return 1
    args.repo = root
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

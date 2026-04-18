#!/usr/bin/env python3
"""Backend preflight for Azoth /worktree-sync.

Producer branches are refreshed against the local integration branch before
commit creation. Integration branches fail closed when the target worktree is
dirty so only one clean integrator pass happens at a time.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml


def _git_top(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(result.stdout.strip())


def _run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _roadmap_target_branch(repo: Path) -> str | None:
    roadmap_path = repo / ".azoth" / "roadmap.yaml"
    if not roadmap_path.exists():
        return None
    try:
        data = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    active_version = str(data.get("active_version") or "").strip()
    if not active_version:
        return None
    return f"phase/{active_version}"


def _fallback_phase_branch(repo: Path) -> str | None:
    result = _run_git(
        repo,
        "for-each-ref",
        "--format=%(refname:short)",
        "refs/heads/phase",
        "refs/heads/phase/*",
        check=False,
    )
    branches = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(branches) == 1:
        return branches[0]
    return None


def resolve_target_branch(repo: Path, override: str | None) -> str:
    if override:
        return override
    roadmap_branch = _roadmap_target_branch(repo)
    if roadmap_branch:
        return roadmap_branch
    fallback = _fallback_phase_branch(repo)
    if fallback:
        return fallback
    raise RuntimeError(
        "Could not resolve the integration branch. Pass --target-branch explicitly "
        "or ensure .azoth/roadmap.yaml has active_version."
    )


def current_branch(repo: Path) -> str:
    result = _run_git(repo, "branch", "--show-current", check=False)
    branch = result.stdout.strip()
    if not branch:
        raise RuntimeError("worktree-sync requires a named branch; detached HEAD is not supported.")
    return branch


def branch_exists(repo: Path, branch: str) -> bool:
    result = _run_git(repo, "show-ref", "--verify", f"refs/heads/{branch}", check=False)
    return result.returncode == 0


def working_tree_dirty(repo: Path) -> bool:
    result = _run_git(repo, "status", "--porcelain", check=False)
    return bool(result.stdout.strip())


def dirty_paths(repo: Path) -> list[str]:
    result = _run_git(repo, "status", "--porcelain", check=False)
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def target_is_ancestor_of_head(repo: Path, target_branch: str) -> bool:
    result = _run_git(repo, "merge-base", "--is-ancestor", target_branch, "HEAD", check=False)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "merge-base failed")


def _stash_ref_for_message(repo: Path, message: str) -> str | None:
    result = _run_git(repo, "stash", "list", "--format=%gd%x00%gs", check=False)
    for line in result.stdout.splitlines():
        if "\x00" not in line:
            continue
        ref, subject = line.split("\x00", 1)
        if message in subject:
            return ref.strip()
    return None


def create_stash(repo: Path) -> str:
    message = f"azoth-worktree-sync-{int(time.time())}-{os.getpid()}"
    result = _run_git(repo, "stash", "push", "-u", "-m", message, check=False)
    output = (result.stderr or "") + (result.stdout or "")
    if result.returncode != 0:
        raise RuntimeError(output.strip() or "git stash push failed")
    stash_ref = _stash_ref_for_message(repo, message)
    if not stash_ref:
        raise RuntimeError("created worktree-sync stash, but could not resolve its stash ref")
    return stash_ref


def restore_stash(repo: Path, stash_ref: str) -> None:
    apply_result = _run_git(repo, "stash", "apply", stash_ref, check=False)
    if apply_result.returncode != 0:
        detail = apply_result.stderr.strip() or apply_result.stdout.strip() or "git stash apply failed"
        raise RuntimeError(
            f"stashed work could not be restored cleanly from {stash_ref}: {detail}. "
            f"Resolve the conflicts and rerun /worktree-sync. The stash remains available."
        )
    drop_result = _run_git(repo, "stash", "drop", stash_ref, check=False)
    if drop_result.returncode != 0:
        detail = drop_result.stderr.strip() or drop_result.stdout.strip() or "git stash drop failed"
        print(
            f"worktree-sync: warning: restored {stash_ref} but could not drop it cleanly: {detail}",
            file=sys.stderr,
        )


def producer_refresh(repo: Path, current: str, target_branch: str) -> int:
    if target_is_ancestor_of_head(repo, target_branch):
        print(
            f"worktree-sync: producer branch '{current}' already contains '{target_branch}'. "
            "No pre-commit refresh needed."
        )
        return 0

    stash_ref: str | None = None
    if working_tree_dirty(repo):
        stash_ref = create_stash(repo)
        print(f"worktree-sync: stashed local changes in {stash_ref} before rebasing.")

    rebase_result = _run_git(repo, "rebase", target_branch, check=False)
    if rebase_result.returncode != 0:
        detail = rebase_result.stderr.strip() or rebase_result.stdout.strip() or "git rebase failed"
        preserved = f" Stashed work is preserved in {stash_ref}." if stash_ref else ""
        print(
            "worktree-sync: producer refresh blocked — rebase onto "
            f"'{target_branch}' hit conflicts. Resolve conflicts, then rerun /worktree-sync."
            f"{preserved}\n{detail}",
            file=sys.stderr,
        )
        return 1

    if stash_ref:
        try:
            restore_stash(repo, stash_ref)
        except RuntimeError as exc:
            print(f"worktree-sync: producer refresh blocked — {exc}", file=sys.stderr)
            return 1

    print(
        f"worktree-sync: producer branch '{current}' rebased onto '{target_branch}'. "
        "Continue with explicit staging, commit, and optional push."
    )
    return 0


def integrator_preflight(repo: Path, current: str, target_branch: str) -> int:
    if working_tree_dirty(repo):
        paths = "\n".join(f"- {path}" for path in dirty_paths(repo))
        print(
            "worktree-sync: integration blocked — the target branch worktree is dirty.\n"
            "Parallel integration is unsafe until those changes are finished or parked.\n"
            f"{paths}",
            file=sys.stderr,
        )
        return 1

    print(
        f"worktree-sync: integrator branch '{current}' is clean and ready to merge exactly "
        "one producer branch."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backend preflight for Azoth /worktree-sync.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Git repository root or any path inside it (default: cwd).",
    )
    parser.add_argument(
        "--target-branch",
        default=None,
        help="Optional integration branch override. Defaults to phase/<active_version>.",
    )
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    root = _git_top(repo)
    if root is None:
        print("worktree-sync: not a git repository", file=sys.stderr)
        return 1

    try:
        target_branch = resolve_target_branch(root, args.target_branch)
        if not branch_exists(root, target_branch):
            raise RuntimeError(
                f"target branch '{target_branch}' does not exist locally. "
                "Refresh your local repo or pass a valid --target-branch."
            )
        branch = current_branch(root)
    except RuntimeError as exc:
        print(f"worktree-sync: {exc}", file=sys.stderr)
        return 1

    if branch == target_branch:
        return integrator_preflight(root, branch, target_branch)
    return producer_refresh(root, branch, target_branch)


if __name__ == "__main__":
    raise SystemExit(main())

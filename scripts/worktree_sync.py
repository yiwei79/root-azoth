#!/usr/bin/env python3
"""Backend preflight for Azoth /worktree-sync.

Producer branches are refreshed against the local integration branch before
commit creation. Integration branches fail closed when the target worktree is
dirty so only one clean integrator pass happens at a time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
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


def _resolve_git_common_dir(repo: Path) -> Path | None:
    env_override = os.environ.get("AZOTH_GIT_COMMON_DIR")
    if env_override:
        return Path(env_override).expanduser().resolve()
    result = _run_git(repo, "rev-parse", "--git-common-dir", check=False)
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (repo / path).resolve()
    return path.resolve()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _handoff_queue_path(repo: Path) -> Path | None:
    explicit_path = os.environ.get("AZOTH_WORKTREE_HANDOFF_QUEUE_PATH")
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()

    common_dir = _resolve_git_common_dir(repo)
    if common_dir is None:
        return None

    digest = hashlib.sha1(str(common_dir).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / "azoth-worktree-handoffs" / f"{digest}.jsonl"


def _append_jsonl_record(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
        handle.write("\n")


def _load_jsonl_records(path: Path | None) -> list[dict[str, object]]:
    if path is None or not path.exists():
        return []
    records: list[dict[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            records.append(data)
    return records


def _current_head(repo: Path) -> str:
    result = _run_git(repo, "rev-parse", "HEAD")
    return result.stdout.strip()


def _latest_ready_handoff(
    repo: Path,
    *,
    target_branch: str,
    producer_branch: str | None = None,
) -> dict[str, object] | None:
    queue_path = _handoff_queue_path(repo)
    states: dict[tuple[str, str], dict[str, object]] = {}
    for record in _load_jsonl_records(queue_path):
        event = str(record.get("event") or "").strip()
        branch = str(record.get("producer_branch") or "").strip()
        target = str(record.get("target_branch") or "").strip()
        if not branch or not target:
            continue
        key = (target, branch)
        if event == "producer-ready":
            states[key] = record
        elif event == "integrated":
            states.pop(key, None)

    ready_records = [
        record
        for (target, branch), record in states.items()
        if target == target_branch and (producer_branch is None or branch == producer_branch)
    ]
    if not ready_records:
        return None
    ready_records.sort(key=lambda record: str(record.get("recorded_at") or ""))
    return ready_records[-1]


def register_producer_handoff(repo: Path, current: str, target_branch: str) -> int:
    if current == target_branch:
        print(
            "worktree-sync: cannot record a producer handoff from the integration branch",
            file=sys.stderr,
        )
        return 1
    if working_tree_dirty(repo):
        print(
            "worktree-sync: producer handoff requires a clean worktree. Commit or park local changes first.",
            file=sys.stderr,
        )
        return 1

    queue_path = _handoff_queue_path(repo)
    if queue_path is None:
        print("worktree-sync: could not resolve the shared handoff queue path", file=sys.stderr)
        return 1

    record: dict[str, object] = {
        "event": "producer-ready",
        "recorded_at": _utc_now_iso(),
        "producer_branch": current,
        "target_branch": target_branch,
        "head_sha": _current_head(repo),
        "worktree_path": str(repo.resolve()),
        "queue_path": str(queue_path),
    }
    common_dir = _resolve_git_common_dir(repo)
    if common_dir is not None:
        record["git_common_dir"] = str(common_dir)

    _append_jsonl_record(queue_path, record)
    print(
        "worktree-sync: recorded producer handoff "
        f"'{current}' -> '{target_branch}' at {record['head_sha']} in {queue_path}"
    )
    return 0


def show_ready_handoff(
    repo: Path, target_branch: str, producer_branch: str | None, *, as_json: bool
) -> int:
    record = _latest_ready_handoff(
        repo,
        target_branch=target_branch,
        producer_branch=producer_branch,
    )
    if record is None:
        wanted = f" for '{producer_branch}'" if producer_branch else ""
        print(
            f"worktree-sync: no ready producer handoff found for target '{target_branch}'{wanted}",
            file=sys.stderr,
        )
        return 1

    if as_json:
        print(json.dumps(record, ensure_ascii=True, sort_keys=True))
    else:
        print(
            "worktree-sync: selected ready producer handoff "
            f"'{record['producer_branch']}' at {record['head_sha']} targeting '{target_branch}'"
        )
    return 0


def mark_integrated(repo: Path, current: str, target_branch: str, producer_branch: str) -> int:
    if current != target_branch:
        print(
            "worktree-sync: integration completion can only be recorded from the active integration branch",
            file=sys.stderr,
        )
        return 1

    ready = _latest_ready_handoff(
        repo,
        target_branch=target_branch,
        producer_branch=producer_branch,
    )
    if ready is None:
        print(
            f"worktree-sync: no ready producer handoff found for '{producer_branch}' on '{target_branch}'",
            file=sys.stderr,
        )
        return 1

    queue_path = _handoff_queue_path(repo)
    if queue_path is None:
        print("worktree-sync: could not resolve the shared handoff queue path", file=sys.stderr)
        return 1

    record: dict[str, object] = {
        "event": "integrated",
        "recorded_at": _utc_now_iso(),
        "producer_branch": producer_branch,
        "producer_head_sha": ready.get("head_sha"),
        "target_branch": target_branch,
        "integrator_branch": current,
        "integrated_head_sha": _current_head(repo),
        "worktree_path": str(repo.resolve()),
        "queue_path": str(queue_path),
    }
    common_dir = _resolve_git_common_dir(repo)
    if common_dir is not None:
        record["git_common_dir"] = str(common_dir)

    _append_jsonl_record(queue_path, record)
    print(
        "worktree-sync: marked producer handoff "
        f"'{producer_branch}' integrated into '{target_branch}' at {record['integrated_head_sha']}"
    )
    return 0


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
        detail = (
            apply_result.stderr.strip() or apply_result.stdout.strip() or "git stash apply failed"
        )
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


def integrator_preflight(
    repo: Path, current: str, target_branch: str, *, quiet: bool = False
) -> int:
    if working_tree_dirty(repo):
        paths = "\n".join(f"- {path}" for path in dirty_paths(repo))
        print(
            "worktree-sync: integration blocked — the target branch worktree is dirty.\n"
            "Parallel integration is unsafe until those changes are finished or parked.\n"
            f"{paths}",
            file=sys.stderr,
        )
        return 1

    if not quiet:
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
    parser.add_argument(
        "--record-producer-handoff",
        action="store_true",
        help="Record the current clean producer branch as ready for integrator handoff.",
    )
    parser.add_argument(
        "--next-ready-handoff",
        action="store_true",
        help="Show the next ready producer handoff for the target branch.",
    )
    parser.add_argument(
        "--producer-branch",
        default=None,
        help="Optional producer branch selector for ready/integrated handoff actions.",
    )
    parser.add_argument(
        "--mark-integrated",
        default=None,
        metavar="BRANCH",
        help="Mark a queued producer handoff as integrated into the target branch.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON for ready handoff selection.",
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
        result = integrator_preflight(
            root,
            branch,
            target_branch,
            quiet=args.json and args.next_ready_handoff,
        )
    else:
        result = producer_refresh(root, branch, target_branch)
    if result != 0:
        return result

    if args.record_producer_handoff:
        return register_producer_handoff(root, branch, target_branch)
    if args.next_ready_handoff:
        return show_ready_handoff(
            root,
            target_branch,
            args.producer_branch,
            as_json=args.json,
        )
    if args.mark_integrated:
        return mark_integrated(root, branch, target_branch, args.mark_integrated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

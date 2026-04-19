from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "worktree_sync.py"


def _run_sync(
    cwd: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    cmd_env = os.environ.copy()
    if env:
        cmd_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=cmd_env,
    )


def _run_git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _init_repo(path: Path) -> None:
    init = subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    if init.returncode != 0:
        legacy = subprocess.run(
            ["git", "init"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        if legacy.returncode != 0:
            pytest.skip(
                "git init failed (install git or relax sandbox for worktree-sync tests): "
                f"{legacy.stderr.strip() or legacy.stdout.strip()}"
            )
    _run_git(path, "config", "user.email", "test@example.com")
    _run_git(path, "config", "user.name", "test")
    (path / ".azoth").mkdir(parents=True, exist_ok=True)
    (path / ".azoth" / "roadmap.yaml").write_text("active_version: v0.2.0-p2\n", encoding="utf-8")
    (path / "tracked.txt").write_text("base\n", encoding="utf-8")
    _run_git(path, "add", ".")
    _run_git(path, "commit", "-m", "init")


def _commit_file(repo: Path, branch: str, relpath: str, content: str, message: str) -> None:
    _run_git(repo, "checkout", branch)
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _run_git(repo, "add", relpath)
    _run_git(repo, "commit", "-m", message)


def _setup_phase_and_feature(repo: Path) -> None:
    _run_git(repo, "checkout", "-b", "phase/v0.2.0-p2")
    _run_git(repo, "checkout", "-b", "feat/test-producer")


def test_worktree_sync_resolves_target_from_roadmap_and_allows_clean_producer_path(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    (tmp_path / "tracked.txt").write_text("producer dirty\n", encoding="utf-8")

    result = _run_sync(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "already contains 'phase/v0.2.0-p2'" in result.stdout
    status = _run_git(tmp_path, "status", "--porcelain").stdout
    assert "tracked.txt" in status


def test_worktree_sync_rebases_clean_producer_branch_before_commit(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    _commit_file(tmp_path, "feat/test-producer", "feature.txt", "feature\n", "feature commit")
    _commit_file(tmp_path, "phase/v0.2.0-p2", "target.txt", "target\n", "target update")
    _run_git(tmp_path, "checkout", "feat/test-producer")

    result = _run_sync(tmp_path, "--target-branch", "phase/v0.2.0-p2")

    assert result.returncode == 0, result.stderr
    assert "rebased onto 'phase/v0.2.0-p2'" in result.stdout
    assert (
        _run_git(
            tmp_path, "merge-base", "--is-ancestor", "phase/v0.2.0-p2", "HEAD", check=False
        ).returncode
        == 0
    )


def test_worktree_sync_stashes_rebases_and_restores_dirty_producer_branch(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    _commit_file(tmp_path, "phase/v0.2.0-p2", "target.txt", "target\n", "target update")
    _run_git(tmp_path, "checkout", "feat/test-producer")
    (tmp_path / "local-untracked.txt").write_text("keep me\n", encoding="utf-8")

    result = _run_sync(tmp_path, "--target-branch", "phase/v0.2.0-p2")

    assert result.returncode == 0, result.stderr
    assert "stashed local changes" in result.stdout
    assert (tmp_path / "local-untracked.txt").read_text(encoding="utf-8") == "keep me\n"
    status = _run_git(tmp_path, "status", "--porcelain").stdout
    assert "local-untracked.txt" in status
    assert (
        _run_git(
            tmp_path, "merge-base", "--is-ancestor", "phase/v0.2.0-p2", "HEAD", check=False
        ).returncode
        == 0
    )


def test_worktree_sync_stops_on_rebase_conflict_without_creating_commit(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    _commit_file(
        tmp_path, "feat/test-producer", "tracked.txt", "feature branch line\n", "feature change"
    )
    _commit_file(
        tmp_path, "phase/v0.2.0-p2", "tracked.txt", "target branch line\n", "target change"
    )
    _run_git(tmp_path, "checkout", "feat/test-producer")
    head_before = _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    result = _run_sync(tmp_path, "--target-branch", "phase/v0.2.0-p2")

    assert result.returncode == 1
    assert "hit conflicts" in result.stderr
    assert _run_git(tmp_path, "rev-parse", "feat/test-producer").stdout.strip() == head_before
    status = _run_git(tmp_path, "status", "--porcelain", check=False).stdout
    assert "UU tracked.txt" in status


def test_worktree_sync_stops_on_stash_restore_conflict_and_preserves_stash(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    _commit_file(
        tmp_path, "phase/v0.2.0-p2", "tracked.txt", "target branch line\n", "target change"
    )
    _run_git(tmp_path, "checkout", "feat/test-producer")
    (tmp_path / "tracked.txt").write_text("local dirty line\n", encoding="utf-8")

    result = _run_sync(tmp_path, "--target-branch", "phase/v0.2.0-p2")

    assert result.returncode == 1
    assert "could not be restored cleanly" in result.stderr
    status = _run_git(tmp_path, "status", "--porcelain", check=False).stdout
    assert "UU tracked.txt" in status
    stash_list = _run_git(tmp_path, "stash", "list").stdout
    assert "azoth-worktree-sync-" in stash_list


def test_worktree_sync_fails_closed_when_target_branch_is_missing(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)

    result = _run_sync(tmp_path, "--target-branch", "phase/does-not-exist")

    assert result.returncode == 1
    assert "does not exist locally" in result.stderr


def test_worktree_sync_integrator_mode_fails_closed_on_dirty_target_branch(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _run_git(tmp_path, "checkout", "-b", "phase/v0.2.0-p2")
    (tmp_path / "tracked.txt").write_text("dirty target\n", encoding="utf-8")

    result = _run_sync(tmp_path, "--target-branch", "phase/v0.2.0-p2")

    assert result.returncode == 1
    assert "integration blocked" in result.stderr
    assert "- tracked.txt" in result.stderr


def test_worktree_sync_integrator_mode_allows_clean_target_branch(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _run_git(tmp_path, "checkout", "-b", "phase/v0.2.0-p2")

    result = _run_sync(tmp_path, "--target-branch", "phase/v0.2.0-p2")

    assert result.returncode == 0, result.stderr
    assert "clean and ready to merge exactly one producer branch" in result.stdout


def test_worktree_sync_records_producer_handoff_in_shared_queue(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    _commit_file(tmp_path, "feat/test-producer", "feature.txt", "feature\n", "feature commit")
    queue_path = tmp_path.parent / f"{tmp_path.name}-shared-handoffs.jsonl"

    result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--record-producer-handoff",
        env={"AZOTH_WORKTREE_HANDOFF_QUEUE_PATH": str(queue_path)},
    )

    assert result.returncode == 0, result.stderr
    assert "recorded producer handoff 'feat/test-producer'" in result.stdout
    records = [
        json.loads(line)
        for line in queue_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert records[0]["event"] == "producer-ready"
    assert records[0]["producer_branch"] == "feat/test-producer"
    assert records[0]["target_branch"] == "phase/v0.2.0-p2"


def test_worktree_sync_integrator_selects_and_clears_ready_handoff(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    _commit_file(tmp_path, "feat/test-producer", "feature.txt", "feature\n", "feature commit")
    queue_path = tmp_path.parent / f"{tmp_path.name}-shared-handoffs.jsonl"
    env = {"AZOTH_WORKTREE_HANDOFF_QUEUE_PATH": str(queue_path)}

    producer_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--record-producer-handoff",
        env=env,
    )
    assert producer_result.returncode == 0, producer_result.stderr

    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    select_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--next-ready-handoff",
        "--json",
        env=env,
    )
    assert select_result.returncode == 0, select_result.stderr
    selected = json.loads(select_result.stdout)
    assert selected["producer_branch"] == "feat/test-producer"

    merge_result = _run_git(tmp_path, "merge", "--no-ff", "feat/test-producer")
    assert merge_result.returncode == 0, merge_result.stderr

    integrated_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--mark-integrated",
        "feat/test-producer",
        env=env,
    )
    assert integrated_result.returncode == 0, integrated_result.stderr
    assert "marked producer handoff 'feat/test-producer' integrated" in integrated_result.stdout

    empty_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--next-ready-handoff",
        env=env,
    )
    assert empty_result.returncode == 1
    assert "no ready producer handoff found" in empty_result.stderr

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "worktree_sync.py"
sys.path.insert(0, str(ROOT / "scripts"))
import worktree_sync as worktree_sync_mod  # noqa: E402


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


def _queue_records(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _extract_sandbox_path(output: str) -> Path:
    match = re.search(r"Sandbox preserved at (.+)", output)
    assert match, output
    return Path(match.group(1).strip())


def _merge_commit_count(repo: Path, rev: str = "HEAD") -> int:
    return int(_run_git(repo, "rev-list", "--count", "--merges", rev).stdout.strip())


def _branch_exists(repo: Path, branch: str) -> bool:
    return _run_git(repo, "show-ref", "--verify", f"refs/heads/{branch}", check=False).returncode == 0


def _branch_tip(repo: Path, branch: str) -> str | None:
    result = _run_git(repo, "rev-parse", f"refs/heads/{branch}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


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


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
            handle.write("\n")


def _seed_shared_state(repo: Path) -> None:
    (repo / ".azoth" / "memory").mkdir(parents=True, exist_ok=True)
    _write_jsonl(
        repo / ".azoth" / "memory" / "episodes.jsonl",
        [{"id": "ep-001", "summary": "target", "timestamp": "2026-04-19T00:00:00Z"}],
    )
    _write_jsonl(
        repo / ".azoth" / "final-delivery-approvals.jsonl",
        [
            {
                "session_id": "2026-04-19-base",
                "gate": "final-delivery",
                "decision": "approved",
                "approved": True,
            }
        ],
    )
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "DECISIONS_INDEX.md").write_text(
        "| Decision |\n| D1 |\n| D2 |\n", encoding="utf-8"
    )
    (repo / "azoth.yaml").write_text(
        "\n".join(
            [
                "name: root-azoth",
                "decisions: 0",
                "memory:",
                "  episodes: 0",
                "  patterns: 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / ".azoth" / "memory" / "patterns.yaml").write_text("patterns: []\n", encoding="utf-8")


def _write_scope_gate(repo: Path, *, session_id: str, backlog_id: str, goal: str) -> None:
    (repo / ".azoth").mkdir(parents=True, exist_ok=True)
    (repo / ".azoth" / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "backlog_id": backlog_id,
                "goal": goal,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_governed_capsule(
    repo: Path,
    *,
    session_id: str,
    backlog_id: str,
    goal: str,
    allowlist_unit: str = "task",
    whole_initiative_approved: bool = False,
    backlog_ids: list[str] | None = None,
    roadmap_task_refs: list[str] | None = None,
    initiative_refs: list[str] | None = None,
) -> Path:
    allowlist = {
        "backlog_ids": sorted(set(backlog_ids or [])),
        "roadmap_task_refs": sorted(set(roadmap_task_refs or [])),
        "initiative_refs": sorted(set(initiative_refs or [])),
    }
    capsule = {
        "schema_version": 1,
        "artifact_kind": "governed-shared-state-approval",
        "session_id": session_id,
        "backlog_id": backlog_id,
        "goal": goal,
        "pipeline": "deliver-full",
        "approved_stage_id": "deliver_full_s2_architect",
        "actor_type": "human",
        "decision": "approved",
        "approved_at": "2026-04-19T16:00:00Z",
        "allowlist_unit": allowlist_unit,
        "whole_initiative_approved": whole_initiative_approved,
        "shared_state_allowlist": allowlist,
    }
    payload = worktree_sync_mod._scope_payload_from_capsule(capsule)
    capsule["scope_fingerprint"] = worktree_sync_mod._scope_fingerprint(payload)
    relpath = repo / ".azoth" / "governed-state-approvals" / f"{session_id}-{backlog_id}.yaml"
    relpath.parent.mkdir(parents=True, exist_ok=True)
    relpath.write_text(yaml.safe_dump(capsule, sort_keys=False), encoding="utf-8")
    return relpath


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


def test_worktree_sync_detached_head_auto_creates_branch_before_refresh(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    _commit_file(tmp_path, "feat/test-producer", "feature.txt", "feature\n", "feature commit")
    _commit_file(tmp_path, "phase/v0.2.0-p2", "target.txt", "target\n", "target update")
    producer_head = _run_git(tmp_path, "rev-parse", "feat/test-producer").stdout.strip()
    expected_branch = worktree_sync_mod._detached_branch_base(tmp_path, producer_head)

    _run_git(tmp_path, "checkout", "--detach", producer_head)
    result = _run_sync(tmp_path, "--target-branch", "phase/v0.2.0-p2")

    assert result.returncode == 0, result.stderr
    assert f"auto-created local branch '{expected_branch}'" in result.stdout
    assert _run_git(tmp_path, "branch", "--show-current").stdout.strip() == expected_branch
    assert _branch_exists(tmp_path, expected_branch)
    assert (
        _run_git(
            tmp_path, "merge-base", "--is-ancestor", "phase/v0.2.0-p2", "HEAD", check=False
        ).returncode
        == 0
    )


def test_worktree_sync_detached_head_reuses_existing_branch_for_same_commit(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    _commit_file(tmp_path, "feat/test-producer", "feature.txt", "feature\n", "feature commit")
    producer_head = _run_git(tmp_path, "rev-parse", "feat/test-producer").stdout.strip()
    expected_branch = worktree_sync_mod._detached_branch_base(tmp_path, producer_head)

    _run_git(tmp_path, "checkout", "--detach", producer_head)
    first_result = _run_sync(tmp_path, "--target-branch", "phase/v0.2.0-p2")
    assert first_result.returncode == 0, first_result.stderr
    assert _branch_exists(tmp_path, expected_branch)

    _run_git(tmp_path, "checkout", "--detach", producer_head)
    second_result = _run_sync(tmp_path, "--target-branch", "phase/v0.2.0-p2")

    assert second_result.returncode == 0, second_result.stderr
    assert f"existing local branch '{expected_branch}'" in second_result.stdout
    assert _run_git(tmp_path, "branch", "--show-current").stdout.strip() == expected_branch


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
    records = _queue_records(queue_path)
    assert len(records) == 1
    assert records[0]["event"] == "producer-ready"
    assert records[0]["handoff_id"]
    assert records[0]["producer_branch"] == "feat/test-producer"
    assert records[0]["target_branch"] == "phase/v0.2.0-p2"
    cleanup_candidates = records[0]["cleanup_candidates"]
    assert cleanup_candidates == [
        {
            "branch": "feat/test-producer",
            "expected_sha": records[0]["head_sha"],
            "reason": "queued-producer-branch",
        }
    ]


def test_record_producer_handoff_adds_integrable_sibling_cleanup_candidate(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _run_git(tmp_path, "checkout", "-b", "phase/v0.2.0-p2")
    _run_git(tmp_path, "checkout", "-b", "foo")
    _commit_file(tmp_path, "foo", "feature.txt", "base\n", "base producer commit")
    _run_git(tmp_path, "checkout", "-b", "foo-integrable")
    _commit_file(
        tmp_path,
        "foo-integrable",
        "feature.txt",
        "integrable\n",
        "integrable producer commit",
    )
    queue_path = tmp_path.parent / f"{tmp_path.name}-shared-handoffs.jsonl"

    result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--record-producer-handoff",
        env={"AZOTH_WORKTREE_HANDOFF_QUEUE_PATH": str(queue_path)},
    )

    assert result.returncode == 0, result.stderr
    record = _queue_records(queue_path)[0]
    assert record["producer_branch"] == "foo-integrable"
    assert record["cleanup_candidates"] == [
        {
            "branch": "foo-integrable",
            "expected_sha": record["head_sha"],
            "reason": "queued-producer-branch",
        },
        {
            "branch": "foo",
            "expected_sha": _branch_tip(tmp_path, "foo"),
            "reason": "superseded-by-integrable",
        },
    ]


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
    handoff_id = _queue_records(queue_path)[0]["handoff_id"]

    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    select_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--next-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--json",
        env=env,
    )
    assert select_result.returncode == 0, select_result.stderr
    selected = json.loads(select_result.stdout)
    assert selected["handoff_id"] == handoff_id
    assert selected["producer_branch"] == "feat/test-producer"

    merge_result = _run_git(tmp_path, "merge", "--no-ff", "feat/test-producer")
    assert merge_result.returncode == 0, merge_result.stderr

    integrated_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--mark-integrated",
        "--handoff-id",
        handoff_id,
        env=env,
    )
    assert integrated_result.returncode == 0, integrated_result.stderr
    assert "marked producer handoff 'feat/test-producer' integrated" in integrated_result.stdout

    empty_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--next-ready-handoff",
        "--handoff-id",
        handoff_id,
        env=env,
    )
    assert empty_result.returncode == 1
    assert "no ready producer handoff found" in empty_result.stderr


def test_worktree_sync_integrate_ready_handoff_promotes_verified_merge_from_queued_head(
    tmp_path: Path,
) -> None:
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
    queued = _queue_records(queue_path)[0]
    handoff_id = str(queued["handoff_id"])

    _commit_file(tmp_path, "feat/test-producer", "drift.txt", "drift\n", "drift commit")

    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    verify_command = (
        f'{sys.executable} -c "from pathlib import Path; '
        "assert Path('feature.txt').read_text() == 'feature\\\\n'; "
        "assert not Path('drift.txt').exists()\""
    )
    integrate_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--verify-command",
        verify_command,
        "--json",
        env=env,
    )
    assert integrate_result.returncode == 0, integrate_result.stderr
    payload = json.loads(integrate_result.stdout)
    assert payload["handoff_id"] == handoff_id
    assert payload["producer_branch"] == "feat/test-producer"
    assert payload["queued_head_sha"] == queued["head_sha"]
    assert payload["verification_count"] == 1
    assert payload["cleanup_summary"]["removed_branches"] == []
    assert payload["cleanup_summary"]["removed_worktrees"] == []
    assert payload["cleanup_summary"]["skipped_cleanup"] == [
        {
            "branch": "feat/test-producer",
            "reason": "tip-moved",
        }
    ]
    assert not Path(payload["sandbox_path"]).exists()
    assert (tmp_path / "feature.txt").read_text(encoding="utf-8") == "feature\n"
    assert not (tmp_path / "drift.txt").exists()
    assert _branch_exists(tmp_path, "feat/test-producer")
    assert (
        _run_git(
            tmp_path,
            "merge-base",
            "--is-ancestor",
            str(queued["head_sha"]),
            "phase/v0.2.0-p2",
            check=False,
        ).returncode
        == 0
    )

    empty_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--next-ready-handoff",
        "--handoff-id",
        handoff_id,
        env=env,
    )
    assert empty_result.returncode == 1
    assert "no ready producer handoff found" in empty_result.stderr


def test_integrate_ready_handoff_deletes_queued_branch_when_tip_still_matches(
    tmp_path: Path,
) -> None:
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
    handoff_id = str(_queue_records(queue_path)[0]["handoff_id"])

    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    verify_command = (
        f'{sys.executable} -c "from pathlib import Path; '
        "assert Path('feature.txt').read_text() == 'feature\\\\n'\""
    )
    integrate_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--verify-command",
        verify_command,
        "--json",
        env=env,
    )

    assert integrate_result.returncode == 0, integrate_result.stderr
    payload = json.loads(integrate_result.stdout)
    assert payload["cleanup_summary"]["removed_branches"] == ["feat/test-producer"]
    assert payload["cleanup_summary"]["removed_worktrees"] == []
    assert payload["cleanup_summary"]["skipped_cleanup"] == []
    assert not _branch_exists(tmp_path, "feat/test-producer")


def test_worktree_sync_integrate_ready_handoff_fails_closed_before_promotion(
    tmp_path: Path,
) -> None:
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
    handoff_id = str(_queue_records(queue_path)[0]["handoff_id"])

    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    head_before = _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    fail_command = f'{sys.executable} -c "import sys; sys.exit(1)"'
    integrate_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--verify-command",
        fail_command,
        env=env,
    )
    assert integrate_result.returncode == 1
    assert "verification failed" in integrate_result.stderr
    assert "Sandbox preserved at" in integrate_result.stderr
    assert _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip() == head_before
    sandbox_path = _extract_sandbox_path(integrate_result.stderr)
    assert sandbox_path.exists()

    queued_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--next-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--json",
        env=env,
    )
    assert queued_result.returncode == 0, queued_result.stderr
    assert json.loads(queued_result.stdout)["producer_branch"] == "feat/test-producer"
    _run_git(tmp_path, "worktree", "remove", "--force", str(sandbox_path))


def test_worktree_sync_integrate_ready_handoff_replay_repairs_queue_without_second_merge(
    tmp_path: Path,
) -> None:
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
    handoff_id = str(_queue_records(queue_path)[0]["handoff_id"])

    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    verify_command = f"{sys.executable} -c \"from pathlib import Path; assert Path('feature.txt').read_text() == 'feature\\\\n'\""
    queue_path.chmod(0o400)
    try:
        first_result = _run_sync(
            tmp_path,
            "--target-branch",
            "phase/v0.2.0-p2",
            "--integrate-ready-handoff",
            "--handoff-id",
            handoff_id,
            "--verify-command",
            verify_command,
            env=env,
        )
    finally:
        queue_path.chmod(0o600)

    assert first_result.returncode == 1
    assert "promoted the tested merge but could not update the handoff queue" in first_result.stderr
    failed_sandbox = _extract_sandbox_path(first_result.stderr)
    assert failed_sandbox.exists()
    promoted_head = _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    assert _merge_commit_count(tmp_path) == 1

    replay_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--verify-command",
        verify_command,
        "--json",
        env=env,
    )
    assert replay_result.returncode == 0, replay_result.stderr
    replay_payload = json.loads(replay_result.stdout)
    assert replay_payload["handoff_id"] == handoff_id
    assert replay_payload["repair_only"] is True
    assert replay_payload["cleanup_summary"]["removed_branches"] == ["feat/test-producer"]
    assert _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip() == promoted_head
    assert _merge_commit_count(tmp_path) == 1
    assert not _branch_exists(tmp_path, "feat/test-producer")

    records = _queue_records(queue_path)
    assert any(
        record["event"] == "integrated" and record["handoff_id"] == handoff_id for record in records
    )
    empty_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--next-ready-handoff",
        "--handoff-id",
        handoff_id,
        env=env,
    )
    assert empty_result.returncode == 1
    _run_git(tmp_path, "worktree", "remove", "--force", str(failed_sandbox))


def test_worktree_sync_mark_integrated_rejects_ambiguous_unresolved_branch_match(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    _setup_phase_and_feature(tmp_path)
    queue_path = tmp_path.parent / f"{tmp_path.name}-shared-handoffs.jsonl"
    env = {"AZOTH_WORKTREE_HANDOFF_QUEUE_PATH": str(queue_path)}

    _commit_file(tmp_path, "feat/test-producer", "feature.txt", "v1\n", "feature commit 1")
    first_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--record-producer-handoff",
        env=env,
    )
    assert first_result.returncode == 0, first_result.stderr

    _commit_file(tmp_path, "feat/test-producer", "feature.txt", "v2\n", "feature commit 2")
    second_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--record-producer-handoff",
        env=env,
    )
    assert second_result.returncode == 0, second_result.stderr
    records = _queue_records(queue_path)
    assert len(records) == 2

    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    mark_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--mark-integrated",
        "feat/test-producer",
        env=env,
    )

    assert mark_result.returncode == 1
    assert "ambiguous unresolved handoff match" in mark_result.stderr
    for record in records:
        assert record["handoff_id"] in mark_result.stderr
        assert record["head_sha"] in mark_result.stderr


def test_integrate_ready_handoff_removes_clean_attached_producer_worktree(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _run_git(tmp_path, "checkout", "-b", "phase/v0.2.0-p2")
    producer_worktree = tmp_path.parent / f"{tmp_path.name}-producer-worktree"
    _run_git(tmp_path, "worktree", "add", "-b", "feat/test-producer", str(producer_worktree))
    (producer_worktree / "feature.txt").write_text("feature\n", encoding="utf-8")
    _run_git(producer_worktree, "add", "feature.txt")
    _run_git(producer_worktree, "commit", "-m", "feature commit")
    queue_path = tmp_path.parent / f"{tmp_path.name}-shared-handoffs.jsonl"
    env = {"AZOTH_WORKTREE_HANDOFF_QUEUE_PATH": str(queue_path)}

    producer_result = _run_sync(
        producer_worktree,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--record-producer-handoff",
        env=env,
    )
    assert producer_result.returncode == 0, producer_result.stderr
    handoff_id = str(_queue_records(queue_path)[0]["handoff_id"])

    verify_command = (
        f'{sys.executable} -c "from pathlib import Path; '
        "assert Path('feature.txt').read_text() == 'feature\\\\n'\""
    )
    integrate_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--verify-command",
        verify_command,
        "--json",
        env=env,
    )

    assert integrate_result.returncode == 0, integrate_result.stderr
    payload = json.loads(integrate_result.stdout)
    assert payload["cleanup_summary"]["removed_branches"] == ["feat/test-producer"]
    assert payload["cleanup_summary"]["removed_worktrees"] == [str(producer_worktree.resolve())]
    assert payload["cleanup_summary"]["skipped_cleanup"] == []
    assert not producer_worktree.exists()
    assert not _branch_exists(tmp_path, "feat/test-producer")


def test_integrate_ready_handoff_skips_dirty_attached_producer_worktree(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _run_git(tmp_path, "checkout", "-b", "phase/v0.2.0-p2")
    producer_worktree = tmp_path.parent / f"{tmp_path.name}-producer-worktree"
    _run_git(tmp_path, "worktree", "add", "-b", "feat/test-producer", str(producer_worktree))
    (producer_worktree / "feature.txt").write_text("feature\n", encoding="utf-8")
    _run_git(producer_worktree, "add", "feature.txt")
    _run_git(producer_worktree, "commit", "-m", "feature commit")
    queue_path = tmp_path.parent / f"{tmp_path.name}-shared-handoffs.jsonl"
    env = {"AZOTH_WORKTREE_HANDOFF_QUEUE_PATH": str(queue_path)}

    producer_result = _run_sync(
        producer_worktree,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--record-producer-handoff",
        env=env,
    )
    assert producer_result.returncode == 0, producer_result.stderr
    handoff_id = str(_queue_records(queue_path)[0]["handoff_id"])
    (producer_worktree / "local-dirty.txt").write_text("dirty\n", encoding="utf-8")

    verify_command = (
        f'{sys.executable} -c "from pathlib import Path; '
        "assert Path('feature.txt').read_text() == 'feature\\\\n'\""
    )
    integrate_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--verify-command",
        verify_command,
        "--json",
        env=env,
    )

    assert integrate_result.returncode == 0, integrate_result.stderr
    payload = json.loads(integrate_result.stdout)
    assert payload["cleanup_summary"]["removed_branches"] == []
    assert payload["cleanup_summary"]["removed_worktrees"] == []
    assert payload["cleanup_summary"]["skipped_cleanup"] == [
        {
            "branch": "feat/test-producer",
            "reason": "attached-worktree-dirty",
            "worktree_path": str(producer_worktree.resolve()),
        }
    ]
    assert producer_worktree.exists()
    assert _branch_exists(tmp_path, "feat/test-producer")


def test_integrate_ready_handoff_skips_cleanup_when_branch_tip_moved(tmp_path: Path) -> None:
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
    handoff_id = str(_queue_records(queue_path)[0]["handoff_id"])
    _commit_file(tmp_path, "feat/test-producer", "after.txt", "after\n", "post handoff drift")
    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")

    verify_command = (
        f'{sys.executable} -c "from pathlib import Path; '
        "assert Path('feature.txt').read_text() == 'feature\\\\n'; "
        "assert not Path('after.txt').exists()\""
    )
    integrate_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--verify-command",
        verify_command,
        "--json",
        env=env,
    )

    assert integrate_result.returncode == 0, integrate_result.stderr
    payload = json.loads(integrate_result.stdout)
    assert payload["cleanup_summary"]["removed_branches"] == []
    assert payload["cleanup_summary"]["removed_worktrees"] == []
    assert payload["cleanup_summary"]["skipped_cleanup"] == [
        {
            "branch": "feat/test-producer",
            "reason": "tip-moved",
        }
    ]
    assert _branch_exists(tmp_path, "feat/test-producer")


def test_record_producer_handoff_includes_governed_metadata_when_present(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _seed_shared_state(tmp_path)
    _run_git(tmp_path, "add", "azoth.yaml", "docs/DECISIONS_INDEX.md", ".azoth")
    _run_git(tmp_path, "commit", "-m", "seed shared state")
    _setup_phase_and_feature(tmp_path)
    session_id = "2026-04-19-t-013"
    backlog_id = "T-013"
    goal = "T-013: Deterministic reconciliation policy"
    _write_scope_gate(tmp_path, session_id=session_id, backlog_id=backlog_id, goal=goal)
    capsule_path = _write_governed_capsule(
        tmp_path,
        session_id=session_id,
        backlog_id=backlog_id,
        goal=goal,
        backlog_ids=["T-013"],
        roadmap_task_refs=["T-013"],
    )
    _run_git(
        tmp_path,
        "add",
        ".azoth/scope-gate.json",
        str(capsule_path.relative_to(tmp_path)),
    )
    _run_git(tmp_path, "commit", "-m", "add governed approval capsule")
    queue_path = tmp_path.parent / f"{tmp_path.name}-shared-handoffs.jsonl"

    result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--record-producer-handoff",
        env={"AZOTH_WORKTREE_HANDOFF_QUEUE_PATH": str(queue_path)},
    )

    assert result.returncode == 0, result.stderr
    record = _queue_records(queue_path)[0]
    assert record["approval_evidence_path"] == (
        f".azoth/governed-state-approvals/{session_id}-{backlog_id}.yaml"
    )
    assert record["allowlist_unit"] == "task"
    assert record["scope_session_id"] == session_id
    assert record["scope_backlog_id"] == backlog_id
    assert record["scope_goal"] == goal
    assert record["shared_state_allowlist"]["backlog_ids"] == ["T-013"]
    assert record["shared_state_allowlist"]["roadmap_task_refs"] == ["T-013"]
    expected_sha = worktree_sync_mod._sha256_hex(capsule_path.read_bytes())
    assert record["approval_evidence_sha256"] == expected_sha
    assert record["scope_fingerprint"]


def test_integrate_ready_handoff_runs_reconcile_before_verify_commands(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _seed_shared_state(tmp_path)
    _run_git(tmp_path, "add", "azoth.yaml", "docs/DECISIONS_INDEX.md", ".azoth")
    _run_git(tmp_path, "commit", "-m", "seed shared state")
    _setup_phase_and_feature(tmp_path)
    _write_jsonl(
        tmp_path / ".azoth" / "memory" / "episodes.jsonl",
        [
            {"id": "ep-001", "summary": "target", "timestamp": "2026-04-19T00:00:00Z"},
            {"id": "ep-002", "summary": "producer", "timestamp": "2026-04-19T01:00:00Z"},
        ],
    )
    _write_jsonl(
        tmp_path / ".azoth" / "final-delivery-approvals.jsonl",
        [
            {
                "session_id": "2026-04-19-base",
                "gate": "final-delivery",
                "decision": "approved",
                "approved": True,
            },
            {
                "session_id": "2026-04-19-base",
                "gate": "final-delivery",
                "decision": "approved",
                "approved": True,
            },
            {
                "session_id": "2026-04-19-feature",
                "gate": "final-delivery",
                "decision": "approved",
                "approved": True,
            },
        ],
    )
    _run_git(
        tmp_path,
        "add",
        ".azoth/memory/episodes.jsonl",
        ".azoth/final-delivery-approvals.jsonl",
    )
    _run_git(tmp_path, "commit", "-m", "update append-only shared state")
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
    handoff_id = str(_queue_records(queue_path)[0]["handoff_id"])

    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    verify_command = (
        f'{sys.executable} -c "import json, pathlib; '
        "episodes = [json.loads(line) for line in pathlib.Path('.azoth/memory/episodes.jsonl').read_text().splitlines() if line.strip()]; "
        "approvals = [json.loads(line) for line in pathlib.Path('.azoth/final-delivery-approvals.jsonl').read_text().splitlines() if line.strip()]; "
        "assert len(episodes) == 2; "
        "assert {item['id'] for item in episodes} == {'ep-001', 'ep-002'}; "
        "assert len(approvals) == 2; "
        "manifest = pathlib.Path('azoth.yaml').read_text(); "
        "assert 'decisions: 3' in manifest; "
        "assert '  episodes: 2' in manifest\""
    )
    integrate_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--verify-command",
        verify_command,
        "--json",
        env=env,
    )

    assert integrate_result.returncode == 0, integrate_result.stderr
    payload = json.loads(integrate_result.stdout)
    assert payload["verification_count"] == 1
    assert "ep-002" in (tmp_path / ".azoth" / "memory" / "episodes.jsonl").read_text(
        encoding="utf-8"
    )
    approvals = _queue_records(tmp_path / ".azoth" / "final-delivery-approvals.jsonl")
    assert len(approvals) == 2
    assert "decisions: 3" in (tmp_path / "azoth.yaml").read_text(encoding="utf-8")
    assert "  episodes: 2" in (tmp_path / "azoth.yaml").read_text(encoding="utf-8")


def test_integrate_ready_handoff_fails_closed_on_handoffs_approval_path(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    backlog = (
        "schema_version: 1\nitems:\n"
        "- id: T-013\n  title: Allowed task\n  target_layer: M1\n  delivery_pipeline: governed\n  status: pending\n"
    )
    (tmp_path / ".azoth" / "backlog.yaml").write_text(backlog, encoding="utf-8")
    _run_git(tmp_path, "add", ".azoth/backlog.yaml")
    _run_git(tmp_path, "commit", "-m", "add backlog")
    _setup_phase_and_feature(tmp_path)
    _commit_file(
        tmp_path,
        "feat/test-producer",
        ".azoth/backlog.yaml",
        "schema_version: 1\nitems:\n- id: T-013\n  title: Allowed task\n  target_layer: M1\n  delivery_pipeline: governed\n  status: active\n",
        "change backlog",
    )
    queue_path = tmp_path.parent / f"{tmp_path.name}-shared-handoffs.jsonl"
    producer_head = _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    handoff_id = worktree_sync_mod._handoff_id(
        "phase/v0.2.0-p2", "feat/test-producer", producer_head
    )
    _write_jsonl(
        queue_path,
        [
            {
                "event": "producer-ready",
                "recorded_at": "2026-04-19T16:00:00Z",
                "producer_branch": "feat/test-producer",
                "target_branch": "phase/v0.2.0-p2",
                "head_sha": producer_head,
                "handoff_id": handoff_id,
                "scope_session_id": "2026-04-19-t-013",
                "scope_backlog_id": "T-013",
                "scope_goal": "T-013: Deterministic reconciliation policy",
                "scope_fingerprint": "bad",
                "approval_evidence_path": ".azoth/handoffs/not-valid.yaml",
                "approval_evidence_sha256": "bad",
                "allowlist_unit": "task",
                "whole_initiative_approved": False,
                "shared_state_allowlist": {"backlog_ids": ["T-013"], "roadmap_task_refs": []},
            }
        ],
    )
    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    head_before = _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    env = {"AZOTH_WORKTREE_HANDOFF_QUEUE_PATH": str(queue_path)}

    result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        env=env,
    )

    assert result.returncode == 1
    assert (
        "approval_evidence_path must point to a tracked governed approval capsule" in result.stderr
    )
    assert "Sandbox preserved at" in result.stderr
    assert _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip() == head_before
    queued_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--next-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--json",
        env=env,
    )
    assert queued_result.returncode == 0, queued_result.stderr


def test_merge_episode_records_dedupes_exact_rows_but_keeps_legacy_id_collisions() -> None:
    target = [
        {"id": "ep-112", "session_id": "capture", "summary": "first"},
        {"id": "ep-112", "session_id": "closeout", "summary": "second"},
    ]
    producer = [
        {"id": "ep-112", "session_id": "capture", "summary": "first"},
        {"id": "ep-130", "session_id": "new", "summary": "third"},
    ]

    merged = worktree_sync_mod._merge_episode_records(target, producer)

    assert merged == [
        {"id": "ep-112", "session_id": "capture", "summary": "first"},
        {"id": "ep-112", "session_id": "closeout", "summary": "second"},
        {"id": "ep-130", "session_id": "new", "summary": "third"},
    ]


def test_merge_episode_records_keeps_verbatim_payload_on_new_rows() -> None:
    target = [
        {
            "id": "ep-112",
            "session_id": "capture",
            "summary": "first",
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "first"},
            },
        }
    ]
    producer = [
        {
            "id": "ep-130",
            "session_id": "new",
            "summary": "third",
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "third"},
            },
        }
    ]

    merged = worktree_sync_mod._merge_episode_records(target, producer)

    assert merged == [
        {
            "id": "ep-112",
            "session_id": "capture",
            "summary": "first",
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "first"},
            },
        },
        {
            "id": "ep-130",
            "session_id": "new",
            "summary": "third",
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "third"},
            },
        },
    ]


def test_merge_episode_records_reconciles_same_id_verbatim_rewrite_from_producer() -> None:
    target = [
        {
            "id": "ep-112",
            "session_id": "capture",
            "summary": "first",
            "reinforcement_count": 0,
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "first"},
            },
        }
    ]
    producer = [
        {
            "id": "ep-112",
            "session_id": "capture",
            "summary": "first",
            "reinforcement_count": 1,
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "first"},
                "reinforced_by_sessions": ["sess-002"],
                "last_reinforced_session": "sess-002",
                "last_reinforced_source": "closeout",
            },
        }
    ]

    merged = worktree_sync_mod._merge_episode_records(target, producer)

    assert merged == producer


def test_merge_episode_records_rejects_non_reinforcement_same_id_rewrite() -> None:
    target = [
        {
            "id": "ep-112",
            "session_id": "capture",
            "summary": "first",
            "reinforcement_count": 0,
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "first"},
            },
        }
    ]
    producer = [
        {
            "id": "ep-112",
            "session_id": "capture",
            "summary": "rewritten",
            "reinforcement_count": 0,
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "first"},
            },
        }
    ]

    with pytest.raises(ValueError, match="non-audited rewrite"):
        worktree_sync_mod._merge_episode_records(target, producer)


def test_merge_episode_records_rejects_legacy_same_id_rewrite() -> None:
    target = [{"id": "ep-112", "session_id": "capture", "summary": "first"}]
    producer = [{"id": "ep-112", "session_id": "capture", "summary": "rewritten"}]

    with pytest.raises(ValueError, match="ambiguous same-id rewrite"):
        worktree_sync_mod._merge_episode_records(target, producer)


def test_merge_episode_records_rejects_duplicate_verbatim_backed_target_identity() -> None:
    target = [
        {
            "id": "ep-112",
            "session_id": "capture-a",
            "summary": "first",
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "first"},
            },
        },
        {
            "id": "ep-112",
            "session_id": "capture-b",
            "summary": "first",
            "context": {
                "verbatim_source": "scope-gate.json",
                "verbatim_payload": {"goal": "first"},
            },
        },
    ]

    with pytest.raises(ValueError, match="duplicate verbatim-backed"):
        worktree_sync_mod._merge_episode_records(target, [])


def test_merge_episode_records_rejects_duplicate_new_producer_episode_id() -> None:
    producer = [
        {"id": "ep-112", "session_id": "producer-a", "summary": "first"},
        {"id": "ep-112", "session_id": "producer-b", "summary": "second"},
    ]

    with pytest.raises(ValueError, match="ambiguous same-id rewrite"):
        worktree_sync_mod._merge_episode_records([], producer)


def test_merge_allowlisted_items_rejects_duplicate_producer_rows() -> None:
    producer = [
        {"id": "T-013", "status": "active", "title": "Allowed task"},
        {"id": "T-013", "status": "active", "title": "Allowed task"},
    ]

    with pytest.raises(ValueError, match="duplicate allowlisted producer row"):
        worktree_sync_mod._merge_allowlisted_items(
            [],
            producer,
            allowed_ids={"T-013"},
            protected_fields=("title",),
            status_field="status",
        )


def test_merge_allowlisted_items_accepts_existing_target_row_update() -> None:
    target = [{"id": "BL-069", "status": "pending", "title": "Allowed task"}]
    producer = [{"id": "BL-069", "status": "complete", "title": "Allowed task"}]

    merged = worktree_sync_mod._merge_allowlisted_items(
        target,
        producer,
        allowed_ids={"BL-069"},
        protected_fields=("title",),
        status_field="status",
    )

    assert merged == producer


def test_integrate_ready_handoff_fails_closed_on_non_allowlisted_backlog_change(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    backlog = "\n".join(
        [
            "schema_version: 1",
            "items:",
            "- id: T-013",
            "  title: Allowed task",
            "  target_layer: M1",
            "  delivery_pipeline: governed",
            "  status: pending",
            "- id: T-099",
            "  title: Not allowlisted",
            "  target_layer: M1",
            "  delivery_pipeline: governed",
            "  status: pending",
            "",
        ]
    )
    (tmp_path / ".azoth" / "backlog.yaml").write_text(backlog, encoding="utf-8")
    _run_git(tmp_path, "add", ".azoth/backlog.yaml")
    _run_git(tmp_path, "commit", "-m", "seed backlog")
    _setup_phase_and_feature(tmp_path)
    session_id = "2026-04-19-t-013"
    backlog_id = "T-013"
    goal = "T-013: Deterministic reconciliation policy"
    _write_scope_gate(tmp_path, session_id=session_id, backlog_id=backlog_id, goal=goal)
    capsule_path = _write_governed_capsule(
        tmp_path,
        session_id=session_id,
        backlog_id=backlog_id,
        goal=goal,
        backlog_ids=["T-013"],
        roadmap_task_refs=[],
    )
    (tmp_path / ".azoth" / "backlog.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "items:",
                "- id: T-013",
                "  title: Allowed task",
                "  target_layer: M1",
                "  delivery_pipeline: governed",
                "  status: pending",
                "- id: T-099",
                "  title: Not allowlisted",
                "  target_layer: M1",
                "  delivery_pipeline: governed",
                "  status: active",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _run_git(
        tmp_path,
        "add",
        ".azoth/backlog.yaml",
        ".azoth/scope-gate.json",
        str(capsule_path.relative_to(tmp_path)),
    )
    _run_git(tmp_path, "commit", "-m", "governed backlog change")
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
    handoff_id = str(_queue_records(queue_path)[0]["handoff_id"])

    _run_git(tmp_path, "checkout", "phase/v0.2.0-p2")
    head_before = _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--integrate-ready-handoff",
        "--handoff-id",
        handoff_id,
        env=env,
    )

    assert result.returncode == 1
    assert "non-allowlisted rows changed: T-099" in result.stderr
    assert _run_git(tmp_path, "rev-parse", "HEAD").stdout.strip() == head_before
    queued_result = _run_sync(
        tmp_path,
        "--target-branch",
        "phase/v0.2.0-p2",
        "--next-ready-handoff",
        "--handoff-id",
        handoff_id,
        "--json",
        env=env,
    )
    assert queued_result.returncode == 0, queued_result.stderr


def test_worktree_sync_docs_describe_governed_reconcile_substep() -> None:
    command_text = (ROOT / ".claude" / "commands" / "worktree-sync.md").read_text(encoding="utf-8")
    playbook_text = (ROOT / "docs" / "playbook" / "05-parallel-sessions.md").read_text(
        encoding="utf-8"
    )
    assert "pre-approved governed reconciliation substep" in command_text
    assert "auto-materialize a local branch named `codex/wt-<id>-<shortsha>`" in command_text
    assert "remote branch cleanup remains out of scope" in command_text
    assert "allowlist-gated" in playbook_text
    assert "Detached producer worktrees auto-materialize a local branch first" in playbook_text
    assert "automatic cleanup after a successful integrate run also covers safe local producer branch pruning" in playbook_text

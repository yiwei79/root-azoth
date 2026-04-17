"""Tests for scripts/do_closeout.py governed closeout enforcement."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import do_closeout  # noqa: E402


def _future() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def _build_repo(
    tmp_path: Path,
    *,
    delivery_pipeline: str = "governed",
    session_id: str = "sess-123",
    backlog_id: str = "BL-123",
    include_session_state: bool = False,
    include_sessions_registry: bool = True,
    include_resumable_run: bool = False,
) -> Path:
    (tmp_path / "azoth.yaml").write_text(
        "version: 0.1.1.29\nphase: 1\nmemory:\n  episodes: 0\n", encoding="utf-8"
    )
    azoth_dir = tmp_path / ".azoth"
    (azoth_dir / "memory").mkdir(parents=True)
    (azoth_dir / "memory" / "episodes.jsonl").write_text("", encoding="utf-8")
    (azoth_dir / "session-orientation.txt").write_text("cached\n", encoding="utf-8")
    (azoth_dir / "roadmap.yaml").write_text(
        "\n".join(
            [
                "active_version: v0.2.0-p1",
                "versions:",
                "  - id: v0.2.0-p1",
                "    status: active",
                "    current_patch: 29",
                "    tasks:",
                f"      - id: {backlog_id}",
                '        title: "Governed closeout"',
                "        decision_ref: [D50]",
                "    completed_tasks:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    scope_gate = {
        "approved": True,
        "expires_at": _future(),
        "session_id": session_id,
        "goal": f"{backlog_id}: Governed closeout",
        "backlog_id": backlog_id,
        "delivery_pipeline": delivery_pipeline,
    }
    (azoth_dir / "scope-gate.json").write_text(json.dumps(scope_gate), encoding="utf-8")

    (azoth_dir / "backlog.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "items:",
                f'  - id: "{backlog_id}"',
                "    status: active",
                '    title: "Governed closeout"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    run_ledger: dict[str, object] = {
        "schema_version": 1,
        "runs": [],
        "write_claim": {
            "session_id": session_id,
            "expires_at": _future(),
            "acquired_at": "2026-04-15T00:00:00+00:00",
        },
    }
    if include_sessions_registry:
        session_entry: dict[str, object] = {
            "session_id": session_id,
            "backlog_id": backlog_id,
            "goal": f"{backlog_id}: Governed closeout",
            "status": "active",
            "ide": "codex",
            "next_action": "Continue current scope",
            "updated_at": "2026-04-15T00:00:00+00:00",
        }
        if include_resumable_run:
            session_entry["active_run_id"] = "run-123"
            run_ledger["runs"] = [
                {
                    "run_id": "run-123",
                    "session_id": session_id,
                    "backlog_id": backlog_id,
                    "ide": "codex",
                    "mode": "auto",
                    "goal": f"{backlog_id}: Governed closeout",
                    "status": "paused",
                    "created_at": "2026-04-15T00:00:00+00:00",
                    "updated_at": "2026-04-15T00:00:00+00:00",
                    "next_action": "Resume wave 2 review.",
                    "stages_completed": ["planner"],
                    "active_stage_id": "architect_review",
                    "pending_stage_ids": ["builder_apply", "reviewer_gate"],
                    "pause_reason": "human-gate",
                    "waves": [],
                    "branches": [],
                }
            ]
        run_ledger["sessions"] = [session_entry]
    (azoth_dir / "run-ledger.local.yaml").write_text(
        yaml.safe_dump(run_ledger, sort_keys=False),
        encoding="utf-8",
    )
    if include_session_state:
        session_state: dict[str, object] = {
            "session_id": session_id,
            "state": "active",
            "last_ide": "codex",
            "timestamp": "2026-04-15T00:00:00+00:00",
            "active_task": "In progress",
            "active_files": [],
            "pending_decisions": [],
            "approved_scope": f"{backlog_id}: Governed closeout",
            "next_action": "Continue current scope",
        }
        if include_resumable_run:
            session_state.update(
                {
                    "pipeline": "auto",
                    "pipeline_position": 2,
                    "current_stage_id": "architect_review",
                    "completed_stages": ["planner"],
                    "pending_stages": ["builder_apply", "reviewer_gate"],
                    "pause_reason": "human-gate",
                    "active_run_id": "run-123",
                }
            )
        (azoth_dir / "session-state.md").write_text(
            yaml.safe_dump(session_state, sort_keys=False),
            encoding="utf-8",
        )
    return tmp_path


def _write_approvals(repo_root: Path, *records: dict[str, object]) -> str:
    text = "".join(json.dumps(record) + "\n" for record in records)
    (repo_root / ".azoth" / "final-delivery-approvals.jsonl").write_text(text, encoding="utf-8")
    return text


def test_governed_closeout_requires_approval_evidence_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path)
    version_bump_calls: list[tuple[list[str], Path]] = []

    def _fake_run(cmd: list[str], cwd: Path, check: bool) -> None:
        version_bump_calls.append((cmd, cwd))

    monkeypatch.setattr(do_closeout.subprocess, "run", _fake_run)

    with pytest.raises(do_closeout.ApprovalEvidenceError):
        do_closeout.run_closeout(repo_root)
    assert version_bump_calls == []
    assert (repo_root / ".azoth" / "memory" / "episodes.jsonl").read_text(encoding="utf-8") == ""
    assert (
        json.loads((repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8"))[
            "approved"
        ]
        is True
    )
    assert "status: active" in (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    assert "write_claim:" in (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(
        encoding="utf-8"
    )
    assert (repo_root / ".azoth" / "session-orientation.txt").exists()


def test_governed_closeout_rejects_malformed_approval_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path)
    (repo_root / ".azoth" / "final-delivery-approvals.jsonl").write_text(
        '{"session_id":"sess-123","gate":"final-delivery"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)

    with pytest.raises(do_closeout.ApprovalEvidenceError, match="Invalid JSON"):
        do_closeout.run_closeout(repo_root)

    assert (repo_root / ".azoth" / "memory" / "episodes.jsonl").read_text(encoding="utf-8") == ""


@pytest.mark.parametrize(
    ("records", "expected_message"),
    [
        (
            [
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "agent",
                    "approved": True,
                }
            ],
            "actor_type=human",
        ),
        (
            [
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": True,
                },
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": False,
                    "decision": "denied",
                },
            ],
            "actor_type=human and approved=true",
        ),
        (
            [
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": True,
                },
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "decision": "approved",
                },
            ],
            "actor_type=human and approved=true",
        ),
        (
            [
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": True,
                },
                {
                    "session_id": "sess-123",
                    "gate": "final-delivery",
                    "actor_type": "human",
                    "approved": False,
                    "decision": "approved",
                },
            ],
            "actor_type=human and approved=true",
        ),
    ],
)
def test_governed_closeout_fails_closed_on_invalid_latest_approval_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    records: list[dict[str, object]],
    expected_message: str,
) -> None:
    repo_root = _build_repo(tmp_path)
    _write_approvals(repo_root, *records)
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)

    with pytest.raises(do_closeout.ApprovalEvidenceError, match=expected_message):
        do_closeout.run_closeout(repo_root)

    assert (repo_root / ".azoth" / "memory" / "episodes.jsonl").read_text(encoding="utf-8") == ""


def test_governed_closeout_accepts_matching_human_approval_without_consuming_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path, include_session_state=True)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    approvals_before = _write_approvals(
        repo_root,
        {
            "session_id": "other-session",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
        },
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    version_bump_calls: list[tuple[list[str], Path, bool]] = []

    def _fake_run(cmd: list[str], cwd: Path, check: bool) -> None:
        version_bump_calls.append((cmd, cwd, check))

    monkeypatch.setattr(do_closeout.subprocess, "run", _fake_run)
    monkeypatch.setenv("HOME", str(fake_home))
    do_closeout.run_closeout(repo_root)

    episode_lines = (
        (repo_root / ".azoth" / "memory" / "episodes.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )
    assert len(episode_lines) == 1
    episode = json.loads(episode_lines[0])
    assert episode["session_id"] == "sess-123"
    assert episode["goal"] == "BL-123: Governed closeout"
    assert ".azoth/backlog.yaml" in episode["context"]["files_changed"]
    assert ".azoth/roadmap.yaml" in episode["context"]["files_changed"]
    assert ".azoth/run-ledger.local.yaml" in episode["context"]["files_changed"]
    assert ".azoth/bootloader-state.md" in episode["context"]["files_changed"]
    assert ".azoth/session-state.md" in episode["context"]["files_changed"]

    scope = json.loads((repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8"))
    assert scope["approved"] is False
    assert "closed_at" in scope
    backlog_text = (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    assert "status: active" not in backlog_text
    assert "status: complete" in backlog_text
    assert "completed_date:" in backlog_text
    roadmap_text = (repo_root / ".azoth" / "roadmap.yaml").read_text(encoding="utf-8")
    assert "      - id: BL-123\n" not in roadmap_text
    assert '{id: BL-123, title: "Governed closeout", completed_date:' in roadmap_text
    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    assert "write_claim" not in ledger
    session_entry = ledger["sessions"][0]
    assert session_entry["status"] == "closed"
    assert session_entry["next_action"] == do_closeout.default_next_action()
    assert "updated_at" in session_entry
    assert "closed_at" in session_entry
    assert "active_run_id" not in session_entry
    assert (repo_root / ".azoth" / "final-delivery-approvals.jsonl").read_text(
        encoding="utf-8"
    ) == approvals_before
    assert not (repo_root / ".azoth" / "session-orientation.txt").exists()
    session_state = (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    assert "state: closed" in session_state
    assert "last_ide: codex" in session_state
    assert f"next_action: {do_closeout.default_next_action()}" in session_state
    bootloader_state = (repo_root / ".azoth" / "bootloader-state.md").read_text(encoding="utf-8")
    assert "sess-123" in bootloader_state
    assert "ep-001" in bootloader_state
    assert do_closeout.default_next_action() in bootloader_state
    memory_dir = do_closeout.claude_project_memory_dir(repo_root)
    project_status = (memory_dir / "project_status.md").read_text(encoding="utf-8")
    memory_index = (memory_dir / "MEMORY.md").read_text(encoding="utf-8")
    assert "Toolkit version: 0.1.1.29" in project_status
    assert "Roadmap active_version: v0.2.0-p1" in project_status
    assert "Last episode: ep-001" in project_status
    assert f"Next action: {do_closeout.default_next_action()}" in project_status
    assert "Project Status" in memory_index
    assert version_bump_calls == [
        ([sys.executable, "scripts/version-bump.py", "--patch"], repo_root, True)
    ]


def test_governed_closeout_rejects_unknown_reinforcement_id_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path)
    episodes_path = repo_root / ".azoth" / "memory" / "episodes.jsonl"
    episodes_path.write_text(
        json.dumps(
            {
                "id": "ep-010",
                "session_id": "older-session",
                "reinforcement_count": 0,
                "context": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    scope_before = (repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8")
    backlog_before = (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8")
    episodes_before = episodes_path.read_text(encoding="utf-8")
    version_bump_calls: list[tuple[list[str], Path, bool]] = []

    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )

    def _fake_run(cmd: list[str], cwd: Path, check: bool) -> None:
        version_bump_calls.append((cmd, cwd, check))

    monkeypatch.setattr(do_closeout.subprocess, "run", _fake_run)

    with pytest.raises(do_closeout.ReinforcementValidationError, match="unknown reinforce"):
        do_closeout.run_closeout(repo_root, reinforce_episode_ids=["ep-010", "ep-999"])

    assert version_bump_calls == []
    assert episodes_path.read_text(encoding="utf-8") == episodes_before
    assert (repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8") == scope_before
    assert (repo_root / ".azoth" / "backlog.yaml").read_text(encoding="utf-8") == backlog_before
    assert "write_claim:" in (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(
        encoding="utf-8"
    )
    assert (repo_root / ".azoth" / "session-orientation.txt").exists()


def test_governed_closeout_can_reinforce_exact_prior_episode_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    (repo_root / ".azoth" / "memory" / "episodes.jsonl").write_text(
        json.dumps(
            {
                "id": "ep-010",
                "session_id": "older-session",
                "goal": "Prior lesson",
                "summary": "Older reinforced lesson.",
                "reinforcement_count": 0,
                "context": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root, reinforce_episode_ids=["ep-010", "ep-010"])

    episodes = [
        json.loads(line)
        for line in (repo_root / ".azoth" / "memory" / "episodes.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    ]
    prior = episodes[0]
    new_episode = episodes[1]

    assert prior["reinforcement_count"] == 1
    assert prior["context"]["reinforced_by_sessions"] == ["sess-123"]
    assert new_episode["reinforcement_count"] == 0


def test_governed_closeout_uses_resumable_run_next_action_for_w2_and_w3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(
        tmp_path,
        include_session_state=True,
        include_resumable_run=True,
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    expected_next_action = "Resume wave 2 review."
    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    session_entry = ledger["sessions"][0]
    assert session_entry["status"] == "parked"
    assert session_entry["active_run_id"] == "run-123"
    assert session_entry["next_action"] == expected_next_action
    assert "closed_at" not in session_entry

    session_state = (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    assert f"next_action: {expected_next_action}" in session_state

    bootloader_state = (repo_root / ".azoth" / "bootloader-state.md").read_text(encoding="utf-8")
    assert expected_next_action in bootloader_state

    memory_dir = do_closeout.claude_project_memory_dir(repo_root)
    project_status = (memory_dir / "project_status.md").read_text(encoding="utf-8")
    assert f"Next action: {expected_next_action}" in project_status


def test_governed_closeout_preserves_checkpoint_fields_in_session_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(
        tmp_path,
        include_session_state=True,
        include_resumable_run=True,
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["pipeline"] == "auto"
    assert session_state["pipeline_position"] == 2
    assert session_state["current_stage_id"] == "architect_review"
    assert session_state["completed_stages"] == ["planner"]
    assert session_state["pending_stages"] == ["builder_apply", "reviewer_gate"]
    assert session_state["pause_reason"] == "human-gate"
    assert session_state["active_run_id"] == "run-123"


def test_governed_closeout_creates_session_registry_entry_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(
        tmp_path,
        include_session_state=True,
        include_sessions_registry=False,
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    session_entry = ledger["sessions"][0]
    assert session_entry["session_id"] == "sess-123"
    assert session_entry["status"] == "closed"
    assert session_entry["backlog_id"] == "BL-123"
    assert session_entry["goal"] == "BL-123: Governed closeout"


def test_governed_closeout_skips_session_state_when_file_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path, include_session_state=False)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    assert not (repo_root / ".azoth" / "session-state.md").exists()
    assert (repo_root / ".azoth" / "bootloader-state.md").exists()

    episode_lines = (
        (repo_root / ".azoth" / "memory" / "episodes.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )
    episode = json.loads(episode_lines[0])
    assert ".azoth/session-state.md" not in episode["context"]["files_changed"]


def test_governed_closeout_runs_w3_before_w4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_repo(tmp_path, include_session_state=True)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_approvals(
        repo_root,
        {
            "session_id": "sess-123",
            "gate": "final-delivery",
            "actor_type": "human",
            "approved": True,
            "decision": "approved",
        },
    )
    order: list[str] = []

    def _fake_w3(*args: object, **kwargs: object) -> None:
        order.append("W3")

    def _fake_w4(*args: object, **kwargs: object) -> None:
        order.append("W4")

    monkeypatch.setattr(do_closeout, "write_claude_memory_mirror", _fake_w3)
    monkeypatch.setattr(do_closeout, "run_version_bump", _fake_w4)
    monkeypatch.setenv("HOME", str(fake_home))

    do_closeout.run_closeout(repo_root)

    assert order == ["W3", "W4"]

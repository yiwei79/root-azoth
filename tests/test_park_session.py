"""Tests for scripts/park_session.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import park_session  # noqa: E402


def _build_repo(
    tmp_path: Path,
    *,
    with_session_state: bool = True,
    with_resumable_run: bool = False,
    run_status: str = "active",
    run_pause_reason: str | None = None,
    delivery_pipeline: str = "standard",
    target_layer: str = "infrastructure",
) -> Path:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir(parents=True)
    goal = "AD-HOC: Merge feat/gemini-cli-adapter into phase/v0.2.0-p2 and prune stale branches"
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": "2099-04-16T19:17:45+00:00",
                "goal": goal,
                "session_id": "2026-04-16-branch-hygiene",
                "approved_by": "human",
                "backlog_id": "AD-HOC",
                "delivery_pipeline": delivery_pipeline,
                "target_layer": target_layer,
            }
        ),
        encoding="utf-8",
    )
    runs: list[dict[str, object]] = []
    if with_resumable_run:
        run_entry: dict[str, object] = {
            "run_id": "run-001",
            "session_id": "2026-04-16-branch-hygiene",
            "backlog_id": "AD-HOC",
            "ide": "claude-code",
            "mode": delivery_pipeline,
            "goal": goal,
            "status": run_status,
            "created_at": "2026-04-16T17:00:00+00:00",
            "updated_at": "2026-04-16T17:17:46+00:00",
            "next_action": "Continue governed review.",
            "stages_completed": ["stage0_discovery", "planner_brief"],
            "active_stage_id": "architect_brief",
            "pending_stage_ids": ["builder_apply", "reviewer_gate"],
        }
        if run_pause_reason:
            run_entry["pause_reason"] = run_pause_reason
        runs.append(run_entry)
    (azoth_dir / "run-ledger.local.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "runs": runs,
                "write_claim": {
                    "session_id": "2026-04-16-branch-hygiene",
                    "expires_at": "2099-04-16T19:17:45+00:00",
                    "acquired_at": "2026-04-16T17:17:46+00:00",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    if with_session_state:
        (azoth_dir / "session-state.md").write_text(
            yaml.safe_dump(
                {
                    "session_id": "2026-04-16-branch-hygiene",
                    "state": "active",
                    "last_ide": "claude-code",
                    "timestamp": "2026-04-16T17:18:00+00:00",
                    "active_task": "Continue branch hygiene",
                    "active_files": ["CLAUDE.md"],
                    "pending_decisions": ["Decide whether to prune merged branches now."],
                    "approved_scope": goal,
                    "next_action": "Continue current scope",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        if with_resumable_run:
            (azoth_dir / "session-state.md").write_text(
                yaml.safe_dump(
                    {
                        "session_id": "2026-04-16-branch-hygiene",
                        "state": "active",
                        "last_ide": "claude-code",
                        "timestamp": "2026-04-16T17:18:00+00:00",
                        "active_task": "Continue branch hygiene",
                        "active_files": ["CLAUDE.md"],
                        "pending_decisions": ["Decide whether to prune merged branches now."],
                        "approved_scope": goal,
                        "next_action": "Continue current scope",
                        "pipeline": delivery_pipeline,
                        "pipeline_position": 3,
                        "current_stage_id": "architect_brief",
                        "completed_stages": ["stage0_discovery", "planner_brief"],
                        "pending_stages": ["builder_apply", "reviewer_gate"],
                        "active_run_id": "run-001",
                        **({"pause_reason": run_pause_reason} if run_pause_reason else {}),
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
    return tmp_path


def _rewrite_replay_queue(
    repo_root: Path,
    *,
    current_stage_id: str = "deliver_full_s5",
    revision_stage_id: str = "deliver_full_s4",
) -> None:
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    run = ledger["runs"][0]
    run["mode"] = "deliver-full"
    run["status"] = "paused"
    run["next_action"] = (
        f"Resume at human gate for stage `{current_stage_id}` in pipeline `deliver-full`; "
        f"approval replays `{revision_stage_id}`."
    )
    run["stages_completed"] = [
        "deliver_full_s2_architect",
        "deliver_full_s3",
        revision_stage_id,
    ]
    run["active_stage_id"] = current_stage_id
    run["pending_stage_ids"] = [
        revision_stage_id,
        current_stage_id,
        "deliver_full_s6",
        "deliver_full_s7_architect_review",
    ]
    run["pause_reason"] = "human-gate"
    ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")

    session_state_path = repo_root / ".azoth" / "session-state.md"
    session_state = yaml.safe_load(session_state_path.read_text(encoding="utf-8"))
    session_state["pipeline"] = "deliver-full"
    session_state["pipeline_position"] = 5
    session_state["current_stage_id"] = current_stage_id
    session_state["completed_stages"] = [
        "deliver_full_s2_architect",
        "deliver_full_s3",
        revision_stage_id,
    ]
    session_state["pending_stages"] = [
        revision_stage_id,
        current_stage_id,
        "deliver_full_s6",
        "deliver_full_s7_architect_review",
    ]
    session_state["pause_reason"] = "human-gate"
    session_state["active_run_id"] = "run-001"
    session_state["next_action"] = (
        f"Resume at human gate for stage `{current_stage_id}` in pipeline `deliver-full`; "
        f"approval replays `{revision_stage_id}`."
    )
    session_state_path.write_text(
        yaml.safe_dump(session_state, sort_keys=False),
        encoding="utf-8",
    )


def _stub_restore_pipeline_gate(
    repo_root: Path,
    *,
    session_id: str,
    pipeline: str,
    expires_at: str,
    require: bool = True,
) -> None:
    del require
    (repo_root / ".azoth" / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "pipeline": pipeline,
                "approved": True,
                "expires_at": expires_at,
                "opened_at": "2099-04-16T18:10:00+00:00",
                "research_required": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_park_session_records_parked_handoff_and_releases_claim(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)

    result = park_session.park_session(
        repo_root,
        next_action="Resume in Claude Code after the usage limit resets.",
        timestamp="2026-04-16T18:00:00+00:00",
    )

    assert result["status"] == "parked"
    assert result["write_claim_released"] is True

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    assert "write_claim" not in ledger
    assert ledger["sessions"][0]["session_id"] == "2026-04-16-branch-hygiene"
    assert ledger["sessions"][0]["status"] == "parked"

    scope = json.loads((repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8"))
    assert scope["approved"] is False
    assert scope["closed_at"] == "2026-04-16T18:00:00+00:00"

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["state"] == "parked"
    assert session_state["last_ide"] == "claude-code"
    assert session_state["active_files"] == ["CLAUDE.md"]
    assert session_state["next_action"] == "Resume in Claude Code after the usage limit resets."


def test_park_session_creates_session_state_when_missing(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path, with_session_state=False)

    park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        ide="codex",
        active_files=[".azoth/scope-gate.json"],
        pending_decisions=["Confirm whether the branch prune should stay ad hoc."],
        timestamp="2026-04-16T18:05:00+00:00",
    )

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["state"] == "parked"
    assert session_state["last_ide"] == "codex"
    assert session_state["active_files"] == [".azoth/scope-gate.json"]
    assert session_state["pending_decisions"] == [
        "Confirm whether the branch prune should stay ad hoc."
    ]


def test_resume_session_reopens_scope_and_write_claim(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)
    park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        timestamp="2026-04-16T18:05:00+00:00",
    )

    result = park_session.resume_session(
        repo_root,
        ide="codex",
        timestamp="2026-04-16T18:10:00+00:00",
    )

    assert result["status"] == "active"
    assert result["write_claim"] == "2026-04-16-branch-hygiene"

    scope = json.loads((repo_root / ".azoth" / "scope-gate.json").read_text(encoding="utf-8"))
    assert scope["approved"] is True
    assert scope["session_id"] == "2026-04-16-branch-hygiene"

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    assert ledger["sessions"][0]["status"] == "active"
    assert ledger["write_claim"]["session_id"] == "2026-04-16-branch-hygiene"

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["state"] == "active"
    assert session_state["last_ide"] == "codex"


def test_resume_session_uses_explicit_session_or_parked_session_state(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)
    park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        timestamp="2026-04-16T18:05:00+00:00",
    )

    result = park_session.resume_session(
        repo_root,
        session_id="2026-04-16-branch-hygiene",
        timestamp="2026-04-16T18:12:00+00:00",
    )

    assert result["session_id"] == "2026-04-16-branch-hygiene"


def test_park_session_snapshots_stage_checkpoint_into_run_and_session_state(tmp_path: Path) -> None:
    repo_root = _build_repo(
        tmp_path,
        with_resumable_run=True,
        delivery_pipeline="governed",
        target_layer="M1",
    )

    result = park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        timestamp="2026-04-16T18:05:00+00:00",
    )

    assert result["status"] == "parked"
    assert result["active_run_id"] == "run-001"
    assert result["pause_reason"] == "handoff"
    assert result["current_stage_id"] == "architect_brief"

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    run = ledger["runs"][0]
    assert run["status"] == "paused"
    assert run["mode"] == "governed"
    assert run["stages_completed"] == ["stage0_discovery", "planner_brief"]
    assert run["active_stage_id"] == "architect_brief"
    assert run["pending_stage_ids"] == ["builder_apply", "reviewer_gate"]
    assert run["pause_reason"] == "handoff"

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["pipeline"] == "governed"
    assert session_state["pipeline_position"] == 3
    assert session_state["current_stage_id"] == "architect_brief"
    assert session_state["completed_stages"] == ["stage0_discovery", "planner_brief"]
    assert session_state["pending_stages"] == ["builder_apply", "reviewer_gate"]
    assert session_state["pause_reason"] == "handoff"
    assert session_state["active_run_id"] == "run-001"


def test_resume_session_restores_scope_and_pipeline_gate_from_saved_run(tmp_path: Path) -> None:
    repo_root = _build_repo(
        tmp_path,
        with_resumable_run=True,
        delivery_pipeline="governed",
        target_layer="M1",
    )
    park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        timestamp="2026-04-16T18:05:00+00:00",
    )

    result = park_session.resume_session(
        repo_root,
        session_id="2026-04-16-branch-hygiene",
        ide="codex",
        timestamp="2099-04-16T18:10:00+00:00",
    )

    assert result["resume_type"] == "stage-aware"
    assert result["pipeline"] == "deliver-full"
    assert result["current_stage_id"] == "architect_brief"
    assert result["pending_stage_ids"] == ["builder_apply", "reviewer_gate"]
    assert result["human_gate"] is False

    pipeline_gate = json.loads(
        (repo_root / ".azoth" / "pipeline-gate.json").read_text(encoding="utf-8")
    )
    assert pipeline_gate["session_id"] == "2026-04-16-branch-hygiene"
    assert pipeline_gate["pipeline"] == "deliver-full"
    assert pipeline_gate["approved"] is True

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    run = ledger["runs"][0]
    assert run["status"] == "active"
    assert run["active_stage_id"] == "architect_brief"
    assert run["pending_stage_ids"] == ["builder_apply", "reviewer_gate"]
    assert "pause_reason" not in run

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["state"] == "active"
    assert session_state["pipeline"] == "deliver-full"
    assert session_state["current_stage_id"] == "architect_brief"
    assert session_state["active_run_id"] == "run-001"


def test_resume_session_restores_saved_human_gate_without_pipeline_restart(tmp_path: Path) -> None:
    repo_root = _build_repo(
        tmp_path,
        with_resumable_run=True,
        run_status="paused",
        run_pause_reason="human-gate",
        delivery_pipeline="governed",
        target_layer="M1",
    )
    park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        timestamp="2026-04-16T18:05:00+00:00",
    )

    result = park_session.resume_session(
        repo_root,
        session_id="2026-04-16-branch-hygiene",
        timestamp="2099-04-16T18:10:00+00:00",
    )

    assert result["resume_type"] == "stage-aware"
    assert result["human_gate"] is True
    assert result["pause_reason"] == "human-gate"
    assert result["pipeline"] == "deliver-full"
    assert result["current_stage_id"] == "architect_brief"

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    run = ledger["runs"][0]
    assert run["status"] == "paused"
    assert run["pause_reason"] == "human-gate"
    assert run["mode"] == "deliver-full"
    assert run["active_stage_id"] == "architect_brief"

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["pipeline"] == "deliver-full"
    assert session_state["pause_reason"] == "human-gate"
    assert "Resume at human gate" in session_state["next_action"]


def test_resume_session_can_consume_saved_human_gate_and_advance(tmp_path: Path) -> None:
    repo_root = _build_repo(
        tmp_path,
        with_resumable_run=True,
        run_status="paused",
        run_pause_reason="human-gate",
        delivery_pipeline="governed",
        target_layer="M1",
    )
    park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        timestamp="2026-04-16T18:05:00+00:00",
    )

    result = park_session.resume_session(
        repo_root,
        session_id="2026-04-16-branch-hygiene",
        timestamp="2099-04-16T18:10:00+00:00",
        approve_human_gate=True,
    )

    assert result["resume_type"] == "stage-aware"
    assert result["human_gate"] is False
    assert result["pause_reason"] is None
    assert result["pipeline"] == "deliver-full"
    assert result["current_stage_id"] == "builder_apply"
    assert result["pending_stage_ids"] == ["reviewer_gate"]

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    run = ledger["runs"][0]
    assert run["status"] == "active"
    assert run["active_stage_id"] == "builder_apply"
    assert run["pending_stage_ids"] == ["reviewer_gate"]
    assert run["stages_completed"] == [
        "stage0_discovery",
        "planner_brief",
        "architect_brief",
    ]
    assert "pause_reason" not in run

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert session_state["pipeline"] == "deliver-full"
    assert session_state["current_stage_id"] == "builder_apply"
    assert session_state["pending_stages"] == ["reviewer_gate"]
    assert "pause_reason" not in session_state


def test_resume_session_surfaces_replay_target_after_human_gate_rewrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _build_repo(
        tmp_path,
        with_resumable_run=True,
        run_status="paused",
        run_pause_reason="human-gate",
        delivery_pipeline="governed",
        target_layer="M1",
    )
    monkeypatch.setattr(park_session, "_restore_pipeline_gate", _stub_restore_pipeline_gate)
    _rewrite_replay_queue(repo_root)
    park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        timestamp="2026-04-16T18:05:00+00:00",
    )

    result = park_session.resume_session(
        repo_root,
        session_id="2026-04-16-branch-hygiene",
        timestamp="2099-04-16T18:10:00+00:00",
    )

    assert result["resume_type"] == "stage-aware"
    assert result["human_gate"] is True
    assert result["current_stage_id"] == "deliver_full_s5"
    assert result["pending_stage_ids"] == [
        "deliver_full_s4",
        "deliver_full_s5",
        "deliver_full_s6",
        "deliver_full_s7_architect_review",
    ]

    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert "deliver_full_s4" in session_state["next_action"]


def test_resume_session_approval_updates_registry_to_promoted_revision_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _build_repo(
        tmp_path,
        with_resumable_run=True,
        run_status="paused",
        run_pause_reason="human-gate",
        delivery_pipeline="governed",
        target_layer="M1",
    )
    monkeypatch.setattr(park_session, "_restore_pipeline_gate", _stub_restore_pipeline_gate)
    _rewrite_replay_queue(repo_root)
    park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        timestamp="2026-04-16T18:05:00+00:00",
    )

    result = park_session.resume_session(
        repo_root,
        session_id="2026-04-16-branch-hygiene",
        timestamp="2099-04-16T18:10:00+00:00",
        approve_human_gate=True,
    )

    assert result["resume_type"] == "stage-aware"
    assert result["human_gate"] is False
    assert result["current_stage_id"] == "deliver_full_s4"
    assert result["pending_stage_ids"] == [
        "deliver_full_s5",
        "deliver_full_s6",
        "deliver_full_s7_architect_review",
    ]

    ledger = yaml.safe_load(
        (repo_root / ".azoth" / "run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    assert ledger["sessions"][0]["next_action"] != "Resume at human gate for stage `deliver_full_s5` in pipeline `deliver-full`."
    assert "deliver_full_s4" in ledger["sessions"][0]["next_action"]


def test_resume_session_scope_only_removes_stale_pipeline_gate(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)
    (repo_root / ".azoth" / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "2026-04-16-branch-hygiene",
                "pipeline": "governed",
                "approved": True,
                "expires_at": "2026-04-16T19:17:45+00:00",
                "opened_at": "2026-04-16T17:17:46+00:00",
            }
        ),
        encoding="utf-8",
    )
    park_session.park_session(
        repo_root,
        next_action="Resume later with /resume 2026-04-16-branch-hygiene.",
        timestamp="2026-04-16T18:05:00+00:00",
    )

    result = park_session.resume_session(repo_root, timestamp="2026-04-16T18:10:00+00:00")

    assert result["resume_type"] == "scope-only"
    assert result["pipeline"] is None
    assert not (repo_root / ".azoth" / "pipeline-gate.json").exists()
    session_state = yaml.safe_load(
        (repo_root / ".azoth" / "session-state.md").read_text(encoding="utf-8")
    )
    assert "Stage 0" in session_state["next_action"]


def test_resume_session_blocks_conflicting_live_scope(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    ledger["sessions"] = [
        {
            "session_id": "2026-04-16-other-session",
            "backlog_id": "AD-HOC",
            "goal": "Resume something else",
            "status": "parked",
            "ide": "codex",
            "next_action": "Resume later with /resume 2026-04-16-other-session.",
            "updated_at": "2026-04-16T18:05:00+00:00",
        }
    ]
    ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")

    with pytest.raises(park_session.ParkSessionError, match="Active scope"):
        park_session.resume_session(repo_root, session_id="2026-04-16-other-session")

"""Tests for scripts/session_continuity.py."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from session_continuity import resolve_transition, scope_conflict_message  # noqa: E402


def _write_scope(
    tmp_path: Path,
    *,
    session_id: str = "sess-active",
    goal: str = "BL-123: Active scope",
    expires_at: str = "2099-04-16T19:17:45+00:00",
) -> Path:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir(parents=True, exist_ok=True)
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": expires_at,
                "goal": goal,
                "session_id": session_id,
                "approved_by": "human",
                "backlog_id": "BL-123",
                "governance_mode": "standard",
                "pipeline_command": "auto",
                "target_layer": "application",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_scope_conflict_blocks_next_when_live_scope_exists(tmp_path: Path) -> None:
    repo_root = _write_scope(tmp_path)

    conflict = scope_conflict_message(repo_root, command_name="next")

    assert conflict is not None
    assert "replace decision" in conflict


def test_scope_conflict_blocks_new_pipeline_goal_when_live_scope_exists(tmp_path: Path) -> None:
    repo_root = _write_scope(tmp_path)

    conflict = scope_conflict_message(
        repo_root,
        command_name="auto",
        command_args="BL-456 implement stage-aware resume",
    )

    assert conflict is not None
    assert "replace decision" in conflict


def test_scope_conflict_blocks_explicit_resume_of_other_session(tmp_path: Path) -> None:
    repo_root = _write_scope(tmp_path)

    conflict = scope_conflict_message(
        repo_root,
        command_name="resume",
        requested_session_id="sess-other",
    )

    assert conflict is not None
    assert "Do not reopen 'sess-other'" in conflict


def test_scope_conflict_allows_resume_of_active_session(tmp_path: Path) -> None:
    repo_root = _write_scope(tmp_path, session_id="sess-active")

    conflict = scope_conflict_message(
        repo_root,
        command_name="resume",
        requested_session_id="sess-active",
    )

    assert conflict is None


def test_scope_conflict_allows_matching_pipeline_goal_when_live_scope_exists(
    tmp_path: Path,
) -> None:
    repo_root = _write_scope(tmp_path, goal="BL-123: Active scope")

    conflict = scope_conflict_message(
        repo_root,
        command_name="auto",
        command_args="BL-123: Active scope",
    )

    assert conflict is None


def test_resolve_transition_prefers_replace_for_different_pipeline_goal(tmp_path: Path) -> None:
    repo_root = _write_scope(tmp_path, goal="BL-123: Active scope")

    decision = resolve_transition(
        repo_root,
        command_name="auto",
        command_args="BL-456 implement stage-aware resume",
    )

    assert decision.action == "replace"
    assert decision.active_session_id == "sess-active"


def test_resolve_transition_prefers_resume_for_matching_pipeline_goal(tmp_path: Path) -> None:
    repo_root = _write_scope(tmp_path, goal="BL-123: Active scope")

    decision = resolve_transition(
        repo_root,
        command_name="auto",
        command_args="BL-123: Active scope",
    )

    assert decision.action == "resume"
    assert decision.active_session_id == "sess-active"


def test_resolve_transition_uses_replace_for_next_when_live_scope_exists(tmp_path: Path) -> None:
    repo_root = _write_scope(tmp_path)

    decision = resolve_transition(repo_root, command_name="next")

    assert decision.action == "replace"
    assert decision.reason == "next-with-live-scope"


def test_resolve_transition_prefers_extend_for_low_ttl_matching_pipeline_goal(
    tmp_path: Path,
) -> None:
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    repo_root = _write_scope(tmp_path, goal="BL-123: Active scope", expires_at=expires_at)

    decision = resolve_transition(
        repo_root,
        command_name="auto",
        command_args="BL-123: Active scope",
    )

    assert decision.action == "extend"
    assert decision.reason == "matching-goal-low-ttl"


def test_resolve_transition_does_not_collapse_distinct_work_item_ids(tmp_path: Path) -> None:
    repo_root = _write_scope(tmp_path, goal="BL-123: Active scope")

    decision = resolve_transition(
        repo_root,
        command_name="auto",
        command_args="BL-12: Active scope",
    )

    assert decision.action == "replace"
    assert decision.reason == "different-pipeline-goal"

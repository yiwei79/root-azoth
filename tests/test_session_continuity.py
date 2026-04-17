"""Tests for scripts/session_continuity.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from session_continuity import scope_conflict_message  # noqa: E402


def _write_scope(
    tmp_path: Path,
    *,
    session_id: str = "sess-active",
    goal: str = "BL-123: Active scope",
) -> Path:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir(parents=True, exist_ok=True)
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": "2099-04-16T19:17:45+00:00",
                "goal": goal,
                "session_id": session_id,
                "approved_by": "human",
                "backlog_id": "BL-123",
                "delivery_pipeline": "auto",
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
    assert "Use `resume`, `/park`, or `/session-closeout`" in conflict


def test_scope_conflict_blocks_new_pipeline_goal_when_live_scope_exists(tmp_path: Path) -> None:
    repo_root = _write_scope(tmp_path)

    conflict = scope_conflict_message(
        repo_root,
        command_name="auto",
        command_args="BL-456 implement stage-aware resume",
    )

    assert conflict is not None
    assert "Do not start a new `/auto` goal" in conflict


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

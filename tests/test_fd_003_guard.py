from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_fd_003_subagent_isolation import check  # noqa: E402


def test_inline_only_run_is_blocked() -> None:
    """A pipeline plan with multiple side-effectful stages but zero spawned subagents must be blocked."""
    result = check({
        "stages": [
            {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": False, "subagent_type": None},
            {"name": "planning_bank", "kind": "planning_bank", "spawned_subagent": False, "subagent_type": None},
            {"name": "validation", "kind": "validation", "spawned_subagent": False, "subagent_type": None},
        ]
    })
    assert result["ok"] is False
    assert "fd_003" in result["violations"][0]["rule"]


def test_real_subagent_runs_are_allowed() -> None:
    """A pipeline plan with real spawned subagents passes the guard."""
    result = check({
        "stages": [
            {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": True, "subagent_type": "context-architect"},
            {"name": "planning_bank", "kind": "planning_bank", "spawned_subagent": True, "subagent_type": "planner"},
            {"name": "validation", "kind": "validation", "spawned_subagent": True, "subagent_type": "evaluator"},
        ]
    })
    assert result["ok"] is True


def test_single_side_effect_stage_passes() -> None:
    """A single side-effectful stage alone is not isolation theater."""
    result = check({
        "stages": [
            {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": False, "subagent_type": None},
        ]
    })
    assert result["ok"] is True


def test_non_side_effect_stages_are_not_counted() -> None:
    """Read-only stages don't trigger the isolation rule."""
    result = check({
        "stages": [
            {"name": "inspect", "kind": "inspect", "spawned_subagent": False},
            {"name": "summarize", "kind": "summarize", "spawned_subagent": False},
        ]
    })
    assert result["ok"] is True


def test_invalid_payload_is_blocked() -> None:
    """A malformed payload is rejected."""
    result = check({"stages": "not-a-list"})
    assert result["ok"] is False
    assert "fd_003" in result["violations"][0]["rule"]

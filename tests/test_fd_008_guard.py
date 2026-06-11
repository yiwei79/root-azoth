from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_fd_008_subagent_contract import check  # noqa: E402


def test_deliver_full_without_architect_spawn_is_blocked() -> None:
    """The FD-008 case: architect brief drafted inline instead of spawned."""
    result = check({
        "pipeline": "deliver_full",
        "stages": [
            {"name": "goal_clarification", "spawned": True, "subagent_type": "planner"},
            # FD-008 case: architect brief drafted inline
            {"name": "architect_brief", "spawned": False, "subagent_type": None},
            {"name": "build", "spawned": True, "subagent_type": "builder"},
        ]
    })
    assert result["ok"] is False
    assert "fd_008" in result["violations"][0]["rule"]


def test_deliver_full_with_proper_architect_spawn_passes() -> None:
    """Architect stage properly spawned as the architect archetype."""
    result = check({
        "pipeline": "deliver_full",
        "stages": [
            {"name": "goal_clarification", "spawned": True, "subagent_type": "planner"},
            {"name": "architect_brief", "spawned": True, "subagent_type": "architect"},
            {"name": "build", "spawned": True, "subagent_type": "builder"},
        ]
    })
    assert result["ok"] is True


def test_deliver_with_governance_review_wrong_subagent_blocked() -> None:
    """Governance review must be spawned as reviewer."""
    result = check({
        "pipeline": "deliver_full",
        "stages": [
            {"name": "architect_brief", "spawned": True, "subagent_type": "architect"},
            {"name": "governance_review", "spawned": True, "subagent_type": "builder"},
        ]
    })
    assert result["ok"] is False
    assert "fd_008_wrong_subagent_type_governance_review" in result["violations"][0]["rule"]


def test_non_governed_pipeline_passes_without_spawns() -> None:
    """A non-governed pipeline (e.g. deliver) does not require governed-stage spawns."""
    result = check({
        "pipeline": "deliver",
        "stages": [
            {"name": "build", "spawned": False, "subagent_type": None},
        ]
    })
    assert result["ok"] is True


def test_dynamic_full_auto_governed_enforced() -> None:
    """The dynamic-full-auto governed pipeline is also enforced."""
    result = check({
        "pipeline": "dynamic_full_auto_governed",
        "stages": [
            {"name": "architect_brief", "spawned": False, "subagent_type": None},
        ]
    })
    assert result["ok"] is False


def test_governance_review_inline_is_blocked() -> None:
    """Governance review drafted inline is a separate violation from architect."""
    result = check({
        "pipeline": "deliver_full",
        "stages": [
            {"name": "architect_brief", "spawned": True, "subagent_type": "architect"},
            {"name": "governance_review", "spawned": False, "subagent_type": None},
        ]
    })
    assert result["ok"] is False
    assert "fd_008_inline_governance_review" in result["violations"][0]["rule"]

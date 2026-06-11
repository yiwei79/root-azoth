from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from azoth_guards import GUARD_MODULES, run  # noqa: E402


def test_runner_returns_combined_verdict() -> None:
    """The runner emits per-guard results for fd_003, fd_004, fd_005, fd_008."""
    payload = run({
        "friction_check": {
            "stages": [
                {"name": "context_recovery", "kind": "context_recovery",
                 "spawned_subagent": True, "subagent_type": "context-architect"},
                {"name": "planning_bank", "kind": "planning_bank",
                 "spawned_subagent": True, "subagent_type": "planner"},
            ]
        },
        "hydration_check": {
            "action": "edit_readme", "planned_paths": ["README.md"],
        },
        "completion_check": {
            "marking": "in_progress", "achieved_states": ["hydrated"],
        },
        "subagent_contract_check": {
            "pipeline": "deliver", "stages": [],
        }
    })
    assert "guards" in payload
    for guard_id in GUARD_MODULES:
        assert guard_id in payload["guards"]
        assert "ok" in payload["guards"][guard_id]
        assert "violations" in payload["guards"][guard_id]


def test_runner_exits_zero_when_all_pass() -> None:
    """When every guard passes individually, the runner returns ok=true."""
    payload = run({
        "friction_check": {
            "stages": [
                {"name": "context_recovery", "kind": "context_recovery",
                 "spawned_subagent": True, "subagent_type": "context-architect"},
            ]
        },
        "hydration_check": {
            "action": "hydrate_caches", "planned_paths": ["tmp/data.json"],
        },
        "completion_check": {
            "marking": "in_progress", "achieved_states": ["hydrated"],
        },
        "subagent_contract_check": {
            "pipeline": "deliver", "stages": [],
        }
    })
    assert payload["ok"] is True


def test_runner_exits_one_when_any_fails() -> None:
    """When any guard fails, the runner returns ok=false."""
    payload = run({
        "friction_check": {
            "stages": [
                {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": False},
                {"name": "planning_bank", "kind": "planning_bank", "spawned_subagent": False},
            ]
        },
    })
    assert payload["ok"] is False


def test_runner_handles_missing_payload_sections() -> None:
    """Empty payload: each guard runs with default empty input and should pass trivially."""
    payload = run({})
    # Most guards treat empty payload as "nothing to check" (pass).
    assert payload["ok"] is True
    assert all(g["ok"] for g in payload["guards"].values())


def test_runner_reports_specific_violation_count() -> None:
    """The top-level payload surfaces a violation_count for CI consumption."""
    payload = run({
        "friction_check": {
            "stages": [
                {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": False},
                {"name": "planning_bank", "kind": "planning_bank", "spawned_subagent": False},
            ]
        },
    })
    assert payload.get("violation_count", 0) >= 1


def test_guard_modules_includes_all_four_guards() -> None:
    """GUARD_MODULES is the canonical mapping from guard_id to module file."""
    assert set(GUARD_MODULES) == {"fd_003", "fd_004", "fd_005", "fd_008"}

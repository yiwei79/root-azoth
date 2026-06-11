from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "azoth_guards.py"


def _run(payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        path = f.name
    try:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--input", path, "--json"],
            cwd=REPO_ROOT, text=True, capture_output=True, check=False,
        )
    finally:
        Path(path).unlink(missing_ok=True)


def test_runner_returns_combined_verdict() -> None:
    """The runner emits per-guard results for fd_003, fd_004, fd_005, fd_008."""
    proc = _run({
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
    payload = json.loads(proc.stdout)
    assert "guards" in payload
    for guard_id in ("fd_003", "fd_004", "fd_005", "fd_008"):
        assert guard_id in payload["guards"]
        assert "ok" in payload["guards"][guard_id]
        assert "violations" in payload["guards"][guard_id]


def test_runner_exits_zero_when_all_pass() -> None:
    """When every guard passes individually, exit code is 0."""
    proc = _run({
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
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_runner_exits_one_when_any_fails() -> None:
    """When any guard fails, exit code is 1."""
    proc = _run({
        "friction_check": {
            "stages": [
                {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": False},
                {"name": "planning_bank", "kind": "planning_bank", "spawned_subagent": False},
            ]
        },
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False


def test_runner_handles_missing_payload_sections() -> None:
    """Empty payload: each guard runs with default empty input and should pass trivially."""
    proc = _run({})
    # Most guards treat empty payload as "nothing to check" (pass).
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert all(g["ok"] for g in payload["guards"].values())


def test_runner_reports_specific_violation_count() -> None:
    """The top-level payload surfaces a violation_count for CI consumption."""
    proc = _run({
        "friction_check": {
            "stages": [
                {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": False},
                {"name": "planning_bank", "kind": "planning_bank", "spawned_subagent": False},
            ]
        },
    })
    payload = json.loads(proc.stdout)
    assert payload.get("violation_count", 0) >= 1

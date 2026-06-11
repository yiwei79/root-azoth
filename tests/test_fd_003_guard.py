from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_fd_003_subagent_isolation.py"


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


def test_inline_only_run_is_blocked() -> None:
    """A pipeline plan with multiple side-effectful stages but zero spawned subagents must be blocked."""
    proc = _run({
        "stages": [
            {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": False, "subagent_type": None},
            {"name": "planning_bank", "kind": "planning_bank", "spawned_subagent": False, "subagent_type": None},
            {"name": "validation", "kind": "validation", "spawned_subagent": False, "subagent_type": None},
        ]
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert "fd_003" in payload["violations"][0]["rule"]


def test_real_subagent_runs_are_allowed() -> None:
    """A pipeline plan with real spawned subagents passes the guard."""
    proc = _run({
        "stages": [
            {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": True, "subagent_type": "context-architect"},
            {"name": "planning_bank", "kind": "planning_bank", "spawned_subagent": True, "subagent_type": "planner"},
            {"name": "validation", "kind": "validation", "spawned_subagent": True, "subagent_type": "evaluator"},
        ]
    })
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_single_side_effect_stage_passes() -> None:
    """A single side-effectful stage alone is not isolation theater."""
    proc = _run({
        "stages": [
            {"name": "context_recovery", "kind": "context_recovery", "spawned_subagent": False, "subagent_type": None},
        ]
    })
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_non_side_effect_stages_are_not_counted() -> None:
    """Read-only stages don't trigger the isolation rule."""
    proc = _run({
        "stages": [
            {"name": "inspect", "kind": "inspect", "spawned_subagent": False},
            {"name": "summarize", "kind": "summarize", "spawned_subagent": False},
        ]
    })
    assert proc.returncode == 0


def test_invalid_payload_is_blocked() -> None:
    """A malformed payload is rejected."""
    proc = _run({"stages": "not-a-list"})
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert "fd_003" in payload["violations"][0]["rule"]

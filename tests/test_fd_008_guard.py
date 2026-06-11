from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_fd_008_subagent_contract.py"


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


def test_deliver_full_without_architect_spawn_is_blocked() -> None:
    """The FD-008 case: architect brief drafted inline instead of spawned."""
    proc = _run({
        "pipeline": "deliver_full",
        "stages": [
            {"name": "goal_clarification", "spawned": True, "subagent_type": "planner"},
            # FD-008 case: architect brief drafted inline
            {"name": "architect_brief", "spawned": False, "subagent_type": None},
            {"name": "build", "spawned": True, "subagent_type": "builder"},
        ]
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert "fd_008" in payload["violations"][0]["rule"]


def test_deliver_full_with_proper_architect_spawn_passes() -> None:
    """Architect stage properly spawned as the architect archetype."""
    proc = _run({
        "pipeline": "deliver_full",
        "stages": [
            {"name": "goal_clarification", "spawned": True, "subagent_type": "planner"},
            {"name": "architect_brief", "spawned": True, "subagent_type": "architect"},
            {"name": "build", "spawned": True, "subagent_type": "builder"},
        ]
    })
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_deliver_with_governance_review_wrong_subagent_blocked() -> None:
    """Governance review must be spawned as reviewer."""
    proc = _run({
        "pipeline": "deliver_full",
        "stages": [
            {"name": "architect_brief", "spawned": True, "subagent_type": "architect"},
            {"name": "governance_review", "spawned": True, "subagent_type": "builder"},
        ]
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert "fd_008_wrong_subagent_type_governance_review" in payload["violations"][0]["rule"]


def test_non_governed_pipeline_passes_without_spawns() -> None:
    """A non-governed pipeline (e.g. deliver) does not require governed-stage spawns."""
    proc = _run({
        "pipeline": "deliver",
        "stages": [
            {"name": "build", "spawned": False, "subagent_type": None},
        ]
    })
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_dynamic_full_auto_governed_enforced() -> None:
    """The dynamic-full-auto governed pipeline is also enforced."""
    proc = _run({
        "pipeline": "dynamic_full_auto_governed",
        "stages": [
            {"name": "architect_brief", "spawned": False, "subagent_type": None},
        ]
    })
    assert proc.returncode == 1


def test_governance_review_inline_is_blocked() -> None:
    """Governance review drafted inline is a separate violation from architect."""
    proc = _run({
        "pipeline": "deliver_full",
        "stages": [
            {"name": "architect_brief", "spawned": True, "subagent_type": "architect"},
            {"name": "governance_review", "spawned": False, "subagent_type": None},
        ]
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert "fd_008_inline_governance_review" in payload["violations"][0]["rule"]

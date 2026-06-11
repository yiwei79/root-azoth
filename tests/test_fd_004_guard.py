from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_fd_004_hydration_scope.py"


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


def test_hydration_without_open_scope_is_blocked() -> None:
    """Hydration that mutates governed state without an open scope-gate must be blocked."""
    proc = _run({
        "action": "hydrate_planning_bank",
        "planned_paths": [".azoth/roadmap.yaml", ".azoth/backlog.yaml"],
        "scope_gate": None,
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["violations"][0]["rule"] == "fd_004_no_scope"


def test_hydration_with_open_scope_passes() -> None:
    """Hydration with an approved scope-gate passes."""
    proc = _run({
        "action": "hydrate_planning_bank",
        "planned_paths": [".azoth/roadmap.yaml", ".azoth/backlog.yaml"],
        "scope_gate": {"session_id": "s-1", "approved_at": "2026-06-11T00:00:00Z"},
    })
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_non_hydration_action_passes() -> None:
    """A read or edit that is not 'hydrate*' is not in scope of this guard."""
    proc = _run({
        "action": "edit_readme",
        "planned_paths": ["README.md"],
        "scope_gate": None,
    })
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload.get("reason") == "non-hydration action"


def test_hydration_with_only_non_governed_paths_passes() -> None:
    """Hydration that touches only non-governed paths does not require a scope-gate."""
    proc = _run({
        "action": "hydrate_caches",
        "planned_paths": ["docs/cache.md", "tmp/data.json"],
        "scope_gate": None,
    })
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload.get("reason") == "no governed paths"


def test_hydration_with_empty_scope_session_id_blocked() -> None:
    """A scope-gate with empty session_id is the same as no scope-gate."""
    proc = _run({
        "action": "hydrate_planning_bank",
        "planned_paths": [".azoth/roadmap.yaml"],
        "scope_gate": {"session_id": "", "approved_at": "2026-06-11T00:00:00Z"},
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["violations"][0]["rule"] == "fd_004_no_scope"

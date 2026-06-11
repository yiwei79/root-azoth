from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_fd_004_hydration_scope import check  # noqa: E402


def test_hydration_without_open_scope_is_blocked() -> None:
    """Hydration that mutates governed state without an open scope-gate must be blocked."""
    result = check({
        "action": "hydrate_planning_bank",
        "planned_paths": [".azoth/roadmap.yaml", ".azoth/backlog.yaml"],
        "scope_gate": None,
    })
    assert result["ok"] is False
    assert result["violations"][0]["rule"] == "fd_004_no_scope"


def test_hydration_with_open_scope_passes() -> None:
    """Hydration with an approved scope-gate passes."""
    result = check({
        "action": "hydrate_planning_bank",
        "planned_paths": [".azoth/roadmap.yaml", ".azoth/backlog.yaml"],
        "scope_gate": {"session_id": "s-1", "approved_at": "2026-06-11T00:00:00Z"},
    })
    assert result["ok"] is True


def test_non_hydration_action_passes() -> None:
    """A read or edit that is not 'hydrate*' is not in scope of this guard."""
    result = check({
        "action": "edit_readme",
        "planned_paths": ["README.md"],
        "scope_gate": None,
    })
    assert result["ok"] is True
    assert result.get("reason") == "non-hydration action"


def test_hydration_with_only_non_governed_paths_passes() -> None:
    """Hydration that touches only non-governed paths does not require a scope-gate."""
    result = check({
        "action": "hydrate_caches",
        "planned_paths": ["docs/cache.md", "tmp/data.json"],
        "scope_gate": None,
    })
    assert result["ok"] is True
    assert result.get("reason") == "no governed paths"


def test_hydration_with_empty_scope_session_id_blocked() -> None:
    """A scope-gate with empty session_id is the same as no scope-gate."""
    result = check({
        "action": "hydrate_planning_bank",
        "planned_paths": [".azoth/roadmap.yaml"],
        "scope_gate": {"session_id": "", "approved_at": "2026-06-11T00:00:00Z"},
    })
    assert result["ok"] is False
    assert result["violations"][0]["rule"] == "fd_004_no_scope"

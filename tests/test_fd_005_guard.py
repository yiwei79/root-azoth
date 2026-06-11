from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_fd_005_completion_semantics import check  # noqa: E402


def test_complete_after_only_hydration_is_blocked() -> None:
    """The FD-005 failure mode: marking complete after only hydration. Blocked."""
    result = check({
        "marking": "complete",
        "achieved_states": ["hydrated"],
        "missing_states": ["implementation_accepted", "tests_pass", "receipt_written"],
    })
    assert result["ok"] is False
    assert result["violations"][0]["rule"] == "fd_005_admin_complete_pretends_delivery"


def test_complete_after_full_delivery_passes() -> None:
    """All required states present: pass."""
    result = check({
        "marking": "complete",
        "achieved_states": ["hydrated", "implementation_accepted", "tests_pass", "receipt_written"],
        "missing_states": [],
    })
    assert result["ok"] is True


def test_complete_alias_done_passes() -> None:
    """The 'done' alias for complete also passes when states are satisfied."""
    result = check({
        "marking": "done",
        "achieved_states": ["implementation_accepted", "tests_pass", "receipt_written"],
    })
    assert result["ok"] is True


def test_in_progress_marking_passes() -> None:
    """Non-completion markings are not in scope of this guard."""
    result = check({
        "marking": "in_progress",
        "achieved_states": ["hydrated"],
    })
    assert result["ok"] is True
    assert "reason" in result


def test_complete_with_partial_delivery_is_blocked() -> None:
    """Missing tests_pass but otherwise satisfied: still blocked."""
    result = check({
        "marking": "complete",
        "achieved_states": ["hydrated", "implementation_accepted", "receipt_written"],
    })
    assert result["ok"] is False
    # Falls into the generic incomplete-state rule, not the admin-complete rule
    assert "fd_005" in result["violations"][0]["rule"]


def test_complete_with_only_planning_blocked_as_admin() -> None:
    """Marking complete after only planning/admin states is the FD-005 case."""
    result = check({
        "marking": "complete",
        "achieved_states": ["hydrated", "scoped", "planned"],
    })
    assert result["ok"] is False
    assert result["violations"][0]["rule"] == "fd_005_admin_complete_pretends_delivery"

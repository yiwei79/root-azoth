from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_fd_005_completion_semantics.py"


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


def test_complete_after_only_hydration_is_blocked() -> None:
    """The FD-005 failure mode: marking complete after only hydration. Blocked."""
    proc = _run({
        "marking": "complete",
        "achieved_states": ["hydrated"],
        "missing_states": ["implementation_accepted", "tests_pass", "receipt_written"],
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["violations"][0]["rule"] == "fd_005_admin_complete_pretends_delivery"


def test_complete_after_full_delivery_passes() -> None:
    """All required states present: pass."""
    proc = _run({
        "marking": "complete",
        "achieved_states": ["hydrated", "implementation_accepted", "tests_pass", "receipt_written"],
        "missing_states": [],
    })
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_complete_alias_done_passes() -> None:
    """The 'done' alias for complete also passes when states are satisfied."""
    proc = _run({
        "marking": "done",
        "achieved_states": ["implementation_accepted", "tests_pass", "receipt_written"],
    })
    assert proc.returncode == 0


def test_in_progress_marking_passes() -> None:
    """Non-completion markings are not in scope of this guard."""
    proc = _run({
        "marking": "in_progress",
        "achieved_states": ["hydrated"],
    })
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert "reason" in payload


def test_complete_with_partial_delivery_is_blocked() -> None:
    """Missing tests_pass but otherwise satisfied: still blocked."""
    proc = _run({
        "marking": "complete",
        "achieved_states": ["hydrated", "implementation_accepted", "receipt_written"],
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    # Falls into the generic incomplete-state rule, not the admin-complete rule
    assert "fd_005" in payload["violations"][0]["rule"]


def test_complete_with_only_planning_blocked_as_admin() -> None:
    """Marking complete after only planning/admin states is the FD-005 case."""
    proc = _run({
        "marking": "complete",
        "achieved_states": ["hydrated", "scoped", "planned"],
    })
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["violations"][0]["rule"] == "fd_005_admin_complete_pretends_delivery"

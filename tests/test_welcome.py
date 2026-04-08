"""Tests for scripts/welcome.py — Azoth session welcome dashboard."""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from rich.console import Console

# Allow importing welcome.py from scripts/ without installing it as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import welcome  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────────


def _item(
    id: str,
    status: str = "active",
    priority: int = 1,
    blocked_by: list[str] | None = None,
) -> dict:
    item: dict = {"id": id, "status": status, "priority": priority}
    if blocked_by is not None:
        item["blocked_by"] = blocked_by
    return item


def _future() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def _past() -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()


# ── filter_unblocked_items ────────────────────────────────────────────────────


def test_filter_excludes_complete() -> None:
    items = [_item("A", status="complete"), _item("B")]
    result = welcome.filter_unblocked_items(items, {"A"})
    assert [x["id"] for x in result] == ["B"]


def test_filter_excludes_deferred() -> None:
    items = [_item("A", status="deferred"), _item("B")]
    result = welcome.filter_unblocked_items(items, set())
    assert [x["id"] for x in result] == ["B"]


def test_filter_excludes_blocked_when_dep_incomplete() -> None:
    items = [_item("A"), _item("B", blocked_by=["A"])]
    result = welcome.filter_unblocked_items(items, set())
    assert [x["id"] for x in result] == ["A"]


def test_filter_includes_when_blocker_complete() -> None:
    items = [_item("A", status="complete"), _item("B", blocked_by=["A"])]
    result = welcome.filter_unblocked_items(items, {"A"})
    assert [x["id"] for x in result] == ["B"]


def test_filter_sorts_by_priority() -> None:
    items = [_item("A", priority=5), _item("B", priority=1), _item("C", priority=3)]
    result = welcome.filter_unblocked_items(items, set())
    assert [x["id"] for x in result] == ["B", "C", "A"]


def test_filter_empty_input() -> None:
    assert welcome.filter_unblocked_items([], set()) == []


def test_filter_null_blocked_by_treated_as_unblocked() -> None:
    """An item with blocked_by: null/None should be treated as unblocked."""
    item = _item("A")
    item["blocked_by"] = None
    result = welcome.filter_unblocked_items([item], set())
    assert [x["id"] for x in result] == ["A"]


# ── is_scope_active ───────────────────────────────────────────────────────────


def test_scope_active_valid() -> None:
    assert welcome.is_scope_active({"approved": True, "expires_at": _future()}) is True


def test_scope_inactive_expired() -> None:
    assert welcome.is_scope_active({"approved": True, "expires_at": _past()}) is False


def test_scope_inactive_not_approved() -> None:
    assert welcome.is_scope_active({"approved": False, "expires_at": _future()}) is False


def test_scope_inactive_empty_dict() -> None:
    assert welcome.is_scope_active({}) is False


def test_scope_inactive_bad_date_string() -> None:
    assert welcome.is_scope_active({"approved": True, "expires_at": "not-a-date"}) is False


def test_scope_inactive_missing_expires_at() -> None:
    assert welcome.is_scope_active({"approved": True}) is False


def test_scope_active_naive_future_datetime() -> None:
    """Naive datetime (no tz) in the future should be treated as UTC and count as active."""
    naive_future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    assert welcome.is_scope_active({"approved": True, "expires_at": naive_future}) is True


def test_scope_inactive_when_goal_item_complete() -> None:
    """A scope gate is stale when its referenced backlog item is already complete."""
    scope = {
        "approved": True,
        "expires_at": _future(),
        "goal": "BL-007: Session Welcome UX",
    }
    assert welcome.is_scope_active(scope, complete_ids={"BL-007"}) is False


def test_scope_active_when_goal_item_not_complete() -> None:
    """A scope gate is still active when its referenced item is not yet complete."""
    scope = {
        "approved": True,
        "expires_at": _future(),
        "goal": "BL-006: Enforce subagent invocation",
    }
    assert welcome.is_scope_active(scope, complete_ids={"BL-007"}) is True


def test_scope_active_without_complete_ids() -> None:
    """Calling without complete_ids preserves backward-compatible behaviour."""
    scope = {"approved": True, "expires_at": _future(), "goal": "BL-007: something"}
    assert welcome.is_scope_active(scope) is True


# ── is_governed_scope / is_pipeline_gate_valid ────────────────────────────────


def test_is_governed_by_delivery_pipeline() -> None:
    assert welcome.is_governed_scope({"delivery_pipeline": "governed"}) is True


def test_is_governed_by_target_layer_m1() -> None:
    assert welcome.is_governed_scope({"target_layer": "M1"}) is True


def test_is_not_governed_standard() -> None:
    assert welcome.is_governed_scope({"delivery_pipeline": "standard"}) is False


def test_pipeline_gate_valid_matching_session() -> None:
    scope = {"session_id": "s1", "approved": True, "expires_at": _future()}
    pg = {
        "approved": True,
        "session_id": "s1",
        "expires_at": _future(),
        "pipeline": "deliver-full",
    }
    assert welcome.is_pipeline_gate_valid(scope, pg) is True


def test_pipeline_gate_invalid_session_mismatch() -> None:
    scope = {"session_id": "s1", "approved": True, "expires_at": _future()}
    pg = {"approved": True, "session_id": "other", "expires_at": _future()}
    assert welcome.is_pipeline_gate_valid(scope, pg) is False


def test_pipeline_gate_invalid_expired() -> None:
    scope = {"session_id": "s1", "approved": True, "expires_at": _future()}
    pg = {"approved": True, "session_id": "s1", "expires_at": _past()}
    assert welcome.is_pipeline_gate_valid(scope, pg) is False


# ── render_dashboard smoke tests ──────────────────────────────────────────────


def _patched_console(tmp_path: Path) -> Console:
    return Console(file=io.StringIO(), force_terminal=False)


def test_render_no_crash_all_files_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """render_dashboard() must not crash when all data files are absent."""
    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", _patched_console(tmp_path))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard()  # must not raise


def test_render_with_active_scope_shows_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """render_dashboard() shows the resume option when scope gate is active."""
    (tmp_path / "azoth.yaml").write_text("version: 0.1.0\nphase: 3\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "memory").mkdir()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future(),
                "goal": "BL-007: Session Welcome UX",
                "session_id": "2026-04-06-bl-007",
            }
        )
    )

    buf = io.StringIO()
    from rich.console import Console

    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard()

    output = buf.getvalue()
    assert "resume" in output
    assert "BL-007" in output


def test_render_with_backlog_shows_top_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """render_dashboard() surfaces top unblocked backlog items."""
    (tmp_path / "azoth.yaml").write_text("version: 0.1.0\nphase: 3\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "memory").mkdir()
    backlog_content = """
schema_version: 1
items:
  - id: T-001
    title: First task
    status: active
    priority: 1
    target_layer: infrastructure
    delivery_pipeline: standard
  - id: T-002
    title: Second task
    status: active
    priority: 2
    target_layer: M1
    delivery_pipeline: governed
  - id: T-DONE
    title: Done task
    status: complete
    priority: 3
"""
    (azoth_dir / "backlog.yaml").write_text(backlog_content)

    buf = io.StringIO()
    from rich.console import Console

    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard()

    output = buf.getvalue()
    assert "T-001" in output
    assert "T-002" in output
    assert "T-DONE" not in output


def test_render_governed_scope_shows_pipeline_gate_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Governed active scope without pipeline-gate.json shows OPEN in health."""
    (tmp_path / "azoth.yaml").write_text("version: 0.1.0\nphase: 3\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "memory").mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future(),
                "goal": "BL-099: Governed task",
                "session_id": "2026-04-07-bl-099",
                "delivery_pipeline": "governed",
            }
        )
    )

    buf = io.StringIO()
    from rich.console import Console

    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard()

    out = buf.getvalue()
    assert "Pipeline gate: OPEN" in out
    assert "/deliver-full" in out


def test_render_governed_scope_shows_pipeline_gate_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Governed scope with valid pipeline-gate.json shows OK and pipeline name."""
    (tmp_path / "azoth.yaml").write_text("version: 0.1.0\nphase: 3\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "memory").mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    sid = "2026-04-07-bl-099"
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future(),
                "goal": "BL-099: Governed task",
                "session_id": sid,
                "target_layer": "M1",
            }
        )
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "session_id": sid,
                "expires_at": _future(),
                "pipeline": "deliver-full",
            }
        )
    )

    buf = io.StringIO()
    from rich.console import Console

    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard()

    out = buf.getvalue()
    assert "Pipeline gate: OK" in out
    assert "deliver-full" in out


def test_plain_dashboard_includes_all_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--plain layout keeps section structure for SessionStart / model context."""
    (tmp_path / "azoth.yaml").write_text("version: 1\nphase: 3\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "memory").mkdir()
    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    buf = io.StringIO()
    from rich.console import Console

    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())
    out = buf.getvalue()
    assert "── System Health ──" in out
    assert "── Top Backlog" in out
    assert "── Last Session" in out
    assert "── START" in out
    assert "AZOTH" in out
    assert "AZOTH_SESSION_ORIENTATION_BEGIN" in out
    assert "AZOTH_SESSION_ORIENTATION_END" in out

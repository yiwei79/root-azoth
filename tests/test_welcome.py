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


# ── format_gate_ttl (P1-004) ─────────────────────────────────────────────────


def test_ttl_returns_empty_when_no_expires_at() -> None:
    assert welcome.format_gate_ttl({}) == ""
    assert welcome.format_gate_ttl({"approved": True}) == ""


def test_ttl_returns_empty_for_unparseable_date() -> None:
    assert welcome.format_gate_ttl({"expires_at": "not-a-date"}) == ""


def test_ttl_returns_expired_when_past() -> None:
    past = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    assert welcome.format_gate_ttl({"expires_at": past}) == "EXPIRED"


def test_ttl_returns_expired_with_injected_clock() -> None:
    """Clock injection: fixed expires_at with now > expires."""
    gate = {"expires_at": "2026-04-11T12:00:00+00:00"}
    now = datetime(2026, 4, 11, 13, 0, 0, tzinfo=timezone.utc)
    assert welcome.format_gate_ttl(gate, now=now) == "EXPIRED"


def test_ttl_returns_hours_and_minutes_with_injected_clock() -> None:
    """Clock injection: deterministic hours + minutes remaining."""
    gate = {"expires_at": "2026-04-11T14:30:00+00:00"}
    now = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
    result = welcome.format_gate_ttl(gate, now=now)
    assert result == "2h 30m remaining"


def test_ttl_returns_minutes_only_when_under_one_hour() -> None:
    gate = {"expires_at": "2026-04-11T12:45:00+00:00"}
    now = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
    result = welcome.format_gate_ttl(gate, now=now)
    assert result == "45m remaining"


def test_ttl_returns_less_than_one_minute() -> None:
    gate = {"expires_at": "2026-04-11T12:00:30+00:00"}
    now = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
    result = welcome.format_gate_ttl(gate, now=now)
    assert result == "<1m remaining"


def test_ttl_handles_z_suffix() -> None:
    gate = {"expires_at": "2026-04-11T14:00:00Z"}
    now = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
    result = welcome.format_gate_ttl(gate, now=now)
    assert result == "2h 00m remaining"


def test_ttl_boundary_exactly_zero() -> None:
    gate = {"expires_at": "2026-04-11T12:00:00+00:00"}
    now = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
    assert welcome.format_gate_ttl(gate, now=now) == "EXPIRED"


# ── TTL / EXPIRED in dashboard renders (P1-004 integration) ──────────────────


def test_plain_dashboard_shows_scope_ttl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plain layout shows remaining TTL for an active scope gate."""
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
                "goal": "P1-004: TTL test",
                "session_id": "ttl-test",
            }
        )
    )

    buf = io.StringIO()
    from rich.console import Console

    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())
    out = buf.getvalue()
    assert "Scope: ACTIVE" in out
    assert "remaining" in out


def test_plain_dashboard_shows_scope_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plain layout shows EXPIRED when scope gate has expired."""
    (tmp_path / "azoth.yaml").write_text("version: 0.1.0\nphase: 3\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "memory").mkdir()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _past(),
                "goal": "P1-004: Expired test",
                "session_id": "expired-test",
            }
        )
    )

    buf = io.StringIO()
    from rich.console import Console

    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())
    out = buf.getvalue()
    assert "Scope: EXPIRED" in out


def test_rich_dashboard_shows_scope_ttl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rich layout shows remaining TTL for an active scope gate."""
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
                "goal": "P1-004: TTL test",
                "session_id": "ttl-test",
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
    assert "Scope: ACTIVE" in out
    assert "remaining" in out


def test_rich_dashboard_shows_scope_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rich layout shows EXPIRED when scope gate has expired."""
    (tmp_path / "azoth.yaml").write_text("version: 0.1.0\nphase: 3\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "memory").mkdir()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _past(),
                "goal": "P1-004: Expired test",
                "session_id": "expired-test",
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
    assert "Scope: EXPIRED" in out


def test_plain_dashboard_pipeline_gate_shows_ttl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plain layout shows TTL for governed pipeline gate."""
    (tmp_path / "azoth.yaml").write_text("version: 0.1.0\nphase: 3\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "memory").mkdir()
    sid = "ttl-pipe-test"
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future(),
                "goal": "P1-004: Pipe TTL",
                "session_id": sid,
                "delivery_pipeline": "governed",
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
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())
    out = buf.getvalue()
    assert "Pipeline gate: OK" in out
    assert "remaining" in out


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


def test_resolve_strip_phase_milestone_uses_lifecycle() -> None:
    azoth = {"phase": 1, "milestone": "v0.2.0", "lifecycle_phase": 8}
    assert welcome.resolve_strip_phase(azoth, {}) == 8


def test_resolve_strip_phase_milestone_falls_back_to_roadmap() -> None:
    azoth = {"phase": 1, "milestone": "v0.2.0"}
    roadmap = {"lifecycle_phase": 8}
    assert welcome.resolve_strip_phase(azoth, roadmap) == 8


def test_resolve_strip_phase_legacy_uses_azoth_phase() -> None:
    azoth = {"phase": 3}
    assert welcome.resolve_strip_phase(azoth, {}) == 3


def test_header_phase_label_includes_milestone() -> None:
    azoth = {"milestone": "v0.2.0"}
    assert welcome.header_phase_label(azoth, 1) == "Phase 1 · v0.2.0"


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


# ── gather_unphased_initiatives ───────────────────────────────────────────────


def test_gather_unphased_initiatives_empty_when_no_initiatives() -> None:
    assert welcome.gather_unphased_initiatives({}) == []
    assert welcome.gather_unphased_initiatives({"versions": []}) == []


def test_gather_unphased_initiatives_filters_phase_null_only() -> None:
    data = {
        "initiatives": [
            {"id": "INI-MEM-001", "title": "Unphased A", "priority": "high", "phase": None},
            {"id": "INI-MEM-002", "title": "Assigned", "priority": "high", "phase": "v0.3.0"},
            {"id": "INI-PLT-001", "title": "Unphased B", "priority": "medium", "phase": None},
        ]
    }
    result = welcome.gather_unphased_initiatives(data)
    ids = [x["id"] for x in result]
    assert "INI-MEM-001" in ids
    assert "INI-PLT-001" in ids
    assert "INI-MEM-002" not in ids


def test_gather_unphased_initiatives_sorts_by_priority() -> None:
    data = {
        "initiatives": [
            {"id": "C", "title": "Low", "priority": "low", "phase": None},
            {"id": "A", "title": "High", "priority": "high", "phase": None},
            {"id": "B", "title": "Medium", "priority": "medium", "phase": None},
        ]
    }
    result = welcome.gather_unphased_initiatives(data)
    assert [x["id"] for x in result] == ["A", "B", "C"]


def test_gather_unphased_initiatives_skips_non_dict() -> None:
    data = {
        "initiatives": [
            "plain-string",
            {"id": "INI-MEM-001", "title": "Good", "priority": "high", "phase": None},
            42,
        ]
    }
    result = welcome.gather_unphased_initiatives(data)
    assert len(result) == 1
    assert result[0]["id"] == "INI-MEM-001"


# ── welcome backlog-panel fallback to initiatives ─────────────────────────────


def _setup_tmp_with_initiatives(tmp_path: Path) -> None:
    """Create minimal repo layout with initiatives in roadmap.yaml but empty backlog."""
    (tmp_path / "azoth.yaml").write_text("version: 0.1.6\nphase: 1\nmilestone: v0.2.0\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "memory").mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "roadmap.yaml").write_text(
        "schema_version: 2\n"
        "active_version: v0.2.0\n"
        "initiatives:\n"
        "  - id: INI-MEM-001\n"
        "    title: Verbatim storage\n"
        "    category: memory\n"
        "    phase: null\n"
        "    priority: high\n"
        "  - id: INI-PLT-001\n"
        "    title: Platform parity\n"
        "    category: platform\n"
        "    phase: null\n"
        "    priority: medium\n"
        "versions: []\n"
    )


def test_welcome_backlog_panel_shows_initiatives_when_top3_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Top Backlog panel shows unphased initiatives when backlog is empty."""
    _setup_tmp_with_initiatives(tmp_path)
    buf = io.StringIO()
    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard()
    out = buf.getvalue()
    assert "INI-MEM-001" in out
    assert "INI-PLT-001" in out


def test_welcome_plain_shows_initiatives_when_top3_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plain layout Top Backlog section shows unphased initiatives when backlog empty."""
    _setup_tmp_with_initiatives(tmp_path)
    buf = io.StringIO()
    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())
    out = buf.getvalue()
    assert "INI-MEM-001" in out
    assert "INI-PLT-001" in out


def test_welcome_plain_no_crash_when_no_initiatives_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plain layout must not crash when roadmap.yaml has no 'initiatives' key."""
    (tmp_path / "azoth.yaml").write_text("version: 0.1.6\nphase: 1\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "memory").mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "roadmap.yaml").write_text(
        "schema_version: 1\nactive_version: v0.2.0\nversions: []\n"
    )
    buf = io.StringIO()
    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())  # must not raise


def test_welcome_plain_shows_next_resume_for_parked_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "azoth.yaml").write_text("version: 1\nphase: 1\nmilestone: v0.2.0\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "memory").mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "run-ledger.local.yaml").write_text(
        "schema_version: 1\n"
        "sessions:\n"
        "  - session_id: sid-parked\n"
        "    backlog_id: P1-005\n"
        "    goal: Resume me\n"
        "    status: parked\n"
        "    ide: copilot\n"
        "    next_action: Resume this parked session\n"
        "    updated_at: 2026-04-10T10:00:00+00:00\n"
        "runs: []\n",
        encoding="utf-8",
    )

    buf = io.StringIO()
    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())
    out = buf.getvalue()
    assert "next resume sid-parked" in out
    assert "resume   → continue approved scope" not in out


def test_welcome_plain_shows_continuity_ok_for_matching_registry_scope_and_mirror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "azoth.yaml").write_text("version: 1\nphase: 1\nmilestone: v0.2.0\n")
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "memory").mkdir()
    (azoth_dir / "backlog.yaml").write_text("schema_version: 1\nitems: []\n")
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future(),
                "goal": "P1-001: Test goal",
                "session_id": "sid-match",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "session-state.md").write_text(
        "session_id: sid-match\n"
        "state: active\n"
        "last_ide: copilot\n"
        "timestamp: 2026-04-10T10:00:00+00:00\n"
        "active_task: Test\n"
        "active_files: []\n"
        "pending_decisions: []\n"
        "approved_scope: sid-match\n"
        "next_action: Resume\n",
        encoding="utf-8",
    )
    (azoth_dir / "run-ledger.local.yaml").write_text(
        "schema_version: 1\n"
        "sessions:\n"
        "  - session_id: sid-match\n"
        "    backlog_id: P1-001\n"
        "    goal: Test goal\n"
        "    status: active\n"
        "    ide: copilot\n"
        "    next_action: Continue\n"
        "    updated_at: 2026-04-10T10:00:00+00:00\n"
        "runs: []\n",
        encoding="utf-8",
    )

    buf = io.StringIO()
    monkeypatch.setattr(welcome, "ROOT", tmp_path)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False))
    monkeypatch.setattr(welcome, "git_info", lambda: ("test-repo", "main"))
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())
    out = buf.getvalue()
    assert "Continuity: OK  (sid-match)" in out
    assert "Sessions" in out
    assert "sid-match" in out

"""Tests for scripts/roadmap_dashboard.py — versioned roadmap Rich dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import roadmap_dashboard  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def test_load_roadmap_reads_repo_file() -> None:
    data = roadmap_dashboard.load_roadmap(REPO / ".azoth" / "roadmap.yaml")
    assert data.get("active_version")
    assert isinstance(data.get("versions"), list)
    assert len(data["versions"]) >= 1


def test_load_roadmap_missing_returns_empty() -> None:
    assert roadmap_dashboard.load_roadmap(REPO / "nonexistent-roadmap-xyz.yaml") == {}


def test_load_roadmap_invalid_yaml_returns_empty(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("{ not valid yaml [[[\n", encoding="utf-8")
    assert roadmap_dashboard.load_roadmap(bad) == {}


def test_load_roadmap_scalar_root_returns_empty(tmp_path: Path) -> None:
    """Non-dict YAML root normalizes to {} (load_roadmap contract)."""
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("bare-scalar-root\n", encoding="utf-8")
    assert roadmap_dashboard.load_roadmap(scalar) == {}


def test_load_roadmap_diag_reasons(tmp_path: Path) -> None:
    missing = roadmap_dashboard.load_roadmap_diag(REPO / "nonexistent-xyz-123.yaml")
    assert missing.data == {}
    assert missing.empty_reason == "missing"

    bad = tmp_path / "bad.yaml"
    bad.write_text("{ not valid yaml\n", encoding="utf-8")
    inv = roadmap_dashboard.load_roadmap_diag(bad)
    assert inv.data == {}
    assert inv.empty_reason is not None
    assert "yaml_parse_error" in inv.empty_reason

    scalar = tmp_path / "s.yaml"
    scalar.write_text("scalar-only\n", encoding="utf-8")
    nd = roadmap_dashboard.load_roadmap_diag(scalar)
    assert nd.data == {}
    assert nd.empty_reason is not None
    assert "non_dict_root" in nd.empty_reason

    empty_map = tmp_path / "empty.yaml"
    empty_map.write_text("{}\n", encoding="utf-8")
    em = roadmap_dashboard.load_roadmap_diag(empty_map)
    assert em.data == {}
    assert em.empty_reason == "empty_mapping"


def test_render_dashboard_differentiates_empty_causes(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    miss = tmp_path / "missing.yaml"
    buf = io.StringIO()
    c = Console(record=True, width=100, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=miss, console=c)
    assert "not found" in c.export_text().lower()

    bad = tmp_path / "bad.yaml"
    bad.write_text("{ not valid yaml [[[\n", encoding="utf-8")
    buf2 = io.StringIO()
    c2 = Console(record=True, width=100, file=buf2)
    roadmap_dashboard.render_dashboard(roadmap_path=bad, console=c2)
    assert "Invalid YAML" in c2.export_text()

    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("only-scalar\n", encoding="utf-8")
    buf3 = io.StringIO()
    c3 = Console(record=True, width=100, file=buf3)
    roadmap_dashboard.render_dashboard(roadmap_path=scalar, console=c3)
    assert "mapping" in c3.export_text().lower()

    empty = tmp_path / "empty_map.yaml"
    empty.write_text("{}\n", encoding="utf-8")
    buf4 = io.StringIO()
    c4 = Console(record=True, width=100, file=buf4)
    roadmap_dashboard.render_dashboard(roadmap_path=empty, console=c4)
    assert "empty mapping" in c4.export_text().lower()


def test_build_version_body_includes_tasks() -> None:
    path = REPO / ".azoth" / "roadmap.yaml"
    with path.open() as f:
        data = yaml.safe_load(f)
    v004 = next(x for x in data["versions"] if x["id"] == "v0.0.4")
    body = roadmap_dashboard.build_version_body(v004)
    assert "P4-001" in body or "README" in body
    assert "Delivered" in body


def test_render_dashboard_smoke() -> None:
    import io

    from rich.console import Console

    buf = io.StringIO()
    console = Console(record=True, width=100, file=buf)
    roadmap_dashboard.render_dashboard(
        roadmap_path=REPO / ".azoth" / "roadmap.yaml",
        console=console,
    )
    out = console.export_text()
    assert "ROADMAP" in out
    assert "v0.0.6" in out
    assert "v0.0.7" in out


def test_status_style_known() -> None:
    assert "green" in roadmap_dashboard._status_style("complete")


def test_render_dashboard_versions_not_list_shows_error(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "active_version: v0\nversions: {not: a list}\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    console = Console(record=True, width=100, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=bad, console=console)
    out = console.export_text()
    assert "Invalid `versions`" in out
    assert "expected list" in out


def test_render_dashboard_skips_non_dict_version_entry(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "active_version: v0\n"
        "versions:\n"
        "  - plain-string-version\n"
        "  - id: v-fixed\n"
        "    status: complete\n"
        "    goal: ok\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    console = Console(record=True, width=100, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=bad, console=console)
    out = console.export_text()
    assert "Skipping versions[0]" in out
    assert "v-fixed" in out
    assert "ok" in out


def test_build_version_body_schema_warning_for_non_dict_task() -> None:
    version: dict = {
        "status": "complete",
        "id": "v0.0.x",
        "completed_tasks": ["not-a-dict", {"id": "T1", "title": "Fine"}],
        "tasks": [],
    }
    body = roadmap_dashboard.build_version_body(version)
    assert "schema:" in body
    assert "completed_tasks[0]" in body
    assert "T1" in body
    assert "Fine" in body


def test_build_version_body_tasks_block_non_list() -> None:
    version: dict = {
        "status": "active",
        "id": "v0.0.x",
        "completed_tasks": [],
        "tasks": "not-a-list",
    }
    body = roadmap_dashboard.build_version_body(version)
    assert "schema:" in body
    assert "tasks: expected list" in body


def test_build_version_body_escapes_rich_markup_in_task_fields() -> None:
    version: dict = {
        "status": "complete",
        "id": "v0.0.x",
        "completed_tasks": [
            {"id": "T1", "title": "[bold]fake[/bold]", "note": "[red]x[/]"},
        ],
        "tasks": [],
    }
    body = roadmap_dashboard.build_version_body(version)
    assert "\\[bold]fake\\[/bold]" in body
    assert "fake" in body


def test_schema_warnings_cap_message() -> None:
    bad_tasks = [f"bad-{i}" for i in range(roadmap_dashboard.MAX_SCHEMA_WARNINGS + 8)]
    version: dict = {
        "status": "complete",
        "id": "v0.0.x",
        "completed_tasks": bad_tasks,
        "tasks": [],
    }
    body = roadmap_dashboard.build_version_body(version)
    assert "more schema warning" in body


def test_normalize_task_entries_non_list() -> None:
    valid, warnings = roadmap_dashboard._normalize_task_entries("oops", block_label="tasks")
    assert valid == []
    assert "expected list" in warnings[0]


def test_build_version_body_non_dict_version() -> None:
    body = roadmap_dashboard.build_version_body("not-a-mapping")
    assert "Invalid version block" in body
    assert "str" in body


def test_render_version_panel_non_dict() -> None:
    panel = roadmap_dashboard.render_version_panel(["list-not-dict"])
    assert "Invalid version" in str(panel.renderable)


def test_render_header_non_dict_root() -> None:
    panel = roadmap_dashboard.render_header("oops")
    assert "Invalid roadmap root" in str(panel.renderable)


def test_format_task_block_non_dict_entry_still_renders_valid() -> None:
    """BL-022: malformed entries after normalization must not crash Rich render."""
    bad_entries: list = [{"id": "ok", "title": "Fine"}, "string-instead-of-dict"]
    lines = roadmap_dashboard._format_task_block(
        "Upcoming",
        bad_entries,  # type: ignore[arg-type]
        done=False,
        schema_warnings=[],
    )
    joined = "\n".join(lines)
    assert "Fine" in joined
    assert "expected mapping" in joined
    assert "str" in joined

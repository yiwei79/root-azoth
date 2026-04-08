"""Tests for scripts/roadmap_dashboard.py — versioned roadmap Rich dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
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

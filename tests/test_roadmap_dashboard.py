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


def test_build_version_body_includes_carried_forward_section() -> None:
    version = {
        "id": "v0.2.0-p2",
        "status": "complete",
        "completed_tasks": [],
        "tasks": [],
        "deferred_tasks": [
            {
                "id": "T-KRP-A",
                "title": "Karpathy follow-on",
                "deferred_to": "v0.2.0-p3",
            }
        ],
    }
    body = roadmap_dashboard.build_version_body(version)
    assert "Carried Forward" in body
    assert "T-KRP-A" in body


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
    assert "v0.2.0" in out


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


# ── initiatives: gather_initiatives ──────────────────────────────────────────


def test_gather_initiatives_empty_when_no_key() -> None:
    """data without 'initiatives' key returns empty dict."""
    assert roadmap_dashboard.gather_initiatives({}) == {}
    assert roadmap_dashboard.gather_initiatives({"versions": []}) == {}


def test_gather_initiatives_groups_by_category() -> None:
    data = {
        "initiatives": [
            {"id": "INI-MEM-001", "title": "Verbatim storage", "category": "memory"},
            {"id": "INI-MEM-002", "title": "Temporal KG", "category": "memory"},
            {"id": "INI-PLT-001", "title": "Platform parity", "category": "platform"},
        ]
    }
    result = roadmap_dashboard.gather_initiatives(data)
    assert set(result.keys()) == {"memory", "platform"}
    assert len(result["memory"]) == 2
    assert len(result["platform"]) == 1
    assert result["memory"][0]["id"] == "INI-MEM-001"


def test_gather_initiatives_skips_non_dict_entries() -> None:
    data = {
        "initiatives": [
            "plain-string",
            {"id": "INI-MEM-001", "title": "Good", "category": "memory"},
            42,
        ]
    }
    result = roadmap_dashboard.gather_initiatives(data)
    assert list(result.keys()) == ["memory"]
    assert len(result["memory"]) == 1


def test_gather_initiatives_uncategorized_fallback() -> None:
    data = {
        "initiatives": [
            {"id": "INI-XYZ-001", "title": "No category"},
        ]
    }
    result = roadmap_dashboard.gather_initiatives(data)
    assert "uncategorized" in result
    assert result["uncategorized"][0]["id"] == "INI-XYZ-001"


def test_gather_initiatives_filters_phase_null_history_only_entries() -> None:
    data = {
        "initiatives": [
            {
                "id": "INI-HIST-001",
                "title": "Historical only",
                "category": "memory",
                "phase": None,
                "slices": [{"task_ref": "P1-020", "status": "complete", "role": "historical"}],
            },
            {
                "id": "INI-LIVE-001",
                "title": "Live",
                "category": "memory",
                "phase": None,
                "slices": [{"task_ref": "T-KRP-A", "status": "planned", "role": "primary"}],
            },
        ]
    }
    result = roadmap_dashboard.gather_initiatives(data)
    assert [item["id"] for item in result["memory"]] == ["INI-LIVE-001"]


def test_build_drift_warnings_detects_stale_open_tasks_and_scheduled_initiatives() -> None:
    roadmap = {
        "versions": [
            {
                "id": "v0.2.0-p2",
                "status": "complete",
                "tasks": [{"id": "P1-020", "title": "Stale open task"}],
                "completed_tasks": [],
            }
        ],
        "initiatives": [
            {
                "id": "INI-MEM-001",
                "phase": "v0.2.0-p2",
                "task_ref": "P1-020",
                "slices": [{"task_ref": "P1-020", "status": "complete", "role": "historical"}],
            }
        ],
    }
    backlog = {
        "items": [
            {"id": "P1-020", "roadmap_ref": "P1-020", "status": "complete"},
        ]
    }
    warnings = roadmap_dashboard.build_drift_warnings(roadmap, backlog=backlog)
    assert any("backlog-complete" in warning for warning in warnings)
    assert any("version is complete" in warning for warning in warnings)
    assert any("INI-MEM-001" in warning for warning in warnings)


# ── initiatives: render_initiatives_panel ────────────────────────────────────


def test_render_initiatives_panel_none_when_empty() -> None:
    """render_initiatives_panel returns None for empty input."""
    assert roadmap_dashboard.render_initiatives_panel({}) is None


def test_render_initiatives_panel_contains_ids_and_titles() -> None:
    import io

    from rich.console import Console

    by_category = {
        "memory": [
            {"id": "INI-MEM-001", "title": "Verbatim storage", "priority": "high"},
        ],
        "platform": [
            {"id": "INI-PLT-001", "title": "Platform parity", "priority": "medium"},
        ],
    }
    panel = roadmap_dashboard.render_initiatives_panel(by_category)
    assert panel is not None
    buf = io.StringIO()
    c = Console(record=True, width=120, file=buf)
    c.print(panel)
    out = c.export_text()
    assert "INI-MEM-001" in out
    assert "Verbatim storage" in out
    assert "INI-PLT-001" in out
    assert "Platform parity" in out


# ── initiatives: render_dashboard integration ─────────────────────────────────


def test_render_dashboard_shows_initiatives_zone(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    roadmap_yaml = tmp_path / "roadmap.yaml"
    roadmap_yaml.write_text(
        "schema_version: 2\n"
        "active_version: v0.2.0\n"
        "versions:\n"
        "  - id: v0.2.0\n"
        "    status: active\n"
        "    goal: Test milestone\n"
        "    tasks: []\n"
        "    completed_tasks: []\n"
        "initiatives:\n"
        "  - id: INI-MEM-001\n"
        "    title: Verbatim storage\n"
        "    category: memory\n"
        "    phase: null\n"
        "    priority: high\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    c = Console(record=True, width=120, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=roadmap_yaml, console=c)
    out = c.export_text()
    assert "INI-MEM-001" in out


def test_render_dashboard_shows_drift_warning_panel(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    roadmap_yaml = tmp_path / "roadmap.yaml"
    backlog_yaml = tmp_path / "backlog.yaml"
    roadmap_yaml.write_text(
        "schema_version: 2\n"
        "active_version: v0.2.0-p3\n"
        "versions:\n"
        "  - id: v0.2.0-p3\n"
        "    status: complete\n"
        "    tasks:\n"
        "      - id: P1-020\n"
        "        title: Stale open task\n"
        "    completed_tasks: []\n"
        "initiatives:\n"
        "  - id: INI-MEM-001\n"
        "    title: Memory\n"
        "    phase: v0.2.0-p3\n"
        "    task_ref: P1-020\n"
        "    slices:\n"
        "      - task_ref: P1-020\n"
        "        status: complete\n"
        "        role: historical\n",
        encoding="utf-8",
    )
    backlog_yaml.write_text(
        "schema_version: 1\n"
        "items:\n"
        "  - id: P1-020\n"
        "    roadmap_ref: P1-020\n"
        "    status: complete\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    c = Console(record=True, width=120, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=roadmap_yaml, console=c)
    out = c.export_text()
    assert "Planning Drift Warnings" in out
    assert "P1-020" in out
    assert "INI-MEM-001" in out


def test_render_dashboard_surfaces_tracked_planning_bank_panel(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    (azoth_dir / "design-banks").mkdir()
    (azoth_dir / "initiative-banks").mkdir()
    roadmap_yaml = azoth_dir / "roadmap.yaml"
    roadmap_yaml.write_text(
        "schema_version: 2\n"
        "active_version: v0.2.0\n"
        "versions:\n"
        "  - id: v0.2.0\n"
        "    status: active\n"
        "    goal: Test milestone\n"
        "    tasks: []\n"
        "    completed_tasks: []\n",
        encoding="utf-8",
    )
    (azoth_dir / "design-banks" / "planning-banks-layer.yaml").write_text(
        "schema_version: 1\n"
        "bank_type: design\n"
        "id: planning-banks-layer\n"
        "title: Planning banks layer\n"
        "status: active_refinement\n"
        "source_proposal_refs:\n"
        "  - .azoth/proposals/local-draft.yaml\n"
        "readiness:\n"
        "  readiness_status: continue_refinement\n"
        "  target_route: dashboard_routing_surfacing\n"
        "  human_decision: approved\n",
        encoding="utf-8",
    )
    (azoth_dir / "initiative-banks" / "INI-TEST.yaml").write_text(
        "schema_version: 1\n"
        "bank_type: initiative\n"
        "initiative_id: INI-TEST\n"
        "title: Initiative test bank\n"
        "status: active_refinement\n"
        "source_proposal_refs:\n"
        "  - .azoth/proposals/ignored-draft.yaml\n"
        "readiness:\n"
        "  readiness_status: continue_research\n"
        "  human_decision: approved\n"
        "  hydration_recommendation: refine candidate before hydration\n"
        "  candidate_first_slice: slice-test\n"
        "candidate_slices:\n"
        "  - candidate_id: slice-test\n"
        "    proposed_task_id: TBD-TEST\n"
        "    status: candidate\n",
        encoding="utf-8",
    )

    buf = io.StringIO()
    c = Console(record=True, width=120, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=roadmap_yaml, console=c)
    out = c.export_text()
    assert "Planning Banks" in out
    assert "planning-banks-layer" in out
    assert "INI-TEST" in out
    assert "human: approved" in out
    assert "Proposal drafts are source history" in out
    assert "hydrate explicitly before backlog/spec work" in out
    assert ".azoth/proposals/local-draft.yaml" not in out
    assert ".azoth/proposals/ignored-draft.yaml" not in out


def test_render_dashboard_no_crash_when_no_initiatives(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    roadmap_yaml = tmp_path / "roadmap.yaml"
    roadmap_yaml.write_text(
        "schema_version: 1\n"
        "active_version: v0.2.0\n"
        "versions:\n"
        "  - id: v0.2.0\n"
        "    status: active\n"
        "    goal: Test\n"
        "    tasks: []\n"
        "    completed_tasks: []\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    c = Console(record=True, width=120, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=roadmap_yaml, console=c)  # must not raise


def test_filter_roadmap_cross_section_theme_uses_initiative_links() -> None:
    data = {
        "active_version": "v0.2.0",
        "versions": [
            {
                "id": "v0.2.0-p1",
                "status": "complete",
                "goal": "Phase 1",
                "completed_tasks": [
                    {"id": "P1-011", "title": "Historical efficiency task"},
                    {"id": "P1-020", "title": "Historical memory task"},
                ],
                "tasks": [],
            },
            {
                "id": "v0.2.0-p3",
                "status": "active",
                "goal": "Phase 3",
                "completed_tasks": [],
                "tasks": [
                    {"id": "T-KRP-A", "title": "Karpathy follow-on"},
                    {"id": "P1-020", "title": "Memory carry-forward"},
                ],
            },
        ],
        "initiatives": [
            {
                "id": "INI-KRP-001",
                "title": "Karpathy",
                "category": "efficiency",
                "phase": None,
                "dimensions": {"themes": ["E"], "tracks": ["autonomous-quality"]},
                "slices": [{"task_ref": "T-KRP-A", "status": "planned", "role": "primary"}],
            },
            {
                "id": "INI-EFF-001",
                "title": "Token efficiency",
                "category": "efficiency",
                "phase": None,
                "dimensions": {"themes": ["E"], "tracks": ["context-budget"]},
                "task_ref": "P1-011",
                "slices": [{"task_ref": "P1-011", "status": "complete", "role": "historical"}],
            },
            {
                "id": "INI-MEM-001",
                "title": "Memory",
                "category": "memory",
                "phase": None,
                "dimensions": {"themes": ["C"], "tracks": ["verbatim-storage"]},
                "task_ref": "P1-020",
                "slices": [{"task_ref": "P1-020", "status": "planned", "role": "primary"}],
            },
        ],
    }

    filtered = roadmap_dashboard.filter_roadmap_cross_section(data, theme="E")
    initiative_ids = [item["id"] for item in filtered["initiatives"]]
    assert initiative_ids == ["INI-KRP-001", "INI-EFF-001"]
    version_ids = [version["id"] for version in filtered["versions"]]
    assert version_ids == ["v0.2.0-p1", "v0.2.0-p3"]
    assert [task["id"] for task in filtered["versions"][0]["completed_tasks"]] == ["P1-011"]
    assert [task["id"] for task in filtered["versions"][1]["tasks"]] == ["T-KRP-A"]


def test_filter_roadmap_cross_section_drops_version_prose_with_unmatched_refs() -> None:
    data = {
        "active_version": "v0.2.0-p3",
        "versions": [
            {
                "id": "v0.2.0-p3",
                "status": "active",
                "goal": "Ship T-E-001 now; T-M-001 remains deferred.",
                "note": "Coordinate INI-E-001 with INI-M-001 before closeout.",
                "completed_tasks": [],
                "tasks": [
                    {"id": "T-E-001", "title": "Efficiency slice"},
                    {"id": "T-M-001", "title": "Memory slice"},
                ],
            }
        ],
        "initiatives": [
            {
                "id": "INI-E-001",
                "title": "Efficiency",
                "category": "efficiency",
                "phase": None,
                "task_ref": "T-E-001",
                "dimensions": {"themes": ["E"], "tracks": ["context-budget"]},
            },
            {
                "id": "INI-M-001",
                "title": "Memory",
                "category": "memory",
                "phase": None,
                "task_ref": "T-M-001",
                "dimensions": {"themes": ["C"], "tracks": ["verbatim-storage"]},
            },
        ],
    }

    filtered = roadmap_dashboard.filter_roadmap_cross_section(data, theme="E")
    version = filtered["versions"][0]
    assert [task["id"] for task in version["tasks"]] == ["T-E-001"]
    assert "goal" not in version
    assert "note" not in version


def test_filter_roadmap_cross_section_drops_generic_version_prose_in_filtered_mode() -> None:
    data = {
        "active_version": "v0.2.0-p3",
        "versions": [
            {
                "id": "v0.2.0-p3",
                "status": "active",
                "goal": "Phase 3 coordinates roadmap stabilization work.",
                "note": "This milestone closes the loop on related platform follow-ons.",
                "completed_tasks": [],
                "tasks": [
                    {"id": "T-E-001", "title": "Efficiency slice"},
                ],
            }
        ],
        "initiatives": [
            {
                "id": "INI-E-001",
                "title": "Efficiency",
                "category": "efficiency",
                "phase": None,
                "task_ref": "T-E-001",
                "dimensions": {"themes": ["E"], "tracks": ["context-budget"]},
            }
        ],
    }

    filtered = roadmap_dashboard.filter_roadmap_cross_section(data, theme="E")
    version = filtered["versions"][0]
    assert [task["id"] for task in version["tasks"]] == ["T-E-001"]
    assert "goal" not in version
    assert "note" not in version


def test_filter_roadmap_cross_section_sanitizes_task_row_text_with_unmatched_refs() -> None:
    data = {
        "active_version": "v0.2.0-p3",
        "versions": [
            {
                "id": "v0.2.0-p3",
                "status": "active",
                "goal": "Phase 3",
                "completed_tasks": [],
                "tasks": [
                    {
                        "id": "T-E-001",
                        "title": "Efficiency slice paired with T-M-001",
                        "note": "Coordinate with INI-M-001 before closeout.",
                        "deferred_from": "T-M-001",
                    },
                    {"id": "T-M-001", "title": "Memory slice"},
                ],
            }
        ],
        "initiatives": [
            {
                "id": "INI-E-001",
                "title": "Efficiency",
                "category": "efficiency",
                "phase": None,
                "task_ref": "T-E-001",
                "dimensions": {"themes": ["E"], "tracks": ["context-budget"]},
            },
            {
                "id": "INI-M-001",
                "title": "Memory",
                "category": "memory",
                "phase": None,
                "task_ref": "T-M-001",
                "dimensions": {"themes": ["C"], "tracks": ["verbatim-storage"]},
            },
        ],
    }

    filtered = roadmap_dashboard.filter_roadmap_cross_section(data, theme="E")
    task = filtered["versions"][0]["tasks"][0]
    assert task["id"] == "T-E-001"
    assert "T-M-001" not in task["title"]
    assert "paired with" in task["title"]
    assert roadmap_dashboard.FILTERED_REF_PLACEHOLDER in task["title"]
    assert "INI-M-001" not in task["note"]
    assert "Coordinate with" in task["note"]
    assert roadmap_dashboard.FILTERED_REF_PLACEHOLDER in task["note"]
    assert task["deferred_from"] == roadmap_dashboard.FILTERED_REF_PLACEHOLDER


def test_render_dashboard_theme_filter_shows_only_matching_items(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    roadmap_yaml = tmp_path / "roadmap.yaml"
    roadmap_yaml.write_text(
        "schema_version: 2\n"
        "active_version: v0.2.0\n"
        "versions:\n"
        "  - id: v0.2.0-p1\n"
        "    status: complete\n"
        "    goal: Phase 1\n"
        "    completed_tasks:\n"
        "      - id: P1-011\n"
        "        title: Historical efficiency task\n"
        "      - id: P1-020\n"
        "        title: Historical memory task\n"
        "    tasks: []\n"
        "  - id: v0.2.0-p3\n"
        "    status: active\n"
        "    goal: Phase 3\n"
        "    completed_tasks: []\n"
        "    tasks:\n"
        "      - id: T-KRP-A\n"
        "        title: Karpathy follow-on\n"
        "      - id: P1-020\n"
        "        title: Memory carry-forward\n"
        "initiatives:\n"
        "  - id: INI-KRP-001\n"
        "    title: Karpathy\n"
        "    category: efficiency\n"
        "    phase: null\n"
        "    dimensions:\n"
        "      themes: [E]\n"
        "      categories: [efficiency]\n"
        "      tracks: [autonomous-quality]\n"
        "    slices:\n"
        "      - task_ref: T-KRP-A\n"
        "        status: planned\n"
        "        role: primary\n"
        "  - id: INI-EFF-001\n"
        "    title: Token efficiency\n"
        "    category: efficiency\n"
        "    phase: null\n"
        "    task_ref: P1-011\n"
        "    dimensions:\n"
        "      themes: [E]\n"
        "      categories: [efficiency]\n"
        "      tracks: [context-budget]\n"
        "    slices:\n"
        "      - task_ref: P1-011\n"
        "        status: complete\n"
        "        role: historical\n"
        "  - id: INI-MEM-001\n"
        "    title: Memory\n"
        "    category: memory\n"
        "    phase: null\n"
        "    task_ref: P1-020\n"
        "    dimensions:\n"
        "      themes: [C]\n"
        "      categories: [memory]\n"
        "      tracks: [verbatim-storage]\n"
        "    slices:\n"
        "      - task_ref: P1-020\n"
        "        status: planned\n"
        "        role: primary\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    console = Console(record=True, width=120, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=roadmap_yaml, console=console, theme="E")
    out = console.export_text()
    assert "theme=E" in out
    assert "INI-KRP-001" in out
    assert "T-KRP-A" in out
    assert "INI-EFF-001" not in out
    assert "P1-011" in out
    assert "INI-MEM-001" not in out
    assert "P1-020" not in out


def test_render_dashboard_theme_filter_hides_version_prose_leaks(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    roadmap_yaml = tmp_path / "roadmap.yaml"
    roadmap_yaml.write_text(
        "schema_version: 2\n"
        "active_version: v0.2.0-p3\n"
        "versions:\n"
        "  - id: v0.2.0-p3\n"
        "    status: active\n"
        "    goal: Ship T-E-001 now; T-M-001 remains deferred.\n"
        "    note: Coordinate INI-E-001 with INI-M-001 before closeout.\n"
        "    completed_tasks: []\n"
        "    tasks:\n"
        "      - id: T-E-001\n"
        "        title: Efficiency slice\n"
        "      - id: T-M-001\n"
        "        title: Memory slice\n"
        "initiatives:\n"
        "  - id: INI-E-001\n"
        "    title: Efficiency\n"
        "    category: efficiency\n"
        "    phase: null\n"
        "    task_ref: T-E-001\n"
        "    dimensions:\n"
        "      themes: [E]\n"
        "      tracks: [context-budget]\n"
        "  - id: INI-M-001\n"
        "    title: Memory\n"
        "    category: memory\n"
        "    phase: null\n"
        "    task_ref: T-M-001\n"
        "    dimensions:\n"
        "      themes: [C]\n"
        "      tracks: [verbatim-storage]\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    console = Console(record=True, width=120, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=roadmap_yaml, console=console, theme="E")
    out = console.export_text()
    assert "theme=E" in out
    assert "T-E-001" in out
    assert "Ship T-E-001 now; T-M-001 remains deferred." not in out
    assert "Coordinate INI-E-001 with INI-M-001 before closeout." not in out
    assert "T-M-001" not in out
    assert "INI-M-001" not in out


def test_render_dashboard_theme_filter_sanitizes_task_row_ref_text(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    roadmap_yaml = tmp_path / "roadmap.yaml"
    roadmap_yaml.write_text(
        "schema_version: 2\n"
        "active_version: v0.2.0-p3\n"
        "versions:\n"
        "  - id: v0.2.0-p3\n"
        "    status: active\n"
        "    goal: Phase 3\n"
        "    completed_tasks: []\n"
        "    tasks:\n"
        "      - id: T-E-001\n"
        "        title: Efficiency slice paired with T-M-001\n"
        "        note: Coordinate with INI-M-001 before closeout.\n"
        "        deferred_from: T-M-001\n"
        "      - id: T-M-001\n"
        "        title: Memory slice\n"
        "initiatives:\n"
        "  - id: INI-E-001\n"
        "    title: Efficiency\n"
        "    category: efficiency\n"
        "    phase: null\n"
        "    task_ref: T-E-001\n"
        "    dimensions:\n"
        "      themes: [E]\n"
        "      tracks: [context-budget]\n"
        "  - id: INI-M-001\n"
        "    title: Memory\n"
        "    category: memory\n"
        "    phase: null\n"
        "    task_ref: T-M-001\n"
        "    dimensions:\n"
        "      themes: [C]\n"
        "      tracks: [verbatim-storage]\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    console = Console(record=True, width=120, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=roadmap_yaml, console=console, theme="E")
    out = console.export_text()
    assert "T-E-001" in out
    assert "paired with" in out
    assert roadmap_dashboard.FILTERED_REF_PLACEHOLDER in out
    assert "T-M-001" not in out
    assert "INI-M-001" not in out


def test_render_dashboard_without_filter_keeps_version_prose_refs(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    roadmap_yaml = tmp_path / "roadmap.yaml"
    roadmap_yaml.write_text(
        "schema_version: 2\n"
        "active_version: v0.2.0-p3\n"
        "versions:\n"
        "  - id: v0.2.0-p3\n"
        "    status: active\n"
        "    goal: Ship T-E-001 now; T-M-001 remains deferred.\n"
        "    note: Coordinate INI-E-001 with INI-M-001 before closeout.\n"
        "    completed_tasks: []\n"
        "    tasks:\n"
        "      - id: T-E-001\n"
        "        title: Efficiency slice\n"
        "      - id: T-M-001\n"
        "        title: Memory slice\n"
        "initiatives:\n"
        "  - id: INI-E-001\n"
        "    title: Efficiency\n"
        "    category: efficiency\n"
        "    phase: null\n"
        "    task_ref: T-E-001\n"
        "    dimensions:\n"
        "      themes: [E]\n"
        "      tracks: [context-budget]\n"
        "  - id: INI-M-001\n"
        "    title: Memory\n"
        "    category: memory\n"
        "    phase: null\n"
        "    task_ref: T-M-001\n"
        "    dimensions:\n"
        "      themes: [C]\n"
        "      tracks: [verbatim-storage]\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    console = Console(record=True, width=120, file=buf)
    roadmap_dashboard.render_dashboard(roadmap_path=roadmap_yaml, console=console)
    out = console.export_text()
    assert "Ship T-E-001 now; T-M-001 remains deferred." in out
    assert "Coordinate INI-E-001 with INI-M-001 before closeout." in out
    assert "T-M-001" in out
    assert "INI-M-001" in out


def test_render_dashboard_track_filter_shows_only_matching_items(tmp_path: Path) -> None:
    import io

    from rich.console import Console

    roadmap_yaml = tmp_path / "roadmap.yaml"
    roadmap_yaml.write_text(
        "schema_version: 2\n"
        "active_version: v0.2.0\n"
        "versions:\n"
        "  - id: v0.2.0-p3\n"
        "    status: active\n"
        "    goal: Phase 3\n"
        "    tasks:\n"
        "      - id: T-KRP-A\n"
        "        title: Karpathy follow-on\n"
        "      - id: P1-011\n"
        "        title: Token efficiency\n"
        "    completed_tasks: []\n"
        "initiatives:\n"
        "  - id: INI-KRP-001\n"
        "    title: Karpathy\n"
        "    category: efficiency\n"
        "    phase: null\n"
        "    dimensions:\n"
        "      themes: [E]\n"
        "      categories: [efficiency]\n"
        "      tracks: [autonomous-quality]\n"
        "    slices:\n"
        "      - task_ref: T-KRP-A\n"
        "        status: planned\n"
        "        role: primary\n"
        "  - id: INI-EFF-001\n"
        "    title: Token efficiency\n"
        "    category: efficiency\n"
        "    phase: null\n"
        "    task_ref: P1-011\n"
        "    dimensions:\n"
        "      themes: [E]\n"
        "      categories: [efficiency]\n"
        "      tracks: [context-budget]\n"
        "    slices:\n"
        "      - task_ref: P1-011\n"
        "        status: complete\n"
        "        role: historical\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    console = Console(record=True, width=120, file=buf)
    roadmap_dashboard.render_dashboard(
        roadmap_path=roadmap_yaml,
        console=console,
        track="autonomous-quality",
    )
    out = console.export_text()
    assert "track=autonomous-quality" in out
    assert "INI-KRP-001" in out
    assert "T-KRP-A" in out
    assert "INI-EFF-001" not in out
    assert "P1-011" not in out

"""Tests for scripts/initiative_scaffold.py."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "initiative_scaffold.py"


def _write_repo(
    base: Path,
    *,
    active_version: str,
    versions_content: str,
    initiatives_content: str = "[]",
    backlog_items: str = "[]",
) -> tuple[Path, Path]:
    roadmap = {
        "active_version": active_version,
        "versions": yaml.safe_load(versions_content) or [],
        "initiatives": yaml.safe_load(initiatives_content) or [],
    }
    backlog = {
        "schema_version": 1,
        "items": yaml.safe_load(backlog_items) or [],
    }
    roadmap_path = base / "roadmap.yaml"
    backlog_path = base / "backlog.yaml"
    roadmap_path.write_text(yaml.safe_dump(roadmap, sort_keys=False), encoding="utf-8")
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")
    return roadmap_path, backlog_path


def test_scaffold_initiative_creates_phase_null_stubbed_tasks(tmp_path: Path) -> None:
    roadmap_path, backlog_path = _write_repo(
        tmp_path,
        active_version="v0.2.0-p3",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p3
              status: active
              tasks: []
            """
        ).rstrip(),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--id",
            "INI-KRP-001",
            "--title",
            "Karpathy Principles",
            "--tasks",
            "3",
            "--theme",
            "E",
            "--category",
            "efficiency",
            "--track",
            "autonomous-quality",
            "--track",
            "goal-grounding",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--created-date",
            "2026-04-22",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == "INI-KRP-001"

    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    active = roadmap["versions"][0]
    assert [item["id"] for item in active["tasks"]] == ["T-KRP-A", "T-KRP-B", "T-KRP-C"]
    assert active["tasks"][0]["title"] == "Karpathy Principles [stub A]"
    assert active["tasks"][0]["status"] == "planned"
    assert active["tasks"][0]["initiative_ref"] == "INI-KRP-001"

    initiative = roadmap["initiatives"][0]
    assert initiative["id"] == "INI-KRP-001"
    assert initiative["phase"] is None
    assert initiative["dimensions"] == {
        "themes": ["E"],
        "categories": ["efficiency"],
        "tracks": ["autonomous-quality", "goal-grounding"],
    }
    assert initiative["slices"] == [
        {"task_ref": "T-KRP-A", "phase": None, "role": "primary", "status": "planned"},
        {"task_ref": "T-KRP-B", "phase": None, "role": "follow-on", "status": "planned"},
        {"task_ref": "T-KRP-C", "phase": None, "role": "follow-on", "status": "planned"},
    ]

    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    assert backlog["items"] == []


def test_scaffold_initiative_can_add_backlog_rows_for_stubbed_tasks(tmp_path: Path) -> None:
    roadmap_path, backlog_path = _write_repo(
        tmp_path,
        active_version="v0.2.0-p3",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p3
              status: active
              tasks: []
            """
        ).rstrip(),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--id",
            "INI-RST-007",
            "--title",
            "Fresh initiative",
            "--tasks",
            "2",
            "--task-title",
            "First planned slice",
            "--task-title",
            "Second planned slice",
            "--backlog-items",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--created-date",
            "2026-04-22",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    active = roadmap["versions"][0]
    assert active["tasks"][0]["title"] == "First planned slice"
    assert active["tasks"][1]["title"] == "Second planned slice"

    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    assert [item["id"] for item in backlog["items"]] == ["T-RST-A", "T-RST-B"]
    assert backlog["items"][0]["roadmap_ref"] == "T-RST-A"
    assert backlog["items"][0]["initiative_ref"] == "INI-RST-007"
    assert backlog["items"][0]["target_version"] == "v0.2.0-p3"
    assert backlog["items"][0]["status"] == "pending"


def test_scaffold_initiative_rejects_non_null_phase_that_mismatches_target_version(
    tmp_path: Path,
) -> None:
    roadmap_path, backlog_path = _write_repo(
        tmp_path,
        active_version="v0.2.0-p3",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p2
              status: planned
              tasks: []
            - id: v0.2.0-p3
              status: active
              tasks: []
            """
        ).rstrip(),
    )
    before_roadmap = roadmap_path.read_text(encoding="utf-8")
    before_backlog = backlog_path.read_text(encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--id",
            "INI-RST-008",
            "--title",
            "Scheduled mismatch",
            "--tasks",
            "1",
            "--phase",
            "v0.2.0-p2",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--phase" in result.stderr
    assert "v0.2.0-p2" in result.stderr
    assert "v0.2.0-p3" in result.stderr
    assert roadmap_path.read_text(encoding="utf-8") == before_roadmap
    assert backlog_path.read_text(encoding="utf-8") == before_backlog


def test_scaffold_initiative_rejects_stub_id_collision_in_pending_task_refs(tmp_path: Path) -> None:
    roadmap_path, backlog_path = _write_repo(
        tmp_path,
        active_version="v0.2.0-p3",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p3
              status: active
              tasks: []
              pending_task_refs:
                - T-RST-A
            """
        ).rstrip(),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--id",
            "INI-RST-009",
            "--title",
            "Pending collision",
            "--tasks",
            "1",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "T-RST-A" in result.stderr
    assert "--task-prefix" in result.stderr


def test_scaffold_initiative_rejects_stub_id_collision_in_top_level_roadmap_tasks(
    tmp_path: Path,
) -> None:
    roadmap_path, backlog_path = _write_repo(
        tmp_path,
        active_version="v0.2.0-p3",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p3
              status: active
              tasks: []
            """
        ).rstrip(),
    )
    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    roadmap["tasks"] = [
        {
            "id": "T-RST-A",
            "title": "Reserved top-level task",
            "status": "planned",
        }
    ]
    roadmap_path.write_text(yaml.safe_dump(roadmap, sort_keys=False), encoding="utf-8")
    before_roadmap = roadmap_path.read_text(encoding="utf-8")
    before_backlog = backlog_path.read_text(encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--id",
            "INI-RST-011",
            "--title",
            "Top-level collision",
            "--tasks",
            "1",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "T-RST-A" in result.stderr
    assert "--task-prefix" in result.stderr
    assert roadmap_path.read_text(encoding="utf-8") == before_roadmap
    assert backlog_path.read_text(encoding="utf-8") == before_backlog


def test_scaffold_initiative_scheduled_case_uses_matching_phase_version_and_backlog_rows(
    tmp_path: Path,
) -> None:
    roadmap_path, backlog_path = _write_repo(
        tmp_path,
        active_version="v0.2.0-p3",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p2
              status: planned
              tasks: []
            - id: v0.2.0-p3
              status: active
              tasks: []
            """
        ).rstrip(),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--id",
            "INI-RST-010",
            "--title",
            "Scheduled slice train",
            "--tasks",
            "2",
            "--phase",
            "v0.2.0-p2",
            "--active-version",
            "v0.2.0-p2",
            "--target-version",
            "v0.2.0-p2",
            "--backlog-items",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--created-date",
            "2026-04-22",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    scheduled = roadmap["versions"][0]
    active = roadmap["versions"][1]
    assert scheduled["id"] == "v0.2.0-p2"
    assert [item["id"] for item in scheduled["tasks"]] == ["T-RST-A", "T-RST-B"]
    assert active["id"] == "v0.2.0-p3"
    assert active["tasks"] == []

    initiative = roadmap["initiatives"][0]
    assert initiative["id"] == "INI-RST-010"
    assert initiative["phase"] == "v0.2.0-p2"
    assert initiative["slices"] == [
        {
            "task_ref": "T-RST-A",
            "phase": "v0.2.0-p2",
            "role": "primary",
            "status": "planned",
        },
        {
            "task_ref": "T-RST-B",
            "phase": "v0.2.0-p2",
            "role": "follow-on",
            "status": "planned",
        },
    ]

    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    assert [item["id"] for item in backlog["items"]] == ["T-RST-A", "T-RST-B"]
    assert all(item["target_version"] == "v0.2.0-p2" for item in backlog["items"])

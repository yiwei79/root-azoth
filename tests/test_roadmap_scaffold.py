"""Tests for scripts/roadmap_scaffold.py."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "roadmap_scaffold.py"


def _write_repo(
    base: Path,
    *,
    active_version: str,
    milestone: str,
    versions_content: str,
    initiatives_content: str,
    backlog_items: str = "[]",
    spec_files: list[str] | None = None,
) -> tuple[Path, Path, Path]:
    roadmap = {
        "active_version": active_version,
        "task_id_policy": {
            "legacy_milestones": [
                {
                    "milestone": "v0.2.0",
                    "prefix": "P1",
                    "width": 3,
                    "frozen": True,
                }
            ],
            "future_default": {"prefix": "T", "width": 3},
        },
        "versions": yaml.safe_load(versions_content) or [],
        "initiatives": yaml.safe_load(initiatives_content) or [],
    }
    backlog = {
        "schema_version": 1,
        "items": yaml.safe_load(backlog_items) or [],
    }
    roadmap_path = base / "roadmap.yaml"
    backlog_path = base / "backlog.yaml"
    specs_root = base / "roadmap-specs"
    specs_dir = specs_root / milestone
    specs_dir.mkdir(parents=True, exist_ok=True)
    roadmap_path.write_text(yaml.safe_dump(roadmap, sort_keys=False), encoding="utf-8")
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")
    for name in spec_files or []:
        (specs_dir / name).write_text("id: placeholder\n", encoding="utf-8")
    return roadmap_path, backlog_path, specs_root


def test_scaffold_roadmap_task_creates_backlog_roadmap_spec_and_initiative_link(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.2.0-p2",
        milestone="v0.2.0",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p2
              status: active
              tasks:
                - id: P1-024
                  title: Existing legacy slice
            """
        ).rstrip(),
        initiatives_content=textwrap.dedent(
            """\
            - id: INI-RST-004
              title: Roadmap/backlog/spec scaffolding
              category: run-state
              theme: A
              phase: null
              priority: medium
              summary: >
                Add a coherent authoring path for roadmap work.
            """
        ).rstrip(),
        backlog_items=textwrap.dedent(
            """\
            - id: P1-024
              roadmap_ref: P1-024
            """
        ).rstrip(),
        spec_files=["P1-024.yaml"],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--title",
            "Dedicated roadmap authoring helper",
            "--initiative-ref",
            "INI-RST-004",
            "--decision-ref",
            "D47",
            "D48",
            "D50",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--specs-root",
            str(specs_root),
            "--created-date",
            "2026-04-18",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == "T-001"

    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    created_item = backlog["items"][-1]
    assert created_item["id"] == "T-001"
    assert created_item["roadmap_ref"] == "T-001"
    assert created_item["initiative_ref"] == "INI-RST-004"
    assert created_item["decision_ref"] == ["D47", "D48", "D50"]
    assert created_item["target_version"] == "v0.2.0-p2"

    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    active = roadmap["versions"][0]
    assert active["tasks"][-1]["id"] == "T-001"
    assert active["tasks"][-1]["initiative_ref"] == "INI-RST-004"

    initiative = roadmap["initiatives"][0]
    assert initiative["phase"] == "v0.2.0-p2"
    assert initiative["task_ref"] == "T-001"
    assert initiative["spec_ref"] == ".azoth/roadmap-specs/v0.2.0/T-001.yaml"
    assert initiative["dimensions"] == {
        "themes": ["A"],
        "categories": ["run-state"],
        "tracks": [],
    }
    assert initiative["slices"] == [
        {
            "task_ref": "T-001",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-001.yaml",
            "phase": "v0.2.0-p2",
            "status": "active",
            "role": "primary",
        }
    ]

    spec_path = specs_root / "v0.2.0" / "T-001.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    assert spec["id"] == "T-001"
    assert spec["roadmap_version"] == "v0.2.0"
    assert spec["delivery"]["target_layer"] == "infrastructure"
    assert spec["delivery"]["suggested_command"] == "/auto"


def test_scaffold_roadmap_task_uses_future_t_namespace_for_new_milestone(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.3.0-p1",
        milestone="v0.3.0",
        versions_content=textwrap.dedent(
            """\
            - id: v0.3.0-p1
              status: active
              tasks: []
            """
        ).rstrip(),
        initiatives_content="[]",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--title",
            "Future milestone helper",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--specs-root",
            str(specs_root),
            "--created-date",
            "2026-04-18",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == "T-001"
    assert (specs_root / "v0.3.0" / "T-001.yaml").exists()


def test_scaffold_backlog_only_creates_bl_item_without_roadmap_or_spec(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.2.0-p2",
        milestone="v0.2.0",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p2
              status: active
              tasks: []
            """
        ).rstrip(),
        initiatives_content="[]",
        backlog_items=textwrap.dedent(
            """\
            - id: BL-009
            """
        ).rstrip(),
    )

    before_roadmap = roadmap_path.read_text(encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--title",
            "Backlog-only intake follow-up",
            "--namespace",
            "backlog",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--specs-root",
            str(specs_root),
            "--created-date",
            "2026-04-18",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == "BL-010"

    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    created_item = backlog["items"][-1]
    assert created_item["id"] == "BL-010"
    assert "roadmap_ref" not in created_item
    assert not (specs_root / "v0.2.0" / "BL-010.yaml").exists()
    assert roadmap_path.read_text(encoding="utf-8") == before_roadmap


def test_scaffold_roadmap_task_appends_follow_on_slice_without_changing_live_primary(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.2.0-p2",
        milestone="v0.2.0",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p2
              status: active
              tasks:
                - id: T-005
                  title: Existing primary slice
            """
        ).rstrip(),
        initiatives_content=textwrap.dedent(
            """\
            - id: INI-PPL-001
              title: Pipeline initiative
              category: pipeline
              theme: B
              phase: v0.2.0-p2
              task_ref: T-005
              spec_ref: ".azoth/roadmap-specs/v0.2.0/T-005.yaml"
              summary: >
                Existing live slice.
              slices:
                - task_ref: T-005
                  spec_ref: ".azoth/roadmap-specs/v0.2.0/T-005.yaml"
                  phase: v0.2.0-p2
                  status: active
                  role: primary
            """
        ).rstrip(),
        backlog_items=textwrap.dedent(
            """\
            - id: T-005
              roadmap_ref: T-005
              status: pending
            """
        ).rstrip(),
        spec_files=["T-005.yaml"],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--title",
            "Queued follow-on slice",
            "--initiative-ref",
            "INI-PPL-001",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--specs-root",
            str(specs_root),
            "--created-date",
            "2026-04-18",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == "T-006"

    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    initiative = roadmap["initiatives"][0]
    assert initiative["task_ref"] == "T-005"
    assert initiative["spec_ref"] == ".azoth/roadmap-specs/v0.2.0/T-005.yaml"
    assert initiative["slices"] == [
        {
            "task_ref": "T-005",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-005.yaml",
            "phase": "v0.2.0-p2",
            "status": "active",
            "role": "primary",
        },
        {
            "task_ref": "T-006",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-006.yaml",
            "phase": "v0.2.0-p2",
            "status": "planned",
            "role": "follow-on",
        },
    ]


def test_scaffold_roadmap_task_promotes_alias_when_existing_primary_is_complete(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.2.0-p2",
        milestone="v0.2.0",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p2
              status: active
              tasks: []
              completed_tasks:
                - id: T-005
                  title: Seed slice
            """
        ).rstrip(),
        initiatives_content=textwrap.dedent(
            """\
            - id: INI-PPL-001
              title: Pipeline initiative
              category: pipeline
              theme: B
              phase: v0.2.0-p1
              task_ref: T-005
              spec_ref: ".azoth/roadmap-specs/v0.2.0/T-005.yaml"
              summary: >
                Historical seed slice.
            """
        ).rstrip(),
        backlog_items=textwrap.dedent(
            """\
            - id: T-005
              roadmap_ref: T-005
              status: complete
            """
        ).rstrip(),
        spec_files=["T-005.yaml"],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--title",
            "Replacement live slice",
            "--initiative-ref",
            "INI-PPL-001",
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--specs-root",
            str(specs_root),
            "--created-date",
            "2026-04-18",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == "T-006"

    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    initiative = roadmap["initiatives"][0]
    assert initiative["phase"] == "v0.2.0-p2"
    assert initiative["task_ref"] == "T-006"
    assert initiative["spec_ref"] == ".azoth/roadmap-specs/v0.2.0/T-006.yaml"
    assert initiative["slices"] == [
        {
            "task_ref": "T-005",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-005.yaml",
            "phase": "v0.2.0-p1",
            "status": "complete",
            "role": "historical",
        },
        {
            "task_ref": "T-006",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-006.yaml",
            "phase": "v0.2.0-p2",
            "status": "active",
            "role": "primary",
        },
    ]

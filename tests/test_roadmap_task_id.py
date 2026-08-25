"""Tests for scripts/roadmap_task_id.py."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "roadmap_task_id.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import roadmap_task_id as mod  # noqa: E402


def test_active_milestone_resolves_consumer_seed_and_rejects_unsafe_values() -> None:
    assert mod.active_milestone({"active_version": "v0.1.0-p1"}) == "v0.1.0"

    with pytest.raises(ValueError, match="active_version is required"):
        mod.active_milestone({})

    with pytest.raises(ValueError, match="invalid milestone"):
        mod.active_milestone({"active_version": "../../private"})


def _write_repo(
    base: Path,
    *,
    active_version: str,
    versions_content: str = "[]",
    initiatives_content: str = "[]",
    backlog_extra: str = "",
    milestone: str = "v0.2.0",
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
        "items": yaml.safe_load(backlog_extra) or [],
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


def test_next_task_id_uses_t_namespace_when_legacy_v020_ids_are_frozen(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.2.0-p2",
        versions_content=textwrap.dedent(
            """\
            - id: v0.2.0-p2
              status: active
              tasks:
                - id: P1-024
            """
        ).rstrip(),
        initiatives_content=textwrap.dedent(
            """\
            - id: INI-PLT-006
              task_ref: P1-024
            """
        ).rstrip(),
        backlog_extra=textwrap.indent(
            textwrap.dedent(
                """\
                - id: P1-023
                  roadmap_ref: P1-023
                """
            ),
            "",
        ),
        spec_files=["P1-024.yaml"],
    )

    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    assert mod.next_task_id(roadmap, backlog, specs_root) == "T-001"


def test_next_task_id_uses_future_t_namespace_for_new_milestone(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.3.0-p1",
        milestone="v0.3.0",
    )
    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    assert mod.next_task_id(roadmap, backlog, specs_root) == "T-001"


def test_next_task_id_scans_existing_t_ids_across_backlog_roadmap_and_specs(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.3.0-p1",
        milestone="v0.3.0",
        versions_content=textwrap.dedent(
            """\
            - id: v0.3.0-p1
              status: active
              tasks:
                - id: T-007
            """
        ).rstrip(),
        backlog_extra=textwrap.indent(
            textwrap.dedent(
                """\
                - id: T-002
                  roadmap_ref: T-002
                """
            ),
            "",
        ),
        spec_files=["T-005.yaml"],
    )
    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    assert mod.next_task_id(roadmap, backlog, specs_root) == "T-008"


def test_next_backlog_id_scans_existing_bl_ids(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.2.0-p2",
        backlog_extra=textwrap.indent(
            textwrap.dedent(
                """\
                - id: BL-051
                  blocked_by:
                    - BL-007
                """
            ),
            "",
        ),
    )
    roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    assert mod.next_backlog_id(roadmap, backlog, specs_root) == "BL-052"


def test_cli_prints_next_task_id(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.3.0-p1",
        milestone="v0.3.0",
    )
    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--specs-root",
            str(specs_root),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "T-001"


def test_cli_prints_next_backlog_id(tmp_path: Path) -> None:
    roadmap_path, backlog_path, specs_root = _write_repo(
        tmp_path,
        active_version="v0.2.0-p2",
        backlog_extra=textwrap.indent(
            textwrap.dedent(
                """\
                - id: BL-009
                """
            ),
            "",
        ),
    )
    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--roadmap-yaml",
            str(roadmap_path),
            "--backlog-yaml",
            str(backlog_path),
            "--specs-root",
            str(specs_root),
            "--namespace",
            "backlog",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "BL-010"

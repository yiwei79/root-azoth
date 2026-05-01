from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cockpit_menu import check_cockpit, load_cockpit, render_menu  # noqa: E402


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_cockpit_fixture(root: Path) -> Path:
    project_path = root.parent / "ras or ray"
    project_path.mkdir(parents=True)
    _write_yaml(
        root / "azoth.yaml",
        {
            "name": "azoth",
            "version": "0.1.4.0",
            "project": "yiwei-azoth-cockpit",
            "deployment_role": "personal-cockpit",
        },
    )
    _write_yaml(
        root / ".azoth" / "releases" / "applied.yaml",
        {
            "version": 1,
            "applied_releases": [
                {
                    "product": "azoth",
                    "version": "v0.2.0",
                    "commit": "0e93832ea5a9caff499128a84e4b046b8d44ac34",
                    "source": "https://github.com/yiwei79/azoth/releases/tag/v0.2.0",
                }
            ],
        },
    )
    receipt = ".azoth/projects/handoffs/t-049-ras-or-ray-2026-05-01.yaml"
    _write_yaml(root / receipt, {"schema_version": 1, "receipt_id": "t-049"})
    _write_yaml(
        root / ".azoth" / "projects" / "index.yaml",
        {
            "version": 1,
            "projects": [
                {
                    "project_id": "ras-or-ray",
                    "title": "ras or ray",
                    "repo_path": str(project_path),
                    "default_branch": "main",
                    "tracking_ref": "origin/main",
                    "privacy_class": "local-only",
                    "profile_mode": "pointer_only",
                    "handoff_receipt_ref": receipt,
                    "validation_commands": [
                        f"git -C '{project_path}' status --short --branch",
                    ],
                }
            ],
        },
    )
    return root


def test_render_menu_lists_release_sync_project_and_safe_handoff(tmp_path: Path) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")

    state = load_cockpit(root, include_status=False)
    text = render_menu(state)

    assert "Release sync: OK" in text
    assert "public azoth v0.2.0" in text
    assert "latest approved public/installable azoth release" in text
    assert "root-azoth workshop drift is advisory only" in text
    assert "manifest 0.1.4.0" in text
    assert "ras-or-ray" in text
    assert "cd " in text
    assert "ras or ray" in text
    assert "Project-local context is authoritative" in text
    assert "Do not paste cockpit memory as project instructions" in text

    forbidden_context_imports = [
        "source_files",
        "code_summaries",
        "dependency_inventory",
        "secrets",
        "retrieval_index",
    ]
    for forbidden in forbidden_context_imports:
        assert forbidden not in text


def test_check_cockpit_rejects_missing_receipt_and_context_fields(tmp_path: Path) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    state = load_cockpit(root, include_status=False)

    assert check_cockpit(state) == []

    projects_index = root / ".azoth" / "projects" / "index.yaml"
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    doc["projects"][0]["source_files"] = ["app.py"]
    doc["projects"][0]["handoff_receipt_ref"] = ".azoth/projects/handoffs/missing.yaml"
    _write_yaml(projects_index, doc)

    errors = check_cockpit(load_cockpit(root, include_status=False))

    assert any("forbidden context field source_files" in error for error in errors)
    assert any("missing handoff receipt" in error for error in errors)


def test_project_filter_renders_only_selected_handoff(tmp_path: Path) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    projects_index = root / ".azoth" / "projects" / "index.yaml"
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    doc["projects"].append(
        {
            "project_id": "other-project",
            "title": "other project",
            "repo_path": str(root.parent / "other"),
            "default_branch": "main",
            "tracking_ref": "origin/main",
            "privacy_class": "local-only",
            "profile_mode": "pointer_only",
            "handoff_receipt_ref": ".azoth/projects/handoffs/t-other.yaml",
            "validation_commands": [],
        }
    )
    _write_yaml(root / ".azoth" / "projects" / "handoffs" / "t-other.yaml", {})
    _write_yaml(projects_index, doc)

    state = load_cockpit(root, include_status=False)
    text = render_menu(state, project_id="ras-or-ray")

    assert "ras-or-ray" in text
    assert "other-project" not in text

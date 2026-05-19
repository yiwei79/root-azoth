from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cockpit_menu import READBACK_PROJECT_FIELDS, check_cockpit, load_cockpit, render_menu  # noqa: E402


READBACK_FIELDS = {
    "project_pointer": "ras-or-ray",
    "authority_plane": "personal_cockpit",
    "selected_mode": "assisted",
    "readiness_state": "ready",
    "freshness_status": "current",
    "installed_asset_classes": ["skills", "command wrappers"],
    "missing_asset_classes": ["planning-bank seed", "autonomous control"],
    "approval_scope": "pointer_only_handoff",
    "active_write_claim": False,
    "next_safe_action": "Open a project session; project writes require a fresh project-scoped gate.",
    "stop_reason": "none",
}


def _yaml_list_after_field(path: Path, field: str) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == f"{field}:")
    values: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped.startswith("- "):
            break
        values.append(stripped[2:])
    return values


def test_planning_artifacts_preserve_canonical_cockpit_readback_fields() -> None:
    spec_fields = _yaml_list_after_field(
        ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-062.yaml",
        "canonical_readback_fields",
    )
    research_fields = _yaml_list_after_field(
        ROOT / ".azoth" / "research" / "ini-dep-002-project-readiness-handoff-map.yaml",
        "canonical_cockpit_readback_fields",
    )

    assert set(spec_fields) == READBACK_PROJECT_FIELDS
    assert set(research_fields) == READBACK_PROJECT_FIELDS


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
                    **READBACK_FIELDS,
                    "handoff_receipt_ref": receipt,
                    "validation_commands": [
                        f"git -C '{project_path}' status --short --branch",
                    ],
                }
            ],
        },
    )
    return root


def _write_project_local_receipt(root: Path, project_path: Path, **overrides: object) -> str:
    receipt_ref = ".azoth/projects/handoffs/project-local-mode.yaml"
    receipt: dict[str, object] = {
        "schema_version": 1,
        "artifact_type": "project_local_mode_receipt",
        "project_id": "ras-or-ray",
        "repo_path": str(project_path),
        "receipt_owner": "project_local",
        "selected_mode": "managed",
        "release_profile_ref": "full@v0.2.0",
        "readiness_state": "ready",
        "freshness_status": "current",
        "installed_asset_classes": [
            "roadmap seed",
            "backlog seed",
            "planning-bank seed",
            "validation helpers",
            "project-local receipt",
        ],
        "missing_asset_classes": [],
        "approval_scope": "managed_mode_project_local_gate",
        "active_write_claim": False,
        "next_safe_action": "hydrate planning state under the project-local managed-mode gate",
        "stop_reason": "none",
        "handoff_receipt_ref": receipt_ref,
    }
    receipt.update(overrides)
    _write_yaml(root / receipt_ref, receipt)
    return receipt_ref


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
    assert "Mode: assisted" in text
    assert "Readiness: ready" in text
    assert "Freshness: current" in text
    assert "Authority: personal_cockpit" in text
    assert "Pointer: ras-or-ray" in text
    assert "Installed assets: skills, command wrappers" in text
    assert "Missing assets: planning-bank seed, autonomous control" in text
    assert "Approval: pointer_only_handoff" in text
    assert "Write claim: none" in text
    assert "Next safe action: Open a project session" in text
    assert "Stop reason: none" in text
    assert "cd " in text
    assert "ras or ray" in text
    assert "Project-local context is authoritative" in text
    assert "Do not paste cockpit memory into project-local guidance" in text

    forbidden_context_imports = [
        "source_files",
        "code_summaries",
        "dependency_inventory",
        "secrets",
        "retrieval_index",
        "project instructions",
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


def test_check_cockpit_rejects_incomplete_readback_contract(tmp_path: Path) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    projects_index = root / ".azoth" / "projects" / "index.yaml"
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    for field in ("selected_mode", "readiness_state", "next_safe_action"):
        doc["projects"][0].pop(field)
    _write_yaml(projects_index, doc)

    errors = check_cockpit(load_cockpit(root, include_status=False))

    assert any("missing required field next_safe_action" in error for error in errors)
    assert any("missing required field readiness_state" in error for error in errors)
    assert any("missing required field selected_mode" in error for error in errors)


def test_check_cockpit_rejects_invalid_mode_and_authority(tmp_path: Path) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    projects_index = root / ".azoth" / "projects" / "index.yaml"
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    doc["projects"][0]["selected_mode"] = "invented"
    doc["projects"][0]["authority_plane"] = "somewhere_else"
    _write_yaml(projects_index, doc)

    errors = check_cockpit(load_cockpit(root, include_status=False))

    assert any("selected_mode must be one of" in error for error in errors)
    assert any("authority_plane must be one of" in error for error in errors)


def test_check_cockpit_rejects_invalid_asset_and_write_claim_types(tmp_path: Path) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    projects_index = root / ".azoth" / "projects" / "index.yaml"
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    doc["projects"][0]["installed_asset_classes"] = "skills"
    doc["projects"][0]["missing_asset_classes"] = ["planning-bank seed", ""]
    doc["projects"][0]["active_write_claim"] = "false"
    _write_yaml(projects_index, doc)

    errors = check_cockpit(load_cockpit(root, include_status=False))

    assert any("installed_asset_classes must be a list" in error for error in errors)
    assert any("missing_asset_classes must contain only non-empty values" in error for error in errors)
    assert any("active_write_claim must be a boolean" in error for error in errors)


def test_check_cockpit_accepts_authoritative_project_local_receipt(tmp_path: Path) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    project_path = root.parent / "ras or ray"
    receipt_ref = _write_project_local_receipt(root, project_path)
    projects_index = root / ".azoth" / "projects" / "index.yaml"
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    doc["projects"][0]["authority_plane"] = "project_local"
    doc["projects"][0]["selected_mode"] = "managed"
    doc["projects"][0]["readiness_state"] = "ready"
    doc["projects"][0]["approval_scope"] = "managed_mode_project_local_gate"
    doc["projects"][0]["handoff_receipt_ref"] = receipt_ref
    _write_yaml(projects_index, doc)

    assert check_cockpit(load_cockpit(root, include_status=False)) == []


def test_check_cockpit_fails_closed_for_unsafe_project_local_receipt(tmp_path: Path) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    project_path = root.parent / "ras or ray"
    receipt_ref = _write_project_local_receipt(
        root,
        project_path,
        receipt_owner="root_azoth",
        freshness_status="stale",
    )
    projects_index = root / ".azoth" / "projects" / "index.yaml"
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    doc["projects"][0]["authority_plane"] = "project_local"
    doc["projects"][0]["selected_mode"] = "managed"
    doc["projects"][0]["approval_scope"] = "managed_mode_project_local_gate"
    doc["projects"][0]["handoff_receipt_ref"] = receipt_ref
    _write_yaml(projects_index, doc)

    errors = check_cockpit(load_cockpit(root, include_status=False))

    assert any("receipt_owner must be project_local" in error for error in errors)
    assert any("freshness_status must be current" in error for error in errors)


def test_check_cockpit_requires_receipt_for_project_local_managed_readback(
    tmp_path: Path,
) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    projects_index = root / ".azoth" / "projects" / "index.yaml"
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    doc["projects"][0]["authority_plane"] = "project_local"
    doc["projects"][0]["selected_mode"] = "managed"
    doc["projects"][0]["handoff_receipt_ref"] = ""
    _write_yaml(projects_index, doc)

    errors = check_cockpit(load_cockpit(root, include_status=False))

    assert any("handoff_receipt_ref is required for project-local authority" in error for error in errors)


def test_check_cockpit_reports_malformed_project_local_receipt(tmp_path: Path) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    projects_index = root / ".azoth" / "projects" / "index.yaml"
    receipt_ref = ".azoth/projects/handoffs/project-local-mode.yaml"
    (root / receipt_ref).write_text("receipt: [unterminated\n", encoding="utf-8")
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    doc["projects"][0]["authority_plane"] = "project_local"
    doc["projects"][0]["selected_mode"] = "managed"
    doc["projects"][0]["handoff_receipt_ref"] = receipt_ref
    _write_yaml(projects_index, doc)

    errors = check_cockpit(load_cockpit(root, include_status=False))

    assert any("failed to parse handoff receipt" in error for error in errors)


def test_check_cockpit_rejects_managed_mode_without_project_local_authority(
    tmp_path: Path,
) -> None:
    root = _write_cockpit_fixture(tmp_path / "yiwei-azoth-cockpit")
    projects_index = root / ".azoth" / "projects" / "index.yaml"
    doc = yaml.safe_load(projects_index.read_text(encoding="utf-8"))
    doc["projects"][0]["selected_mode"] = "managed"
    doc["projects"][0]["authority_plane"] = "personal_cockpit"
    _write_yaml(projects_index, doc)

    errors = check_cockpit(load_cockpit(root, include_status=False))

    assert any("selected_mode managed requires authority_plane project_local" in error for error in errors)


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
            **READBACK_FIELDS,
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

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-048-desired-state-manifest.yaml"
REPORT_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-048-validation-report.yaml"


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_t048_manifest_records_approved_apply_boundary() -> None:
    manifest = _load_yaml(MANIFEST_PATH)

    assert manifest["schema_version"] == 1
    assert manifest["manifest_id"] == "personal-root-update-20260501-t048"
    assert manifest["release_ref"] == "v0.2.0"
    assert manifest["product_revision"] == "0e93832ea5a9caff499128a84e4b046b8d44ac34"
    assert manifest["source_revision"] == "546191b5735d3137717f06bc7cafb5bc5be83b4a"
    assert manifest["target_path"] == "/Users/yiwei/GithubRepos/personal-azoth-root"
    assert manifest["storage_policy"] == "local_only"
    assert manifest["reconciliation_mode"] == "no_op_product_already_applied"
    assert manifest["enabled_surfaces"] == ["installed_runtime"]
    assert manifest["approved_card_ids"] == []
    assert manifest["project_pilots"] == []
    assert manifest["source_registry_changes"] == []
    assert manifest["rollback_ref"] == "1744b3c45fd1762b5b917f00a9bbe8014d4b0e0e"


def test_t048_manifest_keeps_forbidden_expansions_empty() -> None:
    manifest = _load_yaml(MANIFEST_PATH)

    assert manifest["project_pilots"] == []
    assert manifest["source_registry_changes"] == []
    assert manifest["retrieval_changes"] == []
    assert manifest["credential_changes"] == []
    assert manifest["public_release_changes"] == []


def test_t048_validation_report_records_receipt_and_noop_reconciliation() -> None:
    report = _load_yaml(REPORT_PATH)

    assert report["schema_version"] == 1
    assert report["task_ref"] == "T-048"
    assert report["manifest_ref"] == ".azoth/handoffs/2026-05-01-t-048-desired-state-manifest.yaml"
    assert report["reconciliation_mode"] == "no_op_product_already_applied"
    assert report["product_revision_already_applied"] is True
    assert report["receipt"]["deployment_id"] == "t-048-personal-root-update-rehearsal-2026-05-01"
    assert report["receipt"]["target_paths"] == [".azoth/releases/applied.yaml"]
    assert report["receipt"]["non_goals_confirmed"] == [
        "no runtime overwrite",
        "no source registry onboarding",
        "no project repo mutation",
        "no retrieval expansion",
        "no public azoth release",
        "no credential access",
        "no governance, kernel, or M1 change",
    ]

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
INTAKE_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-051-continuation-intake.yaml"
INI_PKB_PATH = ROOT / ".azoth" / "initiative-banks" / "INI-PKB-001.yaml"
BACKLOG_PATH = ROOT / ".azoth" / "backlog.yaml"
ROADMAP_PATH = ROOT / ".azoth" / "roadmap.yaml"


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_t051_intake_records_root_only_post_t050_boundary() -> None:
    intake = _load_yaml(INTAKE_PATH)

    assert intake["candidate_ref"] == "INI-PKB-001#slice-pkb-001-h"
    assert intake["proposed_task_id"] == "T-051"
    assert intake["decision"] == "ready_to_hydrate_planning_scaffold"
    assert intake["approval_scope"] == "hydration_specific_slice_pkb_001_h"
    assert intake["hydration_boundary"]["can_hydrate_task_scaffold_now"] is False
    assert intake["hydration_boundary"]["can_recommend_hydration"] is True
    assert intake["hydration_boundary"]["can_deliver_task"] is False
    assert intake["hydration_boundary"]["can_mutate_personal_root"] is False
    assert intake["hydration_boundary"]["can_publish_public_azoth"] is False
    assert "public_azoth_release" in intake["forbidden_outputs"]
    assert "personal_root_mutation" in intake["forbidden_outputs"]
    assert "project_repo_write" in intake["forbidden_outputs"]
    assert "retrieval_indexing" in intake["forbidden_outputs"]


def test_ini_pkb_routes_t051_as_ready_planning_scaffold_without_delivery() -> None:
    bank = _load_yaml(INI_PKB_PATH)
    candidates = {
        candidate["candidate_id"]: candidate for candidate in bank["candidate_slices"]
    }
    candidate = candidates["slice-pkb-001-h"]

    assert candidate["proposed_task_id"] == "T-051"
    assert candidate["status"] == "candidate"
    assert candidate["target_layer"] == "planning"
    assert candidate["delivery_pipeline"] == "governed"
    assert ".azoth/handoffs/2026-05-01-t-051-continuation-intake.yaml" in candidate[
        "research_evidence_refs"
    ]
    assert "No public azoth release or tag." in candidate["known_non_goals"]
    assert "No personal-root mutation." in candidate["known_non_goals"]
    assert "No project repo write or source scanning." in candidate["known_non_goals"]
    assert candidate["open_questions"] == []
    assert "Post-T-050 release-readiness continuation intake" in candidate["hydration_plan"][
        "scaffold_command"
    ]

    readiness = bank["readiness"]
    assert readiness["readiness_status"] == "ready_to_hydrate"
    assert readiness["candidate_first_slice"] == "slice-pkb-001-h"
    assert readiness["next_candidate_ref"] == "slice-pkb-001-h"
    assert readiness["approval_scope"] == "hydration_specific_slice_pkb_001_h"
    assert readiness["delivery_authorized"] is False
    assert readiness["hydrate_authorized"] is False
    assert readiness["ship_authorized"] is False
    assert readiness["next_readiness_gate"] == "hydrate_post_t050_release_readiness_planning_scaffold"


def test_t051_intake_does_not_create_roadmap_backlog_or_spec_artifacts() -> None:
    backlog = _load_yaml(BACKLOG_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)
    p4 = next(version for version in roadmap["versions"] if version["id"] == "v0.2.0-p4")

    assert not any(item.get("id") == "T-051" for item in backlog["items"])
    assert not any(task.get("id") == "T-051" for task in p4.get("tasks", []))
    assert not any(task.get("id") == "T-051" for task in p4.get("completed_tasks", []))
    assert not (ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-051.yaml").exists()

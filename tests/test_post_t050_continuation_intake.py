from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
INTAKE_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-051-continuation-intake.yaml"
INI_PKB_PATH = ROOT / ".azoth" / "initiative-banks" / "INI-PKB-001.yaml"
BACKLOG_PATH = ROOT / ".azoth" / "backlog.yaml"
ROADMAP_PATH = ROOT / ".azoth" / "roadmap.yaml"
SPEC_PATH = ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-051.yaml"


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


def test_ini_pkb_routes_t051_as_hydrated_planning_scaffold_without_delivery() -> None:
    bank = _load_yaml(INI_PKB_PATH)
    candidates = {
        candidate["candidate_id"]: candidate for candidate in bank["candidate_slices"]
    }
    candidate = candidates["slice-pkb-001-h"]

    assert candidate["proposed_task_id"] == "T-051"
    assert candidate["status"] == "hydrated"
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
    assert candidate["hydration_plan"]["mode"] == "executed"
    assert candidate["hydration_plan"]["hydrated_task_ref"] == "T-051"
    assert candidate["hydration_plan"]["hydrated_spec_ref"] == (
        ".azoth/roadmap-specs/v0.2.0/T-051.yaml"
    )

    readiness = bank["readiness"]
    assert readiness["readiness_status"] == "ready_to_hydrate"
    assert readiness["candidate_first_slice"] == "slice-pkb-001-h"
    assert readiness["next_candidate_ref"] == "slice-pkb-001-h"
    assert readiness["approval_scope"] == "hydration_specific_slice_pkb_001_h"
    assert readiness["delivery_authorized"] is False
    assert readiness["hydrate_authorized"] is False
    assert readiness["ship_authorized"] is False
    assert readiness["next_readiness_gate"] == "hydrate_post_t050_release_readiness_planning_scaffold"
    assert "has been hydrated as T-051" in readiness["hydration_recommendation"]


def test_t051_hydration_creates_only_planning_scaffold() -> None:
    backlog = _load_yaml(BACKLOG_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)
    spec = _load_yaml(SPEC_PATH)
    p4 = next(version for version in roadmap["versions"] if version["id"] == "v0.2.0-p4")

    row = next(item for item in backlog["items"] if item.get("id") == "T-051")
    assert row["status"] == "pending"
    assert row["target_layer"] == "planning"
    assert row["delivery_pipeline"] == "governed"
    assert "does not authorize release publication" in row["description"]

    assert any(task.get("id") == "T-051" for task in p4.get("tasks", []))
    assert not any(task.get("id") == "T-051" for task in p4.get("completed_tasks", []))
    assert spec["id"] == "T-051"
    assert ".azoth/handoffs/2026-05-01-t-051-continuation-intake.yaml" in spec[
        "context_refs"
    ]
    assert "T-050" in spec["dependencies"]
    assert spec["delivery"]["delivery_pipeline"] == "governed"
    assert "Do not publish or tag public azoth." in spec["non_goals"]
    assert any("chooses exactly one next operation lane" in item for item in spec["acceptance"])

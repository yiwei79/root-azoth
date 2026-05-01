from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
INTAKE_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-051-continuation-intake.yaml"
INI_PKB_PATH = ROOT / ".azoth" / "initiative-banks" / "INI-PKB-001.yaml"
BACKLOG_PATH = ROOT / ".azoth" / "backlog.yaml"
ROADMAP_PATH = ROOT / ".azoth" / "roadmap.yaml"
SPEC_PATH = ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-051.yaml"
DECISION_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-051-release-readiness-decision.yaml"
T052_SPEC_PATH = ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-052.yaml"
T052_HANDOFF_PATH = (
    ROOT / ".azoth" / "handoffs" / "2026-05-01-t-052-personal-cockpit-deployment.yaml"
)
T053_SEED_PATH = (
    ROOT / ".azoth" / "handoffs" / "2026-05-01-t-053-private-backup-recovery-seed.yaml"
)
T053_HYDRATION_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-053-hydration.yaml"
T053_DELIVERY_PATH = (
    ROOT
    / ".azoth"
    / "handoffs"
    / "2026-05-01-t-053-private-backup-recovery-readiness.yaml"
)
T053_SPEC_PATH = ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-053.yaml"


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


def test_ini_pkb_marks_t051_stop_defer_decision_complete() -> None:
    bank = _load_yaml(INI_PKB_PATH)
    candidates = {
        candidate["candidate_id"]: candidate for candidate in bank["candidate_slices"]
    }
    candidate = candidates["slice-pkb-001-h"]

    assert candidate["proposed_task_id"] == "T-051"
    assert candidate["status"] == "complete"
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
    assert candidate["delivery_evidence_refs"] == [
        ".azoth/handoffs/2026-05-01-t-051-release-readiness-decision.yaml"
    ]
    assert candidate["selected_lane"] == "stop_defer"

    readiness = bank["readiness"]
    assert readiness["readiness_status"] == "complete"
    assert readiness["candidate_first_slice"] == "slice-pkb-001-j"
    assert readiness["next_candidate_ref"] == "slice-pkb-001-j"
    assert (
        readiness["approval_scope"]
        == "t053_delivery_scope_private_backup_recovery_onboarding"
    )
    assert readiness["delivery_authorized"] is False
    assert readiness["hydrate_authorized"] is False
    assert readiness["ship_authorized"] is False
    assert readiness["next_readiness_gate"] == "operator_selected_follow_on_gate"
    assert "T-053 delivered" in readiness["hydration_recommendation"]


def test_t051_delivery_closes_roadmap_backlog_and_preserves_spec() -> None:
    backlog = _load_yaml(BACKLOG_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)
    spec = _load_yaml(SPEC_PATH)
    p4 = next(version for version in roadmap["versions"] if version["id"] == "v0.2.0-p4")

    row = next(item for item in backlog["items"] if item.get("id") == "T-051")
    assert row["status"] == "complete"
    assert row["target_layer"] == "planning"
    assert row["delivery_pipeline"] == "governed"
    assert "does not authorize release publication" in row["description"]

    assert not any(task.get("id") == "T-051" for task in p4.get("tasks", []))
    assert any(task.get("id") == "T-051" for task in p4.get("completed_tasks", []))
    assert spec["id"] == "T-051"
    assert ".azoth/handoffs/2026-05-01-t-051-continuation-intake.yaml" in spec[
        "context_refs"
    ]
    assert "T-050" in spec["dependencies"]
    assert spec["delivery"]["delivery_pipeline"] == "governed"
    assert "Do not publish or tag public azoth." in spec["non_goals"]
    assert any("chooses exactly one next operation lane" in item for item in spec["acceptance"])


def test_t051_decision_selects_stop_defer_without_mutation_authority() -> None:
    decision = _load_yaml(DECISION_PATH)

    assert decision["task_ref"] == "T-051"
    assert decision["delivery_mode"] == "root_only_release_readiness_continuation_decision"
    assert decision["gate"]["approval_scope"] == "t051_root_only_release_readiness_decision"
    assert decision["gate"]["mutation_authority"]["public_product"] is False
    assert decision["gate"]["mutation_authority"]["personal_root"] is False
    assert decision["gate"]["mutation_authority"]["pilot_project"] is False
    assert decision["decision"]["selected_lane"] == "stop_defer"
    assert decision["selected_next_gate"]["gate_required"] == "operator_selected_follow_on"
    assert "public_product_update" in {
        item["lane"] for item in decision["decision"]["rejected_lanes"]
    }
    assert "personal_root_mutation" in decision["forbidden_outputs_confirmed"]
    assert "project_repo_write" in decision["forbidden_outputs_confirmed"]
    assert "retrieval_indexing" in decision["forbidden_outputs_confirmed"]


def test_t052_spec_defines_cockpit_rename_without_project_expansion() -> None:
    spec = _load_yaml(T052_SPEC_PATH)

    assert spec["id"] == "T-052"
    assert spec["delivery"]["target_layer"] == "infrastructure"
    assert spec["delivery"]["delivery_pipeline"] == "governed"
    assert "T-051" in spec["dependencies"]
    assert any("yiwei-azoth-cockpit" in item for item in spec["scope"])
    assert "No project source or project code mutation." in spec["non_goals"]
    assert "No source registry onboarding." in spec["non_goals"]
    assert any("old local path no longer exists" in item for item in spec["acceptance"])


def test_t052_handoff_records_local_rename_and_forbidden_boundaries() -> None:
    handoff = _load_yaml(T052_HANDOFF_PATH)

    assert handoff["task_ref"] == "T-052"
    assert handoff["delivery_mode"] == "governed_personal_cockpit_local_rename"
    assert handoff["gate"]["approval_scope"] == (
        "t052_personal_cockpit_deployment_and_local_rename"
    )
    assert handoff["applied"]["renamed_from"] == (
        "/Users/yiwei/GithubRepos/personal-azoth-root"
    )
    assert handoff["applied"]["renamed_to"] == (
        "/Users/yiwei/GithubRepos/yiwei-azoth-cockpit"
    )
    assert handoff["applied"]["cockpit_commit"] == (
        "56dcb693cd24d4431a0ba89c37228264cf45285d"
    )
    assert handoff["applied"]["pointer_only_contract_preserved"] is True
    assert "project_source_mutation" in handoff["forbidden_outputs_confirmed"]
    assert "retrieval_indexing" in handoff["forbidden_outputs_confirmed"]
    assert "storage_backup_provisioning" in handoff["forbidden_outputs_confirmed"]


def test_t052_planning_truth_is_terminal_and_points_to_next_gate() -> None:
    backlog = _load_yaml(BACKLOG_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)
    bank = _load_yaml(INI_PKB_PATH)

    row = next(item for item in backlog["items"] if item.get("id") == "T-052")
    assert row["status"] == "complete"
    assert row["target_layer"] == "infrastructure"
    assert row["blocked_by"] == ["T-051"]

    initiative = next(item for item in roadmap["initiatives"] if item["id"] == "INI-PKB-001")
    t052_slice = next(item for item in initiative["slices"] if item["task_ref"] == "T-052")
    p4 = next(version for version in roadmap["versions"] if version["id"] == "v0.2.0-p4")
    assert initiative["discovery_status"] == (
        "t053_private_backup_recovery_readiness_complete"
    )
    assert initiative["candidate_slice_ref"] == "slice-pkb-001-j"
    assert t052_slice["status"] == "complete"
    assert t052_slice["role"] == "historical"
    assert not any(task.get("id") == "T-052" for task in p4.get("tasks", []))
    assert any(task.get("id") == "T-052" for task in p4["completed_tasks"])
    assert not any(task.get("id") == "T-053" for task in p4.get("tasks", []))
    assert any(task.get("id") == "T-053" for task in p4["completed_tasks"])

    candidate = next(
        item for item in bank["candidate_slices"] if item["candidate_id"] == "slice-pkb-001-i"
    )
    assert candidate["status"] == "complete"
    assert candidate["personal_cockpit_path"] == (
        "/Users/yiwei/GithubRepos/yiwei-azoth-cockpit"
    )
    assert candidate["previous_personal_root_path"] == (
        "/Users/yiwei/GithubRepos/personal-azoth-root"
    )
    assert candidate["personal_cockpit_commit"] == (
        "56dcb693cd24d4431a0ba89c37228264cf45285d"
    )

    readiness = bank["readiness"]
    assert readiness["candidate_first_slice"] == "slice-pkb-001-j"
    assert readiness["readiness_status"] == "complete"
    assert readiness["next_readiness_gate"] == "operator_selected_follow_on_gate"


def test_t053_seed_selects_backup_recovery_without_provisioning() -> None:
    seed = _load_yaml(T053_SEED_PATH)
    bank = _load_yaml(INI_PKB_PATH)
    candidates = {
        candidate["candidate_id"]: candidate for candidate in bank["candidate_slices"]
    }
    candidate = candidates["slice-pkb-001-j"]

    assert seed["selected_lane"] == "private_backup_recovery_readiness"
    assert seed["gate"]["mutation_authority"]["backup_provisioning"] is False
    assert seed["gate"]["mutation_authority"]["credential_access"] is False
    assert seed["seeded_candidate"]["proposed_task_id"] == "T-053"
    assert seed["seeded_candidate"]["next_readiness_gate"] == (
        "hydration_specific_slice_pkb_001_j"
    )

    assert candidate["proposed_task_id"] == "T-053"
    assert candidate["status"] == "complete"
    assert candidate["target_layer"] == "planning"
    assert candidate["delivery_pipeline"] == "governed"
    assert "No backup provisioning or storage writes." in candidate["known_non_goals"]
    assert "No credential access or cloud account provisioning." in candidate[
        "known_non_goals"
    ]
    assert candidate["hydration_plan"]["mode"] == "executed"
    assert candidate["hydration_plan"]["hydrated_task_ref"] == "T-053"
    assert candidate["hydration_plan"]["hydrated_spec_ref"] == (
        ".azoth/roadmap-specs/v0.2.0/T-053.yaml"
    )
    assert "Private backup and recovery readiness" in candidate["hydration_plan"][
        "scaffold_command"
    ]


def test_t053_hydration_sets_delivery_boundary_for_onboarding() -> None:
    spec = _load_yaml(T053_SPEC_PATH)
    handoff = _load_yaml(T053_HYDRATION_PATH)
    delivery = _load_yaml(T053_DELIVERY_PATH)
    backlog = _load_yaml(BACKLOG_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)

    row = next(item for item in backlog["items"] if item.get("id") == "T-053")
    initiative = next(item for item in roadmap["initiatives"] if item["id"] == "INI-PKB-001")
    p4 = next(version for version in roadmap["versions"] if version["id"] == "v0.2.0-p4")

    assert row["status"] == "complete"
    assert row["target_layer"] == "planning"
    assert row["delivery_pipeline"] == "governed"
    assert "operator onboarding guide" in row["description"]
    assert initiative["task_ref"] is None
    assert initiative["spec_ref"] == ".azoth/roadmap-specs/v0.2.0/T-053.yaml"
    assert not any(task.get("id") == "T-053" for task in p4.get("tasks", []))
    assert any(task.get("id") == "T-053" for task in p4.get("completed_tasks", []))

    assert spec["id"] == "T-053"
    assert "T-052" in spec["dependencies"]
    assert spec["delivery"]["delivery_pipeline"] == "governed"
    assert any("operator onboarding guide" in item for item in spec["scope"])
    assert "No backup provisioning or storage writes." in spec["non_goals"]
    assert "No personal-cockpit mutation." in spec["non_goals"]

    assert handoff["approval_scope"] == "hydration_specific_slice_pkb_001_j"
    assert handoff["delivery_boundary"]["next_gate"] == (
        "t053_delivery_scope_private_backup_recovery_onboarding"
    )
    assert "operator_onboarding_guide" in handoff["delivery_boundary"][
        "allowed_next_outputs"
    ]
    assert "credential_access" in handoff["delivery_boundary"]["forbidden_next_outputs"]

    assert delivery["gate"]["approval_scope"] == (
        "t053_delivery_scope_private_backup_recovery_onboarding"
    )
    assert "docs/personal-control-plane/YIWEI-AZOTH-COCKPIT-OPERATOR-ONBOARDING.md" in (
        delivery["delivered_artifacts"]
    )
    assert delivery["readiness_result"]["operator_onboarding"] == "delivered"
    assert delivery["gate"]["mutation_authority"]["personal_cockpit_mutation"] is False

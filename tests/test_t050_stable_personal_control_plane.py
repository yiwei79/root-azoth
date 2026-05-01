from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-050.yaml"
INTAKE_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-050-intake.yaml"
CLOSEOUT_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-050-stable-deployment-closeout.yaml"
BACKLOG_PATH = ROOT / ".azoth" / "backlog.yaml"
ROADMAP_PATH = ROOT / ".azoth" / "roadmap.yaml"
INITIATIVE_PATH = ROOT / ".azoth" / "initiative-banks" / "INI-PKB-001.yaml"


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_t050_spec_packages_stable_closeout_without_mutation_authority() -> None:
    spec = _load_yaml(SPEC_PATH)

    assert spec["id"] == "T-050"
    assert spec["delivery"]["delivery_pipeline"] == "governed"
    assert ".azoth/handoffs/2026-05-01-t-050-intake.yaml" in spec["context_refs"]
    assert ".azoth/handoffs/2026-05-01-t-050-stable-deployment-closeout.yaml" in spec[
        "context_refs"
    ]
    assert "T-049" in spec["dependencies"]
    assert any("root-only stable deployment closeout" in item for item in spec["scope"])
    assert "Do not mutate personal-root, project repos, public azoth, or external storage." in spec[
        "non_goals"
    ]
    assert any("local-only storage" in item for item in spec["acceptance"])
    assert "personal-root mutation" in spec["elasticity"]


def test_t050_intake_defers_backup_and_delivery_to_separate_gates() -> None:
    intake = _load_yaml(INTAKE_PATH)

    assert intake["decision"] == "ready_to_hydrate_planning_scaffold"
    disposition = intake["architectural_disposition"]
    assert disposition["storage_policy"] == "local_only_accepted_for_t050_closeout"
    assert "separate task" in disposition["storage_policy_follow_up"]
    assert intake["hydration_boundary"]["can_hydrate_task_scaffold"] is True
    assert intake["hydration_boundary"]["can_deliver_task"] is False
    assert intake["hydration_boundary"]["can_mutate_personal_root"] is False
    assert "storage_backup_provisioning" in intake["forbidden_outputs"]


def test_t050_backlog_row_is_complete_governed_closeout() -> None:
    backlog = _load_yaml(BACKLOG_PATH)
    row = next(item for item in backlog["items"] if item.get("id") == "T-050")

    assert row["status"] == "complete"
    assert row["delivery_pipeline"] == "governed"
    assert row["target_layer"] == "planning"
    assert row["blocked_by"] == ["T-049"]
    assert "Delivery does not authorize personal-root mutation" in row["description"]


def test_t050_closeout_artifact_records_stable_root_only_delivery() -> None:
    closeout = _load_yaml(CLOSEOUT_PATH)

    assert closeout["schema_version"] == 1
    assert closeout["task_ref"] == "T-050"
    assert closeout["session_id"] == "2026-05-01-t-050-delivery"
    assert closeout["delivery_mode"] == "root_only_stable_deployment_closeout"
    assert closeout["gate"]["approval_scope"] == "t050_root_only_stable_deployment_closeout"
    assert closeout["gate"]["mutation_authority"]["personal_root"] is False
    assert closeout["gate"]["mutation_authority"]["pilot_project"] is False

    evidence_refs = closeout["evidence_chain"]
    assert ".azoth/roadmap-specs/v0.2.0/T-047.yaml" in evidence_refs
    assert ".azoth/handoffs/2026-05-01-t-048-validation-report.yaml" in evidence_refs
    assert ".azoth/handoffs/2026-05-01-t-049-validation-report.yaml" in evidence_refs
    assert any(
        ref.startswith("/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/projects/handoffs/")
        for ref in evidence_refs
    )

    cadence = closeout["update_cadence"]
    assert [step["plane"] for step in cadence] == [
        "root-azoth",
        "public-azoth",
        "personal-root",
        "project-consumers",
    ]
    assert all(step["executed_in_t050"] is False for step in cadence)

    assert closeout["storage_policy"]["accepted_for_t050"] == "local_only"
    assert closeout["storage_policy"]["private_remote_or_encrypted_backup"] == "deferred"
    assert "public_azoth_release" in closeout["deferred_boundaries"]
    assert "personal_root_mutation" in closeout["deferred_boundaries"]
    assert "project_repo_write" in closeout["deferred_boundaries"]
    assert closeout["next_safe_action"].startswith("Route v0.2.0 release readiness")

    validation_commands = {item["command"]: item["status"] for item in closeout["validation_results"]}
    assert validation_commands[
        "PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest tests/test_t050_stable_personal_control_plane.py -q"
    ] == "passed"
    assert validation_commands["python3 scripts/check_gates.py --session-id 2026-05-01-t-050-delivery --require-pipeline-gate"] == "passed"
    assert validation_commands["python3 scripts/azoth-deploy.py --check"] == "passed"


def test_t050_planning_truth_is_complete_across_roadmap_and_initiative_bank() -> None:
    roadmap = _load_yaml(ROADMAP_PATH)
    initiative = next(item for item in roadmap["initiatives"] if item["id"] == "INI-PKB-001")
    t050_slice = next(item for item in initiative["slices"] if item["task_ref"] == "T-050")
    t051_slice = next(item for item in initiative["slices"] if item["task_ref"] == "T-051")
    t052_slice = next(item for item in initiative["slices"] if item["task_ref"] == "T-052")
    p4 = next(version for version in roadmap["versions"] if version["id"] == "v0.2.0-p4")

    assert initiative["task_ref"] == "T-053"
    assert t050_slice["status"] == "complete"
    assert t050_slice["role"] == "historical"
    assert t051_slice["status"] == "complete"
    assert t051_slice["role"] == "historical"
    assert t052_slice["status"] == "complete"
    assert t052_slice["role"] == "historical"
    assert initiative["discovery_status"] == "t053_private_backup_recovery_hydrated"
    assert initiative["candidate_slice_ref"] == "slice-pkb-001-j"
    assert initiative["next_discovery_action"].startswith("T-053 is hydrated")
    assert any(task["id"] == "T-053" for task in p4.get("tasks", []))
    assert not any(task["id"] == "T-052" for task in p4.get("tasks", []))
    assert any(task["id"] == "T-052" for task in p4["completed_tasks"])
    assert not any(task["id"] == "T-051" for task in p4.get("tasks", []))
    assert any(task["id"] == "T-051" for task in p4["completed_tasks"])
    assert not any(task["id"] == "T-050" for task in p4.get("tasks", []))
    assert any(task["id"] == "T-050" for task in p4["completed_tasks"])

    initiative_bank = _load_yaml(INITIATIVE_PATH)
    candidate = next(
        item for item in initiative_bank["candidate_slices"] if item["candidate_id"] == "slice-pkb-001-g"
    )
    assert candidate["status"] == "complete"
    t050_closeout = next(
        item for item in initiative_bank["closeout_history"] if item["task_ref"] == "T-050"
    )
    assert t050_closeout["result"].startswith("Delivered root-only T-050")
    readiness = initiative_bank["readiness"]
    assert readiness["candidate_first_slice"] == "slice-pkb-001-j"
    assert readiness["readiness_status"] == "ready_to_hydrate"
    assert (
        readiness["freshness_status"]
        == "current_as_of_2026_05_01_hydrated_to_t_053"
    )

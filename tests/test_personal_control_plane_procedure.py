from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
PROCEDURE_PATH = (
    ROOT
    / "docs"
    / "personal-control-plane"
    / "PERSONAL-CONTROL-PLANE-DEPLOYMENT-PROCEDURE.md"
)
T047_PATH = ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-047.yaml"
INI_PKB_PATH = ROOT / ".azoth" / "initiative-banks" / "INI-PKB-001.yaml"
P4_ROLLOUT_PATH = (
    ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "V0.2.0-P4-ROLLOUT-PLAN.md"
)


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_procedure_declares_required_operating_stages() -> None:
    text = PROCEDURE_PATH.read_text(encoding="utf-8")

    required_sections = [
        "## Gate",
        "## Desired-State Manifest",
        "## Reconciliation Preflight",
        "## Apply Boundary",
        "## Verification",
        "## Deployment Receipt",
        "## Rollback",
        "## Closeout",
        "## Forbidden Boundaries",
        "## Follow-On Route",
    ]

    for heading in required_sections:
        assert heading in text


def test_procedure_names_manifest_and_receipt_contract_fields() -> None:
    text = PROCEDURE_PATH.read_text(encoding="utf-8")

    manifest_fields = [
        "release_ref",
        "product_revision",
        "target_path",
        "storage_policy",
        "enabled_surfaces",
        "approved_card_ids",
        "project_pilots",
        "validation_commands",
        "rollback_ref",
    ]
    receipt_fields = [
        "source_revision",
        "product_revision",
        "candidate_ids",
        "target_paths",
        "validation_result",
        "applied_at",
        "rollback_ref",
        "approval_basis",
        "residual_risks",
    ]

    for field in manifest_fields + receipt_fields:
        assert field in text


def test_procedure_keeps_forbidden_boundaries_explicit() -> None:
    text = PROCEDURE_PATH.read_text(encoding="utf-8")

    forbidden_boundaries = [
        "/Users/yiwei/GithubRepos/personal-azoth-root",
        "credentials",
        "source registries",
        "project repos",
        "retrieval indexes",
        "public azoth release",
        "kernel",
        "governance",
        "M1",
    ]
    approval_boundaries = [
        "Release approval does not imply personal-root deployment approval",
        "personal-root deployment approval does not imply project-write approval",
    ]

    for boundary in forbidden_boundaries + approval_boundaries:
        assert boundary in text


def test_planning_truth_links_t047_procedure_artifact() -> None:
    t047 = _load_yaml(T047_PATH)
    bank = _load_yaml(INI_PKB_PATH)
    rollout_text = P4_ROLLOUT_PATH.read_text(encoding="utf-8")

    assert PROCEDURE_PATH.relative_to(ROOT).as_posix() in t047["artifacts"]
    t047_candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["proposed_task_id"] == "T-047"
    )
    assert (
        PROCEDURE_PATH.relative_to(ROOT).as_posix()
        in t047_candidate["research_evidence_refs"]
    )
    assert PROCEDURE_PATH.relative_to(ROOT).as_posix() in rollout_text


def test_follow_on_route_is_staged_t047_to_t050() -> None:
    bank = _load_yaml(INI_PKB_PATH)
    rollout_text = P4_ROLLOUT_PATH.read_text(encoding="utf-8")
    candidates = {
        candidate["proposed_task_id"]: candidate for candidate in bank["candidate_slices"]
    }

    assert candidates["T-047"]["hydration_plan"]["mode"] == "executed"
    assert candidates["T-048"]["hydration_plan"]["mode"] == "executed"
    assert candidates["T-049"]["hydration_plan"]["mode"] == "executed"
    assert candidates["T-049"]["hydration_plan"]["hydrated_task_ref"] == "T-049"
    assert candidates["T-050"]["hydration_plan"]["mode"] == "executed"
    assert candidates["T-050"]["hydration_plan"]["hydrated_task_ref"] == "T-050"

    route_positions = [
        rollout_text.index(task_ref)
        for task_ref in ["T-047", "T-048", "T-049", "T-050"]
    ]
    assert route_positions == sorted(route_positions)

    readiness = bank["readiness"]
    assert readiness["candidate_first_slice"] == "slice-pkb-001-g"
    assert readiness["next_candidate_ref"] == "slice-pkb-001-g"
    assert readiness["readiness_status"] == "complete"
    assert readiness["human_decision"] == "approved"
    assert readiness["delivery_authorized"] is False
    assert (
        readiness["next_readiness_gate"]
        == "release_readiness_requires_evaluator_orchestrator_gate"
    )

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import planning_bank_validate  # noqa: E402
from planning_bank_validate import (  # noqa: E402
    PlanningBankValidationError,
    build_initiative_readiness_report,
    validate_design_bank,
    validate_initiative_bank,
    validate_roadmap_refs,
)


INITIATIVE_BANK_PATH = ROOT / ".azoth" / "initiative-banks" / "INI-EVI-002.yaml"
DESIGN_BANK_PATH = ROOT / ".azoth" / "design-banks" / "planning-banks-layer.yaml"
RESEARCH_INDEX_PATH = ROOT / ".azoth" / "research" / "ini-evi-002-research-bank.yaml"
ROADMAP_PATH = ROOT / ".azoth" / "roadmap.yaml"
BACKLOG_PATH = ROOT / ".azoth" / "backlog.yaml"
SPECS_DIR = ROOT / ".azoth" / "roadmap-specs" / "v0.2.0"


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _write_temp_initiative_bank(repo: Path, *, initiative_id: str = "INI-TEST") -> tuple[Path, dict]:
    bank_path = repo / ".azoth" / "initiative-banks" / f"{initiative_id}.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = initiative_id
    if isinstance(bank.get("readiness"), dict):
        bank["readiness"]["source_bank_ref"] = f".azoth/initiative-banks/{initiative_id}.yaml"
    for candidate in bank["candidate_slices"]:
        candidate["initiative_ref"] = initiative_id
        hydration_plan = candidate.get("hydration_plan")
        if isinstance(hydration_plan, dict) and isinstance(
            hydration_plan.get("scaffold_command"),
            str,
        ):
            hydration_plan["scaffold_command"] = hydration_plan["scaffold_command"].replace(
                "--initiative-ref INI-EVI-002",
                f"--initiative-ref {initiative_id}",
            )
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")
    return bank_path, bank


def test_live_planning_banks_validate() -> None:
    validate_design_bank(DESIGN_BANK_PATH)
    validate_initiative_bank(INITIATIVE_BANK_PATH)


def test_ini_evi_002_bank_is_authoritative_planning_state() -> None:
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    research = _load_yaml(RESEARCH_INDEX_PATH)

    assert bank["schema_version"] == 1
    assert bank["bank_type"] == "initiative"
    assert bank["initiative_id"] == "INI-EVI-002"
    assert bank["research_refs"] == [".azoth/research/ini-evi-002-research-bank.yaml"]
    assert research["artifact_type"] == "research_evidence_index"
    assert research["planning_bank_ref"] == ".azoth/initiative-banks/INI-EVI-002.yaml"
    assert "candidate_slices" not in research
    assert "readiness" not in research


def test_ini_evi_002_candidate_slices_are_planning_evidence_only() -> None:
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    slices = bank.get("candidate_slices")

    assert isinstance(slices, list)
    assert slices
    for candidate in slices:
        assert isinstance(candidate, dict)
        assert candidate["initiative_ref"] == "INI-EVI-002"
        assert candidate["status"] in {"candidate", "hydrated", "complete", "parked", "rejected"}
        if candidate["status"] in {"candidate", "hydrated", "complete"}:
            assert candidate["acceptance_criteria"]
            assert candidate["research_evidence_refs"]
            assert candidate["known_non_goals"]


def test_ini_evi_002_bank_third_slice_is_complete_and_routes_helper_refinement() -> None:
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    readiness = bank.get("readiness")
    completed_candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-b"
    )
    hydrated_candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )

    assert bank["status"] == "active_refinement"
    assert isinstance(readiness, dict)
    assert readiness["readiness_status"] == "continue_research"
    assert readiness["human_decision"] == "approved"
    assert readiness["candidate_first_slice"] == "slice-evi-002-c"
    assert readiness["next_readiness_gate"] == "helper_proposal_refinement_before_next_hydration"
    assert (
        readiness["next_candidate_ref"]
        == ".azoth/proposals/initiative-bank-tooling-and-hydration-helper.yaml"
    )
    assert bank["hydration_history"]
    assert bank["hydration_history"][-1]["task_ref"] == "T-021"
    assert completed_candidate["status"] == "complete"
    assert completed_candidate["proposed_task_id"] == "T-019"
    assert completed_candidate["acceptance_criteria"]
    assert completed_candidate["open_questions"] == []
    assert hydrated_candidate["status"] == "complete"
    assert hydrated_candidate["proposed_task_id"] == "T-021"
    assert hydrated_candidate["open_questions"] == []


def test_ini_evi_002_readiness_report_exposes_hydration_decision() -> None:
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    report = build_initiative_readiness_report(INITIATIVE_BANK_PATH)

    assert report["initiative_id"] == "INI-EVI-002"
    assert report["initiative_ref"] == "INI-EVI-002"
    assert report["source_bank_ref"] == ".azoth/initiative-banks/INI-EVI-002.yaml"
    assert report["readiness_status"] == "continue_research"
    assert report["human_decision"] == "approved"
    assert report["candidate_first_slice"] == "slice-evi-002-c"
    assert report["candidate_id"] == "slice-evi-002-c"
    assert report["candidate_slice_ref"] == "slice-evi-002-c"
    assert report["candidate_task_ref"] == "T-021"
    assert report["candidate_status"] == "complete"
    assert report["proposed_title"] == "Planning-bank ID and coverage policy"
    assert report["target_layer"] == "infrastructure"
    assert report["delivery_pipeline"] == "standard"
    assert report["acceptance"] == candidate["acceptance_criteria"]
    assert report["acceptance_criteria_status"] == "stable"
    assert report["non_goals"] == candidate["known_non_goals"]
    assert report["non_goals_status"] == "stable"
    assert report["freshness_status"] == "reconciled_after_t_021_completion"
    assert (
        report["hydration_recommendation"]
        == "T-021 is complete across roadmap and backlog history; do not hydrate another raw slice until the helper proposal is refined into a narrow readiness or helper candidate."
    )
    assert report["blocking_reasons"] == [
        "candidate.status is complete; no hydration action remains",
        "readiness.readiness_status must be ready_to_hydrate",
    ]
    assert report["ready_to_hydrate"] is False
    assert report["scaffold_command"] is None


def test_readiness_report_emits_plan_only_handoff_for_approved_temp_candidate(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    readiness["acceptance_criteria_status"] = "stable"
    readiness["non_goals_status"] = "stable"
    readiness["hydration_recommendation"] = "Ready for plan-only scaffold."
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate["status"] = "candidate"
    candidate["proposed_task_id"] = "TBD-INI-TEST-001"
    candidate["acceptance_criteria"] = [
        "The approved temp candidate emits a scaffold command.",
        "The report remains plan-only and read-only.",
    ]
    candidate["known_non_goals"] = [
        "Do not mutate roadmap state.",
        "Do not implement write-mode hydration.",
    ]
    candidate["open_questions"] = []
    candidate["hydration_plan"]["proposed_title"] = "Temp approved planning-bank slice"
    candidate["hydration_plan"]["scaffold_command"] = (
        'scripts/roadmap_scaffold.py --title "Temp approved planning-bank slice" '
        "--initiative-ref INI-TEST --target-layer infrastructure --delivery-pipeline standard"
    )
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    report = build_initiative_readiness_report(bank_path, repo_root=repo)

    assert report == {
        "initiative_id": "INI-TEST",
        "initiative_ref": "INI-TEST",
        "source_bank_ref": ".azoth/initiative-banks/INI-TEST.yaml",
        "readiness_status": "ready_to_hydrate",
        "human_decision": "approved",
        "candidate_first_slice": "slice-evi-002-c",
        "candidate_id": "slice-evi-002-c",
        "candidate_slice_ref": "slice-evi-002-c",
        "candidate_task_ref": "TBD-INI-TEST-001",
        "candidate_status": "candidate",
        "proposed_title": "Temp approved planning-bank slice",
        "target_layer": "infrastructure",
        "delivery_pipeline": "standard",
        "acceptance": [
            "The approved temp candidate emits a scaffold command.",
            "The report remains plan-only and read-only.",
        ],
        "acceptance_criteria_status": "stable",
        "non_goals": [
            "Do not mutate roadmap state.",
            "Do not implement write-mode hydration.",
        ],
        "non_goals_status": "stable",
        "freshness_status": "fresh",
        "hydration_recommendation": "Ready for plan-only scaffold.",
        "blocking_reasons": [],
        "ready_to_hydrate": True,
        "scaffold_command": (
            'scripts/roadmap_scaffold.py --title "Temp approved planning-bank slice" '
            "--initiative-ref INI-TEST --target-layer infrastructure --delivery-pipeline standard"
        ),
    }


def test_readiness_report_fails_closed_when_candidate_status_is_missing(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate.pop("status", None)
    candidate["proposed_task_id"] = "TBD-INI-TEST-001"
    candidate["open_questions"] = []
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    report = build_initiative_readiness_report(bank_path, repo_root=repo)

    assert report["candidate_status"] == "missing"
    assert report["ready_to_hydrate"] is False
    assert report["scaffold_command"] is None
    assert "candidate.status must be present" in report["blocking_reasons"]


def test_readiness_report_fails_closed_when_proposed_title_is_missing(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate["status"] = "candidate"
    candidate["proposed_task_id"] = "TBD-INI-TEST-001"
    candidate["open_questions"] = []
    candidate["hydration_plan"].pop("proposed_title", None)
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    report = build_initiative_readiness_report(bank_path, repo_root=repo)

    assert report["proposed_title"] is None
    assert report["ready_to_hydrate"] is False
    assert report["scaffold_command"] is None
    assert (
        "candidate.hydration_plan.proposed_title must be a non-empty string"
        in report["blocking_reasons"]
    )


def test_readiness_report_fails_closed_on_missing_or_stale_freshness(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness.pop("freshness_status", None)
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate["status"] = "candidate"
    candidate["open_questions"] = []
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    missing_report = build_initiative_readiness_report(bank_path, repo_root=repo)

    assert missing_report["freshness_status"] == "missing"
    assert missing_report["ready_to_hydrate"] is False
    assert missing_report["scaffold_command"] is None
    assert (
        "readiness.freshness_status must be present and non-stale"
        in missing_report["blocking_reasons"]
    )

    readiness["freshness_status"] = "stale"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    stale_report = build_initiative_readiness_report(bank_path, repo_root=repo)

    assert stale_report["freshness_status"] == "stale"
    assert stale_report["ready_to_hydrate"] is False
    assert stale_report["scaffold_command"] is None
    assert "readiness.freshness_status must not be stale" in stale_report["blocking_reasons"]


def test_readiness_report_fails_closed_without_human_approval(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "initiative-banks" / "INI-TEST.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = "INI-TEST"
    bank["readiness"]["readiness_status"] = "ready_to_hydrate"
    bank["readiness"]["human_decision"] = "pending"
    for candidate in bank["candidate_slices"]:
        candidate["initiative_ref"] = "INI-TEST"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    report = build_initiative_readiness_report(bank_path, repo_root=repo)

    assert report["readiness_status"] == "ready_to_hydrate"
    assert report["human_decision"] == "pending"
    assert report["ready_to_hydrate"] is False
    assert "readiness.human_decision must be approved" in report["blocking_reasons"]


def test_readiness_report_fails_closed_when_human_decision_is_absent(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "initiative-banks" / "INI-TEST.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = "INI-TEST"
    bank["readiness"]["readiness_status"] = "ready_to_hydrate"
    bank["readiness"].pop("human_decision")
    for candidate in bank["candidate_slices"]:
        candidate["initiative_ref"] = "INI-TEST"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    report = build_initiative_readiness_report(bank_path, repo_root=repo)

    assert report["human_decision"] == "missing"
    assert report["ready_to_hydrate"] is False
    assert "readiness.human_decision must be approved" in report["blocking_reasons"]


def test_readiness_report_can_target_completed_prior_candidate() -> None:
    report = build_initiative_readiness_report(INITIATIVE_BANK_PATH, candidate_id="slice-evi-002-a")

    assert report["candidate_first_slice"] == "slice-evi-002-c"
    assert report["candidate_id"] == "slice-evi-002-a"
    assert report["candidate_task_ref"] == "T-018"
    assert report["candidate_status"] == "complete"
    assert report["ready_to_hydrate"] is False
    assert "candidate.status is complete; no hydration action remains" in report["blocking_reasons"]


def test_ini_evi_002_has_completed_third_slice_and_next_helper_route() -> None:
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)
    backlog = _load_yaml(BACKLOG_PATH)
    pending_candidate_ids = {
        str(candidate["proposed_task_id"])
        for candidate in bank["candidate_slices"]
        if str(candidate["proposed_task_id"]).startswith("TBD-")
    }
    completed_candidates = [
        candidate for candidate in bank["candidate_slices"] if candidate["status"] == "complete"
    ]
    hydrated_candidates = [
        candidate for candidate in bank["candidate_slices"] if candidate["status"] == "hydrated"
    ]

    initiative = next(item for item in roadmap["initiatives"] if item["id"] == "INI-EVI-002")
    assert initiative["phase"] == "v0.2.0-p3"
    assert initiative["task_ref"] == "T-022"
    assert initiative["slices"] == [
        {
            "task_ref": "T-018",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-018.yaml",
            "phase": "v0.2.0-p3",
            "status": "complete",
            "role": "historical",
        },
        {
            "task_ref": "T-019",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-019.yaml",
            "phase": "v0.2.0-p3",
            "status": "complete",
            "role": "historical",
        },
        {
            "task_ref": "T-021",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-021.yaml",
            "phase": "v0.2.0-p3",
            "status": "complete",
            "role": "historical",
        },
        {
            "task_ref": "T-022",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-022.yaml",
            "phase": "v0.2.0-p3",
            "status": "complete",
            "role": "primary",
        },
    ]
    assert initiative["initiative_bank_ref"] == ".azoth/initiative-banks/INI-EVI-002.yaml"
    assert initiative["design_bank_refs"] == [".azoth/design-banks/planning-banks-layer.yaml"]
    assert initiative["research_refs"] == [".azoth/research/ini-evi-002-research-bank.yaml"]
    assert initiative["candidate_slice_ref"] == "slice-evi-002-c"
    assert initiative["readiness_ref"] == ".azoth/initiative-banks/INI-EVI-002.yaml#readiness"
    assert "proposal_refs" not in initiative
    seeded_candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    assert [candidate["proposed_task_id"] for candidate in completed_candidates] == [
        "T-018",
        "T-019",
        "T-021",
    ]
    assert seeded_candidate["proposed_task_id"] == "T-021"
    assert seeded_candidate["status"] == "complete"
    assert hydrated_candidates == []
    assert initiative["discovery_status"] == "plan_only_handoff_helper_complete"
    assert "T-022 is complete" in initiative["next_discovery_action"]
    assert "fresh budget" in initiative["next_discovery_action"]

    roadmap_task_ids = {
        str(task.get("id"))
        for version in roadmap.get("versions") or []
        for block in ("tasks", "completed_tasks", "deferred_tasks")
        for task in (version.get(block) or [])
        if isinstance(task, dict)
    }
    backlog_ids = {str(item.get("id")) for item in backlog.get("items") or []}
    spec_ids = {path.stem for path in SPECS_DIR.glob("*.yaml")}

    assert pending_candidate_ids.isdisjoint(roadmap_task_ids)
    assert pending_candidate_ids.isdisjoint(backlog_ids)
    assert pending_candidate_ids.isdisjoint(spec_ids)
    assert "T-018" in roadmap_task_ids
    assert "T-018" in backlog_ids
    assert "T-018" in spec_ids
    assert "T-019" in roadmap_task_ids
    assert "T-019" in backlog_ids
    assert "T-019" in spec_ids
    assert "T-021" in roadmap_task_ids
    assert "T-021" in backlog_ids
    assert "T-021" in spec_ids
    assert "T-022" in roadmap_task_ids
    assert "T-022" in backlog_ids
    assert "T-022" in spec_ids


def test_design_bank_id_must_match_filename(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "design-banks" / "not-planning-banks-layer.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(DESIGN_BANK_PATH)
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="id must match filename stem"):
        validate_design_bank(bank_path, repo_root=repo)


def test_initiative_bank_filename_must_match_initiative_id(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "initiative-banks" / "INI-WRONG.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(
        PlanningBankValidationError,
        match="initiative_id must match filename stem",
    ):
        validate_initiative_bank(bank_path, repo_root=repo)


def test_planning_bank_coverage_report_only_requires_declared_bank_refs() -> None:
    report = planning_bank_validate.build_planning_bank_coverage_report(ROOT)
    initiatives = {
        item["initiative_id"]: item
        for item in report["initiatives"]
    }

    assert initiatives["INI-EVI-002"]["coverage_required"] is True
    assert initiatives["INI-EVI-002"]["covered"] is True
    assert initiatives["INI-EVI-002"]["initiative_bank_ref"] == ".azoth/initiative-banks/INI-EVI-002.yaml"
    assert initiatives["INI-MEM-002"]["coverage_required"] is False
    assert initiatives["INI-MEM-002"]["covered"] is False
    assert report["summary"]["missing_required"] == 0


def test_roadmap_has_no_authoritative_refs_to_ignored_proposal_inbox_files() -> None:
    validate_roadmap_refs()


def test_validator_rejects_ready_initiative_bank_without_human_approval(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "initiative-banks" / "INI-TEST.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = "INI-TEST"
    bank["readiness"]["readiness_status"] = "ready_to_hydrate"
    bank["readiness"]["human_decision"] = "pending"
    for candidate in bank["candidate_slices"]:
        candidate["initiative_ref"] = "INI-TEST"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="human_decision"):
        validate_initiative_bank(bank_path, repo_root=repo)


def test_validator_rejects_ready_initiative_bank_missing_human_decision(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "initiative-banks" / "INI-TEST.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = "INI-TEST"
    bank["readiness"]["readiness_status"] = "ready_to_hydrate"
    bank["readiness"].pop("human_decision")
    for candidate in bank["candidate_slices"]:
        candidate["initiative_ref"] = "INI-TEST"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="readiness.human_decision"):
        validate_initiative_bank(bank_path, repo_root=repo)


def test_validator_rejects_malformed_candidate_slice_types(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "initiative-banks" / "INI-TEST.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = "INI-TEST"
    bank["candidate_slices"][0]["initiative_ref"] = "INI-TEST"
    bank["candidate_slices"][0]["acceptance_criteria"] = "not-a-list"
    for candidate in bank["candidate_slices"][1:]:
        candidate["initiative_ref"] = "INI-TEST"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="acceptance_criteria must be a list"):
        validate_initiative_bank(bank_path, repo_root=repo)


def test_validator_rejects_missing_required_candidate_field(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "initiative-banks" / "INI-TEST.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = "INI-TEST"
    bank["candidate_slices"][0].pop("candidate_id")
    for candidate in bank["candidate_slices"]:
        candidate["initiative_ref"] = "INI-TEST"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="missing required field"):
        validate_initiative_bank(bank_path, repo_root=repo)


def test_validator_rejects_invalid_candidate_status(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "initiative-banks" / "INI-TEST.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = "INI-TEST"
    bank["candidate_slices"][0]["status"] = "ready"
    for candidate in bank["candidate_slices"]:
        candidate["initiative_ref"] = "INI-TEST"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="status must be one of"):
        validate_initiative_bank(bank_path, repo_root=repo)


def test_validator_rejects_duplicate_candidate_ids(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "initiative-banks" / "INI-TEST.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = "INI-TEST"
    bank["candidate_slices"][1]["candidate_id"] = bank["candidate_slices"][0]["candidate_id"]
    for candidate in bank["candidate_slices"]:
        candidate["initiative_ref"] = "INI-TEST"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="candidate_id must be unique"):
        validate_initiative_bank(bank_path, repo_root=repo)


def test_validator_cli_accepts_live_banks_and_roadmap_refs() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "planning_bank_validate.py"),
            str(DESIGN_BANK_PATH),
            str(INITIATIVE_BANK_PATH),
            "--check-roadmap-refs",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_validator_cli_prints_readiness_reports_top_level_yaml() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "planning_bank_validate.py"),
            "--readiness-report",
            str(INITIATIVE_BANK_PATH),
            "--candidate-id",
            "slice-evi-002-c",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    output = yaml.safe_load(result.stdout)
    assert set(output) == {"readiness_reports"}
    report = output["readiness_reports"][0]
    assert {
        "initiative_ref",
        "source_bank_ref",
        "candidate_slice_ref",
        "proposed_title",
        "target_layer",
        "delivery_pipeline",
        "acceptance",
        "non_goals",
        "scaffold_command",
    }.issubset(report)
    assert report["candidate_id"] == "slice-evi-002-c"
    assert report["candidate_slice_ref"] == "slice-evi-002-c"
    assert report["source_bank_ref"] == ".azoth/initiative-banks/INI-EVI-002.yaml"
    assert report["proposed_title"] == "Planning-bank ID and coverage policy"
    assert report["ready_to_hydrate"] is False
    assert report["scaffold_command"] is None


def test_validator_cli_readiness_report_is_read_only() -> None:
    guarded_paths = [
        INITIATIVE_BANK_PATH,
        ROADMAP_PATH,
        BACKLOG_PATH,
        ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-018.yaml",
    ]
    before = {path: path.read_bytes() for path in guarded_paths}

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "planning_bank_validate.py"),
            "--readiness-report",
            str(INITIATIVE_BANK_PATH),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert before == {path: path.read_bytes() for path in guarded_paths}


def test_validator_cli_coverage_report_is_read_only() -> None:
    guarded_paths = [
        DESIGN_BANK_PATH,
        INITIATIVE_BANK_PATH,
        ROADMAP_PATH,
        BACKLOG_PATH,
    ]
    before = {path: path.read_bytes() for path in guarded_paths}

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "planning_bank_validate.py"),
            "--coverage-report",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    output = yaml.safe_load(result.stdout)
    assert set(output) == {"planning_bank_coverage"}
    assert output["planning_bank_coverage"]["summary"]["missing_required"] == 0
    assert before == {path: path.read_bytes() for path in guarded_paths}


def test_richness_cli_initiative_bank_report_is_read_only() -> None:
    guarded_paths = [
        INITIATIVE_BANK_PATH,
        ROADMAP_PATH,
        BACKLOG_PATH,
        ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "T-019.yaml",
    ]
    before = {path: path.read_bytes() for path in guarded_paths}

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "proposal_knowledge_richness.py"),
            str(INITIATIVE_BANK_PATH),
            "--artifact-type",
            "initiative-bank",
            "--candidate-id",
            "slice-evi-002-b",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert before == {path: path.read_bytes() for path in guarded_paths}

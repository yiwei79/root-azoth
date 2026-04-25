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


def test_ini_evi_002_bank_second_slice_is_complete_after_delivery() -> None:
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    readiness = bank.get("readiness")
    completed_candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-b"
    )
    seeded_candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )

    assert bank["status"] == "active_refinement"
    assert isinstance(readiness, dict)
    assert readiness["readiness_status"] == "continue_research"
    assert readiness["human_decision"] == "approved_seed_only"
    assert readiness["candidate_first_slice"] == "slice-evi-002-c"
    assert readiness["next_readiness_gate"] == "research_refinement_before_hydration"
    assert bank["hydration_history"]
    assert bank["hydration_history"][-1]["task_ref"] == "T-019"
    assert completed_candidate["status"] == "complete"
    assert completed_candidate["proposed_task_id"] == "T-019"
    assert completed_candidate["acceptance_criteria"]
    assert completed_candidate["open_questions"] == []
    assert seeded_candidate["status"] == "candidate"
    assert seeded_candidate["proposed_task_id"] == "TBD-EVI-002-C"
    assert seeded_candidate["open_questions"]


def test_ini_evi_002_readiness_report_exposes_hydration_decision() -> None:
    report = build_initiative_readiness_report(INITIATIVE_BANK_PATH)

    assert report == {
        "initiative_id": "INI-EVI-002",
        "readiness_status": "continue_research",
        "human_decision": "approved_seed_only",
        "candidate_first_slice": "slice-evi-002-c",
        "candidate_id": "slice-evi-002-c",
        "candidate_task_ref": "TBD-EVI-002-C",
        "candidate_status": "candidate",
        "acceptance_criteria_status": "seeded",
        "non_goals_status": "seeded",
        "freshness_status": "refreshed_after_t_020",
        "hydration_recommendation": "Seeded slice-evi-002-c for research/refinement. Run /next or /start to discover the bank, then run a research/refinement session before any hydration.",
        "blocking_reasons": [
            "readiness.readiness_status must be ready_to_hydrate",
            "readiness.human_decision must be approved",
            "candidate.open_questions must be empty",
        ],
        "ready_to_hydrate": False,
    }


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


def test_ini_evi_002_has_completed_second_slice_as_completed_task() -> None:
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
    assert initiative["phase"] is None
    assert initiative["task_ref"] == "T-019"
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
    ]
    assert seeded_candidate["proposed_task_id"] == "TBD-EVI-002-C"
    assert seeded_candidate["status"] == "candidate"
    assert hydrated_candidates == []

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
            "slice-evi-002-b",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    output = yaml.safe_load(result.stdout)
    assert set(output) == {"readiness_reports"}
    assert output["readiness_reports"][0]["candidate_id"] == "slice-evi-002-b"
    assert output["readiness_reports"][0]["ready_to_hydrate"] is False


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

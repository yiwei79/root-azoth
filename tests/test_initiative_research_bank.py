from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
BANK_PATH = ROOT / ".azoth" / "research" / "ini-evi-002-research-bank.yaml"
ROADMAP_PATH = ROOT / ".azoth" / "roadmap.yaml"
BACKLOG_PATH = ROOT / ".azoth" / "backlog.yaml"
SPECS_DIR = ROOT / ".azoth" / "roadmap-specs" / "v0.2.0"


REQUIRED_BANK_FIELDS = {
    "schema_version",
    "initiative_id",
    "title",
    "source_sessions",
    "research_questions",
    "research_packs",
    "local_findings",
    "external_findings",
    "assumptions",
    "contradictions",
    "challenge_log",
    "candidate_slices",
    "readiness",
    "hydration_history",
}

REQUIRED_SLICE_FIELDS = {
    "proposed_task_id",
    "title",
    "initiative_ref",
    "target_layer",
    "delivery_pipeline",
    "summary",
    "acceptance_criteria",
    "research_evidence_refs",
    "known_non_goals",
    "open_questions",
    "recommended_phase",
}


def _load_bank() -> dict:
    loaded = yaml.safe_load(BANK_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_ini_evi_002_research_bank_has_required_contract_fields() -> None:
    bank = _load_bank()

    assert bank["schema_version"] == 1
    assert bank["initiative_id"] == "INI-EVI-002"
    assert REQUIRED_BANK_FIELDS <= set(bank)
    assert isinstance(bank.get("contacts"), list)
    assert bank["contacts"], "initiative bank should retain contacts/source touchpoints"


def test_ini_evi_002_candidate_slices_are_planning_evidence_only() -> None:
    bank = _load_bank()
    slices = bank.get("candidate_slices")

    assert isinstance(slices, list)
    assert slices
    for candidate in slices:
        assert isinstance(candidate, dict)
        assert REQUIRED_SLICE_FIELDS <= set(candidate)
        assert candidate["initiative_ref"] == "INI-EVI-002"
        assert str(candidate["proposed_task_id"]).startswith("TBD-")
        assert candidate["status"] in {"candidate", "parked", "rejected"}
        if candidate["status"] == "candidate":
            assert candidate["acceptance_criteria"]
            assert candidate["research_evidence_refs"]
            assert candidate["known_non_goals"]


def test_ini_evi_002_bank_is_not_ready_to_hydrate_yet() -> None:
    bank = _load_bank()
    readiness = bank.get("readiness")

    assert isinstance(readiness, dict)
    assert readiness["readiness_status"] == "continue_research"
    assert readiness["human_decision"] == "pending"
    assert bank["hydration_history"] == []


def test_ini_evi_002_has_not_been_prematurely_hydrated() -> None:
    bank = _load_bank()
    roadmap = _load_yaml(ROADMAP_PATH)
    backlog = _load_yaml(BACKLOG_PATH)
    candidate_ids = {
        str(candidate["proposed_task_id"])
        for candidate in bank["candidate_slices"]
        if str(candidate["proposed_task_id"]).startswith("TBD-")
    }

    initiative = next(item for item in roadmap["initiatives"] if item["id"] == "INI-EVI-002")
    assert initiative["phase"] is None
    assert initiative["task_ref"] is None
    assert initiative["slices"] == []
    assert initiative["research_ref"] == ".azoth/research/ini-evi-002-research-bank.yaml"
    assert initiative["candidate_slice_ref"] == "slice-evi-002-a"
    assert initiative["readiness_ref"] == ".azoth/research/ini-evi-002-research-bank.yaml#readiness"
    assert initiative["proposal_refs"] == [
        ".azoth/proposals/initiative-discovery-to-roadmap-hydration.yaml",
        ".azoth/proposals/initiative-bank-tooling-and-hydration-helper.yaml",
    ]

    roadmap_task_ids = {
        str(task.get("id"))
        for version in roadmap.get("versions") or []
        for block in ("tasks", "completed_tasks", "deferred_tasks")
        for task in (version.get(block) or [])
        if isinstance(task, dict)
    }
    backlog_ids = {str(item.get("id")) for item in backlog.get("items") or []}
    spec_ids = {path.stem for path in SPECS_DIR.glob("*.yaml")}

    assert candidate_ids.isdisjoint(roadmap_task_ids)
    assert candidate_ids.isdisjoint(backlog_ids)
    assert candidate_ids.isdisjoint(spec_ids)


def test_ini_evi_002_bank_ids_and_readiness_values_are_well_formed() -> None:
    bank = _load_bank()
    pack_ids = [pack["pack_id"] for pack in bank["research_packs"]]
    question_ids = [question["question_id"] for question in bank["research_questions"]]
    allowed_readiness = {"continue_research", "ready_to_hydrate", "defer", "reject"}

    assert len(pack_ids) == len(set(pack_ids))
    assert len(question_ids) == len(set(question_ids))
    assert bank["readiness"]["readiness_status"] in allowed_readiness

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
INTAKE_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-049-intake.yaml"
INI_PKB_PATH = ROOT / ".azoth" / "initiative-banks" / "INI-PKB-001.yaml"


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_t049_intake_records_exact_pointer_only_project_boundary() -> None:
    intake = _load_yaml(INTAKE_PATH)

    assert intake["schema_version"] == 1
    assert intake["candidate_ref"] == "INI-PKB-001#slice-pkb-001-f"
    assert intake["decision"] == "ready_to_hydrate_planning_scaffold"
    assert intake["personal_root"]["path"] == "/Users/yiwei/GithubRepos/personal-azoth-root"
    assert intake["personal_root"]["status"] == "clean"

    pilot = intake["pilot_projects"][0]
    assert pilot["project_id"] == "ras-or-ray"
    assert pilot["path"] == "/Users/yiwei/GithubRepos/ras or ray"
    assert pilot["profile_mode"] == "pointer_only"
    assert pilot["status"] == "clean"
    assert intake["project_state_convention"]["convention_id"] == "minimal_pointer_profile_v1"


def test_t049_intake_forbids_project_mutation_and_expansion() -> None:
    intake = _load_yaml(INTAKE_PATH)

    assert intake["hydration_boundary"]["can_hydrate_task_scaffold"] is True
    assert intake["hydration_boundary"]["can_mutate_personal_root"] is False
    assert intake["hydration_boundary"]["can_mutate_project_repo"] is False
    assert "project_repo_write" in intake["forbidden_outputs"]
    assert "source_registry_onboarding" in intake["forbidden_outputs"]
    assert "retrieval_indexing" in intake["forbidden_outputs"]


def test_ini_pkb_t049_readiness_is_hydration_only() -> None:
    bank = _load_yaml(INI_PKB_PATH)
    candidates = {
        candidate["candidate_id"]: candidate for candidate in bank["candidate_slices"]
    }
    t049 = candidates["slice-pkb-001-f"]

    assert t049["hydration_plan"]["mode"] == "executed"
    assert t049["hydration_plan"]["hydrated_task_ref"] == "T-049"
    assert (
        t049["hydration_plan"]["hydrated_spec_ref"]
        == ".azoth/roadmap-specs/v0.2.0/T-049.yaml"
    )
    assert t049["open_questions"] == []
    assert t049["project_state_convention"]["convention_id"] == "minimal_pointer_profile_v1"
    assert t049["pilot_project_refs"] == [
        {
            "project_id": "ras-or-ray",
            "path": "/Users/yiwei/GithubRepos/ras or ray",
            "profile_mode": "pointer_only",
            "head": "82770daadf6db5056efdb1ace38d9535ee082a46",
        }
    ]

    readiness = bank["readiness"]
    assert readiness["readiness_status"] == "ready_to_hydrate"
    assert readiness["human_decision"] == "approved"
    assert readiness["approval_scope"] == "hydration_specific_slice_pkb_001_f"
    assert "hydrated as T-049" in readiness["hydration_recommendation"]
    assert "Do not repeat hydration" in readiness["hydration_recommendation"]

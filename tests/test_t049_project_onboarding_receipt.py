from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / ".azoth" / "handoffs" / "2026-05-01-t-049-validation-report.yaml"
INI_PKB_PATH = ROOT / ".azoth" / "initiative-banks" / "INI-PKB-001.yaml"


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_t049_validation_report_records_pointer_only_personal_root_receipt() -> None:
    report = _load_yaml(REPORT_PATH)

    assert report["task_ref"] == "T-049"
    assert report["delivery_mode"] == "governed_pointer_only_project_onboarding"
    assert report["apply"]["profile_mode"] == "pointer_only"
    assert set(report["apply"]["profile_fields_written"]) == set(
        report["apply"]["allowed_metadata_fields"]
    )
    assert report["receipt"]["personal_root_commit"] == (
        "aeac2fac1628623dc54bb2bb0e050f6135255280"
    )
    assert report["receipt"]["personal_root_initial_receipt_commit"] == (
        "42fcec548ac0197549bae49f0f1627e3f7bc770b"
    )
    assert report["receipt"]["rollback_ref"] == (
        "074748a950eefa9c5a69d63f4631a332fd899b9d"
    )
    assert report["post_validation"]["personal_root_status_after"]["status"] == [
        "## main"
    ]
    assert report["post_validation"]["pilot_project_status_after"]["status"] == [
        "## main...origin/main"
    ]


def test_t049_report_keeps_project_onboarding_boundaries_explicit() -> None:
    report = _load_yaml(REPORT_PATH)

    assert "source_files" in report["apply"]["excluded_fields"]
    assert "code_summaries" in report["apply"]["excluded_fields"]
    assert "retrieval_index" in report["apply"]["excluded_fields"]
    assert "no pilot project repo mutation" in report["non_goals_confirmed"]
    assert "no project source scan" in report["non_goals_confirmed"]
    assert "no retrieval expansion or indexing" in report["non_goals_confirmed"]
    assert "separate project-specific gate" in report["next_safe_action"]


def test_ini_pkb_marks_t049_delivered_and_routes_post_t050_continuation() -> None:
    bank = _load_yaml(INI_PKB_PATH)
    candidates = {
        candidate["proposed_task_id"]: candidate for candidate in bank["candidate_slices"]
    }

    t049 = candidates["T-049"]
    assert t049["status"] == "complete"
    assert t049["delivery_evidence_refs"] == [
        ".azoth/handoffs/2026-05-01-t-049-validation-report.yaml"
    ]
    assert t049["personal_root_receipt_ref"] == (
        "/Users/yiwei/GithubRepos/personal-azoth-root/.azoth/projects/handoffs/"
        "t-049-ras-or-ray-2026-05-01.yaml"
    )
    assert t049["personal_root_commit"] == "aeac2fac1628623dc54bb2bb0e050f6135255280"

    t050 = candidates["T-050"]
    assert t050["status"] == "complete"
    assert t050["hydration_plan"]["hydrated_task_ref"] == "T-050"
    assert t050["hydration_plan"]["hydrated_spec_ref"] == (
        ".azoth/roadmap-specs/v0.2.0/T-050.yaml"
    )
    assert bank["closeout_history"][-1]["closeout_ref"] == (
        ".azoth/handoffs/2026-05-01-t-050-stable-deployment-closeout.yaml"
    )

    readiness = bank["readiness"]
    assert readiness["candidate_first_slice"] == "slice-pkb-001-h"
    assert readiness["next_candidate_ref"] == "slice-pkb-001-h"
    assert readiness["readiness_status"] == "ready_to_hydrate"
    assert readiness["human_decision"] == "approved"
    assert readiness["delivery_authorized"] is False
    assert readiness["hydrate_authorized"] is False
    assert (
        readiness["next_readiness_gate"]
        == "hydrate_post_t050_release_readiness_planning_scaffold"
    )
    assert "has been hydrated as T-051" in readiness["hydration_recommendation"]

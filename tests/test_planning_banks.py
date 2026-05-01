from __future__ import annotations

import json
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
    build_derived_task_capsule_report,
    build_initiative_readiness_report,
    hydrate_approved_initiative_candidate,
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


def _write_temp_initiative_bank(
    repo: Path, *, initiative_id: str = "INI-TEST"
) -> tuple[Path, dict]:
    bank_path = repo / ".azoth" / "initiative-banks" / f"{initiative_id}.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    bank["initiative_id"] = initiative_id
    if isinstance(bank.get("readiness"), dict):
        bank["readiness"]["source_bank_ref"] = f".azoth/initiative-banks/{initiative_id}.yaml"
        bank["readiness"].pop("non_laundering_note", None)
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


def _write_hydration_scope_gate(
    repo: Path,
    *,
    session_id: str = "session-test",
    initiative_id: str = "INI-TEST",
    source_bank_ref: str = ".azoth/initiative-banks/INI-TEST.yaml",
    approval_scope: str = "hydration_specific_slice_evi_002_c",
) -> Path:
    gate_path = repo / ".azoth" / "scope-gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "human",
                "session_id": session_id,
                "expires_at": "2099-01-01T00:00:00Z",
                "goal": "Hydrate approved planning-bank candidate",
                "backlog_id": "AD-HOC",
                "pipeline_command": "dynamic-full-auto",
                "delivery_pipeline": "dynamic-full-auto",
                "target_layer": "planning",
                "source_initiative_ref": initiative_id,
                "source_artifacts": [source_bank_ref],
                "approval_scope": approval_scope,
                "approval_basis": f"Explicitly approves {approval_scope}.",
            }
        ),
        encoding="utf-8",
    )
    return gate_path


def _write_ready_hydration_candidate(
    repo: Path,
    *,
    approval_scope: str = "hydration_specific_slice_evi_002_c",
) -> Path:
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["approval_scope"] = approval_scope
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate["status"] = "candidate"
    candidate["proposed_task_id"] = "TBD-INI-TEST-001"
    candidate["open_questions"] = []
    candidate["hydration_plan"]["proposed_title"] = "Temp approved planning-bank slice"
    candidate["hydration_plan"]["scaffold_command"] = (
        'python3 scripts/roadmap_scaffold.py --title "Temp approved planning-bank slice" '
        "--initiative-ref INI-TEST --target-layer infrastructure --delivery-pipeline standard"
    )
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")
    return bank_path


def _write_ready_derived_capsule_candidate(
    repo: Path,
    *,
    source_status: str = "answered",
    source_fresh_until: str | None = "2099-01-01T00:00:00Z",
    candidate_status: str = "candidate",
    human_decision: str = "approved",
    freshness_status: str = "fresh",
    target_layer: str = "infrastructure",
) -> Path:
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = human_decision
    readiness["freshness_status"] = freshness_status
    readiness["approval_scope"] = "hydration_specific_slice_evi_002_f"
    readiness["approval_basis"] = "Temp approval for derived task-capsule preview."
    readiness["candidate_first_slice"] = "slice-evi-002-f"
    readiness["acceptance_criteria_status"] = "stable"
    readiness["non_goals_status"] = "stable"
    source_question = next(
        question
        for question in bank["research_questions"]
        if question["question_id"] == "rq-evi-002-010"
    )
    source_question["status"] = source_status
    source_question["answered_at"] = "2026-04-30T20:39:24Z"
    if source_fresh_until is None:
        source_question.pop("fresh_until", None)
    else:
        source_question["fresh_until"] = source_fresh_until
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-f"
    )
    candidate["status"] = candidate_status
    candidate["proposed_task_id"] = "T-999"
    candidate["target_layer"] = target_layer
    candidate["open_questions"] = []
    candidate["research_evidence_refs"] = [
        ".azoth/research/ini-evi-002-research-bank.yaml#pack-evi-002-c-policy-selection-001"
    ]
    candidate["hydration_plan"]["proposed_title"] = "Temp derived task capsule"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")
    return bank_path


def test_live_planning_banks_validate() -> None:
    validate_design_bank(DESIGN_BANK_PATH)
    validate_initiative_bank(INITIATIVE_BANK_PATH)


def test_design_bank_declares_closeout_history_policy() -> None:
    bank = _load_yaml(DESIGN_BANK_PATH)
    policy = bank["closeout_history_policy"]

    assert policy["policy_id"] == "planning_bank_closeout_history_merge_policy_v1"
    assert policy["merge_strategy"] == "append_only"
    assert policy["routine_closeout"]["planning_bank_write_mode"] == "forbidden"
    assert policy["explicit_hydration_history"]["append_path"] == "hydration_history"
    assert policy["explicit_hydration_history"]["append_position"] == "append_tail"
    assert policy["explicit_hydration_history"]["required_metadata"] == [
        "hydrated_at",
        "session_id",
        "candidate_slice_ref",
        "task_ref",
        "spec_ref",
        "approval_scope",
        "approval_basis",
        "append_policy_ref",
        "append_mode",
        "merge_key",
    ]
    assert "historical" in policy["non_laundering_rule"]
    assert "non retroactive pipeline compliance" in policy["non_laundering_rule"]


def test_design_bank_validation_requires_closeout_history_policy(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "design-banks" / "planning-banks-layer.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(DESIGN_BANK_PATH)
    bank.pop("closeout_history_policy", None)
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="closeout_history_policy"):
        validate_design_bank(bank_path, repo_root=repo)


@pytest.mark.parametrize(
    ("policy_update", "routine_update", "error_match"),
    [
        ({"merge_strategy": "newest_first"}, {}, "merge_strategy"),
        ({}, {"planning_bank_write_mode": "append"}, "planning_bank_write_mode"),
        ({"non_laundering_rule": "Do not launder."}, {}, "non_laundering_rule"),
    ],
)
def test_design_bank_validation_rejects_non_merge_safe_closeout_policy(
    tmp_path: Path,
    policy_update: dict,
    routine_update: dict,
    error_match: str,
) -> None:
    repo = tmp_path
    bank_path = repo / ".azoth" / "design-banks" / "planning-banks-layer.yaml"
    bank_path.parent.mkdir(parents=True)
    bank = _load_yaml(DESIGN_BANK_PATH)
    policy = bank["closeout_history_policy"]
    policy.update(policy_update)
    policy["routine_closeout"].update(routine_update)
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match=error_match):
        validate_design_bank(bank_path, repo_root=repo)


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


def test_ini_evi_002_bank_reconciles_helper_and_hydrates_distinct_follow_on() -> None:
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
    next_candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-d"
    )
    distinct_follow_on = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-e"
    )
    continuation_seed = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-f"
    )

    assert bank["status"] == "active_refinement"
    assert isinstance(readiness, dict)
    assert readiness["readiness_status"] == "ready_to_hydrate"
    assert readiness["human_decision"] == "approved"
    assert readiness["approval_scope"] == "hydration_specific_slice_evi_002_f"
    assert readiness["candidate_first_slice"] == "slice-evi-002-f"
    assert readiness["next_readiness_gate"] == "hydrate_task_capsule_derivation_slice"
    assert readiness["next_candidate_ref"] == "slice-evi-002-f"
    assert bank["hydration_history"]
    latest_hydration = bank["hydration_history"][0]
    assert latest_hydration["task_ref"] == "T-043"
    assert latest_hydration["pipeline_compliance"] == "historically_bypassed"
    assert "not retroactively pipeline-compliant" in latest_hydration["audit_note"]
    assert completed_candidate["status"] == "complete"
    assert completed_candidate["proposed_task_id"] == "T-019"
    assert completed_candidate["acceptance_criteria"]
    assert completed_candidate["open_questions"] == []
    assert hydrated_candidate["status"] == "complete"
    assert hydrated_candidate["proposed_task_id"] == "T-021"
    assert hydrated_candidate["open_questions"] == []
    assert next_candidate["status"] == "complete"
    assert next_candidate["proposed_task_id"] == "T-022"
    assert next_candidate["open_questions"] == []
    assert distinct_follow_on["status"] == "hydrated"
    assert distinct_follow_on["proposed_task_id"] == "T-043"
    assert distinct_follow_on["open_questions"] == []
    assert continuation_seed["status"] == "hydrated"
    assert continuation_seed["proposed_task_id"] == "T-046"
    assert continuation_seed["open_questions"] == []


def test_ini_evi_002_readiness_report_exposes_hydrated_task_capsule_slice() -> None:
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-f"
    )
    report = build_initiative_readiness_report(INITIATIVE_BANK_PATH)

    assert report["initiative_id"] == "INI-EVI-002"
    assert report["initiative_ref"] == "INI-EVI-002"
    assert report["source_bank_ref"] == ".azoth/initiative-banks/INI-EVI-002.yaml"
    assert report["readiness_status"] == "ready_to_hydrate"
    assert report["human_decision"] == "approved"
    assert report["approval_scope"] == "hydration_specific_slice_evi_002_f"
    assert report["candidate_first_slice"] == "slice-evi-002-f"
    assert report["candidate_id"] == "slice-evi-002-f"
    assert report["candidate_slice_ref"] == "slice-evi-002-f"
    assert report["candidate_task_ref"] == "T-046"
    assert report["candidate_status"] == "hydrated"
    assert (
        report["proposed_title"] == "Task research capsule derivation from initiative-bank evidence"
    )
    assert report["target_layer"] == "infrastructure"
    assert report["delivery_pipeline"] == "standard"
    assert report["acceptance"] == candidate["acceptance_criteria"]
    assert report["acceptance_criteria_status"] == "stable_for_planning"
    assert report["non_goals"] == candidate["known_non_goals"]
    assert report["non_goals_status"] == "stable_for_planning"
    assert report["freshness_status"] == "current_as_of_2026_04_30_hydrated_to_t_046"
    assert "historically bypassed" in report["non_laundering_note"]
    assert "hydrated as T-046" in report["hydration_recommendation"]
    assert report["blocking_reasons"] == [
        "candidate.status is hydrated; no hydration action remains",
    ]
    assert report["ready_to_hydrate"] is False
    assert report["scaffold_command"] is None


def test_t046_spec_preserves_task_capsule_derivation_plan_only_boundary() -> None:
    spec = _load_yaml(SPECS_DIR / "T-046.yaml")
    contract = spec["derived_capsule_contract"]
    freshness = spec["freshness_narrowing"]
    refusal_matrix = spec["refusal_matrix"]

    assert contract["source_question_ref"] == (
        ".azoth/initiative-banks/INI-EVI-002.yaml#rq-evi-002-010"
    )
    assert contract["repo_local_capsule_path"] == ".azoth/research/*.json"
    assert contract["sufficiency_evaluator"] == "scripts/research_sufficiency.py"
    assert contract["required_capsule_fields"] == [
        "schema_version",
        "source_session_id",
        "goal",
        "captured_at",
        "volatility",
        "limitations",
        "questions",
    ]
    assert contract["required_question_fields"] == [
        "question_id",
        "question",
        "status",
        "answered_at",
        "fresh_until",
    ]
    assert contract["initiative_provenance_fields"] == [
        "source_initiative_ref",
        "source_bank_ref",
        "candidate_slice_ref",
        "source_evidence_refs",
        "freshness_window",
        "excluded_stale_evidence",
        "decision_context",
    ]
    assert contract["bypass_policy"] == (
        "forbidden: initiative banks alone are not task-level sufficiency evidence"
    )
    assert contract["output_boundary"] == {
        "this_scope": "plan_only_definition",
        "allowed_output": "roadmap spec contract and test coverage only",
        "forbidden_output": "standalone .azoth/research/*.json capsule emission",
        "future_scope_required": "explicit helper implementation approval",
    }

    assert freshness["per_question_rule"] == (
        "derive fresh_until from the most restrictive relevant source evidence window"
    )
    assert freshness["required_trace_fields"] == [
        "source_evidence_refs",
        "freshness_window",
        "excluded_stale_evidence",
    ]
    assert freshness["stale_or_conflicting_source_policy"] == [
        "exclude from source_evidence_refs and record in excluded_stale_evidence",
        "or force refresh before any derived capsule becomes delivery evidence",
    ]

    assert refusal_matrix == {
        "complete": "refuse: no repeat derivation or hydration action remains",
        "hydrated": "refuse: task already exists; define delivery boundary only",
        "rejected": "refuse: candidate is not eligible evidence",
        "stale": "refuse: refresh source evidence before derivation",
        "conflicting": "refuse: resolve or carry conflict through research_sufficiency.py",
        "missing": "refuse: required candidate or evidence fields are absent",
        "protected": "refuse: protected/kernel/governance outputs require human gate",
        "unapproved": "refuse: explicit approval is required before derivation output",
        "insufficient": "refuse: research_sufficiency.py must report sufficient",
    }


def test_derived_task_capsule_report_builds_sufficient_preview_for_temp_candidate(
    tmp_path: Path,
) -> None:
    bank_path = _write_ready_derived_capsule_candidate(tmp_path)

    report = build_derived_task_capsule_report(
        bank_path,
        repo_root=tmp_path,
        candidate_id="slice-evi-002-f",
        session_id="session-test",
        timestamp="2026-05-01T00:00:00Z",
    )

    assert report["report_type"] == "derived_task_capsule_preview"
    assert report["ready_to_emit"] is True
    assert report["refusal_reasons"] == []
    assert report["sufficiency"]["outcome"] == "research_sufficient"
    preview = report["preview_capsule"]
    assert preview["source_session_id"] == "session-test"
    assert preview["source_initiative_ref"] == "INI-TEST"
    assert preview["source_bank_ref"] == ".azoth/initiative-banks/INI-TEST.yaml"
    assert preview["candidate_slice_ref"] == "slice-evi-002-f"
    assert preview["source_evidence_refs"] == [
        ".azoth/research/ini-evi-002-research-bank.yaml#pack-evi-002-c-policy-selection-001"
    ]
    assert preview["freshness_window"] == {
        "fresh_until": "2099-01-01T00:00:00Z",
        "source_question_id": "rq-evi-002-010",
    }
    assert preview["excluded_stale_evidence"] == []
    assert preview["decision_context"]["approval_scope"] == "hydration_specific_slice_evi_002_f"
    question_ids = {question["question_id"] for question in preview["questions"]}
    assert "phase-1-reuse" in question_ids
    assert "phase-1-slice-t-999-temp-derived-task-capsule" in question_ids


def test_derived_task_capsule_report_refuses_live_hydrated_candidate() -> None:
    report = build_derived_task_capsule_report(
        INITIATIVE_BANK_PATH,
        candidate_id="slice-evi-002-f",
        session_id="session-test",
        timestamp="2026-05-01T00:00:00Z",
    )

    assert report["ready_to_emit"] is False
    assert "refuse: task already exists; define delivery boundary only" in report[
        "refusal_reasons"
    ]
    assert report["preview_capsule"]["candidate_slice_ref"] == "slice-evi-002-f"


@pytest.mark.parametrize(
    ("fixture_updates", "expected_reason"),
    [
        ({"source_fresh_until": "2026-04-30T00:00:00Z"}, "refuse: refresh source evidence before derivation"),
        ({"source_status": "conflicting"}, "refuse: resolve or carry conflict through research_sufficiency.py"),
        ({"source_fresh_until": None}, "refuse: required candidate or evidence fields are absent"),
        ({"human_decision": "pending"}, "refuse: explicit approval is required before derivation output"),
        ({"candidate_status": "parked"}, "refuse: candidate status must be candidate"),
        ({"target_layer": "governance"}, "refuse: protected/kernel/governance outputs require human gate"),
    ],
)
def test_derived_task_capsule_report_refuses_stale_conflicting_missing_unapproved_and_protected_inputs(
    tmp_path: Path,
    fixture_updates: dict,
    expected_reason: str,
) -> None:
    bank_path = _write_ready_derived_capsule_candidate(tmp_path, **fixture_updates)

    report = build_derived_task_capsule_report(
        bank_path,
        repo_root=tmp_path,
        candidate_id="slice-evi-002-f",
        session_id="session-test",
        timestamp="2026-05-01T00:00:00Z",
    )

    assert report["ready_to_emit"] is False
    assert expected_reason in report["refusal_reasons"]


def test_validator_cli_prints_derived_task_capsule_report_without_research_output(
    tmp_path: Path,
) -> None:
    _write_ready_derived_capsule_candidate(tmp_path)
    research_dir = tmp_path / ".azoth" / "research"
    before = sorted(research_dir.glob("*.json")) if research_dir.exists() else []

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "planning_bank_validate.py"),
            "--derive-task-capsule",
            ".azoth/initiative-banks/INI-TEST.yaml",
            "--candidate-id",
            "slice-evi-002-f",
            "--session-id",
            "session-test",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    output = yaml.safe_load(result.stdout)
    assert set(output) == {"derived_task_capsule_reports"}
    report = output["derived_task_capsule_reports"][0]
    assert report["ready_to_emit"] is True
    assert report["preview_capsule"]["source_bank_ref"] == ".azoth/initiative-banks/INI-TEST.yaml"
    after = sorted(research_dir.glob("*.json")) if research_dir.exists() else []
    assert after == before == []


def test_terminal_initiative_readiness_validates_without_selected_candidate(
    tmp_path: Path,
) -> None:
    bank_path, bank = _write_temp_initiative_bank(tmp_path)
    bank["status"] = "complete"
    bank["readiness"].update(
        {
            "readiness_status": "complete",
            "candidate_first_slice": "",
            "next_candidate_ref": "",
            "next_readiness_gate": "none_feature_complete",
            "approval_scope": "feature_closure_no_hydration",
            "hydration_recommendation": "Feature is complete; do not repeat hydration.",
        }
    )
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    validate_initiative_bank(bank_path, repo_root=tmp_path)
    report = build_initiative_readiness_report(bank_path, repo_root=tmp_path)

    assert report["readiness_status"] == "complete"
    assert report["candidate_id"] == "missing"
    assert report["ready_to_hydrate"] is False
    assert report["blocking_reasons"] == [
        "readiness.readiness_status is complete; no hydration action remains",
        "readiness.readiness_status must be ready_to_hydrate",
    ]


def test_readiness_report_emits_plan_only_handoff_for_approved_temp_candidate(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["approval_basis"] = "Temp human approval for plan-only handoff."
    readiness.pop("approval_scope", None)
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
        "approval_scope": None,
        "approval_basis": "Temp human approval for plan-only handoff.",
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


def test_hydrate_approved_candidate_delegates_to_roadmap_scaffold_and_records_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["approval_scope"] = "hydration_specific_slice_evi_002_c"
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate["status"] = "candidate"
    candidate["proposed_task_id"] = "TBD-INI-TEST-001"
    candidate["open_questions"] = []
    candidate["hydration_plan"]["proposed_title"] = "Temp approved planning-bank slice"
    candidate["hydration_plan"]["scaffold_command"] = (
        'python3 scripts/roadmap_scaffold.py --title "Temp approved planning-bank slice" '
        "--initiative-ref INI-TEST --target-layer infrastructure --delivery-pipeline standard"
    )
    sentinel_history = {
        "hydrated_at": "2026-01-01T00:00:00Z",
        "session_id": "sentinel-session",
        "candidate_slice_ref": "sentinel-slice",
        "task_ref": "T-000",
        "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-000.yaml",
        "result": "Existing sentinel row must remain at index 0.",
    }
    bank["hydration_history"] = [sentinel_history]
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")
    _write_hydration_scope_gate(repo)

    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        assert kwargs["cwd"] == repo
        assert kwargs["capture_output"] is True
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=(
                "T-999\n"
                f"{repo}/.azoth/backlog.yaml\n"
                f"{repo}/.azoth/roadmap.yaml\n"
                f"{repo}/.azoth/roadmap-specs/v0.2.0/T-999.yaml\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(planning_bank_validate.subprocess, "run", fake_run)

    result = hydrate_approved_initiative_candidate(
        bank_path,
        repo_root=repo,
        candidate_id="slice-evi-002-c",
        session_id="session-test",
        timestamp="2026-04-26T13:31:45Z",
    )

    assert result["task_ref"] == "T-999"
    assert calls[0][:2] == [sys.executable, "scripts/roadmap_scaffold.py"]
    loaded = _load_yaml(bank_path)
    hydrated = next(
        item for item in loaded["candidate_slices"] if item["candidate_id"] == "slice-evi-002-c"
    )
    assert hydrated["status"] == "hydrated"
    assert hydrated["proposed_task_id"] == "T-999"
    assert hydrated["hydration_plan"]["mode"] == "executed"
    assert hydrated["hydration_plan"]["hydrated_spec_ref"].endswith("T-999.yaml")
    assert loaded["hydration_history"][0] == sentinel_history
    appended_history = loaded["hydration_history"][-1]
    assert appended_history["session_id"] == "session-test"
    assert appended_history["task_ref"] == "T-999"
    assert appended_history["append_policy_ref"] == (
        "planning_bank_closeout_history_merge_policy_v1"
    )
    assert appended_history["append_mode"] == "explicit_hydration_append"
    assert appended_history["merge_key"] == ("slice-evi-002-c:T-999:2026-04-26T13:31:45Z")
    assert loaded["readiness"]["hydration_recommendation"].startswith(
        "slice-evi-002-c has been hydrated as T-999"
    )


def test_hydrate_approved_candidate_refuses_without_pipeline_scope(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["approval_scope"] = "hydration_specific_slice_evi_002_c"
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate["status"] = "candidate"
    candidate["proposed_task_id"] = "TBD-INI-TEST-001"
    candidate["open_questions"] = []
    candidate["hydration_plan"]["proposed_title"] = "Temp approved planning-bank slice"
    candidate["hydration_plan"]["scaffold_command"] = (
        'python3 scripts/roadmap_scaffold.py --title "Temp approved planning-bank slice" '
        "--initiative-ref INI-TEST --target-layer infrastructure --delivery-pipeline standard"
    )
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="scope-gate.json"):
        hydrate_approved_initiative_candidate(
            bank_path,
            repo_root=repo,
            candidate_id="slice-evi-002-c",
            session_id="session-test",
        )


@pytest.mark.parametrize(
    "forbidden_output",
    ["roadmap_hydration", "backlog_mutation", "roadmap_spec_mutation"],
)
def test_hydrate_approved_candidate_refuses_scope_that_forbids_hydration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forbidden_output: str,
) -> None:
    repo = tmp_path
    bank_path = _write_ready_hydration_candidate(repo)
    _write_hydration_scope_gate(repo)
    gate_path = repo / ".azoth" / "scope-gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["forbidden_outputs"] = [forbidden_output]
    gate_path.write_text(json.dumps(gate), encoding="utf-8")

    def fail_run(*args, **kwargs):  # pragma: no cover - assertion helper
        raise AssertionError("roadmap_scaffold.py must not run when hydration is forbidden")

    monkeypatch.setattr(planning_bank_validate.subprocess, "run", fail_run)

    with pytest.raises(PlanningBankValidationError, match="forbids hydration"):
        hydrate_approved_initiative_candidate(
            bank_path,
            repo_root=repo,
            candidate_id="slice-evi-002-c",
            session_id="session-test",
        )


@pytest.mark.parametrize(
    ("gate_updates", "remove_keys", "error_match"),
    [
        ({"approved": False}, (), "approved == true"),
        ({"closed_at": "2098-01-01T00:00:00Z"}, (), "open scope gate"),
        ({"expires_at": "2000-01-01T00:00:00Z"}, (), "unexpired scope gate"),
        ({"session_id": "other-session"}, (), "session_id must match"),
        ({}, ("pipeline_command",), "approved pipeline_command"),
        ({}, ("approval_scope",), "approval_scope must be present"),
        ({"approval_scope": "hydration_specific_other"}, (), "approval_scope must match"),
        ({}, ("source_initiative_ref",), "source_initiative_ref must be present"),
        ({"source_initiative_ref": "INI-OTHER"}, (), "source_initiative_ref must match"),
        ({}, ("source_artifacts",), "source_artifacts must include"),
        (
            {"source_artifacts": [".azoth/initiative-banks/INI-OTHER.yaml"]},
            (),
            "source_artifacts must include",
        ),
    ],
)
def test_hydrate_approved_candidate_refuses_malformed_pipeline_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gate_updates: dict,
    remove_keys: tuple[str, ...],
    error_match: str,
) -> None:
    repo = tmp_path
    bank_path = _write_ready_hydration_candidate(repo)
    gate_path = _write_hydration_scope_gate(repo)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    for key in remove_keys:
        gate.pop(key, None)
    gate.update(gate_updates)
    gate_path.write_text(json.dumps(gate), encoding="utf-8")

    def fail_run(*args, **kwargs):  # pragma: no cover - assertion helper
        raise AssertionError("roadmap_scaffold.py must not run without authority")

    monkeypatch.setattr(planning_bank_validate.subprocess, "run", fail_run)

    with pytest.raises(PlanningBankValidationError, match=error_match):
        hydrate_approved_initiative_candidate(
            bank_path,
            repo_root=repo,
            candidate_id="slice-evi-002-c",
            session_id="session-test",
        )


@pytest.mark.parametrize(
    ("approval_scope", "error_match"),
    [
        ("", "hydration-specific approval_scope"),
        ("planning_seed_only_no_hydration", "planning_seed_only_no_hydration"),
        ("general_pipeline_approval", "approval_scope must be hydration-specific"),
    ],
)
def test_hydrate_approved_candidate_requires_hydration_specific_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approval_scope: str,
    error_match: str,
) -> None:
    repo = tmp_path
    bank_path = _write_ready_hydration_candidate(repo, approval_scope=approval_scope)
    _write_hydration_scope_gate(repo, approval_scope=approval_scope)

    def fail_run(*args, **kwargs):  # pragma: no cover - assertion helper
        raise AssertionError("roadmap_scaffold.py must not run without authority")

    monkeypatch.setattr(planning_bank_validate.subprocess, "run", fail_run)

    with pytest.raises(PlanningBankValidationError, match=error_match):
        hydrate_approved_initiative_candidate(
            bank_path,
            repo_root=repo,
            candidate_id="slice-evi-002-c",
            session_id="session-test",
        )


def test_hydrate_approved_candidate_requires_session_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path
    bank_path = _write_ready_hydration_candidate(repo)
    _write_hydration_scope_gate(repo)

    def fail_run(*args, **kwargs):  # pragma: no cover - assertion helper
        raise AssertionError("roadmap_scaffold.py must not run without authority")

    monkeypatch.setattr(planning_bank_validate.subprocess, "run", fail_run)

    with pytest.raises(PlanningBankValidationError, match="--session-id"):
        hydrate_approved_initiative_candidate(
            bank_path,
            repo_root=repo,
            candidate_id="slice-evi-002-c",
            session_id="",
        )


def test_hydrate_approved_candidate_refuses_non_scaffold_command(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["approval_scope"] = "hydration_specific_slice_evi_002_c"
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate["status"] = "candidate"
    candidate["open_questions"] = []
    candidate["hydration_plan"]["proposed_title"] = "Temp approved planning-bank slice"
    candidate["hydration_plan"]["scaffold_command"] = "python3 scripts/not_scaffold.py"
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    with pytest.raises(PlanningBankValidationError, match="roadmap_scaffold.py"):
        hydrate_approved_initiative_candidate(
            bank_path,
            repo_root=repo,
            candidate_id="slice-evi-002-c",
        )


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


def test_readiness_report_fails_closed_when_hydration_approval_basis_is_missing(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    readiness.pop("approval_basis", None)
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate["status"] = "candidate"
    candidate["open_questions"] = []
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    report = build_initiative_readiness_report(bank_path, repo_root=repo)

    assert report["approval_basis"] is None
    assert report["ready_to_hydrate"] is False
    assert report["scaffold_command"] is None
    assert "readiness.approval_basis must be present before hydration" in report["blocking_reasons"]


def test_readiness_report_fails_closed_for_seed_only_approval_scope(tmp_path: Path) -> None:
    repo = tmp_path
    bank_path, bank = _write_temp_initiative_bank(repo)
    readiness = bank["readiness"]
    readiness["readiness_status"] = "ready_to_hydrate"
    readiness["human_decision"] = "approved"
    readiness["freshness_status"] = "fresh"
    readiness["candidate_first_slice"] = "slice-evi-002-c"
    readiness["approval_scope"] = "planning_seed_only_no_hydration"
    candidate = next(
        candidate
        for candidate in bank["candidate_slices"]
        if candidate["candidate_id"] == "slice-evi-002-c"
    )
    candidate["status"] = "candidate"
    candidate["open_questions"] = []
    bank_path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")

    report = build_initiative_readiness_report(bank_path, repo_root=repo)

    assert report["approval_scope"] == "planning_seed_only_no_hydration"
    assert report["ready_to_hydrate"] is False
    assert report["scaffold_command"] is None
    assert (
        "readiness.approval_scope planning_seed_only_no_hydration does not authorize hydration"
        in report["blocking_reasons"]
    )


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

    assert report["candidate_first_slice"] == "slice-evi-002-f"
    assert report["candidate_id"] == "slice-evi-002-a"
    assert report["candidate_task_ref"] == "T-018"
    assert report["candidate_status"] == "complete"
    assert report["ready_to_hydrate"] is False
    assert "candidate.status is complete; no hydration action remains" in report["blocking_reasons"]


def test_do_closeout_does_not_target_planning_bank_directories() -> None:
    closeout_source = (ROOT / "scripts" / "do_closeout.py").read_text(encoding="utf-8")

    assert ".azoth/design-banks" not in closeout_source
    assert ".azoth/initiative-banks" not in closeout_source
    assert "hydration_history" not in closeout_source


def test_ini_evi_002_has_hydrated_closeout_history_policy_follow_on() -> None:
    bank = _load_yaml(INITIATIVE_BANK_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)
    backlog = _load_yaml(BACKLOG_PATH)
    blocked_candidate_ids = {
        str(candidate["proposed_task_id"])
        for candidate in bank["candidate_slices"]
        if candidate["status"] == "candidate"
    }
    completed_candidates = [
        candidate for candidate in bank["candidate_slices"] if candidate["status"] == "complete"
    ]
    hydrated_candidates = [
        candidate for candidate in bank["candidate_slices"] if candidate["status"] == "hydrated"
    ]

    initiative = next(item for item in roadmap["initiatives"] if item["id"] == "INI-EVI-002")
    assert initiative["phase"] is None
    assert initiative["task_ref"] is None
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
            "role": "historical",
        },
        {
            "task_ref": "T-043",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-043.yaml",
            "phase": "v0.2.0-p4",
            "status": "complete",
            "role": "historical",
        },
        {
            "task_ref": "T-046",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-046.yaml",
            "phase": "v0.2.0-p4",
            "status": "complete",
            "role": "historical",
        },
    ]
    assert initiative["initiative_bank_ref"] == ".azoth/initiative-banks/INI-EVI-002.yaml"
    assert initiative["design_bank_refs"] == [".azoth/design-banks/planning-banks-layer.yaml"]
    assert initiative["research_refs"] == [".azoth/research/ini-evi-002-research-bank.yaml"]
    assert initiative["candidate_slice_ref"] == "slice-evi-002-f"
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
        "T-022",
    ]
    assert seeded_candidate["proposed_task_id"] == "T-021"
    assert seeded_candidate["status"] == "complete"
    assert [candidate["proposed_task_id"] for candidate in hydrated_candidates] == [
        "T-043",
        "T-046",
    ]
    assert initiative["discovery_status"] == "task_capsule_derivation_hydrated"
    assert "T-046 is hydrated" in initiative["next_discovery_action"]
    assert "/next and /auto" in initiative["next_discovery_action"]

    roadmap_task_ids = {
        str(task.get("id"))
        for version in roadmap.get("versions") or []
        for block in ("tasks", "completed_tasks", "deferred_tasks")
        for task in (version.get(block) or [])
        if isinstance(task, dict)
    }
    backlog_ids = {str(item.get("id")) for item in backlog.get("items") or []}
    spec_ids = {path.stem for path in SPECS_DIR.glob("*.yaml")}

    assert blocked_candidate_ids == set()
    assert "T-043" in roadmap_task_ids
    assert "T-043" in backlog_ids
    assert "T-043" in spec_ids
    assert "T-046" in roadmap_task_ids
    assert "T-046" in backlog_ids
    assert "T-046" in spec_ids
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
    initiatives = {item["initiative_id"]: item for item in report["initiatives"]}

    assert initiatives["INI-EVI-002"]["coverage_required"] is True
    assert initiatives["INI-EVI-002"]["covered"] is True
    assert (
        initiatives["INI-EVI-002"]["initiative_bank_ref"]
        == ".azoth/initiative-banks/INI-EVI-002.yaml"
    )
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


def test_validator_cli_prints_intake_contract_report(tmp_path: Path) -> None:
    intake_path = tmp_path / "intake.yaml"
    intake_path.write_text(
        yaml.safe_dump(
            {
                "initiative_id": "INI-RAW-001",
                "operator_goal": "Create a safe raw initiative intake path.",
                "why_now": "Autonomous-auto needs seed-only discovery before hydration.",
                "known_constraints": ["Do not create delivery artifacts."],
                "protected_boundaries": ["No kernel or governance changes."],
                "success_signals": ["A raw initiative validates as planning discovery."],
                "initial_uncertainty": ["Which later slice should become hydration-ready?"],
                "approval_scope": "planning_seed_only_no_hydration",
                "approval_basis": "Operator approved seed-only intake.",
                "allowed_outputs": ["initiative_bank_seed", "validation_report"],
                "forbidden_outputs": sorted(
                    {
                        "scope_gate",
                        "run_ledger_entry",
                        "backlog_row",
                        "roadmap_task",
                        "task_spec",
                        "hydration_write",
                        "implementation_work",
                        "hydrate_task",
                        "ship_task",
                        "protected_expansion",
                        "kernel_change",
                        "governance_change",
                        "destructive_action",
                        "network_expansion",
                        "credential_access",
                        "cross_branch_write",
                    }
                ),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "planning_bank_validate.py"),
            "--intake-contract",
            str(intake_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    output = yaml.safe_load(result.stdout)
    assert set(output) == {"initiative_intake_reports"}
    report = output["initiative_intake_reports"][0]
    assert report["report_type"] == "initiative_intake_validation"
    assert report["classification"] == "planning_discovery_seed"
    assert report["delivery_authorized"] is False
    assert "hydrate_task" in report["blocked_actions"]
    assert "ship_task" in report["blocked_actions"]


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

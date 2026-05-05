from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pm_orchestrator_mobility import build_mobility_capsule  # noqa: E402


def _base_bank(initiative_id: str, candidate_id: str) -> dict:
    return {
        "schema_version": 1,
        "bank_type": "initiative",
        "initiative_id": initiative_id,
        "title": "Temp initiative",
        "status": "active_refinement",
        "contacts": [],
        "source_proposal_refs": [],
        "research_questions": [],
        "research_refs": [],
        "local_findings": [],
        "external_findings": [],
        "assumptions": [],
        "contradictions": [],
        "challenge_log": [],
        "candidate_slices": [
            {
                "candidate_id": candidate_id,
                "proposed_task_id": "TBD-TEMP-001",
                "title": "Temp candidate",
                "initiative_ref": initiative_id,
                "status": "candidate",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
                "summary": "Temp candidate summary.",
                "acceptance_criteria": ["Acceptance is stable."],
                "research_evidence_refs": [],
                "known_non_goals": ["No canonical writes in plan-only mode."],
                "open_questions": [],
                "recommended_phase": "active_version",
                "hydration_plan": {
                    "proposed_title": "Temp candidate",
                    "scaffold_command": (
                        'python3 scripts/roadmap_scaffold.py --title "Temp candidate" '
                        f"--initiative-ref {initiative_id} --target-layer infrastructure "
                        "--delivery-pipeline standard"
                    ),
                },
            }
        ],
        "readiness": {
            "readiness_status": "ready_to_hydrate",
            "human_decision": "approved",
            "freshness_status": "fresh",
            "approval_basis": "Temp approval for plan-only gate packet.",
            "approval_scope": f"hydration_specific_{candidate_id.replace('-', '_')}",
            "candidate_first_slice": candidate_id,
            "hydration_recommendation": "Ready for plan-only gate packet.",
        },
        "hydration_history": [],
    }


def _write_bank(repo: Path, bank: dict) -> Path:
    path = repo / ".azoth" / "initiative-banks" / f"{bank['initiative_id']}.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(bank, sort_keys=False), encoding="utf-8")
    return path


def test_ready_candidate_emits_plan_only_gate_packet(tmp_path: Path) -> None:
    bank_path = _write_bank(tmp_path, _base_bank("INI-TEMP-001", "slice-temp-001-a"))

    capsule = build_mobility_capsule(
        [bank_path],
        repo_root=tmp_path,
        generated_at="2026-05-04T00:00:00Z",
    )

    assert capsule["human_gate_required"] is True
    assert capsule["selected_route"] == "stop_for_human_gate"
    assert capsule["selected_candidate"]["candidate_id"] == "slice-temp-001-a"
    assert capsule["scaffold_command_after_gate"].startswith(
        "python3 scripts/roadmap_scaffold.py"
    )
    assert ".azoth/roadmap.yaml" in capsule["allowed_write_set_after_gate"]
    assert "Approve hydrate_task for slice-temp-001-a" in capsule["required_human_approval"]
    assert capsule["canonical_boundary"]["status"] == "unchanged_by_this_helper"


def test_hydrated_candidate_refuses_repeat_hydration(tmp_path: Path) -> None:
    bank = _base_bank("INI-TEMP-002", "slice-temp-002-a")
    bank["candidate_slices"][0]["status"] = "hydrated"
    bank["candidate_slices"][0]["proposed_task_id"] = "T-999"
    bank_path = _write_bank(tmp_path, bank)

    capsule = build_mobility_capsule([bank_path], repo_root=tmp_path)

    assert capsule["human_gate_required"] is False
    assert capsule["selected_candidate"] is None
    assert capsule["selected_route"] == "stop"
    evaluation = capsule["candidate_evaluations"][0]
    assert evaluation["route_state"] == "hydrated_not_delivered"
    assert evaluation["selected_route"] == "stop_or_delivery_gate"
    assert "candidate.status is hydrated" in "; ".join(evaluation["refusal_reasons"])
    assert capsule["allowed_write_set_after_gate"] == []


def test_hydrated_candidate_with_completed_backlog_is_fulfilled(tmp_path: Path) -> None:
    bank = _base_bank("INI-TEMP-004", "slice-temp-004-a")
    bank["candidate_slices"][0]["status"] = "hydrated"
    bank["candidate_slices"][0]["proposed_task_id"] = "T-777"
    bank_path = _write_bank(tmp_path, bank)
    backlog_path = tmp_path / ".azoth" / "backlog.yaml"
    backlog_path.write_text(
        "schema_version: 1\nitems:\n  - id: T-777\n    status: complete\n",
        encoding="utf-8",
    )

    capsule = build_mobility_capsule([bank_path], repo_root=tmp_path)

    evaluation = capsule["candidate_evaluations"][0]
    assert evaluation["route_state"] == "fulfilled_or_stale"
    assert evaluation["selected_route"] == "stop_or_research_fresh_seed"
    assert capsule["human_gate_required"] is False


def test_complete_candidate_refuses_fulfilled_lane(tmp_path: Path) -> None:
    bank = _base_bank("INI-TEMP-003", "slice-temp-003-a")
    bank["readiness"]["readiness_status"] = "complete"
    bank["candidate_slices"][0]["status"] = "complete"
    bank["candidate_slices"][0]["proposed_task_id"] = "T-998"
    bank_path = _write_bank(tmp_path, bank)

    capsule = build_mobility_capsule([bank_path], repo_root=tmp_path)

    assert capsule["human_gate_required"] is False
    evaluation = capsule["candidate_evaluations"][0]
    assert evaluation["route_state"] == "fulfilled_or_stale"
    assert evaluation["selected_route"] == "stop_or_research_fresh_seed"
    assert "readiness.readiness_status is complete" in "; ".join(
        evaluation["refusal_reasons"]
    )

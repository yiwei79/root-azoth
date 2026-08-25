from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import autonomous_loop  # noqa: E402

D32_REQUIRED_FIELDS = {
    "id",
    "source",
    "source_type",
    "timestamp",
    "category",
    "severity",
    "target",
    "summary",
    "evidence",
    "recommended_action",
    "auto_applicable",
    "requires_human_gate",
}


def _future_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _snapshot_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


def _state(root: Path, **overrides: object) -> Path:
    data: dict = {
        "schema_version": 1,
        "loop_id": "loop-test",
        "status": "active",
        "branch": "codex/autonomous-roadmap-self-development",
        "autonomy_budget": {
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 3,
            "replay_threshold": 2,
            "allowed_actions": [
                "ship_task",
                "hydrate_task",
                "research_initiative",
                "refine_proposal",
                "capture_self_improvement",
            ],
            "stop_conditions": [
                "active_scope_present",
                "active_session_gate_conflict",
                "budget_exhausted",
                "protected_gate_required",
                "async_stop_packet",
                "no_safe_candidate",
            ],
        },
        "iteration": 0,
        "queue": [],
        "self_capture_queue": [],
        "alignment_packets": [],
        "alignment_dispositions": [],
        "history": [],
    }
    data.update(overrides)
    path = root / ".azoth/autonomous-loop-state.local.yaml"
    _write_yaml(path, data)
    return path


def _write_active_session_gate(root: Path, session_id: str = "active-session") -> None:
    _write_json(
        root / ".azoth/session-gate.json",
        {
            "session_id": session_id,
            "goal": "Existing active session",
            "session_mode": "delivery",
            "opened_at": "2026-04-25T12:00:00+00:00",
            "updated_at": "2026-04-25T12:00:00+00:00",
            "status": "active",
            "approved_by": "human",
        },
    )


def _decision_path(root: Path, decision: dict) -> Path:
    path = root / ".azoth/next-decision.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(decision), encoding="utf-8")
    return path


def test_missing_loop_state_stops(tmp_path: Path) -> None:
    decision = autonomous_loop.decide_next(
        tmp_path,
        tmp_path / ".azoth/autonomous-loop-state.local.yaml",
    )
    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "missing_loop_state"


def test_init_loop_writes_active_state_with_approval_packet(tmp_path: Path) -> None:
    state_path = tmp_path / ".azoth/autonomous-loop-state.local.yaml"

    result = autonomous_loop.init_loop(
        tmp_path,
        state_path,
        approval_basis="User approved one branch-local autonomous-auto iteration.",
        objective="Vision-bounded autonomous-auto iteration",
        loop_id="loop-init-test",
        branch="codex/test",
        max_iterations=3,
        replay_threshold=1,
        allowed_actions=["ship_task", "capture_self_improvement"],
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert result["initialized"] is True
    assert state["status"] == "active"
    assert state["objective"] == "Vision-bounded autonomous-auto iteration"
    assert state["autonomy_budget"]["approval_basis"] == (
        "User approved one branch-local autonomous-auto iteration."
    )
    assert state["autonomy_budget"]["max_iterations"] == 3
    assert state["autonomy_budget"]["replay_threshold"] == 1
    assert state["alignment_packets"][0]["packet_type"] == "approval_basis"
    assert state["alignment_packets"][0]["disposition"] == "applied"
    assert state["vision"]["target_band"] == "green"
    assert state["vision"]["current_band"] == "unevaluated"
    assert state["vision"]["declaration"]["status"] == "approved"
    assert state["vision"]["declaration"]["summary"] == "Vision-bounded autonomous-auto iteration"
    assert state["vision"]["declaration"]["allowed_actions"] == [
        "ship_task",
        "capture_self_improvement",
    ]
    assert read["loop_state"] == "active"
    assert read["next_likely_move"] == "ship_task (T-321)"
    assert read["pending_alignment_packets"] == 0
    assert read["vision_target"] == "green"
    assert read["continuation_required"] is True


def test_init_loop_refuses_existing_state_without_replace(tmp_path: Path) -> None:
    state_path = _state(tmp_path)

    with pytest.raises(SystemExit, match="already exists"):
        autonomous_loop.init_loop(
            tmp_path,
            state_path,
            approval_basis="User approved one branch-local autonomous-auto iteration.",
            objective="Vision-bounded autonomous-auto iteration",
            loop_id="loop-init-test",
            branch="codex/test",
            max_iterations=1,
            replay_threshold=1,
            allowed_actions=["ship_task"],
        )


def test_init_loop_persists_locked_vision_declaration(tmp_path: Path) -> None:
    state_path = tmp_path / ".azoth/autonomous-loop-state.local.yaml"

    autonomous_loop.init_loop(
        tmp_path,
        state_path,
        approval_basis="User approved campaign vision declaration.",
        objective="Autonomous Campaign 2",
        loop_id="loop-vision-test",
        branch="codex/test",
        max_iterations=4,
        replay_threshold=1,
        allowed_actions=["research_initiative", "hydrate_task", "ship_task"],
        vision_declaration={
            "summary": "Improve Azoth planning-bank lifecycle autonomy.",
            "selected_seed": "INI-EVI-002",
            "selected_seed_type": "initiative",
            "scope_notes": "Research, hydrate, and ship one bounded planning-bank slice.",
        },
    )

    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    declaration = state["vision"]["declaration"]

    assert declaration["status"] == "approved"
    assert declaration["summary"] == "Improve Azoth planning-bank lifecycle autonomy."
    assert declaration["selected_seed"] == "INI-EVI-002"
    assert declaration["selected_seed_type"] == "initiative"
    assert declaration["scope_notes"] == (
        "Research, hydrate, and ship one bounded planning-bank slice."
    )
    assert declaration["allowed_actions"] == [
        "research_initiative",
        "hydrate_task",
        "ship_task",
    ]
    assert declaration["approval_basis"] == "User approved campaign vision declaration."
    assert declaration["locked_at"]


def test_init_loop_rejects_advisory_recommendation_as_approval(tmp_path: Path) -> None:
    state_path = tmp_path / ".azoth/autonomous-loop-state.local.yaml"

    with pytest.raises(SystemExit, match="advisory recommendation"):
        autonomous_loop.init_loop(
            tmp_path,
            state_path,
            approval_basis="Recommendation packet suggested INI-AUTO-001.",
            objective="Autonomous Campaign 2",
            loop_id="loop-advisory-test",
            branch="codex/test",
            max_iterations=3,
            replay_threshold=1,
            allowed_actions=["research_initiative"],
            vision_declaration={
                "selected_seed": "INI-AUTO-001",
                "selected_seed_type": "initiative",
                "fresh_operator_approval_required": True,
                "selected_route": "research_initiative",
                "route_state": "campaign_strategy_preflight",
            },
        )

    assert not state_path.exists()


def test_record_vision_score_green_marks_continuation_not_required(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "yellow",
            "realized": False,
        },
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )

    vision = autonomous_loop.record_vision_score(
        state_path,
        band="green",
        note="UX anchors are Green after bounded delivery.",
        scorecard={"continuation": "green"},
    )
    read = autonomous_loop.operator_read(tmp_path, state_path)
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))

    assert vision["current_band"] == "green"
    assert vision["realized"] is True
    assert state["status"] == "completed"
    assert state["completion_reason"] == "vision_realized"
    assert read["loop_state"] == "completed"
    assert read["vision_band"] == "green"
    assert read["next_likely_move"] == "complete: vision_realized"
    assert read["continuation_required"] is False
    assert read["continuation_reason"] == "vision_realized"
    assert read["completion_reason"] == "vision_realized"
    assert read["stop_reason"] is None
    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "vision_realized"
    assert decision["architect_judgment"]["residual_risk"] == (
        "Campaign reached its completion condition; open a fresh budget to continue."
    )
    packet = decision["next_campaign_recommendation"]
    assert packet["packet_type"] == "autonomous_auto_next_campaign_recommendation"
    assert packet["status"] == "advisory_only"
    assert packet["requires_fresh_approval"] is True
    assert packet["may_open_scope"] is False
    assert packet["fresh_budget_required"] is True
    assert packet["safe_to_continue_current_loop"] is False
    assert packet["hidden_continuation_allowed"] is False
    assert read["next_campaign_recommendation"]["packet_type"] == packet["packet_type"]
    assert read["next_campaign_recommendation"]["status"] == "advisory_only"
    assert read["next_campaign_recommendation"]["candidate_strategy"]["reason"] == (
        "no_non_protected_candidate"
    )


def test_existing_green_active_state_reads_as_completed_not_blocked(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        iteration=3,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["ship_task"],
        },
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "green",
            "realized": True,
        },
    )

    status = autonomous_loop.loop_status(tmp_path, state_path)
    read = autonomous_loop.operator_read(tmp_path, state_path)
    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert status["status"] == "completed"
    assert status["raw_status"] == "active"
    assert status["stop_reason"] is None
    assert status["completion_reason"] == "vision_realized"
    assert read["next_likely_move"] == "complete: vision_realized"
    assert read["residual_risk"] == (
        "Campaign reached its completion condition; open a fresh budget to continue."
    )
    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "vision_realized"
    assert decision["next_campaign_recommendation"]["status"] == "advisory_only"
    assert read["next_campaign_recommendation"]["fresh_budget_required"] is True


def test_completed_loop_read_ignores_unrelated_active_scope(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        iteration=3,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["ship_task"],
        },
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "green",
            "realized": True,
        },
    )
    _write_json(
        tmp_path / ".azoth/scope-gate.json",
        {
            "approved": True,
            "expires_at": _future_expiry(),
            "session_id": "unrelated-active-scope",
        },
    )

    status = autonomous_loop.loop_status(tmp_path, state_path)
    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert status["status"] == "completed"
    assert status["active_scope_id"] == "unrelated-active-scope"
    assert status["completion_reason"] == "vision_realized"
    assert status["stop_reason"] is None
    assert read["next_likely_move"] == "complete: vision_realized"


def test_closed_scope_gate_does_not_block_next_iteration(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "readback-repair",
                "title": "Readback repair",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    _write_json(
        tmp_path / ".azoth/scope-gate.json",
        {
            "approved": True,
            "expires_at": _future_expiry(),
            "session_id": "already-closed-scope",
            "closed_at": "2026-05-05T18:00:00Z",
        },
    )

    status = autonomous_loop.loop_status(tmp_path, state_path)
    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert status["active_scope_id"] == ""
    assert status["can_continue"] is True
    assert decision["action"] == "ship_task"
    assert decision["candidate_id"] == "readback-repair"


def test_completed_green_campaign_report_exposes_advisory_next_campaign_packet(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        iteration=3,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["ship_task"],
        },
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "green",
            "realized": True,
        },
    )

    report = autonomous_loop.campaign_report(tmp_path, state_path)
    packet = report["next_campaign_recommendation"]

    assert report["current_loop"]["status"] == "completed"
    assert report["observation"]["fresh_budget_required"] is True
    assert packet["packet_type"] == "autonomous_auto_next_campaign_recommendation"
    assert packet["current_loop_authority"] == "closed"
    assert packet["fresh_budget_required"] is True
    assert packet["safe_to_continue_current_loop"] is False
    assert packet["hidden_continuation_allowed"] is False
    assert packet["requires_fresh_approval"] is True
    assert packet["may_open_scope"] is False
    assert packet["hidden_continuation"] is False


def test_completed_green_recommendation_packet_ranks_candidates_without_mutation(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        iteration=3,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["ship_task"],
        },
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "green",
            "realized": True,
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        {
            "items": [
                {
                    "id": "AUTO-NEXT-001",
                    "title": "Improve autonomous continuation strategy",
                    "status": "pending",
                    "priority": 1,
                    "target_layer": "infrastructure",
                    "delivery_pipeline": "standard",
                }
            ]
        },
    )
    before = _snapshot_files(tmp_path)

    report = autonomous_loop.campaign_report(tmp_path, state_path)
    packet = report["next_campaign_recommendation"]

    assert _snapshot_files(tmp_path) == before
    assert packet["available"] is True
    assert packet["mode"] == "recommendation_only"
    assert packet["ranked_recommendations"][0]["candidate_id"] == "AUTO-NEXT-001"
    assert packet["ranked_recommendations"][0]["action"] == "ship_task"
    assert packet["draft_campaign_declaration"]["selected_seed"] == "AUTO-NEXT-001"
    assert packet["blocked_actions"] == [
        {
            "action": "open_next",
            "reason": "fresh approval required after vision_realized",
        },
        {
            "action": "continue_old_campaign",
            "reason": "completed campaign evidence is not continuation authority",
        },
    ]


def test_next_campaign_recommendation_includes_initiative_strategy_preflight(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        iteration=1,
        autonomy_budget={
            "approval_basis": "Previous loop completed green.",
            "max_iterations": 3,
            "allowed_actions": ["research_initiative"],
        },
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "green",
            "realized": True,
        },
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "complete"
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-h",
            "proposed_task_id": "T-AUTO-H",
            "title": "Autonomous campaign strategy budget repair",
            "initiative_ref": "INI-AUTO-001",
            "status": "candidate",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Repair pre-open strategy budget before another campaign opens.",
            "acceptance_criteria": [
                "Recommendation and lifecycle-route are reconciled before open-next."
            ],
            "research_evidence_refs": ["scripts/autonomous_loop.py"],
            "known_non_goals": ["Do not hydrate or ship from the strategy child."],
            "open_questions": ["Which preflight surface owns the refusal?"],
        }
    )
    doc["readiness"].update(
        {
            "readiness_status": "continue_research",
            "candidate_first_slice": "slice-auto-001-h",
            "next_candidate_ref": "slice-auto-001-h",
            "next_readiness_gate": "research_strategy_preflight_before_init_or_open_next",
            "hydration_recommendation": (
                "Slice-auto-001-h is research-only until strategy-preflight behavior is "
                "specified and tested."
            ),
            "approval_scope": "research_to_readiness_slice_auto_001_h",
            "approval_basis": (
                "Operator approved the Autonomous Campaign Strategy Budget Repair campaign "
                "for INI-AUTO-001 slice-auto-001-h."
            ),
        }
    )
    _write_yaml(initiative_path, doc)
    before = _snapshot_files(tmp_path)

    report = autonomous_loop.campaign_report(tmp_path, state_path)
    packet = report["next_campaign_recommendation"]
    top = packet["ranked_recommendations"][0]

    assert _snapshot_files(tmp_path) == before
    assert top["candidate_id"] == "INI-AUTO-001"
    assert top["route_preflight"]["selected_route"] == "research_initiative"
    assert top["route_preflight"]["route_state"] == "campaign_strategy_preflight"
    assert top["route_preflight"]["verdict"] == "can_initialize_research_campaign"
    assert top["route_preflight"]["approval_scope"] == "research_to_readiness_slice_auto_001_h"
    assert top["route_preflight"]["readiness_evidence"]["candidate_id"] == "slice-auto-001-h"
    assert top["route_preflight"]["source_artifacts"]["initiative_bank"].endswith(
        "INI-AUTO-001.yaml"
    )
    assert packet["draft_campaign_declaration"]["strategy_preflight_verdict"] == (
        "can_initialize_research_campaign"
    )
    assert packet["draft_campaign_declaration"]["selected_route"] == "research_initiative"
    assert packet["draft_campaign_declaration"]["lifecycle_route"]["route_state"] == (
        "campaign_strategy_preflight"
    )
    assert (
        packet["draft_campaign_declaration"]["lifecycle_route"]["readiness_evidence"][
            "candidate_id"
        ]
        == "slice-auto-001-h"
    )


def test_completed_green_stop_decision_includes_ranked_recommendations_without_mutation(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        iteration=3,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["ship_task"],
        },
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "green",
            "realized": True,
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        {
            "items": [
                {
                    "id": "AUTO-NEXT-002",
                    "title": "Recommend the next autonomous campaign",
                    "status": "pending",
                    "priority": 1,
                    "target_layer": "infrastructure",
                    "delivery_pipeline": "standard",
                }
            ]
        },
    )
    before = _snapshot_files(tmp_path)

    decision = autonomous_loop.decide_next(tmp_path, state_path)
    packet = decision["next_campaign_recommendation"]

    assert _snapshot_files(tmp_path) == before
    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "vision_realized"
    assert packet["packet_type"] == "autonomous_auto_next_campaign_recommendation"
    assert packet["requires_fresh_approval"] is True
    assert packet["may_open_scope"] is False
    assert packet["ranked_recommendations"][0]["candidate_id"] == "AUTO-NEXT-002"
    assert packet["draft_campaign_declaration"]["selected_seed"] == "AUTO-NEXT-002"


def test_completed_green_plain_operator_and_campaign_outputs_show_recommendation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state_path = _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        iteration=3,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["ship_task"],
        },
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "green",
            "realized": True,
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        {
            "items": [
                {
                    "id": "AUTO-NEXT-003",
                    "title": "Expose recommendation in plain output",
                    "status": "pending",
                    "priority": 1,
                    "target_layer": "infrastructure",
                    "delivery_pipeline": "standard",
                }
            ]
        },
    )

    assert (
        autonomous_loop.main(
            ["--root", str(tmp_path), "--state", str(state_path), "status", "--operator-read"]
        )
        == 0
    )
    operator_output = capsys.readouterr().out
    assert "Next campaign recommendation: advisory_only" in operator_output
    assert "fresh_approval=True" in operator_output
    assert "may_open_scope=False" in operator_output
    assert "top=ship_task:AUTO-NEXT-003" in operator_output

    assert (
        autonomous_loop.main(
            ["--root", str(tmp_path), "--state", str(state_path), "campaign-report"]
        )
        == 0
    )
    report_output = capsys.readouterr().out
    assert "Next campaign recommendation: advisory_only" in report_output
    assert "fresh_approval=True" in report_output
    assert "may_open_scope=False" in report_output
    assert "top=ship_task:AUTO-NEXT-003" in report_output


def test_active_scope_blocks_next_iteration(tmp_path: Path) -> None:
    state_path = _state(tmp_path)
    scope_path = tmp_path / ".azoth/scope-gate.json"
    scope_path.parent.mkdir(parents=True, exist_ok=True)
    scope_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "live-session",
            }
        ),
        encoding="utf-8",
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)
    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "active_scope_present"


def test_active_session_gate_conflict_blocks_next_iteration(tmp_path: Path) -> None:
    state_path = _state(tmp_path)
    _write_active_session_gate(tmp_path)

    decision = autonomous_loop.decide_next(tmp_path, state_path)
    status = autonomous_loop.loop_status(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "active_session_gate_conflict"
    assert status["can_continue"] is False
    assert status["active_session_conflict"] is True
    assert status["stop_reason"] == "active_session_gate_conflict"


def test_budget_exhaustion_stops(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        iteration=2,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 2,
            "allowed_actions": ["ship_task"],
        },
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "budget_exhausted"


def test_queued_candidate_wins_inside_budget(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "refine_proposal",
                "candidate_id": "proposal-a",
                "title": "Refine proposal A",
                "target_layer": "planning",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    assert decision["action"] == "refine_proposal"
    assert decision["candidate_id"] == "proposal-a"
    assert decision["pipeline_command"] == "autonomous-auto"
    assert decision["architect_judgment"]["decision"] == "refine_proposal"


def test_queued_proposal_hydration_stops_when_matching_task_is_complete(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "hydrate_task",
                "candidate_id": "proposal-run-ledger-atomic-stage-evidence",
                "title": "Run-ledger serialized stage evidence writes",
                "source": ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Run-ledger serialized stage evidence writes",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Run-ledger serialized stage evidence writes",
                    "route": "hydrate_task",
                    "placement": {
                        "initiative_ref": "INI-RST-003",
                        "source": "proposal-run-ledger-atomic-stage-evidence",
                        "target_layer": "infrastructure",
                        "delivery_pipeline": "standard",
                    },
                }
            },
        },
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap-specs/v0.2.0/T-028.yaml",
        {"id": "T-028", "title": "Run-ledger serialized stage evidence writes"},
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap.yaml",
        {
            "versions": [
                {
                    "id": "v0.2.0-p3",
                    "completed_tasks": [
                        {
                            "id": "T-028",
                            "title": "Run-ledger serialized stage evidence writes",
                            "completed_date": "2026-04-25",
                        }
                    ],
                }
            ]
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        [
            {
                "id": "T-028",
                "title": "Run-ledger serialized stage evidence writes",
                "source": "proposal-run-ledger-atomic-stage-evidence",
                "initiative_ref": "INI-RST-003",
                "status": "complete",
                "completed_date": "2026-04-25",
                "roadmap_ref": "T-028",
            }
        ],
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "proposal_hydration_already_completed"
    assert decision["candidate_id"] == "T-028"
    assert decision["route_decision"]["selected_route"] == "stop"
    assert decision["route_decision"]["existing_task_id"] == "T-028"


def test_queued_proposal_hydration_routes_existing_pending_task_to_ship(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "hydrate_task",
                "candidate_id": "proposal-run-ledger-atomic-stage-evidence",
                "proposed_task_id": "T-028",
                "title": "Run-ledger serialized stage evidence writes",
                "source": ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Run-ledger serialized stage evidence writes",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Run-ledger serialized stage evidence writes",
                    "route": "hydrate_task",
                    "placement": {"source": "proposal-run-ledger-atomic-stage-evidence"},
                }
            },
        },
    )
    _write_hydrated_task_artifacts(tmp_path, "T-028")

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "ship_task"
    assert decision["candidate_id"] == "T-028"
    assert decision["route_decision"]["selected_route"] == "ship_task"
    assert decision["route_decision"]["existing_task_id"] == "T-028"


def test_queued_proposal_hydration_existing_task_stops_without_ship_budget(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        autonomy_budget={
            "approval_basis": "User approved hydration-only autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["hydrate_task"],
        },
        queue=[
            {
                "action": "hydrate_task",
                "candidate_id": "proposal-run-ledger-atomic-stage-evidence",
                "proposed_task_id": "T-028",
                "title": "Run-ledger serialized stage evidence writes",
                "source": ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Run-ledger serialized stage evidence writes",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Run-ledger serialized stage evidence writes",
                    "route": "hydrate_task",
                }
            },
        },
    )
    _write_hydrated_task_artifacts(tmp_path, "T-028")

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "proposal_hydration_existing_task_requires_ship_approval"
    assert decision["candidate_id"] == "T-028"


def test_queued_proposal_hydration_existing_task_stops_without_artifacts(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "hydrate_task",
                "candidate_id": "run-ledger-atomic-stage-evidence",
                "proposed_task_id": "T-028",
                "title": "Run-ledger serialized stage evidence writes",
                "source": "proposal",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Run-ledger serialized stage evidence writes",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Run-ledger serialized stage evidence writes",
                    "route": "hydrate_task",
                    "placement": {"source": "proposal-run-ledger-atomic-stage-evidence"},
                }
            },
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        [
            {
                "id": "T-028",
                "title": "Run-ledger serialized stage evidence writes",
                "source": "proposal-run-ledger-atomic-stage-evidence",
                "status": "pending",
            }
        ],
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "proposal_hydration_existing_task_requires_ship_approval"
    assert decision["route_decision"]["existing_task_id"] == "T-028"
    assert decision["route_decision"]["live_task_truth"]["artifacts_exist"] is False


def test_discovered_proposal_hydration_stops_when_matching_task_is_complete(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    _write_yaml(
        tmp_path / ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Run-ledger serialized stage evidence writes",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Run-ledger serialized stage evidence writes",
                    "route": "hydrate_task",
                    "placement": {"source": "proposal-run-ledger-atomic-stage-evidence"},
                }
            },
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        [
            {
                "id": "T-028",
                "title": "Run-ledger serialized stage evidence writes",
                "source": "proposal-run-ledger-atomic-stage-evidence",
                "status": "complete",
                "completed_date": "2026-04-25",
            }
        ],
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "proposal_hydration_already_completed"
    assert decision["candidate_id"] == "T-028"
    assert decision["route_decision"]["selected_route"] == "stop"


def test_next_campaign_recommendation_blocks_duplicate_proposal_hydration_with_route_authority(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        vision={"current_band": "green", "target_band": "green", "realized": True},
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Run-ledger serialized stage evidence writes",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Run-ledger serialized stage evidence writes",
                    "route": "hydrate_task",
                    "placement": {"source": "proposal-run-ledger-atomic-stage-evidence"},
                }
            },
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        [
            {
                "id": "T-028",
                "title": "Run-ledger serialized stage evidence writes",
                "source": "proposal-run-ledger-atomic-stage-evidence",
                "status": "complete",
                "completed_date": "2026-04-25",
            }
        ],
    )
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    status = autonomous_loop.operator_read(tmp_path, state_path)

    recommendation = autonomous_loop._next_campaign_recommendation(tmp_path, state, status)

    assert recommendation["available"] is False
    assert recommendation["reason"] == "no_non_protected_candidate"
    assert (
        recommendation["blocked_recommendations"][0]["route_preflight"]["route_state"]
        == "proposal_hydration_already_completed"
    )
    assert (
        recommendation["blocked_recommendations"][0]["route_preflight"]["selected_route"] == "stop"
    )


def test_next_campaign_recommendation_includes_threshold_rationale_for_selected_route(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        vision={"current_band": "green", "target_band": "green", "realized": True},
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        {
            "items": [
                {
                    "id": "BL-900",
                    "title": "Known ready backlog delivery",
                    "status": "pending",
                    "priority": 1,
                    "target_layer": "infrastructure",
                    "delivery_pipeline": "standard",
                }
            ]
        },
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/fresh-hydration.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Fresh hydration",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Fresh hydration",
                    "route": "hydrate_task",
                    "placement": {"target_layer": "infrastructure"},
                }
            },
        },
    )
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    status = autonomous_loop.operator_read(tmp_path, state_path)

    recommendation = autonomous_loop._next_campaign_recommendation(tmp_path, state, status)

    rationale = recommendation["threshold_rationale"]
    assert recommendation["available"] is True
    assert rationale["selected"]["candidate_id"] == "BL-900"
    assert rationale["runner_up"]["candidate_id"] == "fresh-hydration"
    assert rationale["score_delta"] > 0
    assert rationale["decisive_dimensions"]
    assert recommendation["draft_campaign_declaration"]["threshold_rationale"] == rationale


def test_next_campaign_recommendation_rewrites_hydrated_proposal_to_ship_route(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        vision={"current_band": "green", "target_band": "green", "realized": True},
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Run-ledger serialized stage evidence writes",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Run-ledger serialized stage evidence writes",
                    "route": "hydrate_task",
                    "proposed_task_id": "T-028",
                    "placement": {"source": "proposal-run-ledger-atomic-stage-evidence"},
                }
            },
        },
    )
    _write_hydrated_task_artifacts(tmp_path, "T-028")
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    status = autonomous_loop.operator_read(tmp_path, state_path)

    recommendation = autonomous_loop._next_campaign_recommendation(tmp_path, state, status)

    selected = recommendation["ranked_recommendations"][0]
    assert selected["candidate_id"] == "run-ledger-atomic-stage-evidence"
    assert selected["action"] == "ship_task"
    assert selected["route_preflight"]["selected_route"] == "ship_task"
    assert recommendation["draft_campaign_declaration"]["allowed_action_classes"] == [
        "ship_task",
        "capture_self_improvement",
    ]


def test_discovered_proposal_hydration_routes_existing_pending_task_to_ship(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    _write_yaml(
        tmp_path / ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Run-ledger serialized stage evidence writes",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Run-ledger serialized stage evidence writes",
                    "route": "hydrate_task",
                    "proposed_task_id": "T-028",
                    "placement": {"source": "proposal-run-ledger-atomic-stage-evidence"},
                }
            },
        },
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap-specs/v0.2.0/T-028.yaml",
        {"id": "T-028", "title": "Run-ledger serialized stage evidence writes"},
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap.yaml",
        {"tasks": [{"id": "T-028", "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-028.yaml"}]},
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        [
            {
                "id": "T-028",
                "source": "proposal-run-ledger-atomic-stage-evidence",
                "status": "blocked",
            }
        ],
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "ship_task"
    assert decision["candidate_id"] == "T-028"
    assert decision["source"] == ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml"
    assert decision["route_decision"]["existing_task_id"] == "T-028"


def test_discovered_proposal_hydration_existing_task_stops_without_ship_budget(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        autonomy_budget={
            "approval_basis": "User approved hydration-only autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["hydrate_task"],
        },
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/run-ledger-atomic-stage-evidence.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Run-ledger serialized stage evidence writes",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Run-ledger serialized stage evidence writes",
                    "route": "hydrate_task",
                    "proposed_task_id": "T-028",
                }
            },
        },
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap-specs/v0.2.0/T-028.yaml",
        {"id": "T-028", "title": "Run-ledger serialized stage evidence writes"},
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap.yaml",
        {"tasks": [{"id": "T-028", "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-028.yaml"}]},
    )
    _write_yaml(tmp_path / ".azoth/backlog.yaml", [{"id": "T-028", "status": "blocked"}])

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "proposal_hydration_existing_task_requires_ship_approval"
    assert decision["candidate_id"] == "T-028"


def test_discovered_proposal_hydration_protected_match_stops(tmp_path: Path) -> None:
    state_path = _state(tmp_path)
    _write_yaml(
        tmp_path / ".azoth/proposals/protected-hydration.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Protected hydration",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Protected hydration",
                    "route": "hydrate_task",
                    "proposed_task_id": "T-PROTECTED",
                    "placement": {"target_layer": "governance"},
                }
            },
        },
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap-specs/v0.2.0/T-PROTECTED.yaml",
        {"id": "T-PROTECTED", "title": "Protected hydration"},
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap.yaml",
        {
            "tasks": [
                {
                    "id": "T-PROTECTED",
                    "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-PROTECTED.yaml",
                }
            ]
        },
    )
    _write_yaml(tmp_path / ".azoth/backlog.yaml", [{"id": "T-PROTECTED", "status": "blocked"}])

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "protected_gate_required"
    assert decision["candidate_id"] == "T-PROTECTED"


def test_discovered_proposal_hydration_routes_fresh_task_when_allowed(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    _write_yaml(
        tmp_path / ".azoth/proposals/fresh-hydration.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Fresh hydration",
            "status": "draft",
            "details": {
                "recommended_next_slice": {
                    "exact_title": "Fresh hydration",
                    "route": "hydrate_task",
                    "placement": {"target_layer": "infrastructure"},
                }
            },
        },
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "hydrate_task"
    assert decision["candidate_id"] == "fresh-hydration"


def test_queued_candidate_can_override_lifecycle_route_stop(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "route-authority-governor-repair",
                "title": "Repair route authority",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-AUTO-A"
    doc["readiness"]["approval_scope"] = "hydration_specific_slice_auto_001_a"
    _write_yaml(initiative_path, doc)
    _write_completed_task_artifacts(tmp_path, "T-AUTO-A")

    decision = autonomous_loop.decide_next(tmp_path, state_path)
    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert decision["action"] == "ship_task"
    assert decision["candidate_id"] == "route-authority-governor-repair"
    assert read["route_authority"] == "queued-override"


def test_lifecycle_route_stop_blocks_generic_initiative_fallback(tmp_path: Path) -> None:
    state_path = _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-AUTO-A"
    doc["readiness"]["approval_scope"] = "hydration_specific_slice_auto_001_a"
    _write_yaml(initiative_path, doc)
    _write_completed_task_artifacts(tmp_path, "T-AUTO-A")
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        {
            "schema_version": 1,
            "items": [
                {
                    "id": "READY-1",
                    "title": "Ready fallback task",
                    "status": "ready",
                    "priority": 1,
                    "target_layer": "infrastructure",
                    "delivery_pipeline": "standard",
                }
            ],
        },
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)
    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["candidate_id"] == "INI-AUTO-001"
    assert decision["stop_reason"] == "lifecycle_route_stop_completed_or_stale_campaign"
    assert decision["route_decision"]["selected_route"] == "stop"
    assert read["route_authority"] == "stop:completed_or_stale_campaign"


def test_lifecycle_route_terminal_initiative_readiness_stops_cleanly(tmp_path: Path) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["status"] = "complete"
    doc["readiness"].update(
        {
            "readiness_status": "complete",
            "candidate_first_slice": "",
            "next_candidate_ref": "",
            "next_readiness_gate": "none_feature_complete",
            "approval_scope": "feature_closure_no_hydration",
            "hydration_recommendation": "Feature is complete; do not repeat hydration.",
        }
    )
    _write_yaml(initiative_path, doc)

    capsule = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)

    assert capsule["selected_route"] == "stop"
    assert capsule["route_state"] == "completed_or_stale_campaign"
    assert capsule["approval_needed"] == "fresh initiative, proposal, or improvement campaign"
    assert capsule["readiness_evidence"]["readiness_status"] == "complete"
    assert any(
        item["action"] == "hydrate_task"
        and item["reason"] == "initiative readiness is complete; no hydration action remains"
        for item in capsule["blocked_actions"]
    )


def test_declared_proposal_hydrated_task_bypasses_stale_initiative_readiness(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "unevaluated",
            "declaration": {
                "status": "approved",
                "selected_seed": "proposal-hydration-bridge",
                "selected_seed_type": "proposal",
                "summary": "Proposal refinement to hydration readiness bridge",
            },
        },
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-AUTO-A"
    doc["readiness"]["approval_scope"] = "hydration_specific_slice_auto_001_a"
    _write_yaml(initiative_path, doc)
    _write_yaml(
        tmp_path / ".azoth/proposals/autonomous-auto-campaign-evaluation-learning-closure.yaml",
        {
            "proposal_schema_version": 1,
            "title": "Autonomous-auto campaign evaluation learning closure",
            "status": "draft",
            "details": {
                "post_run_refinement": {
                    "selected_next_slice": {
                        "title": "Proposal refinement to hydration readiness bridge",
                        "route": "hydrate_task_after_refinement",
                        "proposed_hydration_plan": {
                            "hydrated_task_ref": "T-032",
                            "scaffold_command": (
                                "python3 scripts/roadmap_scaffold.py --title "
                                '"Proposal refinement to hydration readiness bridge"'
                            ),
                        },
                    }
                }
            },
        },
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap-specs/v0.2.0/T-AUTO-A.yaml",
        {"id": "T-AUTO-A", "title": "Completed stale task"},
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap-specs/v0.2.0/T-032.yaml",
        {
            "id": "T-032",
            "title": "Proposal refinement to hydration readiness bridge",
            "source_proposal_ref": (
                ".azoth/proposals/autonomous-auto-campaign-evaluation-learning-closure.yaml"
            ),
        },
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap.yaml",
        {
            "tasks": [
                {
                    "id": "T-032",
                    "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-032.yaml",
                }
            ],
            "versions": [
                {
                    "id": "v0.2.0-p3",
                    "completed_tasks": [
                        {
                            "id": "T-AUTO-A",
                            "title": "Completed stale task",
                            "completed_date": "2026-04-25",
                        }
                    ],
                }
            ],
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        [
            {"id": "T-AUTO-A", "status": "complete", "completed_date": "2026-04-25"},
            {
                "id": "T-032",
                "title": "Proposal refinement to hydration readiness bridge",
                "status": "pending",
                "source": "proposal-autonomous-auto-campaign-evaluation-learning-closure",
            },
        ],
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "ship_task"
    assert decision["candidate_id"] == "T-032"
    assert decision["route_decision"]["selected_route"] == "ship_task"
    assert decision["route_decision"]["proposal_ref"] == (
        ".azoth/proposals/autonomous-auto-campaign-evaluation-learning-closure.yaml"
    )
    artifacts = decision["strategy_preflight"]["source_artifacts"]
    assert artifacts["proposal_ref"] == (
        ".azoth/proposals/autonomous-auto-campaign-evaluation-learning-closure.yaml"
    )
    assert artifacts["exact_scaffold_command_present"] is True
    assert artifacts["stale_initiative_route"]["selected_route"] == "stop"
    assert artifacts["stale_initiative_route"]["route_state"] == "completed_or_stale_campaign"


def test_lifecycle_route_uses_current_state_path(tmp_path: Path) -> None:
    default_state_path = tmp_path / ".azoth/autonomous-loop-state.local.yaml"
    state_path = tmp_path / ".azoth/custom-autonomous-loop-state.yaml"
    _state(tmp_path)
    default_state_path.unlink()
    data = {
        "schema_version": 1,
        "loop_id": "custom-loop-test",
        "status": "active",
        "autonomy_budget": {
            "approval_basis": "User approved custom autonomous-auto state.",
            "max_iterations": 1,
            "allowed_actions": ["research_initiative"],
        },
        "iteration": 0,
        "queue": [],
        "self_capture_queue": [],
        "alignment_packets": [],
        "alignment_dispositions": [],
        "history": [],
    }
    _write_yaml(state_path, data)
    _write_lifecycle_initiative_bank(tmp_path)

    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert decision["action"] == "research_initiative"
    assert decision["candidate_id"] == "INI-AUTO-001"


def test_protected_queued_candidate_stops(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "BL-999",
                "title": "Kernel change",
                "target_layer": "M1",
                "delivery_pipeline": "governed",
            }
        ],
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "protected_gate_required"


@pytest.mark.parametrize(
    "protected_fields",
    [
        {"governance_mode": "governed"},
        {"requires_human_gate": True},
        {"destructive": True},
        {"requires_credentials": True},
        {"requires_network": True},
        {"flags": ["network-required"]},
    ],
)
def test_protected_queued_candidate_variants_stop(
    tmp_path: Path,
    protected_fields: dict,
) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "BL-999",
                "title": "Protected change",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
                **protected_fields,
            }
        ],
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "protected_gate_required"


def test_ready_backlog_task_selected(tmp_path: Path) -> None:
    state_path = _state(tmp_path)
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        {
            "schema_version": 1,
            "items": [
                {"id": "T-000", "status": "complete", "priority": 1, "title": "Done"},
                {
                    "id": "T-123",
                    "status": "ready",
                    "priority": 2,
                    "title": "Ship ready task",
                    "target_layer": "infrastructure",
                    "delivery_pipeline": "standard",
                },
            ],
        },
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    assert decision["action"] == "ship_task"
    assert decision["candidate_id"] == "T-123"
    assert decision["backlog_id"] == "T-123"


def test_ready_initiative_slice_selected_for_hydration(tmp_path: Path) -> None:
    state_path = _state(tmp_path)
    _write_yaml(
        tmp_path / ".azoth/initiative-banks/INI-TEST-001.yaml",
        {
            "schema_version": 1,
            "initiative_id": "INI-TEST-001",
            "title": "Initiative test",
            "status": "active_refinement",
            "candidate_slices": [
                {
                    "candidate_id": "slice-test-a",
                    "proposed_task_id": "T-200",
                    "title": "Hydrate slice",
                    "status": "ready",
                    "target_layer": "infrastructure",
                    "delivery_pipeline": "standard",
                }
            ],
            "readiness": {
                "readiness_status": "ready_to_hydrate",
                "human_decision": "approved",
                "candidate_first_slice": "slice-test-a",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            },
        },
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    assert decision["action"] == "hydrate_task"
    assert decision["candidate_id"] == "slice-test-a"
    assert decision["backlog_id"] == "T-200"


def test_draft_proposal_selected_after_backlog_and_initiative_paths(tmp_path: Path) -> None:
    state_path = _state(tmp_path)
    _write_yaml(
        tmp_path / ".azoth/proposals/proposal-a.yaml",
        {"proposal_schema_version": 1, "title": "Proposal A", "status": "draft"},
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    assert decision["action"] == "refine_proposal"
    assert decision["candidate_id"] == "proposal-a"


def test_open_next_writes_scope_gate_and_advances_state(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    decision_path = tmp_path / ".azoth/next-decision.json"
    decision_path.write_text(json.dumps(decision), encoding="utf-8")

    result = autonomous_loop.open_next(
        tmp_path,
        state_path,
        decision_path,
        "2026-04-25T12:00:00Z",
    )

    scope = json.loads((tmp_path / ".azoth/scope-gate.json").read_text(encoding="utf-8"))
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    assert result["opened"] is True
    assert scope["pipeline_command"] == "autonomous-auto"
    assert scope["delivery_pipeline"] == "standard"
    assert scope["governance_mode"] == "standard"
    assert scope["approved_by"] == "autonomous-auto-loop"
    assert scope["approval_basis"] == "User approved branch-local autonomous-auto testing."
    assert scope["delegation_plan"]["mode"] == "guidance"
    assert scope["delegation_plan"]["run_ledger_evidence"]["run_id"] == result["session_id"]
    assert [stage["subagent_type"] for stage in scope["delegation_plan"]["stages"]] == [
        "architect",
        "planner",
        "builder",
        "evaluator",
    ]
    assert all(
        stage["evidence_policy"] == "spawn_required"
        for stage in scope["delegation_plan"]["stages"]
    )
    assert scope["delegation_plan"]["stage_evidence_policy"] == {
        "autonomous_auto_s1_architect": "spawn_required",
        "autonomous_auto_s2_planner": "spawn_required",
        "autonomous_auto_s3_builder": "spawn_required",
        "autonomous_auto_s4_evaluator": "spawn_required",
    }
    assert scope["loop_decision"]["action"] == "ship_task"
    assert scope["loop_decision"]["strategy_preflight"]["packet_type"] == (
        "autonomous_auto_strategy_preflight"
    )
    assert scope["loop_decision"]["strategy_preflight"]["verdict"] == "allow_open"
    assert scope["loop_decision"]["strategy_preflight"]["target_classification"] == (
        "delivery-ready"
    )
    ledger = yaml.safe_load((tmp_path / ".azoth/run-ledger.local.yaml").read_text(encoding="utf-8"))
    run = next(item for item in ledger["runs"] if item["run_id"] == result["session_id"])
    assert run["status"] == "active"
    assert run["active_stage_id"] == "autonomous_auto_s1_architect"
    assert run["pending_stage_ids"] == [
        "autonomous_auto_s1_architect",
        "autonomous_auto_s2_planner",
        "autonomous_auto_s3_builder",
        "autonomous_auto_s4_evaluator",
    ]
    assert run["stage_evidence_policy"] == scope["delegation_plan"]["stage_evidence_policy"]
    assert state["iteration"] == 1
    assert state["last_session_id"] == result["session_id"]
    assert state["queue"] == []
    assert state["history"][0]["candidate_id"] == "T-321"
    assert state["history"][0]["delegation_plan_id"] == scope["delegation_plan"]["plan_id"]
    assert state["history"][0]["strategy_preflight"]["verdict"] == "allow_open"


def test_open_next_refuses_advisory_recommendation_packet_as_decision(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision_path = _decision_path(
        tmp_path,
        {
            "packet_type": "autonomous_auto_next_campaign_recommendation",
            "mode": "recommendation_only",
            "status": "advisory_only",
            "may_open_scope": False,
            "fresh_operator_approval_required": True,
            "ranked_recommendations": [
                {
                    "action": "ship_task",
                    "candidate_id": "T-321",
                }
            ],
        },
    )

    with pytest.raises(SystemExit, match="advisory recommendation"):
        autonomous_loop.open_next(
            tmp_path,
            state_path,
            decision_path,
            "2026-04-25T12:00:00Z",
        )

    assert not (tmp_path / ".azoth/scope-gate.json").exists()


def test_open_next_consumes_only_selected_queue_candidate(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            },
            {
                "action": "refine_proposal",
                "candidate_id": "proposal-b",
                "title": "Refine proposal B",
                "target_layer": "planning",
                "delivery_pipeline": "standard",
            },
        ],
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    decision_path = tmp_path / ".azoth/next-decision.json"
    decision_path.write_text(json.dumps(decision), encoding="utf-8")

    autonomous_loop.open_next(
        tmp_path,
        state_path,
        decision_path,
        "2026-04-25T12:00:00Z",
    )

    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    assert [item["candidate_id"] for item in state["queue"]] == ["proposal-b"]


def test_open_next_consumes_selected_self_capture_candidate(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        self_capture_queue=[
            {"candidate_id": "lesson-a", "title": "Capture lesson A"},
            {"candidate_id": "lesson-b", "title": "Capture lesson B"},
        ],
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    decision_path = tmp_path / ".azoth/next-decision.json"
    decision_path.write_text(json.dumps(decision), encoding="utf-8")

    autonomous_loop.open_next(
        tmp_path,
        state_path,
        decision_path,
        "2026-04-25T12:00:00Z",
    )

    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    assert [item["candidate_id"] for item in state["self_capture_queue"]] == ["lesson-b"]


def test_open_next_refuses_active_session_gate_conflict(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    decision_path = tmp_path / ".azoth/next-decision.json"
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    _write_active_session_gate(tmp_path)

    with pytest.raises(SystemExit, match="active session-gate conflict"):
        autonomous_loop.open_next(
            tmp_path,
            state_path,
            decision_path,
            "2026-04-25T12:00:00Z",
        )
    assert not (tmp_path / ".azoth/scope-gate.json").exists()


def test_live_write_claim_blocks_next_iteration_and_operator_read(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    _write_yaml(
        tmp_path / ".azoth/run-ledger.local.yaml",
        {
            "schema_version": 1,
            "runs": [],
            "write_claim": {
                "session_id": "previous-child",
                "expires_at": _future_expiry(),
                "acquired_at": "2026-04-25T12:00:00Z",
                "worktree_path": str(tmp_path),
            },
        },
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)
    status = autonomous_loop.loop_status(tmp_path, state_path)
    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "active_write_claim_present"
    assert status["can_continue"] is False
    assert status["stop_reason"] == "active_write_claim_present"
    assert read["write_claim"].startswith("held by previous-child")
    assert "active_write_claim_present" in read["stop_conditions"]
    assert read["residual_risk"].startswith("Live write claim remains")


def test_open_next_refuses_missing_loop_state_even_with_fabricated_decision(
    tmp_path: Path,
) -> None:
    decision_path = _decision_path(
        tmp_path,
        {
            "decision_schema_version": 1,
            "loop_id": "loop-test",
            "iteration": 1,
            "action": "ship_task",
            "candidate_id": "T-321",
            "source": "queue",
            "goal": "Ship fabricated task",
            "backlog_id": "T-321",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "governance_mode": "standard",
            "pipeline_command": "autonomous-auto",
            "approval_basis": "Fabricated approval.",
        },
    )

    with pytest.raises(SystemExit, match="missing_loop_state"):
        autonomous_loop.open_next(
            tmp_path,
            tmp_path / ".azoth/autonomous-loop-state.local.yaml",
            decision_path,
            "2026-04-25T12:00:00Z",
        )
    assert not (tmp_path / ".azoth/scope-gate.json").exists()


def test_open_next_refuses_stopped_loop_state(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        status="stopped",
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision_path = _decision_path(
        tmp_path,
        {
            "decision_schema_version": 1,
            "loop_id": "loop-test",
            "iteration": 1,
            "action": "ship_task",
            "candidate_id": "T-321",
            "source": "queue",
            "goal": "Ship stale task",
            "backlog_id": "T-321",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "governance_mode": "standard",
            "pipeline_command": "autonomous-auto",
            "approval_basis": "User approved branch-local autonomous-auto testing.",
        },
    )

    with pytest.raises(SystemExit, match="loop_not_active"):
        autonomous_loop.open_next(
            tmp_path,
            state_path,
            decision_path,
            "2026-04-25T12:00:00Z",
        )
    assert not (tmp_path / ".azoth/scope-gate.json").exists()


def test_open_next_refuses_budget_exhausted_state(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        iteration=1,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 1,
            "allowed_actions": ["ship_task"],
        },
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision_path = _decision_path(
        tmp_path,
        {
            "decision_schema_version": 1,
            "loop_id": "loop-test",
            "iteration": 2,
            "action": "ship_task",
            "candidate_id": "T-321",
            "source": "queue",
            "goal": "Ship stale task",
            "backlog_id": "T-321",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "governance_mode": "standard",
            "pipeline_command": "autonomous-auto",
            "approval_basis": "User approved branch-local autonomous-auto testing.",
        },
    )

    with pytest.raises(SystemExit, match="budget_exhausted"):
        autonomous_loop.open_next(
            tmp_path,
            state_path,
            decision_path,
            "2026-04-25T12:00:00Z",
        )
    assert not (tmp_path / ".azoth/scope-gate.json").exists()


def test_open_next_refuses_stale_iteration_decision(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    stale_decision = autonomous_loop.decide_next(tmp_path, state_path)
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    state["iteration"] = 1
    _write_yaml(state_path, state)
    decision_path = _decision_path(tmp_path, stale_decision)

    with pytest.raises(SystemExit, match="stale or mismatched"):
        autonomous_loop.open_next(
            tmp_path,
            state_path,
            decision_path,
            "2026-04-25T12:00:00Z",
        )
    assert not (tmp_path / ".azoth/scope-gate.json").exists()


def test_open_next_refuses_action_not_in_current_budget(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["ship_task"],
        },
        queue=[
            {
                "action": "refine_proposal",
                "candidate_id": "proposal-a",
                "title": "Refine proposal A",
                "target_layer": "planning",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision_path = _decision_path(
        tmp_path,
        {
            "decision_schema_version": 1,
            "loop_id": "loop-test",
            "iteration": 1,
            "action": "refine_proposal",
            "candidate_id": "proposal-a",
            "source": "queue",
            "goal": "Refine proposal A",
            "backlog_id": "proposal-a",
            "target_layer": "planning",
            "delivery_pipeline": "standard",
            "governance_mode": "standard",
            "pipeline_command": "autonomous-auto",
            "approval_basis": "User approved branch-local autonomous-auto testing.",
        },
    )

    with pytest.raises(SystemExit, match="action_not_in_budget"):
        autonomous_loop.open_next(
            tmp_path,
            state_path,
            decision_path,
            "2026-04-25T12:00:00Z",
        )
    assert not (tmp_path / ".azoth/scope-gate.json").exists()


def test_open_next_refuses_initiative_decision_without_route_evidence(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        autonomy_budget={
            "approval_basis": (
                "Operator approved research_to_readiness_slice_auto_001_h strategy preflight."
            ),
            "max_iterations": 3,
            "allowed_actions": ["research_initiative"],
        },
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "complete"
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-h",
            "proposed_task_id": "T-AUTO-H",
            "title": "Autonomous campaign strategy budget repair",
            "initiative_ref": "INI-AUTO-001",
            "status": "candidate",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Repair pre-open strategy budget before another campaign opens.",
            "acceptance_criteria": [
                "Recommendation and lifecycle-route are reconciled before open-next."
            ],
            "known_non_goals": ["Do not hydrate or ship from the strategy child."],
            "open_questions": [],
        }
    )
    doc["readiness"].update(
        {
            "readiness_status": "continue_research",
            "candidate_first_slice": "slice-auto-001-h",
            "next_candidate_ref": "slice-auto-001-h",
            "next_readiness_gate": "research_strategy_preflight_before_init_or_open_next",
            "hydration_recommendation": "Strategy preflight is required before open-next.",
            "approval_scope": "research_to_readiness_slice_auto_001_h",
            "approval_basis": "Operator approved research strategy preflight.",
        }
    )
    _write_yaml(initiative_path, doc)
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    stale_decision = dict(decision)
    stale_decision.pop("route_decision", None)
    decision_path = _decision_path(tmp_path, stale_decision)

    with pytest.raises(SystemExit, match="missing lifecycle-route evidence"):
        autonomous_loop.open_next(
            tmp_path,
            state_path,
            decision_path,
            "2026-04-25T12:00:00Z",
        )

    assert not (tmp_path / ".azoth/scope-gate.json").exists()


def test_open_next_refuses_initiative_decision_with_route_conflict(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        autonomy_budget={
            "approval_basis": (
                "Operator approved research_to_readiness_slice_auto_001_h strategy preflight."
            ),
            "max_iterations": 3,
            "allowed_actions": ["research_initiative"],
        },
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "complete"
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-h",
            "proposed_task_id": "T-AUTO-H",
            "title": "Autonomous campaign strategy budget repair",
            "initiative_ref": "INI-AUTO-001",
            "status": "candidate",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Repair pre-open strategy budget before another campaign opens.",
            "acceptance_criteria": [
                "Recommendation and lifecycle-route are reconciled before open-next."
            ],
            "known_non_goals": ["Do not hydrate or ship from the strategy child."],
            "open_questions": [],
        }
    )
    doc["readiness"].update(
        {
            "readiness_status": "continue_research",
            "candidate_first_slice": "slice-auto-001-h",
            "next_candidate_ref": "slice-auto-001-h",
            "next_readiness_gate": "research_strategy_preflight_before_init_or_open_next",
            "hydration_recommendation": "Strategy preflight is required before open-next.",
            "approval_scope": "research_to_readiness_slice_auto_001_h",
            "approval_basis": "Operator approved research strategy preflight.",
        }
    )
    _write_yaml(initiative_path, doc)
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    conflicted_decision = dict(decision)
    conflicted_decision["route_decision"] = {
        **decision["route_decision"],
        "selected_route": "ship_task",
        "route_state": "delivery_ready",
    }
    decision_path = _decision_path(tmp_path, conflicted_decision)

    with pytest.raises(SystemExit, match="lifecycle-route conflict"):
        autonomous_loop.open_next(
            tmp_path,
            state_path,
            decision_path,
            "2026-04-25T12:00:00Z",
        )

    assert not (tmp_path / ".azoth/scope-gate.json").exists()


def test_strategy_preflight_generated_route_conflict_has_repair_action(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    candidate = {
        "candidate_id": "INI-AUTO-001",
        "title": "Autonomous initiative lifecycle orchestration",
        "target_layer": "planning",
        "delivery_pipeline": "standard",
        "route_decision": {
            "selected_route": "ship_task",
            "route_state": "delivery_ready",
            "approval_needed": "normal scoped delivery approval",
            "readiness_evidence": {
                "candidate_id": "slice-auto-001-h",
                "candidate_task_ref": "T-030",
                "approval_scope": "hydration_specific_slice_auto_001_h",
                "freshness_status": "current_as_of_test",
            },
            "source_artifacts": {"initiative_bank": ".azoth/initiative-banks/INI-AUTO-001.yaml"},
            "blocked_actions": [
                {"action": "hydrate_task", "reason": "repeat hydration is blocked"}
            ],
        },
    }

    preflight = autonomous_loop._strategy_preflight_for_decision(
        tmp_path,
        state,
        action="research_initiative",
        candidate=candidate,
        source="initiative-bank",
    )

    assert preflight["verdict"] == "stop_route_conflict"
    assert preflight["may_open_scope"] is False
    assert preflight["target_classification"] == "route-conflicted"
    assert preflight["selected_route"] == "ship_task"
    assert preflight["route_state"] == "delivery_ready"
    assert preflight["approval_scope"] == "hydration_specific_slice_auto_001_h"
    assert preflight["freshness_status"] == "current_as_of_test"
    assert preflight["next_safe_action"] == "stop_and_reconcile_lifecycle_route"
    assert "does not match lifecycle-route" in preflight["mismatch_reason"]
    assert preflight["source_artifacts"]["initiative_bank"].endswith("INI-AUTO-001.yaml")
    assert any(
        item["action"] == "research_initiative"
        and "does not match lifecycle-route" in item["reason"]
        for item in preflight["blocked_alternatives"]
    )


def test_strategy_preflight_includes_learning_harvester_gate(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    candidate = {
        "candidate_id": "protected-learning-signal",
        "title": "network credential protected autonomous-auto improvement",
    }

    preflight = autonomous_loop._strategy_preflight_for_decision(
        tmp_path,
        state,
        action="ship_task",
        candidate=candidate,
        source="queue",
    )

    harvester = preflight["learning_harvester"]
    assert harvester["consumed"] is True
    assert harvester["write_authority"] == "advisory_only_scope_gates_still_required"
    assert harvester["decision"]["route"] == "human_gate_required"
    assert harvester["decision"]["protected_gate_required"] is True
    assert preflight["may_open_scope"] is False
    assert any(
        "learning harvester routed signal to human_gate_required" in item["reason"]
        for item in preflight["blocked_alternatives"]
    )


def test_strategy_preflight_blocks_user_governed_learning_to_intake(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    candidate = {
        "candidate_id": "user-governed-learning-signal",
        "title": "user-governed cross-system autonomous-auto improvement",
    }

    preflight = autonomous_loop._strategy_preflight_for_decision(
        tmp_path,
        state,
        action="ship_task",
        candidate=candidate,
        source="queue",
    )

    harvester = preflight["learning_harvester"]
    assert harvester["decision"]["route"] == "defer_to_intake"
    assert harvester["decision"]["selected_action"] == "defer_to_inbox_intake"
    assert preflight["may_open_scope"] is False
    assert any(
        "learning harvester routed signal to defer_to_intake" in item["reason"]
        for item in preflight["blocked_alternatives"]
    )


def test_strategy_preflight_allows_research_only_after_protected_corpus_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = _state(
        tmp_path,
        autonomy_budget={
            "approval_basis": (
                "Operator approved candidate-board synthesis as research-only. "
                "Hydration, implementation, and protected mutations remain blocked. "
                "The protected-boundary residual is acknowledged but not authorized "
                "for mutation."
            ),
            "max_iterations": 3,
            "allowed_actions": ["research_initiative"],
            "stop_conditions": ["protected_gate_required"],
        },
    )
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))

    def fake_campaign_audit(*args: object, **kwargs: object) -> dict:
        return {
            "learning_harvester": {
                "selected_learning_route": "human_gate_required",
                "decisions": [
                    {
                        "signal_id": "residual-8",
                        "blast_radius": "protected",
                        "route": "human_gate_required",
                        "protected_gate_required": True,
                    }
                ],
            }
        }

    monkeypatch.setattr(autonomous_loop, "build_campaign_audit", fake_campaign_audit)

    preflight = autonomous_loop._strategy_preflight_for_decision(
        tmp_path,
        state,
        action="research_initiative",
        candidate={
            "candidate_id": "post-p4-candidate-board-synthesis",
            "title": "Post-P4 candidate board synthesis",
        },
        source="campaign-context-ledger",
    )

    assert preflight["verdict"] == "allow_open"
    assert preflight["may_open_scope"] is True
    assert preflight["human_gate_acknowledgement"]["accepted"] is True
    assert not any(
        "learning harvester corpus recommendation" in item["reason"]
        for item in preflight["blocked_alternatives"]
    )


def test_strategy_preflight_keeps_delivery_blocked_after_protected_corpus_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = _state(
        tmp_path,
        autonomy_budget={
            "approval_basis": (
                "Operator approved candidate-board synthesis as research-only. "
                "Hydration, implementation, and protected mutations remain blocked. "
                "The protected-boundary residual is acknowledged but not authorized "
                "for mutation."
            ),
            "max_iterations": 3,
            "allowed_actions": ["research_initiative"],
            "stop_conditions": ["protected_gate_required"],
        },
    )
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))

    def fake_campaign_audit(*args: object, **kwargs: object) -> dict:
        return {
            "learning_harvester": {
                "selected_learning_route": "human_gate_required",
                "decisions": [
                    {
                        "signal_id": "residual-8",
                        "blast_radius": "protected",
                        "route": "human_gate_required",
                        "protected_gate_required": True,
                    }
                ],
            }
        }

    monkeypatch.setattr(autonomous_loop, "build_campaign_audit", fake_campaign_audit)

    preflight = autonomous_loop._strategy_preflight_for_decision(
        tmp_path,
        state,
        action="ship_task",
        candidate={
            "candidate_id": "T-999",
            "title": "Delivery remains blocked",
        },
        source="queue",
    )

    assert preflight["verdict"] == "stop_blocked"
    assert preflight["may_open_scope"] is False
    assert preflight["human_gate_acknowledgement"]["accepted"] is False
    assert preflight["human_gate_acknowledgement"]["reason"] == (
        "corpus_human_gate_only_research_initiative_can_clear"
    )
    assert any(
        "learning harvester corpus recommendation" in item["reason"]
        for item in preflight["blocked_alternatives"]
    )


def test_strategy_preflight_requires_active_approved_campaign_for_auto_self_heal(
    tmp_path: Path,
) -> None:
    candidate = {
        "candidate_id": "safe-learning-signal",
        "title": "low autonomous-auto lifecycle-route report visibility defect",
    }

    active_without_approval = {
        "schema_version": 1,
        "loop_id": "loop-test",
        "status": "active",
        "autonomy_budget": {},
    }
    preflight = autonomous_loop._strategy_preflight_for_decision(
        None,
        active_without_approval,
        action="ship_task",
        candidate=candidate,
        source="queue",
    )
    assert preflight["fresh_campaign_authority"] is False
    assert preflight["learning_harvester"]["decision"]["route"] == "capture_only"
    assert preflight["may_open_scope"] is False
    assert {"action": "ship_task", "reason": "approval_basis is missing"} in preflight[
        "blocked_alternatives"
    ]

    completed_with_old_approval = {
        "schema_version": 1,
        "loop_id": "loop-test",
        "status": "completed",
        "completion_reason": "vision_realized",
        "autonomy_budget": {
            "approval_basis": "Old Green campaign approval is terminal, not fresh authority.",
        },
    }
    preflight = autonomous_loop._strategy_preflight_for_decision(
        None,
        completed_with_old_approval,
        action="ship_task",
        candidate=candidate,
        source="queue",
    )
    assert preflight["current_loop_authority"] == "completed"
    assert preflight["fresh_campaign_authority"] is False
    assert preflight["learning_harvester"]["decision"]["route"] == "capture_only"
    assert preflight["may_open_scope"] is False
    assert any(
        "current loop authority completed requires fresh campaign approval" == item["reason"]
        for item in preflight["blocked_alternatives"]
    )


def test_strategy_preflight_blocks_material_unverifiable_external_freshness(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    candidate = {
        "candidate_id": "external-freshness-needed",
        "title": "External standard dependent route",
        "freshness_materiality": "material",
        "freshness_verification": "unverifiable",
    }

    preflight = autonomous_loop._strategy_preflight_for_decision(
        tmp_path,
        state,
        action="ship_task",
        candidate=candidate,
        source="queue",
    )

    assert preflight["may_open_scope"] is False
    assert preflight["next_safe_action"] == "verify_external_freshness_before_open_next"
    assert any(
        item["reason"] == "external freshness is material and cannot be verified"
        for item in preflight["blocked_alternatives"]
    )


def test_campaign_report_exposes_learning_harvester_route_and_rejected_alternatives(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    inbox = tmp_path / ".azoth/inbox/session-reflection-2026-04-26-report.jsonl"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    inbox.write_text(
        json.dumps(
            {
                "id": "report-signal",
                "session_id": "loop-test",
                "learning_state": "captured",
                "summary": "low autonomous-auto lifecycle-route report visibility defect",
                "tags": ["autonomous-auto", "learning-closure"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = autonomous_loop.campaign_report(
        tmp_path,
        state_path,
        include_next_campaign_recommendation=False,
    )
    harvester = report["learning_harvester"]
    text = autonomous_loop._format_campaign_report(report)

    assert harvester["selected_learning_route"] == "auto_self_heal_now"
    assert "capture_only" in harvester["rejected_alternatives"]
    assert harvester["route_counts"]["auto_self_heal_now"] == 1
    assert "Learning route: auto_self_heal_now" in text
    assert "Learning rejected alternatives:" in text


def test_alignment_packet_record_and_apply_updates_approval_basis(tmp_path: Path) -> None:
    state_path = _state(tmp_path)

    packet = autonomous_loop.record_alignment_packet(
        state_path,
        message="Use this updated approval basis for the branch-local autonomy budget.",
        packet_type="approval_basis",
        checkpoint="before_next_scope",
    )
    applied = autonomous_loop.apply_alignment_packet(
        state_path,
        packet_id=packet["packet_id"],
        disposition="applied",
        affected_artifact=".azoth/scope-gate.json",
        approval_basis="Updated branch-local approval basis.",
    )
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    status = autonomous_loop.loop_status(tmp_path, state_path)

    assert applied["disposition"] == "applied"
    assert state["autonomy_budget"]["approval_basis"] == "Updated branch-local approval basis."
    assert status["alignment"]["packet_count"] == 1
    assert status["alignment"]["disposition_count"] == 1


def test_pending_async_stop_alignment_packet_blocks_decide_next(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    autonomous_loop.record_alignment_packet(
        state_path,
        message="Stop before the next autonomous iteration.",
        packet_type="async_stop",
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)
    status = autonomous_loop.loop_status(tmp_path, state_path)

    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "async_stop_packet"
    assert decision["alignment_checkpoint_summary"]["pending_count"] == 1
    assert status["can_continue"] is False
    assert status["stop_reason"] == "async_stop_packet"


def test_materialize_self_capture_writes_inbox_and_consumes_candidate(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        self_capture_queue=[
            {
                "candidate_id": "lesson-a",
                "title": "Capture async alignment gap",
                "summary": "Async alignment needs durable packet state.",
                "evidence": "UX retrospective found packet classes were only declarative.",
                "recommended_action": "Add packet ledger tests.",
                "tags": ["autonomous-auto", "async-alignment"],
            }
        ],
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    decision_path = _decision_path(tmp_path, decision)

    autonomous_loop.open_next(
        tmp_path,
        state_path,
        decision_path,
        "2026-04-25T12:00:00Z",
    )

    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    materialization = state["history"][0]["self_capture_materialization"]
    inbox_path = tmp_path / materialization["artifact_path"]
    entry = json.loads(inbox_path.read_text(encoding="utf-8").splitlines()[0])
    assert state["self_capture_queue"] == []
    assert materialization["entry_id"] == entry["id"]
    assert entry["summary"] == "Async alignment needs durable packet state."
    assert D32_REQUIRED_FIELDS <= set(entry)
    assert entry["session_id"] == "loop-test"
    assert entry["loop_id"] == "loop-test"
    assert entry["learning_state"] == "captured"

    report = autonomous_loop.campaign_report(
        tmp_path,
        state_path,
        include_next_campaign_recommendation=False,
    )
    decisions = report["learning_harvester"]["decisions"]
    assert any(
        decision["signal_id"] == "Async alignment needs durable packet state."
        and materialization["artifact_path"] in decision["source_refs"]
        for decision in decisions
    )


def test_decision_includes_architect_scorecard_and_rejected_alternatives(tmp_path: Path) -> None:
    state_path = _state(tmp_path)
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        {
            "schema_version": 1,
            "items": [
                {
                    "id": "T-123",
                    "status": "ready",
                    "priority": 2,
                    "title": "Ship ready task",
                    "target_layer": "infrastructure",
                    "delivery_pipeline": "standard",
                },
            ],
        },
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/proposal-a.yaml",
        {"proposal_schema_version": 1, "title": "Proposal A", "status": "draft"},
    )

    decision = autonomous_loop.decide_next(tmp_path, state_path)
    judgment = decision["architect_judgment"]

    assert judgment["selected"]["candidate_id"] == "T-123"
    assert judgment["selected"]["scorecard"]["total"] > 0
    assert [item["candidate_id"] for item in judgment["rejected_alternatives"]] == ["proposal-a"]


def test_operator_read_summarizes_next_move_and_alignment(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "refine_proposal",
                "candidate_id": "proposal-a",
                "title": "Refine proposal A",
                "target_layer": "planning",
                "delivery_pipeline": "standard",
            }
        ],
    )
    autonomous_loop.record_alignment_packet(
        state_path,
        message="Prefer concise operator status.",
        packet_type="async_advisory",
    )

    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert read["next_likely_move"] == "refine_proposal (proposal-a)"
    assert read["approval_basis"] == "User approved branch-local autonomous-auto testing."
    assert read["pending_alignment_packets"] == 1


def test_open_next_persists_budget_and_decision_capsule(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)
    decision_path = _decision_path(tmp_path, decision)

    autonomous_loop.open_next(
        tmp_path,
        state_path,
        decision_path,
        "2026-04-25T12:00:00Z",
    )

    scope = json.loads((tmp_path / ".azoth/scope-gate.json").read_text(encoding="utf-8"))
    assert scope["autonomy_budget"]["replay_threshold"] == 2
    assert scope["loop_decision"]["architect_judgment"]["selected"]["candidate_id"] == "T-321"


def test_wakeup_report_only_builds_decision_without_mutation(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    state_before = state_path.read_text(encoding="utf-8")

    report = autonomous_loop.wakeup(tmp_path, state_path, open_scope=False)

    assert report["opened"] is False
    assert report["session_id"] == ""
    assert report["stop_reason"] is None
    assert report["decision"]["action"] == "ship_task"
    assert report["operator_read"]["next_likely_move"] == "ship_task (T-321)"
    assert report["gate_status"]["blocked"] is False
    assert state_path.read_text(encoding="utf-8") == state_before
    assert not (tmp_path / ".azoth/scope-gate.json").exists()
    assert not (tmp_path / ".azoth/run-ledger.local.yaml").exists()


def test_wakeup_open_writes_built_decision_and_opens_one_scope(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision_out = tmp_path / ".azoth/wakeup-decision.json"

    report = autonomous_loop.wakeup(
        tmp_path,
        state_path,
        open_scope=True,
        decision_out=decision_out,
        expires_at="2026-04-25T12:00:00Z",
    )

    scope = json.loads((tmp_path / ".azoth/scope-gate.json").read_text(encoding="utf-8"))
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    written_decision = json.loads(decision_out.read_text(encoding="utf-8"))
    assert report["opened"] is True
    assert report["session_id"] == scope["session_id"]
    assert report["decision"]["candidate_id"] == "T-321"
    assert written_decision == report["decision"]
    assert scope["loop_decision"]["candidate_id"] == "T-321"
    assert state["iteration"] == 1
    assert state["queue"] == []


def test_wakeup_fails_closed_for_missing_and_malformed_state(tmp_path: Path) -> None:
    missing_state = tmp_path / ".azoth/autonomous-loop-state.local.yaml"

    missing_report = autonomous_loop.wakeup(tmp_path, missing_state, open_scope=True)

    assert missing_report["opened"] is False
    assert missing_report["stop_reason"] == "missing_loop_state"
    assert not (tmp_path / ".azoth/scope-gate.json").exists()

    malformed_state = tmp_path / ".azoth/malformed-autonomous-loop-state.local.yaml"
    malformed_state.parent.mkdir(parents=True, exist_ok=True)
    malformed_state.write_text(":\n", encoding="utf-8")

    malformed_report = autonomous_loop.wakeup(tmp_path, malformed_state, open_scope=True)

    assert malformed_report["opened"] is False
    assert malformed_report["stop_reason"] == "malformed_loop_state"


def test_wakeup_fails_closed_for_active_scope_and_write_claim(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    _write_json(
        tmp_path / ".azoth/scope-gate.json",
        {
            "approved": True,
            "expires_at": _future_expiry(),
            "session_id": "live-session",
        },
    )

    active_scope_report = autonomous_loop.wakeup(tmp_path, state_path, open_scope=True)

    assert active_scope_report["opened"] is False
    assert active_scope_report["stop_reason"] == "active_scope_present"

    (tmp_path / ".azoth/scope-gate.json").unlink()
    _write_yaml(
        tmp_path / ".azoth/run-ledger.local.yaml",
        {
            "schema_version": 1,
            "runs": [],
            "write_claim": {
                "session_id": "previous-child",
                "expires_at": _future_expiry(),
                "acquired_at": "2026-04-25T12:00:00Z",
                "worktree_path": str(tmp_path),
            },
        },
    )

    write_claim_report = autonomous_loop.wakeup(tmp_path, state_path, open_scope=True)

    assert write_claim_report["opened"] is False
    assert write_claim_report["stop_reason"] == "active_write_claim_present"
    assert write_claim_report["write_claim"]["session_id"] == "previous-child"


def test_wakeup_current_active_loop_outranks_discovered_old_handoff(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    handoff_path = tmp_path / ".azoth/handoffs/2026-04-25-autonomous-auto-development-handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        "# Handoff\n\n## Current Truth\n\n- Completion reason: `vision_realized`\n",
        encoding="utf-8",
    )

    report = autonomous_loop.wakeup(tmp_path, state_path, open_scope=False)

    assert report["fresh_budget_required"] is False
    assert report["stop_reason"] is None
    assert report["decision"]["action"] == "ship_task"


def test_wakeup_fails_closed_for_active_session_gate(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    _write_active_session_gate(tmp_path)

    report = autonomous_loop.wakeup(tmp_path, state_path, open_scope=True)

    assert report["opened"] is False
    assert report["stop_reason"] == "active_session_gate_conflict"
    assert report["gate_status"]["blocked"] is True
    assert report["gate_status"]["active_session_id"] == "active-session"


def test_wakeup_fails_closed_for_completed_vision(tmp_path: Path) -> None:
    state_path = _state(
        tmp_path,
        iteration=3,
        autonomy_budget={
            "approval_basis": "User approved branch-local autonomous-auto testing.",
            "max_iterations": 3,
            "allowed_actions": ["ship_task"],
        },
        vision={
            "anchor": ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            "target_band": "green",
            "current_band": "green",
            "realized": True,
        },
    )

    decision_out = tmp_path / ".azoth/completed-green-decision.json"
    before = _snapshot_files(tmp_path)

    report = autonomous_loop.wakeup(
        tmp_path,
        state_path,
        open_scope=True,
        decision_out=decision_out,
    )

    assert report["opened"] is False
    assert report["stop_reason"] == "vision_realized"
    assert report["fresh_budget_required"] is True
    assert "fresh budget" in report["residual_risk"]
    assert not (tmp_path / ".azoth/scope-gate.json").exists()
    assert report["decision"]["action"] == "stop"
    assert report["next_campaign_recommendation"]["requires_fresh_approval"] is True
    assert report["next_campaign_recommendation"]["may_open_scope"] is False
    assert report["decision"]["next_campaign_recommendation"]["status"] == "advisory_only"
    assert json.loads(decision_out.read_text(encoding="utf-8")) == report["decision"]
    after = _snapshot_files(tmp_path)
    expected = dict(before)
    expected[str(decision_out.relative_to(tmp_path))] = decision_out.read_bytes()
    assert after == expected


def test_wakeup_fails_closed_for_protected_candidate_and_no_safe_candidate(
    tmp_path: Path,
) -> None:
    protected_state = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "BL-999",
                "title": "Kernel change",
                "target_layer": "M1",
                "delivery_pipeline": "governed",
            }
        ],
    )

    protected_report = autonomous_loop.wakeup(tmp_path, protected_state, open_scope=True)

    assert protected_report["opened"] is False
    assert protected_report["stop_reason"] == "protected_gate_required"

    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    no_candidate_state = _state(empty_root)

    no_candidate_report = autonomous_loop.wakeup(empty_root, no_candidate_state, open_scope=True)

    assert no_candidate_report["opened"] is False
    assert no_candidate_report["stop_reason"] == "no_safe_candidate"


def test_wakeup_cli_json_writes_report_and_decision(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state_path = _state(
        tmp_path,
        queue=[
            {
                "action": "ship_task",
                "candidate_id": "T-321",
                "title": "Ship task",
                "target_layer": "infrastructure",
                "delivery_pipeline": "standard",
            }
        ],
    )
    decision_out = tmp_path / ".azoth/cli-wakeup-decision.json"
    report_out = tmp_path / ".azoth/cli-wakeup-report.json"

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "--state",
                str(state_path),
                "wakeup",
                "--decision-out",
                str(decision_out),
                "--report-out",
                str(report_out),
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    report_file_payload = json.loads(report_out.read_text(encoding="utf-8"))
    decision_file_payload = json.loads(decision_out.read_text(encoding="utf-8"))
    assert set(
        [
            "loop_status",
            "campaign_report",
            "operator_read",
            "next_campaign_recommendation",
            "gate_status",
            "write_claim",
            "autonomy_budget",
            "alignment",
            "decision",
            "opened",
            "session_id",
            "stop_reason",
            "fresh_budget_required",
            "residual_risk",
        ]
    ).issubset(payload)
    assert payload["opened"] is False
    assert payload["decision"]["candidate_id"] == "T-321"
    assert report_file_payload == payload
    assert decision_file_payload == payload["decision"]


def test_campaign_report_observes_completed_handoff_without_continuing_current_loop(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        objective="Observer campaign",
        iteration=1,
        autonomy_budget={
            "approval_basis": "User approved observer campaign.",
            "max_iterations": 2,
            "allowed_actions": ["ship_task"],
        },
    )
    handoff_path = tmp_path / ".azoth/handoffs/2026-04-25-autonomous-auto-development-handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        "\n".join(
            [
                "# Autonomous-Auto Development Handoff - 2026-04-25",
                "",
                "## Current Truth",
                "",
                "- Autonomous loop: completed `4/4`",
                "- Completion reason: `vision_realized`",
                "- Vision band: `green -> target green`",
                "- Shared write claim: none",
                "",
                "## Known Residuals",
                "",
                "1. T-020 malformed YAML remains outside scope.",
                "2. Bootloader header is stale.",
                "",
                "## Safe Continuation Checks",
                "",
                "```bash",
                "git status --short --branch",
                "python3 scripts/autonomous_loop.py status --operator-read",
                "```",
                "",
                "## Recommended Next Development Options",
                "",
                "### Option A - Metadata Repair",
                "",
                "Why: low risk, improves operator truth.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    state_before = state_path.read_text(encoding="utf-8")
    handoff_before = handoff_path.read_text(encoding="utf-8")

    report = autonomous_loop.campaign_report(tmp_path, state_path, handoff_path=handoff_path)

    assert report["report_schema_version"] == 1
    assert report["current_loop"]["status"] == "active"
    assert report["handoff_campaign"]["observable"] is True
    assert report["handoff_campaign"]["current_truth"]["completion_reason"] == "vision_realized"
    assert report["handoff_campaign"]["completion_reason"] == "vision_realized"
    assert report["handoff_campaign"]["vision_band"] == "green -> target green"
    assert report["observation"]["fresh_budget_required"] is True
    assert report["observation"]["safe_to_continue_old_campaign"] is False
    assert report["handoff_campaign"]["known_residuals"] == [
        "T-020 malformed YAML remains outside scope.",
        "Bootloader header is stale.",
    ]
    assert report["handoff_campaign"]["safe_continuation_commands"] == [
        "git status --short --branch",
        "python3 scripts/autonomous_loop.py status --operator-read",
    ]
    assert report["handoff_campaign"]["recommended_options"][0]["title"] == (
        "Option A - Metadata Repair"
    )
    assert state_path.read_text(encoding="utf-8") == state_before
    assert handoff_path.read_text(encoding="utf-8") == handoff_before


def test_campaign_report_discovers_latest_autonomous_handoff(tmp_path: Path) -> None:
    state_path = _state(tmp_path)
    handoffs = tmp_path / ".azoth/handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)
    older = handoffs / "2026-04-24-autonomous-auto-development-handoff.md"
    latest = handoffs / "2026-04-25-autonomous-auto-development-handoff.md"
    older.write_text(
        "# Old\n\n## Current Truth\n\n- Completion reason: `older`\n",
        encoding="utf-8",
    )
    latest.write_text(
        "# New\n\n## Current Truth\n\n- Completion reason: `vision_realized`\n",
        encoding="utf-8",
    )

    report = autonomous_loop.campaign_report(tmp_path, state_path)

    assert report["handoff_campaign"]["path"].endswith(
        ".azoth/handoffs/2026-04-25-autonomous-auto-development-handoff.md"
    )
    assert report["handoff_campaign"]["completion_reason"] == "vision_realized"


def test_campaign_report_cli_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state_path = _state(tmp_path)
    handoff_path = tmp_path / ".azoth/handoffs/2026-04-25-autonomous-auto-development-handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        "# Handoff\n\n## Current Truth\n\n- Completion reason: `vision_realized`\n",
        encoding="utf-8",
    )

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "--state",
                str(state_path),
                "campaign-report",
                "--handoff",
                str(handoff_path),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["handoff_campaign"]["completion_reason"] == "vision_realized"
    assert payload["observation"]["fresh_budget_required"] is True


def test_campaign_report_fails_closed_for_missing_loop_state(tmp_path: Path) -> None:
    state_path = tmp_path / ".azoth/autonomous-loop-state.local.yaml"
    handoff_path = tmp_path / ".azoth/handoffs/2026-04-25-autonomous-auto-development-handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        "# Handoff\n\n## Current Truth\n\n- Completion reason: `vision_realized`\n",
        encoding="utf-8",
    )

    report = autonomous_loop.campaign_report(tmp_path, state_path, handoff_path=handoff_path)

    assert report["current_loop"]["observable"] is False
    assert report["current_loop"]["failure_reason"] == "missing_loop_state"
    assert report["observation"]["fresh_budget_required"] is True
    assert report["observation"]["safe_to_continue_old_campaign"] is False


def test_campaign_report_fails_closed_for_missing_handoff(tmp_path: Path) -> None:
    state_path = _state(tmp_path)

    report = autonomous_loop.campaign_report(tmp_path, state_path)

    assert report["handoff_campaign"]["observable"] is False
    assert report["handoff_campaign"]["failure_reason"] == "missing_handoff"
    assert report["observation"]["fresh_budget_required"] is True
    assert report["observation"]["safe_to_continue_old_campaign"] is False


def test_campaign_report_requires_fresh_budget_for_nonvision_handoff_completion(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    handoff_path = tmp_path / ".azoth/handoffs/2026-04-25-autonomous-auto-development-handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        "# Handoff\n\n## Current Truth\n\n- Completion reason: `budget_exhausted`\n",
        encoding="utf-8",
    )

    report = autonomous_loop.campaign_report(tmp_path, state_path, handoff_path=handoff_path)

    assert report["handoff_campaign"]["completion_reason"] == "budget_exhausted"
    assert report["observation"]["fresh_budget_required"] is True
    assert report["observation"]["safe_to_continue_old_campaign"] is False


def test_campaign_report_fails_closed_for_missing_handoff_completion_reason(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    handoff_path = tmp_path / ".azoth/handoffs/2026-04-25-autonomous-auto-development-handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        "# Handoff\n\n## Current Truth\n\n- Vision band: green\n", encoding="utf-8"
    )

    report = autonomous_loop.campaign_report(tmp_path, state_path, handoff_path=handoff_path)

    assert report["handoff_campaign"]["completion_reason"] == ""
    assert report["observation"]["fresh_budget_required"] is True
    assert report["observation"]["safe_to_continue_old_campaign"] is False


def test_operator_read_uses_active_scope_strategy_preflight_route_authority(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        history=[
            {
                "session_id": "older-session",
                "strategy_preflight": {
                    "selected_route": "ship_task",
                    "route_state": "delivery_ready",
                    "route_authority": "ship_task:delivery_ready",
                },
            }
        ],
    )
    _write_json(
        tmp_path / ".azoth/scope-gate.json",
        {
            "approved": True,
            "expires_at": _future_expiry(),
            "session_id": "active-session",
            "loop_decision": {
                "route_decision": {
                    "selected_route": "stop",
                    "route_state": "stale_route",
                },
                "strategy_preflight": {
                    "packet_type": "autonomous_auto_strategy_preflight",
                    "selected_route": "research_initiative",
                    "route_state": "campaign_strategy_preflight",
                    "route_authority": "research_initiative:campaign_strategy_preflight",
                },
            },
        },
    )

    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert read["next_likely_move"] == "blocked: active_scope_present"
    assert read["route_authority"] == "research_initiative:campaign_strategy_preflight"
    assert read["route_authority_source"] == "active_scope_strategy_preflight"


def test_operator_read_uses_loop_history_route_authority_without_active_scope(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="stopped",
        stop_reason="manual_pause",
        history=[
            {
                "session_id": "older-session",
                "strategy_preflight": {
                    "selected_route": "hydrate_task",
                    "route_state": "approved_for_hydration",
                },
            }
        ],
    )

    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert read["next_likely_move"] == "blocked: manual_pause"
    assert read["route_authority"] == "hydrate_task:approved_for_hydration"
    assert read["route_authority_source"] == "loop_history"


def test_campaign_report_adds_route_stage_risk_and_historical_handoff_readbacks(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path, last_session_id="active-session")
    handoff_path = tmp_path / ".azoth/handoffs/2026-05-05-autonomous-auto-development-handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        "\n".join(
            [
                "# Handoff",
                "",
                "## Current Truth",
                "",
                "- Completion reason: `vision_realized`",
                "- Vision band: green",
                "",
                "## Known Residuals",
                "",
                "1. Historical auto_self_heal_now suggestion is display-only.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        tmp_path / ".azoth/scope-gate.json",
        {
            "approved": True,
            "expires_at": _future_expiry(),
            "session_id": "active-session",
            "loop_decision": {
                "strategy_preflight": {
                    "selected_route": "ship_task",
                    "route_state": "delivery_ready",
                    "route_authority": "ship_task:delivery_ready",
                }
            },
        },
    )
    _write_yaml(
        tmp_path / ".azoth/run-ledger.local.yaml",
        {
            "schema_version": 1,
            "runs": [
                {
                    "run_id": "active-session",
                    "mode": "autonomous-auto",
                    "status": "active",
                    "active_stage_id": "autonomous_auto_s2_planner",
                    "pending_stage_ids": [
                        "autonomous_auto_s1_architect",
                        "autonomous_auto_s2_planner",
                    ],
                    "stage_spawns": [
                        {
                            "run_id": "active-session",
                            "stage_id": "autonomous_auto_s1_architect",
                            "subagent_type": "architect",
                            "trigger": "strategy",
                            "role_hint": "Design",
                            "dependency_summary_refs": [],
                            "spawned_at": "2026-05-06T10:00:00+00:00",
                        },
                        {
                            "run_id": "active-session",
                            "stage_id": "autonomous_auto_s2_planner",
                            "subagent_type": "planner",
                            "trigger": "plan",
                            "role_hint": "Plan",
                            "dependency_summary_refs": [],
                            "spawned_at": "2026-05-06T10:10:00+00:00",
                        },
                    ],
                    "stage_summaries": [
                        {
                            "run_id": "active-session",
                            "stage_id": "autonomous_auto_s1_architect",
                            "subagent_type": "architect",
                            "trigger": "strategy",
                            "role_hint": "Design",
                            "dependency_summary_refs": [],
                            "summary_recorded_at": "2026-05-06T10:05:00+00:00",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                        }
                    ],
                    "stages_completed": ["autonomous_auto_s1_architect"],
                }
            ],
        },
    )

    report = autonomous_loop.campaign_report(tmp_path, state_path, handoff_path=handoff_path)
    stages = {
        item["stage_id"]: item for item in report["stage_evidence_states"]["stages"]
    }

    assert report["report_schema_version"] == 1
    assert report["handoff_campaign"]["completion_reason"] == "vision_realized"
    assert report["current_route_authority"] == {
        "authority": "ship_task:delivery_ready",
        "source": "active_scope_strategy_preflight",
        "session_id": "active-session",
    }
    assert stages["autonomous_auto_s1_architect"]["state"] == (
        "complete_with_paired_evidence"
    )
    assert stages["autonomous_auto_s2_planner"]["state"] == "in_progress_pending_summary"
    assert report["historical_handoff"]["display_only"] is True
    assert report["historical_handoff"]["can_open_auto_self_heal_now"] is False
    assert report["historical_handoff"]["can_set_next_safe_action"] is False
    assert report["historical_handoff_authority"]["current_authority"] is False
    assert any(
        item["risk"] == "stage_spawn_pending_summary"
        for item in report["structured_residual_risks"]
    )
    assert "auto_self_heal_now" not in json.dumps(report["next_campaign_recommendation"])


def _write_stage_evidence_run(tmp_path: Path, run: dict) -> None:
    _write_yaml(
        tmp_path / ".azoth/run-ledger.local.yaml",
        {"schema_version": 1, "runs": [run]},
    )


def test_stage_evidence_marks_blocking_summary_disposition(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path, last_session_id="run-blocking")
    _write_stage_evidence_run(
        tmp_path,
        {
            "run_id": "run-blocking",
            "mode": "autonomous-auto",
            "status": "active",
            "pending_stage_ids": ["autonomous_auto_s4_evaluator"],
            "stage_spawns": [
                {
                    "run_id": "run-blocking",
                    "stage_id": "autonomous_auto_s4_evaluator",
                    "subagent_type": "evaluator",
                    "trigger": "evaluate",
                    "spawned_at": "2026-05-06T10:00:00+00:00",
                }
            ],
            "stage_summaries": [
                {
                    "run_id": "run-blocking",
                    "stage_id": "autonomous_auto_s4_evaluator",
                    "subagent_type": "evaluator",
                    "trigger": "evaluate",
                    "summary_recorded_at": "2026-05-06T10:05:00+00:00",
                    "summary_status": "complete",
                    "summary_disposition": "request-changes",
                }
            ],
        },
    )

    report = autonomous_loop.campaign_report(tmp_path, state_path)
    stage = report["stage_evidence_states"]["stages"][0]

    assert stage["state"] == "summary_blocking"
    assert stage["summary_status"] == "complete"
    assert stage["summary_disposition"] == "request-changes"


def test_stage_evidence_rejects_stale_or_mismatched_summary(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path, last_session_id="run-stale")
    _write_stage_evidence_run(
        tmp_path,
        {
            "run_id": "run-stale",
            "mode": "autonomous-auto",
            "status": "active",
            "pending_stage_ids": ["autonomous_auto_s3_builder"],
            "stage_spawns": [
                {
                    "run_id": "run-stale",
                    "stage_id": "autonomous_auto_s3_builder",
                    "subagent_type": "builder",
                    "trigger": "implementation",
                    "spawned_at": "2026-05-06T10:10:00+00:00",
                }
            ],
            "stage_summaries": [
                {
                    "run_id": "run-stale",
                    "stage_id": "autonomous_auto_s3_builder",
                    "subagent_type": "planner",
                    "trigger": "implementation",
                    "summary_recorded_at": "2026-05-06T10:05:00+00:00",
                    "summary_status": "complete",
                    "summary_disposition": "approved",
                }
            ],
            "stages_completed": ["autonomous_auto_s3_builder"],
        },
    )

    report = autonomous_loop.campaign_report(tmp_path, state_path)
    stage = report["stage_evidence_states"]["stages"][0]

    assert stage["state"] == "summary_mismatch_or_stale"
    assert stage["summary_counts_for_completion"] is False


def test_stage_evidence_emits_paired_completion_contract_state(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path, last_session_id="run-complete")
    _write_stage_evidence_run(
        tmp_path,
        {
            "run_id": "run-complete",
            "mode": "autonomous-auto",
            "status": "active",
            "pending_stage_ids": ["autonomous_auto_s1_architect"],
            "stage_spawns": [
                {
                    "run_id": "run-complete",
                    "stage_id": "autonomous_auto_s1_architect",
                    "subagent_type": "architect",
                    "trigger": "strategy",
                    "spawned_at": "2026-05-06T10:00:00+00:00",
                }
            ],
            "stage_summaries": [
                {
                    "run_id": "run-complete",
                    "stage_id": "autonomous_auto_s1_architect",
                    "subagent_type": "architect",
                    "trigger": "strategy",
                    "summary_recorded_at": "2026-05-06T10:05:00+00:00",
                    "summary_status": "complete",
                    "summary_disposition": "approved",
                }
            ],
            "stages_completed": ["autonomous_auto_s1_architect"],
        },
    )

    report = autonomous_loop.campaign_report(tmp_path, state_path)
    stage = report["stage_evidence_states"]["stages"][0]

    assert stage["state"] == "complete_with_paired_evidence"
    assert stage["summary_counts_for_completion"] is True


def test_campaign_report_route_authority_fails_closed_when_unavailable(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path, history=[])

    report = autonomous_loop.campaign_report(tmp_path, state_path)
    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert report["current_route_authority"]["authority"] == "unavailable_fail_closed"
    assert read["route_authority"] == "unavailable_fail_closed"


def _write_lifecycle_initiative_bank(tmp_path: Path) -> Path:
    path = tmp_path / ".azoth/initiative-banks/INI-AUTO-001.yaml"
    _write_yaml(
        path,
        {
            "schema_version": 1,
            "bank_type": "initiative",
            "initiative_id": "INI-AUTO-001",
            "title": "Autonomous initiative lifecycle orchestration",
            "status": "active_refinement",
            "owner": "codex",
            "source_proposal_refs": [
                ".azoth/proposals/autonomous-initiative-lifecycle-orchestration.yaml"
            ],
            "local_findings": [
                {
                    "finding_id": "lf-auto-001-005",
                    "status": "active",
                    "summary": "Route initiatives from a normalized lifecycle report.",
                }
            ],
            "candidate_slices": [
                {
                    "candidate_id": "slice-auto-001-a",
                    "proposed_task_id": "T-AUTO-A",
                    "title": "Initiative intake and seed contract",
                    "initiative_ref": "INI-AUTO-001",
                    "status": "candidate",
                    "target_layer": "infrastructure",
                    "delivery_pipeline": "standard",
                    "summary": "Define safe initiative intake before hydration.",
                    "acceptance_criteria": [
                        "Raw initiative input is classified as planning/discovery.",
                        "Protected-scope expansion fails closed.",
                    ],
                    "research_evidence_refs": [
                        "scripts/autonomous_loop.py",
                        "scripts/planning_bank_validate.py",
                    ],
                    "known_non_goals": [
                        "Do not create backlog items.",
                        "Do not hydrate roadmap task specs.",
                    ],
                    "open_questions": [],
                    "hydration_plan": {
                        "proposed_title": "Initiative intake and seed contract",
                        "scaffold_command": "python3 scripts/roadmap_scaffold.py --hydrate-task T-AUTO-A",
                    },
                }
            ],
            "readiness": {
                "evaluated_at": "2026-04-25T12:10:00+00:00",
                "source_bank_ref": ".azoth/initiative-banks/INI-AUTO-001.yaml",
                "readiness_status": "continue_research",
                "freshness_status": "current_as_of_2026_04_25",
                "candidate_first_slice": "slice-auto-001-a",
                "acceptance_criteria_status": "draft",
                "non_goals_status": "draft",
                "next_readiness_gate": "refine_intake_contract_before_hydration",
                "hydration_recommendation": "Do not hydrate yet; refine the intake contract first.",
                "human_decision": "approved",
                "approval_scope": "planning_seed_only_no_hydration",
                "approval_basis": "Operator approved planning-only autonomous-auto exploration.",
            },
            "hydration_history": [],
        },
    )
    return path


def _write_lifecycle_reflection(tmp_path: Path) -> Path:
    path = (
        tmp_path
        / ".azoth/inbox/session-reflection-2026-04-25-autonomous-auto-campaign-report.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "id": "SRF-2026-04-25-AUTOAUTO-CAMPAIGN-REPORT-IMPLICATIONS",
                "severity": "high",
                "summary": "Campaign reports must include implications, quality, scores, and next steps.",
                "recommended_action": "Refine the report contract with evaluator-score visibility.",
                "tags": ["autonomous-auto", "campaign-report", "eval-score"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_hydrated_task_artifacts(tmp_path: Path, task_id: str) -> None:
    _write_yaml(
        tmp_path / ".azoth/roadmap-specs/v0.2.0" / f"{task_id}.yaml",
        {"id": task_id, "title": "Hydrated task"},
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap.yaml",
        {"tasks": [{"id": task_id, "spec_ref": f".azoth/roadmap-specs/v0.2.0/{task_id}.yaml"}]},
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        [{"id": task_id, "status": "pending"}],
    )


def _write_completed_task_artifacts(tmp_path: Path, task_id: str) -> None:
    _write_yaml(
        tmp_path / ".azoth/roadmap-specs/v0.2.0" / f"{task_id}.yaml",
        {"id": task_id, "title": "Hydrated task"},
    )
    _write_yaml(
        tmp_path / ".azoth/roadmap.yaml",
        {
            "versions": [
                {
                    "id": "v0.2.0-p3",
                    "completed_tasks": [
                        {
                            "id": task_id,
                            "title": "Hydrated task",
                            "completed_date": "2026-04-25",
                        }
                    ],
                }
            ]
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        [{"id": task_id, "status": "complete", "completed_date": "2026-04-25"}],
    )


def test_lifecycle_report_json_includes_discoverability_spine_without_writes(
    tmp_path: Path,
) -> None:
    state_path = _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-d",
            "proposed_task_id": "T-026",
            "title": "Durable autonomous-auto wakeup driver",
            "initiative_ref": "INI-AUTO-001",
            "status": "hydrated",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Completed wakeup slice must not silently continue.",
            "acceptance_criteria": ["Wakeup checks gates before opening work."],
            "research_evidence_refs": ["scripts/autonomous_loop.py"],
            "known_non_goals": ["Do not create a daemon."],
            "open_questions": [],
            "hydration_plan": {
                "hydrated_task_ref": "T-026",
                "hydrated_spec_ref": ".azoth/roadmap-specs/v0.2.0/T-026.yaml",
                "hydrated_at": "2026-04-25T19:34:23Z",
            },
        }
    )
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-e",
            "proposed_task_id": "T-027",
            "title": "Initiative lifecycle evaluator and discoverability spine",
            "initiative_ref": "INI-AUTO-001",
            "status": "hydrated",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Read-only lifecycle report.",
            "acceptance_criteria": ["List lifecycle state and next safe actions."],
            "research_evidence_refs": ["scripts/autonomous_loop.py"],
            "known_non_goals": ["Do not mutate planning state."],
            "open_questions": [],
            "hydration_plan": {
                "hydrated_task_ref": "T-027",
                "hydrated_spec_ref": ".azoth/roadmap-specs/v0.2.0/T-027.yaml",
                "hydrated_at": "2026-04-25T20:14:59Z",
            },
        }
    )
    doc["readiness"].update(
        {
            "candidate_first_slice": "slice-auto-001-e",
            "approval_scope": "hydration_specific_slice_auto_001_e",
        }
    )
    doc["hydration_history"] = [
        {
            "candidate_slice_ref": "slice-auto-001-d",
            "task_ref": "T-026",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-026.yaml",
            "session_id": "2026-04-25-autonomous-auto-t-026-3",
        },
        {
            "candidate_slice_ref": "slice-auto-001-e",
            "task_ref": "T-027",
            "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-027.yaml",
            "session_id": "2026-04-25-autonomous-auto-t-027-3",
        },
    ]
    _write_yaml(initiative_path, doc)
    _write_completed_task_artifacts(tmp_path, "T-026")
    _write_hydrated_task_artifacts(tmp_path, "T-027")
    _write_yaml(
        tmp_path / ".azoth/roadmap.yaml",
        {
            "tasks": [
                {"id": "T-027", "spec_ref": ".azoth/roadmap-specs/v0.2.0/T-027.yaml"},
            ],
            "versions": [
                {
                    "id": "v0.2.0-p3",
                    "completed_tasks": [
                        {
                            "id": "T-026",
                            "title": "Durable autonomous-auto wakeup driver",
                            "completed_date": "2026-04-25",
                        }
                    ],
                }
            ],
        },
    )
    _write_yaml(
        tmp_path / ".azoth/backlog.yaml",
        [
            {"id": "T-026", "status": "complete", "completed_date": "2026-04-25"},
            {"id": "T-027", "status": "pending"},
        ],
    )
    _write_json(
        tmp_path / ".azoth/scope-gate.json",
        {
            "session_id": "scope-session",
            "approved": True,
            "scope_status": "active",
            "expires_at": _future_expiry(),
            "pipeline_command": "autonomous-auto",
        },
    )
    _write_active_session_gate(tmp_path, session_id="other-session")
    _write_json(
        tmp_path / ".azoth/pipeline-gate.json",
        {
            "session_id": "scope-session",
            "approved": True,
            "expires_at": _future_expiry(),
            "opened_at": "2026-04-25T20:00:00Z",
            "pipeline_command": "autonomous-auto",
        },
    )
    _write_yaml(
        tmp_path / ".azoth/run-ledger.local.yaml",
        {
            "write_claim": {
                "session_id": "claim-session",
                "expires_at": _future_expiry(),
                "worktree_path": str(tmp_path),
                "branch": "codex/autonomous-roadmap-self-development",
            }
        },
    )
    before = _snapshot_files(tmp_path)

    report = autonomous_loop.build_initiative_lifecycle_report(
        tmp_path,
        initiative_path,
        state_path=state_path,
        candidate_id="slice-auto-001-e",
    )

    assert report["initiative"]["source_proposal_refs"] == [
        ".azoth/proposals/autonomous-initiative-lifecycle-orchestration.yaml"
    ]
    assert report["source_artifacts"]["initiative_bank_count"] == 1
    assert report["initiative_banks"][0]["initiative_id"] == "INI-AUTO-001"
    assert report["initiative_banks"][0]["candidate_count"] == 3
    assert {row["candidate_id"] for row in report["candidate_slices"]} == {
        "slice-auto-001-a",
        "slice-auto-001-d",
        "slice-auto-001-e",
    }
    t026 = next(
        row for row in report["candidate_slices"] if row["candidate_id"] == "slice-auto-001-d"
    )
    assert t026["hydrated_task_ref"] == "T-026"
    assert t026["planning_vs_executable_status"] == "completed_hydrated_task"
    assert t026["repeat_hydration_blocked"] is True
    t027 = next(
        row for row in report["candidate_slices"] if row["candidate_id"] == "slice-auto-001-e"
    )
    assert t027["planning_vs_executable_status"] == "executable_hydrated_task"
    assert report["hydration_history"][0]["task_complete"] is True
    assert report["readiness_blockers"]
    assert report["selected_route_decision"]["selected_route"] == "ship_task"
    assert report["evaluator_evidence"]["status"] == "not_recorded"
    assert report["campaign_context"]["campaign_report"]["report_schema_version"] == 1
    assert report["gate_status"]["active_scope"]["session_id"] == "scope-session"
    assert report["gate_status"]["active_session_conflict"]["session_id"] == "other-session"
    assert report["gate_status"]["pipeline_gate"]["approved"] is True
    assert report["gate_status"]["active_run"]["present"] is False
    assert report["write_claim"]["held"] is True
    assert report["protected_gate_status"]["required"] is False
    assert any(item["action"] == "ship_task" for item in report["next_safe_actions"])
    assert any(item["action"] == "hydrate_task" for item in report["blocked_actions"])
    assert any("T-026" in item["risk"] for item in report["residual_risks"])
    assert all("basis" in item for item in report["residual_risks"])
    assert _snapshot_files(tmp_path) == before


def test_lifecycle_report_completed_t026_blocks_repeat_hydration_and_hidden_shipping(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["candidate_id"] = "slice-auto-001-d"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-026"
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["readiness"]["candidate_first_slice"] = "slice-auto-001-d"
    doc["readiness"]["approval_scope"] = "hydration_specific_slice_auto_001_d"
    _write_yaml(initiative_path, doc)
    _write_completed_task_artifacts(tmp_path, "T-026")

    report = autonomous_loop.build_initiative_lifecycle_report(tmp_path, initiative_path)

    assert report["readiness"]["candidate_task_complete"] is True
    assert report["selected_route_decision"]["selected_route"] == "stop"
    assert all(item["action"] != "ship_task" for item in report["next_safe_actions"])
    assert {item["action"] for item in report["blocked_actions"]} >= {
        "hydrate_task",
        "ship_task",
    }
    assert any("hidden continuation" in item["risk"] for item in report["residual_risks"])


def test_lifecycle_report_reuses_readiness_report_and_reflection_without_writes(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    reflection_path = _write_lifecycle_reflection(tmp_path)
    initiative_before = initiative_path.read_text(encoding="utf-8")
    reflection_before = reflection_path.read_text(encoding="utf-8")

    report = autonomous_loop.build_initiative_lifecycle_report(
        tmp_path,
        initiative_path,
        reflection_path=reflection_path,
    )

    assert report["report_type"] == "initiative_lifecycle_report"
    assert report["scope_boundary"]["read_only"] is True
    assert report["readiness"]["ready_to_hydrate"] is False
    assert report["readiness"]["approval_basis"] == (
        "Operator approved planning-only autonomous-auto exploration."
    )
    assert report["source_artifacts"]["reflection"]["observable"] is True
    assert report["quality"]["evaluator_scores"][0]["score"] is None
    assert report["next_safe_actions"][0]["action"] == "refine_proposal"
    assert any(item["action"] == "hydrate_task" for item in report["blocked_actions"])
    assert initiative_path.read_text(encoding="utf-8") == initiative_before
    assert reflection_path.read_text(encoding="utf-8") == reflection_before


def test_lifecycle_report_cli_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    reflection_path = _write_lifecycle_reflection(tmp_path)

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "lifecycle-report",
                "--initiative",
                str(initiative_path),
                "--reflection",
                str(reflection_path),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["initiative"]["initiative_id"] == "INI-AUTO-001"
    assert payload["candidate"]["candidate_id"] == "slice-auto-001-a"
    assert payload["quality"]["reflection_observable"] is True


def test_lifecycle_report_cli_plain_text(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "lifecycle-report",
                "--initiative",
                str(initiative_path),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out

    assert "Autonomous-auto initiative lifecycle report" in output
    assert "Readiness: continue_research (hydrate=False)" in output
    assert "Human decision: approved (planning_seed_only_no_hydration)" in output
    assert "Evaluator evidence: not_recorded" in output
    assert "Gate summary: scope=none, session_conflict=none, pipeline=none" in output
    assert "Write claim: none" in output
    assert "Blocked actions: hydrate_task, ship_task" in output
    assert "Residual risks:" in output


def test_lifecycle_report_missing_reflection_is_observable_false_and_read_only(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    missing_reflection = tmp_path / ".azoth/inbox/missing.jsonl"
    initiative_before = initiative_path.read_text(encoding="utf-8")

    report = autonomous_loop.build_initiative_lifecycle_report(
        tmp_path,
        initiative_path,
        reflection_path=missing_reflection,
    )

    assert report["source_artifacts"]["reflection"]["observable"] is False
    assert report["source_artifacts"]["reflection"]["failure_reasons"] == ["missing_reflection"]
    assert report["quality"]["meaning"].startswith("No reflection artifact")
    assert initiative_path.read_text(encoding="utf-8") == initiative_before


def test_lifecycle_report_plain_text_keeps_hydration_approval_caveat_visible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["readiness"]["readiness_status"] = "ready_to_hydrate"
    doc["readiness"]["acceptance_criteria_status"] = "present"
    doc["readiness"]["non_goals_status"] = "present"
    doc["readiness"]["next_readiness_gate"] = "hydrate_after_explicit_approval"
    doc["readiness"]["hydration_recommendation"] = "Hydrate only with explicit approval."
    doc["readiness"]["approval_scope"] = "hydration_specific_slice_auto_001_a"
    _write_yaml(initiative_path, doc)

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "lifecycle-report",
                "--initiative",
                str(initiative_path),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out

    assert "Next safe actions: hydrate_task" in output
    assert "explicit hydration approval_basis remains required at the write edge" in output


def test_lifecycle_report_seed_only_approval_never_routes_hydrate_or_ship(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["readiness"]["readiness_status"] = "ready_to_hydrate"
    doc["readiness"]["next_readiness_gate"] = "hydrate_after_explicit_approval"
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-023"
    _write_yaml(initiative_path, doc)

    report = autonomous_loop.build_initiative_lifecycle_report(tmp_path, initiative_path)

    assert report["readiness"]["approval_scope"] == "planning_seed_only_no_hydration"
    assert report["next_safe_actions"][0]["action"] == "research_initiative"
    assert {item["action"] for item in report["blocked_actions"]} == {"hydrate_task", "ship_task"}
    assert all(
        item["action"] not in {"hydrate_task", "ship_task"} for item in report["next_safe_actions"]
    )


def test_lifecycle_report_hydrated_candidate_routes_to_ship_task(tmp_path: Path) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-023"
    doc["readiness"]["readiness_status"] = "continue_research"
    doc["readiness"]["next_readiness_gate"] = "ship_hydrated_task_T_023"
    doc["readiness"]["approval_scope"] = "hydration_specific_slice_auto_001_a"
    doc["readiness"]["hydration_recommendation"] = (
        "slice-auto-001-a is hydrated as T-023; do not hydrate it again."
    )
    _write_yaml(initiative_path, doc)

    report = autonomous_loop.build_initiative_lifecycle_report(tmp_path, initiative_path)

    assert report["next_safe_actions"][0]["action"] == "ship_task"
    assert report["next_safe_actions"][0]["basis"] == "candidate is hydrated as T-023"
    assert report["blocked_actions"] == [
        {
            "action": "hydrate_task",
            "reason": (
                "candidate.status is hydrated; no hydration action remains; "
                "readiness.readiness_status must be ready_to_hydrate"
            ),
        }
    ]
    assert report["operator_implications"][0]["meaning"].startswith(
        "The selected candidate is hydrated"
    )


def test_lifecycle_report_completed_hydrated_task_blocks_stale_ship_task(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-AUTO-A"
    doc["readiness"]["approval_scope"] = "hydration_specific_slice_auto_001_a"
    _write_yaml(initiative_path, doc)
    _write_completed_task_artifacts(tmp_path, "T-AUTO-A")

    report = autonomous_loop.build_initiative_lifecycle_report(tmp_path, initiative_path)
    capsule = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)

    assert report["readiness"]["candidate_task_complete"] is True
    assert all(item["action"] != "ship_task" for item in report["next_safe_actions"])
    assert any(item["action"] == "ship_task" for item in report["blocked_actions"])
    assert capsule["selected_route"] == "stop"
    assert capsule["route_state"] == "completed_or_stale_campaign"
    assert capsule["readiness_evidence"]["candidate_task_complete"] is True


def test_route_decision_capsule_completed_candidate_can_route_to_refresh_with_fresh_research_budget(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-AUTO-A"
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-g",
            "proposed_task_id": "T-AUTO-G",
            "title": "Lifecycle route refresh-state repair",
            "initiative_ref": "INI-AUTO-001",
            "status": "candidate",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Refresh route state after a completed candidate.",
            "acceptance_criteria": ["Refresh candidate readiness before hydration."],
            "research_evidence_refs": ["scripts/autonomous_loop.py"],
            "known_non_goals": ["Do not hydrate or ship the completed candidate."],
            "open_questions": ["Which route state should represent refresh?"],
        }
    )
    doc["readiness"].update(
        {
            "candidate_first_slice": "slice-auto-001-g",
            "approval_scope": "research_to_readiness_slice_auto_001_g",
            "approval_basis": (
                "Operator approved research-to-readiness for INI-AUTO-001 slice-auto-001-g."
            ),
        }
    )
    _write_yaml(initiative_path, doc)
    _write_completed_task_artifacts(tmp_path, "T-AUTO-A")

    capsule = autonomous_loop.build_initiative_route_decision_capsule(
        tmp_path,
        initiative_path,
        candidate_id="slice-auto-001-a",
    )

    assert capsule["selected_route"] == "research_initiative"
    assert capsule["route_state"] == "refresh_initiative_candidate"
    assert capsule["approval_needed"] == "covered by research-to-readiness scope only"
    assert capsule["readiness_evidence"]["candidate_id"] == "slice-auto-001-a"
    assert capsule["readiness_evidence"]["candidate_task_complete"] is True
    assert capsule["readiness_evidence"]["refresh_candidate_id"] == "slice-auto-001-g"
    assert {item["action"] for item in capsule["blocked_actions"]} >= {
        "hydrate_task",
        "ship_task",
    }
    assert all(item["action"] != "open_next_without_budget" for item in capsule["blocked_actions"])
    assert "fresh research-to-readiness approval" in capsule["ux_anchor_rationale"]["route_basis"]


def test_route_decision_capsule_completed_candidate_with_refresh_scope_still_stops_without_active_budget(
    tmp_path: Path,
) -> None:
    _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        vision={"current_band": "green", "target_band": "green", "realized": True},
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-AUTO-A"
    doc["readiness"].update(
        {
            "candidate_first_slice": "slice-auto-001-g",
            "approval_scope": "research_to_readiness_slice_auto_001_g",
            "approval_basis": "Operator approved research-to-readiness for slice-auto-001-g.",
        }
    )
    _write_yaml(initiative_path, doc)
    _write_completed_task_artifacts(tmp_path, "T-AUTO-A")

    capsule = autonomous_loop.build_initiative_route_decision_capsule(
        tmp_path,
        initiative_path,
        candidate_id="slice-auto-001-a",
    )

    assert capsule["selected_route"] == "stop"
    assert capsule["route_state"] == "completed_or_stale_campaign"
    assert any(item["action"] == "open_next_without_budget" for item in capsule["blocked_actions"])


def test_lifecycle_route_strategy_preflight_candidate_survives_completed_old_loop(
    tmp_path: Path,
) -> None:
    _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        vision={"current_band": "green", "target_band": "green", "realized": True},
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "complete"
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-h",
            "proposed_task_id": "T-AUTO-H",
            "title": "Autonomous campaign strategy budget repair",
            "initiative_ref": "INI-AUTO-001",
            "status": "candidate",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Repair pre-open strategy budget before another campaign opens.",
            "acceptance_criteria": [
                "Recommendation and lifecycle-route are reconciled before open-next."
            ],
            "research_evidence_refs": ["scripts/autonomous_loop.py"],
            "known_non_goals": ["Do not hydrate or ship from the strategy child."],
            "open_questions": ["Which preflight surface owns the refusal?"],
        }
    )
    doc["readiness"].update(
        {
            "readiness_status": "continue_research",
            "candidate_first_slice": "slice-auto-001-h",
            "next_candidate_ref": "slice-auto-001-h",
            "next_readiness_gate": "research_strategy_preflight_before_init_or_open_next",
            "hydration_recommendation": (
                "Slice-auto-001-h is research-only until strategy-preflight behavior is "
                "specified and tested."
            ),
            "approval_scope": "research_to_readiness_slice_auto_001_h",
            "approval_basis": (
                "Operator approved the Autonomous Campaign Strategy Budget Repair campaign "
                "for INI-AUTO-001 slice-auto-001-h."
            ),
        }
    )
    _write_yaml(initiative_path, doc)

    capsule = autonomous_loop.build_initiative_route_decision_capsule(
        tmp_path,
        initiative_path,
        candidate_id="slice-auto-001-h",
    )

    assert capsule["selected_route"] == "research_initiative"
    assert capsule["route_state"] == "campaign_strategy_preflight"
    assert capsule["approval_needed"] == "covered by research-to-readiness scope only"
    assert capsule["readiness_evidence"]["candidate_id"] == "slice-auto-001-h"
    assert capsule["readiness_evidence"]["strategy_preflight_required"] is True
    assert capsule["readiness_evidence"]["fresh_research_to_readiness_approval"] is True
    assert "completed loop" in capsule["ux_anchor_rationale"]["route_basis"]
    assert {item["action"] for item in capsule["blocked_actions"]} >= {
        "hydrate_task",
        "ship_task",
        "open_next_without_strategy_preflight",
    }
    assert all(item["action"] != "open_next_without_budget" for item in capsule["blocked_actions"])


def test_decide_next_can_open_strategy_preflight_research_from_completed_old_loop(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="active",
        autonomy_budget={
            "approval_basis": (
                "Operator approved research_to_readiness_slice_auto_001_h strategy "
                "preflight repair."
            ),
            "max_iterations": 3,
            "allowed_actions": ["research_initiative", "capture_self_improvement"],
            "replay_threshold": 1,
            "stop_conditions": ["protected_gate_required"],
        },
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "complete"
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-h",
            "proposed_task_id": "T-AUTO-H",
            "title": "Autonomous campaign strategy budget repair",
            "initiative_ref": "INI-AUTO-001",
            "status": "candidate",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Repair pre-open strategy budget before another campaign opens.",
            "acceptance_criteria": [
                "Recommendation and lifecycle-route are reconciled before open-next."
            ],
            "research_evidence_refs": ["scripts/autonomous_loop.py"],
            "known_non_goals": ["Do not hydrate or ship from the strategy child."],
            "open_questions": ["Which preflight surface owns the refusal?"],
        }
    )
    doc["readiness"].update(
        {
            "readiness_status": "continue_research",
            "candidate_first_slice": "slice-auto-001-h",
            "next_candidate_ref": "slice-auto-001-h",
            "next_readiness_gate": "research_strategy_preflight_before_init_or_open_next",
            "hydration_recommendation": (
                "Slice-auto-001-h is research-only until strategy-preflight behavior is "
                "specified and tested."
            ),
            "approval_scope": "research_to_readiness_slice_auto_001_h",
            "approval_basis": (
                "Operator approved the Autonomous Campaign Strategy Budget Repair campaign "
                "for INI-AUTO-001 slice-auto-001-h."
            ),
        }
    )
    _write_yaml(initiative_path, doc)

    decision = autonomous_loop.decide_next(tmp_path, state_path)
    read = autonomous_loop.operator_read(tmp_path, state_path)

    assert decision["action"] == "research_initiative"
    assert decision["candidate_id"] == "INI-AUTO-001"
    assert decision["route_decision"]["route_state"] == "campaign_strategy_preflight"
    assert decision["route_decision"]["selected_route"] == "research_initiative"
    assert read["route_authority"] == "research_initiative:campaign_strategy_preflight"


def test_strategy_preflight_handoff_stops_for_hydration_approval_instead_of_research_loop(
    tmp_path: Path,
) -> None:
    state_path = _state(
        tmp_path,
        status="active",
        autonomy_budget={
            "approval_basis": (
                "Operator approved research_to_readiness_slice_auto_001_h strategy "
                "preflight repair."
            ),
            "max_iterations": 3,
            "allowed_actions": ["research_initiative", "capture_self_improvement"],
            "replay_threshold": 1,
            "stop_conditions": ["protected_gate_required"],
        },
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "complete"
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-h",
            "proposed_task_id": "T-AUTO-H",
            "title": "Autonomous campaign strategy budget repair",
            "initiative_ref": "INI-AUTO-001",
            "status": "candidate",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Repair pre-open strategy budget before another campaign opens.",
            "acceptance_criteria": [
                "Recommendation and lifecycle-route are reconciled before open-next.",
            ],
            "research_evidence_refs": ["scripts/autonomous_loop.py"],
            "known_non_goals": ["Do not hydrate or ship from the strategy child."],
            "open_questions": [],
            "hydration_plan": {
                "proposed_title": "Autonomous campaign strategy budget repair",
                "approval_scope_required": "hydration_specific_slice_auto_001_h",
                "scaffold_command": (
                    "python3 scripts/roadmap_scaffold.py --source "
                    "initiative-bank-INI-AUTO-001-slice-auto-001-h"
                ),
            },
        }
    )
    doc["readiness"].update(
        {
            "readiness_status": "continue_research",
            "candidate_first_slice": "slice-auto-001-h",
            "next_candidate_ref": "slice-auto-001-h",
            "next_readiness_gate": (
                "request_or_record_hydration_specific_slice_auto_001_h_approval"
            ),
            "hydration_recommendation": (
                "Slice-auto-001-h has a plan-only hydration handoff; request fresh "
                "hydration approval before writes."
            ),
            "approval_scope": "research_to_readiness_slice_auto_001_h",
            "approval_basis": (
                "Operator approved research only for INI-AUTO-001 slice-auto-001-h."
            ),
            "acceptance_criteria_status": "stable",
            "non_goals_status": "stable",
        }
    )
    _write_yaml(initiative_path, doc)

    capsule = autonomous_loop.build_initiative_route_decision_capsule(
        tmp_path,
        initiative_path,
        candidate_id="slice-auto-001-h",
    )
    decision = autonomous_loop.decide_next(tmp_path, state_path)

    assert capsule["selected_route"] == "stop"
    assert capsule["route_state"] == "awaiting_hydration_approval"
    assert capsule["approval_needed"] == "hydration_specific_slice_auto_001_h"
    assert any(item["action"] == "research_initiative" for item in capsule["blocked_actions"])
    assert decision["action"] == "stop"
    assert decision["stop_reason"] == "lifecycle_route_stop_awaiting_hydration_approval"
    assert decision["route_decision"]["approval_needed"] == "hydration_specific_slice_auto_001_h"


def test_lifecycle_route_plain_text_exposes_refresh_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-AUTO-A"
    doc["candidate_slices"].append(
        {
            "candidate_id": "slice-auto-001-g",
            "proposed_task_id": "T-AUTO-G",
            "title": "Lifecycle route refresh-state repair",
            "initiative_ref": "INI-AUTO-001",
            "status": "candidate",
            "target_layer": "infrastructure",
            "delivery_pipeline": "standard",
            "summary": "Refresh route state after a completed candidate.",
            "acceptance_criteria": ["Refresh candidate readiness before hydration."],
            "research_evidence_refs": ["scripts/autonomous_loop.py"],
            "known_non_goals": ["Do not hydrate or ship the completed candidate."],
            "open_questions": ["Which route state should represent refresh?"],
        }
    )
    doc["readiness"].update(
        {
            "candidate_first_slice": "slice-auto-001-g",
            "approval_scope": "research_to_readiness_slice_auto_001_g",
            "approval_basis": "Operator approved research-to-readiness for slice-auto-001-g.",
        }
    )
    _write_yaml(initiative_path, doc)
    _write_completed_task_artifacts(tmp_path, "T-AUTO-A")

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "lifecycle-route",
                "--initiative",
                str(initiative_path),
                "--candidate-id",
                "slice-auto-001-a",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out

    assert "Selected route: research_initiative (refresh_initiative_candidate)" in output
    assert "Approval needed: covered by research-to-readiness scope only" in output
    assert "Blocked actions: hydrate_task, ship_task" in output


def test_route_decision_capsule_delivery_ready_requires_hydrated_task_artifacts(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["status"] = "hydrated"
    doc["candidate_slices"][0]["proposed_task_id"] = "T-AUTO-A"
    doc["readiness"]["approval_scope"] = "hydration_specific_slice_auto_001_a"
    _write_yaml(initiative_path, doc)

    blocked = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)
    assert blocked["selected_route"] == "stop"
    assert blocked["route_state"] == "completed_or_stale_campaign"
    assert any(item["action"] == "ship_task" for item in blocked["blocked_actions"])

    _write_hydrated_task_artifacts(tmp_path, "T-AUTO-A")
    capsule = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)

    assert capsule["selected_route"] == "ship_task"
    assert capsule["route_state"] == "delivery_ready"
    assert set(capsule["route_table_coverage"]) == set(autonomous_loop.ROUTE_TABLE_STATES)
    for field in (
        "selected_route",
        "rejected_alternatives",
        "source_artifacts",
        "readiness_evidence",
        "ux_anchor_rationale",
        "protected_stops",
        "blocked_actions",
        "approval_needed",
        "evaluator_scores",
    ):
        assert field in capsule
    assert any(item["action"] == "hydrate_task" for item in capsule["blocked_actions"])


def test_route_decision_capsule_approved_hydration_requires_exact_slice_command(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    candidate = doc["candidate_slices"][0]
    candidate["candidate_id"] = "slice-auto-001-b"
    candidate["proposed_task_id"] = "T-024"
    candidate["status"] = "candidate"
    candidate["hydration_plan"]["scaffold_command"] = (
        "python3 scripts/roadmap_scaffold.py --source initiative-bank-INI-AUTO-001-slice-auto-001-b"
    )
    doc["readiness"].update(
        {
            "readiness_status": "ready_to_hydrate",
            "freshness_status": "current_as_of_2026_04_25",
            "candidate_first_slice": "slice-auto-001-b",
            "approval_scope": "hydration_specific_slice_auto_001_b",
            "approval_basis": (
                "Operator approved hydration for INI-AUTO-001 slice-auto-001-b "
                "with the exact scaffold command."
            ),
            "acceptance_criteria_status": "present",
            "non_goals_status": "present",
        }
    )
    _write_yaml(initiative_path, doc)

    capsule = autonomous_loop.build_initiative_route_decision_capsule(
        tmp_path, initiative_path, candidate_id="slice-auto-001-b"
    )

    assert capsule["selected_route"] == "hydrate_task"
    assert capsule["route_state"] == "approved_for_hydration"
    assert capsule["approval_needed"] == "hydration_specific_slice_auto_001_b"
    assert capsule["readiness_evidence"]["approval_basis_present"] is True


def test_route_decision_capsule_seed_only_and_self_capture_fail_closed(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)

    seed_only = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)
    assert seed_only["selected_route"] in {"research_initiative", "refine_proposal"}
    assert {item["action"] for item in seed_only["blocked_actions"]} >= {
        "hydrate_task",
        "ship_task",
    }

    reflection_path = _write_lifecycle_reflection(tmp_path)
    capture = autonomous_loop.build_initiative_route_decision_capsule(
        tmp_path,
        initiative_path,
        reflection_path=reflection_path,
    )

    assert capture["selected_route"] == "capture_self_improvement"
    assert capture["route_state"] == "high_severity_self_capture"


def test_route_decision_capsule_consumed_self_capture_does_not_preempt_again(
    tmp_path: Path,
) -> None:
    _state(
        tmp_path,
        history=[
            {
                "action": "capture_self_improvement",
                "self_capture_materialization": {
                    "entry_id": "SRF-2026-04-25-AUTOAUTO-CAMPAIGN-REPORT-IMPLICATIONS",
                    "artifact_path": ".azoth/inbox/session-reflection-2026-04-25-autonomous-auto-campaign-report.jsonl",
                },
            }
        ],
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    reflection_path = _write_lifecycle_reflection(tmp_path)

    capsule = autonomous_loop.build_initiative_route_decision_capsule(
        tmp_path,
        initiative_path,
        reflection_path=reflection_path,
    )

    assert capsule["selected_route"] != "capture_self_improvement"
    assert capsule["route_state"] in {"discovery_active", "candidate_ready_for_review"}


def test_route_decision_capsule_protected_gate_overrides_self_capture(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["candidate_slices"][0]["target_layer"] = "governance"
    _write_yaml(initiative_path, doc)
    reflection_path = _write_lifecycle_reflection(tmp_path)

    capsule = autonomous_loop.build_initiative_route_decision_capsule(
        tmp_path,
        initiative_path,
        reflection_path=reflection_path,
    )

    assert capsule["selected_route"] == "stop"
    assert capsule["approval_needed"] == "protected human gate required"
    assert capsule["protected_stops"] == ["protected target layer or governed delivery pipeline"]
    assert any(item["action"] == "hydrate_task" for item in capsule["blocked_actions"])
    assert any(item["action"] == "ship_task" for item in capsule["blocked_actions"])


def test_route_decision_capsule_raw_missing_readiness_fails_closed(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc.pop("readiness")
    _write_yaml(initiative_path, doc)

    capsule = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)

    assert capsule["selected_route"] == "research_initiative"
    assert capsule["route_state"] == "raw_initiative"
    assert {item["action"] for item in capsule["blocked_actions"]} >= {
        "hydrate_task",
        "ship_task",
    }


def test_route_decision_capsule_blocks_material_unverifiable_external_freshness(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["readiness"].update(
        {
            "freshness_materiality": "material",
            "freshness_verification": "unverifiable",
        }
    )
    _write_yaml(initiative_path, doc)

    capsule = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)

    assert capsule["selected_route"] == "stop"
    assert capsule["route_state"] == "external_freshness_unverifiable"
    assert capsule["approval_needed"] == "verify_external_freshness_before_open_next"
    assert any(
        item["reason"] == "external freshness is material and cannot be verified"
        for item in capsule["blocked_actions"]
    )


def test_route_decision_capsule_stale_campaign_requires_fresh_budget(
    tmp_path: Path,
) -> None:
    _state(
        tmp_path,
        status="completed",
        completion_reason="vision_realized",
        vision={"current_band": "green", "target_band": "green", "realized": True},
    )
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)

    capsule = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)

    assert capsule["selected_route"] == "stop"
    assert capsule["route_state"] == "completed_or_stale_campaign"
    assert any(item["action"] == "open_next_without_budget" for item in capsule["blocked_actions"])


def test_route_decision_capsule_bad_hydration_approval_or_scaffold_fails_closed(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    doc = yaml.safe_load(initiative_path.read_text(encoding="utf-8"))
    doc["readiness"].update(
        {
            "readiness_status": "ready_to_hydrate",
            "freshness_status": "current_as_of_2026_04_25",
            "human_decision": "pending",
            "approval_scope": "hydration_specific_slice_auto_001_a",
            "approval_basis": "Operator approved the wrong thing.",
        }
    )
    _write_yaml(initiative_path, doc)

    denied = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)
    assert denied["selected_route"] != "hydrate_task"
    assert any(item["action"] == "hydrate_task" for item in denied["blocked_actions"])

    doc["readiness"]["human_decision"] = "approved"
    doc["candidate_slices"][0]["hydration_plan"]["scaffold_command"] = (
        "python3 scripts/roadmap_scaffold.py --source wrong-slice"
    )
    _write_yaml(initiative_path, doc)

    malformed = autonomous_loop.build_initiative_route_decision_capsule(tmp_path, initiative_path)
    assert malformed["selected_route"] != "hydrate_task"
    assert any(
        "scaffold command naming the candidate" in item["reason"]
        for item in malformed["blocked_actions"]
        if item["action"] == "hydrate_task"
    )


def test_lifecycle_route_cli_json_and_plain_text_are_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _state(tmp_path)
    initiative_path = _write_lifecycle_initiative_bank(tmp_path)
    before = initiative_path.read_text(encoding="utf-8")

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "lifecycle-route",
                "--initiative",
                str(initiative_path),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["capsule_type"] == "autonomous_auto_initiative_route_decision"

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "lifecycle-route",
                "--initiative",
                str(initiative_path),
            ]
        )
        == 0
    )
    assert "Autonomous-auto initiative route decision" in capsys.readouterr().out
    assert initiative_path.read_text(encoding="utf-8") == before

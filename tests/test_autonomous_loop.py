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


def _future_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


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
    assert scope["loop_decision"]["action"] == "ship_task"
    ledger = yaml.safe_load(
        (tmp_path / ".azoth/run-ledger.local.yaml").read_text(encoding="utf-8")
    )
    run = next(item for item in ledger["runs"] if item["run_id"] == result["session_id"])
    assert run["status"] == "active"
    assert run["active_stage_id"] == "autonomous_auto_s1_architect"
    assert run["pending_stage_ids"] == [
        "autonomous_auto_s1_architect",
        "autonomous_auto_s2_planner",
        "autonomous_auto_s3_builder",
        "autonomous_auto_s4_evaluator",
    ]
    assert state["iteration"] == 1
    assert state["last_session_id"] == result["session_id"]
    assert state["queue"] == []
    assert state["history"][0]["candidate_id"] == "T-321"
    assert state["history"][0]["delegation_plan_id"] == scope["delegation_plan"]["plan_id"]


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

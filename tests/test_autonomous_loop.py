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
    assert "Blocked actions: hydrate_task, ship_task" in output


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

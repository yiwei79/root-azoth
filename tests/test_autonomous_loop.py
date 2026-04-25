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
            "allowed_actions": [
                "ship_task",
                "hydrate_task",
                "research_initiative",
                "refine_proposal",
                "capture_self_improvement",
            ],
        },
        "iteration": 0,
        "queue": [],
        "self_capture_queue": [],
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
    assert scope["loop_decision"]["action"] == "ship_task"
    assert state["iteration"] == 1
    assert state["last_session_id"] == result["session_id"]
    assert state["queue"] == []
    assert state["history"][0]["candidate_id"] == "T-321"


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

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import autonomous_loop  # noqa: E402
from autonomous_campaign_audit import build_campaign_audit  # noqa: E402


LOOP_ID = "2026-04-26-autonomous-auto-t-029-1"
PARENT_LOOP_ID = "parent-campaign-loop"
CHILD_SESSION_ID = "2026-04-25-autonomous-auto-child-1"


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _snapshot_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _fixture_paths(root: Path) -> dict[str, Path]:
    return {
        "state_path": root / ".azoth/autonomous-loop-state.local.yaml",
        "ledger_path": root / ".azoth/run-ledger.local.yaml",
        "episodes_path": root / ".azoth/memory/episodes.jsonl",
        "inbox_dir": root / ".azoth/inbox",
    }


def _write_complete_campaign(root: Path) -> dict[str, Path]:
    paths = _fixture_paths(root)
    _write_yaml(
        paths["state_path"],
        {
            "schema_version": 1,
            "loop_id": LOOP_ID,
            "status": "stopped",
            "objective": "Implement T-029 Autonomous-auto campaign audit report",
            "iteration": 1,
            "completion_reason": "vision_realized",
            "vision": {
                "current_band": "green",
                "target_band": "green",
                "score": 0.93,
                "scorecard": {"continuation": "green", "score": 0.93},
                "latest": {"band": "green", "note": "Audit route complete"},
            },
            "history": [
                {
                    "iteration": 1,
                    "session_id": LOOP_ID,
                    "action": "ship_task",
                    "candidate_id": "T-029",
                    "result": "opened",
                }
            ],
        },
    )
    _write_yaml(
        paths["ledger_path"],
        {
            "schema_version": 1,
            "runs": [
                {
                    "run_id": LOOP_ID,
                    "mode": "autonomous-auto",
                    "goal": "Implement T-029 Autonomous-auto campaign audit report",
                    "status": "complete",
                    "created_at": "2026-04-26T10:00:00+00:00",
                    "updated_at": "2026-04-26T11:00:00+00:00",
                    "next_action": "done",
                    "stages_completed": [
                        "autonomous_auto_s1_architect",
                        "autonomous_auto_s2_planner",
                        "autonomous_auto_s3_builder",
                        "autonomous_auto_s4_evaluator",
                    ],
                    "stage_spawns": [
                        {
                            "run_id": LOOP_ID,
                            "stage_id": "autonomous_auto_s1_architect",
                            "subagent_type": "architect",
                            "trigger": "campaign-plan",
                            "role_hint": "Approve read-only audit boundary.",
                            "dependency_summary_refs": [],
                            "spawned_at": "2026-04-26T10:01:00+00:00",
                        },
                        {
                            "run_id": LOOP_ID,
                            "stage_id": "autonomous_auto_s2_planner",
                            "subagent_type": "planner",
                            "trigger": "campaign-plan",
                            "role_hint": "Specify focused implementation slice.",
                            "dependency_summary_refs": [],
                            "spawned_at": "2026-04-26T10:15:00+00:00",
                        },
                        {
                            "run_id": LOOP_ID,
                            "stage_id": "autonomous_auto_s3_builder",
                            "subagent_type": "builder",
                            "trigger": "campaign-build",
                            "role_hint": "Implement read-only audit report.",
                            "dependency_summary_refs": [],
                            "spawned_at": "2026-04-26T10:25:00+00:00",
                        },
                        {
                            "run_id": LOOP_ID,
                            "stage_id": "autonomous_auto_s4_evaluator",
                            "subagent_type": "evaluator",
                            "trigger": "campaign-eval",
                            "role_hint": "Evaluate learning closure.",
                            "dependency_summary_refs": [],
                            "spawned_at": "2026-04-26T10:40:00+00:00",
                        },
                    ],
                    "stage_summaries": [
                        {
                            "run_id": LOOP_ID,
                            "stage_id": "autonomous_auto_s1_architect",
                            "subagent_type": "architect",
                            "trigger": "campaign-plan",
                            "role_hint": "Approve read-only audit boundary.",
                            "dependency_summary_refs": [],
                            "summary_recorded_at": "2026-04-26T10:10:00+00:00",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                        },
                        {
                            "run_id": LOOP_ID,
                            "stage_id": "autonomous_auto_s2_planner",
                            "subagent_type": "planner",
                            "trigger": "campaign-plan",
                            "role_hint": "Specify focused implementation slice.",
                            "dependency_summary_refs": [],
                            "summary_recorded_at": "2026-04-26T10:20:00+00:00",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                        },
                        {
                            "run_id": LOOP_ID,
                            "stage_id": "autonomous_auto_s3_builder",
                            "subagent_type": "builder",
                            "trigger": "campaign-build",
                            "role_hint": "Implement read-only audit report.",
                            "dependency_summary_refs": [],
                            "summary_recorded_at": "2026-04-26T10:35:00+00:00",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                        },
                        {
                            "run_id": LOOP_ID,
                            "stage_id": "autonomous_auto_s4_evaluator",
                            "subagent_type": "evaluator",
                            "trigger": "campaign-eval",
                            "role_hint": "Evaluate learning closure.",
                            "dependency_summary_refs": [],
                            "summary_recorded_at": "2026-04-26T10:55:00+00:00",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                            "scores": [0.91],
                            "ux_anchor_scorecard": {
                                "continuation": "green",
                                "operator_read": "green",
                            },
                            "verification_commands": [
                                "python3 -m pytest tests/test_autonomous_campaign_audit.py"
                            ],
                        },
                    ],
                }
            ],
        },
    )
    _write_jsonl(
        paths["episodes_path"],
        [
            {
                "id": "ep-t029-verified",
                "session_id": LOOP_ID,
                "timestamp": "2026-04-26T11:05:00Z",
                "learning_state": "verified",
                "summary": "Campaign audit verified with focused tests.",
                "tags": ["autonomous-auto", "learning-closure"],
            }
        ],
    )
    _write_jsonl(
        paths["inbox_dir"] / "session-reflection-2026-04-26-autonomous-auto-t029.jsonl",
        [
            {
                "id": "inbox-t029-captured",
                "session_id": LOOP_ID,
                "learning_state": "captured",
                "summary": "Capture campaign audit learning closure.",
                "tags": ["autonomous-auto", "learning-closure"],
            }
        ],
    )
    return paths


def test_build_campaign_audit_complete_campaign_is_read_only(tmp_path: Path) -> None:
    paths = _write_complete_campaign(tmp_path)
    before = _snapshot_files(tmp_path)

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert _snapshot_files(tmp_path) == before
    assert report["schema_version"] == 1
    assert report["campaign"]["loop_id"] == LOOP_ID
    assert report["campaign"]["provenance"] == "repo_native"
    assert report["campaign"]["completion_reason"] == "vision_realized"
    assert report["campaign"]["vision_band"] == "green"
    assert report["campaign"]["vision_score"] == 0.93
    assert report["campaign"]["vision_provenance"] == "repo_native"
    assert report["source_artifacts"]["state"]["provenance"] == "repo_native"
    assert report["child_scopes"][0]["session_id"] == LOOP_ID
    assert report["stage_evidence"]["provenance"] == "repo_native"
    assert report["stage_evidence"]["stages"]["autonomous_auto_s1_architect"]["provenance"] == (
        "repo_native"
    )
    assert report["evaluator_evidence"]["provenance"] == "repo_native"
    assert report["evaluator_evidence"]["structured_scores"] == [0.91]
    assert report["evaluator_evidence"]["ux_scorecards"] == [
        {"continuation": "green", "operator_read": "green"}
    ]
    assert report["evaluator_evidence"]["verification_commands"] == [
        "python3 -m pytest tests/test_autonomous_campaign_audit.py"
    ]
    assert {row["learning_state"] for row in report["learning_closure_rows"]} == {
        "captured",
        "verified",
    }
    assert report["traceability_scorecard"]["overall_provenance"] == "repo_native"
    assert report["next_route_recommendation"]["route"] == "stop"
    assert report["next_route_recommendation"]["confidence"] == 1.0
    assert report["next_route_recommendation"]["confidence_basis"]
    assert report["verification_commands"] == [
        "python3 -m pytest tests/test_autonomous_campaign_audit.py"
    ]
    assert report["residual_risks"] == []
    assert report["validation"]["read_only"] is True


def test_build_campaign_audit_missing_stage_summary_reports_residual_risk(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    ledger = yaml.safe_load(paths["ledger_path"].read_text(encoding="utf-8"))
    ledger["runs"][0]["stage_summaries"] = [
        row
        for row in ledger["runs"][0]["stage_summaries"]
        if row["stage_id"] != "autonomous_auto_s1_architect"
    ]
    _write_yaml(paths["ledger_path"], ledger)
    before = _snapshot_files(tmp_path)

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert _snapshot_files(tmp_path) == before
    stage = report["stage_evidence"]["stages"]["autonomous_auto_s1_architect"]
    assert stage["provenance"] == "conflict"
    assert stage["spawn_provenance"] == "repo_native"
    assert stage["summary_provenance"] == "missing"
    assert report["traceability_scorecard"]["stage_evidence"] == "conflict"
    assert any("missing stage summary" in risk for risk in report["residual_risks"])
    assert report["next_route_recommendation"]["route"] == "repair_evidence"
    assert report["next_route_recommendation"]["confidence_basis"]


def test_build_campaign_audit_infers_completion_from_green_vision(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    state = yaml.safe_load(paths["state_path"].read_text(encoding="utf-8"))
    state.pop("completion_reason")
    _write_yaml(paths["state_path"], state)

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert report["campaign"]["completion_reason"] == "vision_realized"
    assert report["campaign"]["vision"] == {
        "band": "green",
        "target_band": "green",
        "score": 0.93,
        "scorecard": {"continuation": "green", "score": 0.93},
        "realized": True,
        "updated_at": "",
        "note": "Audit route complete",
        "provenance": "repo_native",
    }


def test_build_campaign_audit_reports_optional_quality_gaps_when_evaluator_exists(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    ledger = yaml.safe_load(paths["ledger_path"].read_text(encoding="utf-8"))
    evaluator_summary = ledger["runs"][0]["stage_summaries"][-1]
    evaluator_summary.pop("scores")
    evaluator_summary.pop("ux_anchor_scorecard")
    evaluator_summary.pop("verification_commands")
    _write_yaml(paths["ledger_path"], ledger)

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert report["evaluator_evidence"]["provenance"] == "repo_native"
    assert report["evaluator_evidence"]["structured_scores"] == []
    assert report["evaluator_evidence"]["ux_scorecards"] == []
    assert report["evaluator_evidence"]["verification_commands"] == []
    assert "missing structured evaluator score fields" in report["residual_risks"]
    assert "missing UX Anchor Scorecard fields" in report["residual_risks"]
    assert "missing evaluator verification command fields" in report["residual_risks"]
    assert report["next_route_recommendation"]["route"] == "review_residuals"


def test_build_campaign_audit_inbox_learning_capture_without_episode_is_triaged(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    paths["episodes_path"].write_text("", encoding="utf-8")

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert report["learning_closure_rows"] == [
        {
            "learning_state": "captured",
            "provenance": "repo_native",
            "source": ".azoth/inbox/session-reflection-2026-04-26-autonomous-auto-t029.jsonl",
            "summary": "Capture campaign audit learning closure.",
        }
    ]
    assert report["traceability_scorecard"]["learning_closure"] == "repo_native"
    assert report["next_route_recommendation"]["route"] == "plan_learning_closure"


def test_build_campaign_audit_orders_children_by_iteration_then_timestamp(
    tmp_path: Path,
) -> None:
    paths = _fixture_paths(tmp_path)
    _write_yaml(
        paths["state_path"],
        {
            "schema_version": 1,
            "loop_id": "fresh-loop",
            "status": "active",
        },
    )
    _write_yaml(
        paths["ledger_path"],
        {
            "schema_version": 1,
            "runs": [
                {"run_id": "child-two", "session_id": "child-two", "status": "complete"},
                {"run_id": "child-one", "session_id": "child-one", "status": "complete"},
                {"run_id": "child-three-a", "session_id": "child-three-a", "status": "complete"},
                {"run_id": "child-three-b", "session_id": "child-three-b", "status": "complete"},
            ],
        },
    )
    _write_jsonl(
        paths["episodes_path"],
        [
            {
                "id": "ep-two",
                "session_id": "child-two",
                "timestamp": "2026-04-26T09:00:00Z",
                "context": {
                    "verbatim_payload": {
                        "loop_id": PARENT_LOOP_ID,
                        "session_id": "child-two",
                        "loop_iteration": 2,
                    }
                },
            },
            {
                "id": "ep-three-b",
                "session_id": "child-three-b",
                "timestamp": "2026-04-26T11:00:00Z",
                "context": {
                    "verbatim_payload": {
                        "loop_id": PARENT_LOOP_ID,
                        "session_id": "child-three-b",
                        "loop_iteration": 3,
                    }
                },
            },
            {
                "id": "ep-one",
                "session_id": "child-one",
                "timestamp": "2026-04-26T12:00:00Z",
                "context": {
                    "verbatim_payload": {
                        "loop_id": PARENT_LOOP_ID,
                        "session_id": "child-one",
                        "loop_iteration": 1,
                    }
                },
            },
            {
                "id": "ep-three-a",
                "session_id": "child-three-a",
                "timestamp": "2026-04-26T10:00:00Z",
                "context": {
                    "verbatim_payload": {
                        "loop_id": PARENT_LOOP_ID,
                        "session_id": "child-three-a",
                        "loop_iteration": 3,
                    }
                },
            },
        ],
    )

    report = build_campaign_audit(tmp_path, PARENT_LOOP_ID, **paths)

    assert [scope["session_id"] for scope in report["child_scopes"]] == [
        "child-one",
        "child-two",
        "child-three-a",
        "child-three-b",
    ]
    assert [scope["loop_iteration"] for scope in report["child_scopes"]] == [1, 2, 3, 3]


def test_build_campaign_audit_joins_state_history_child_run(
    tmp_path: Path,
) -> None:
    paths = _fixture_paths(tmp_path)
    child_session_id = "2026-04-26-autonomous-auto-t-029-1"
    _write_yaml(
        paths["state_path"],
        {
            "schema_version": 1,
            "loop_id": LOOP_ID,
            "status": "active",
            "objective": "T-029 Campaign Audit Completion",
            "iteration": 1,
            "history": [
                {
                    "iteration": 1,
                    "session_id": child_session_id,
                    "action": "ship_task",
                    "candidate_id": "T-029",
                    "result": "opened",
                    "timestamp": "2026-04-26T08:04:42Z",
                }
            ],
        },
    )
    _write_yaml(
        paths["ledger_path"],
        {
            "schema_version": 1,
            "runs": [
                {
                    "run_id": child_session_id,
                    "session_id": child_session_id,
                    "status": "complete",
                    "stages_completed": ["autonomous_auto_s4_evaluator"],
                    "stage_spawns": [
                        {
                            "run_id": child_session_id,
                            "stage_id": "autonomous_auto_s4_evaluator",
                            "subagent_type": "evaluator",
                        }
                    ],
                    "stage_summaries": [
                        {
                            "run_id": child_session_id,
                            "stage_id": "autonomous_auto_s4_evaluator",
                            "subagent_type": "evaluator",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                            "score": 0.88,
                            "ux_anchor_scorecard": {"traceability": "green"},
                            "verification_commands": [
                                "python3 -m pytest tests/test_autonomous_campaign_audit.py"
                            ],
                        }
                    ],
                }
            ],
        },
    )
    _write_jsonl(
        paths["episodes_path"],
        [
            {
                "id": "ep-t029-history-verified",
                "session_id": LOOP_ID,
                "learning_state": "verified",
                "summary": "State-history child run evidence verified.",
                "tags": ["autonomous-auto", "learning-closure"],
            }
        ],
    )

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert [scope["session_id"] for scope in report["child_scopes"]] == [
        child_session_id
    ]
    assert report["child_scopes"][0]["action"] == "ship_task"
    assert report["stage_evidence"]["provenance"] == "repo_native"
    assert report["stage_evidence"]["stages"]["autonomous_auto_s4_evaluator"][
        "run_id"
    ] == child_session_id
    assert report["evaluator_evidence"]["structured_scores"] == [0.88]
    assert report["verification_commands"] == [
        "python3 -m pytest tests/test_autonomous_campaign_audit.py"
    ]
    assert "missing run ledger entry for campaign" not in report["residual_risks"]


def test_build_campaign_audit_joins_parent_closeout_episode_to_child_run(
    tmp_path: Path,
) -> None:
    paths = _fixture_paths(tmp_path)
    _write_yaml(
        paths["state_path"],
        {
            "schema_version": 1,
            "loop_id": "fresh-active-loop",
            "status": "active",
            "objective": "Fresh campaign that must not override parent evidence",
            "autonomy_budget": {
                "approval_basis": "Fresh approval that must not leak into parent audit.",
                "stop_conditions": ["fresh_stop"],
            },
        },
    )
    _write_yaml(
        paths["ledger_path"],
        {
            "schema_version": 1,
            "runs": [
                {
                    "run_id": CHILD_SESSION_ID,
                    "session_id": CHILD_SESSION_ID,
                    "mode": "autonomous-auto",
                    "goal": "Child scope execution",
                    "status": "complete",
                    "stages_completed": [
                        "autonomous_auto_s1_architect",
                        "autonomous_auto_s2_evaluator",
                    ],
                    "stage_spawns": [
                        {
                            "run_id": CHILD_SESSION_ID,
                            "stage_id": "autonomous_auto_s1_architect",
                            "subagent_type": "architect",
                        },
                        {
                            "run_id": CHILD_SESSION_ID,
                            "stage_id": "autonomous_auto_s2_evaluator",
                            "subagent_type": "evaluator",
                        },
                    ],
                    "stage_summaries": [
                        {
                            "run_id": CHILD_SESSION_ID,
                            "stage_id": "autonomous_auto_s1_architect",
                            "subagent_type": "architect",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                        },
                        {
                            "run_id": CHILD_SESSION_ID,
                            "stage_id": "autonomous_auto_s2_evaluator",
                            "subagent_type": "evaluator",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                        },
                    ],
                }
            ],
        },
    )
    _write_jsonl(
        paths["episodes_path"],
        [
            {
                "id": "ep-parent-closeout",
                "session_id": CHILD_SESSION_ID,
                "timestamp": "2026-04-25T22:11:01Z",
                "summary": "Completed session closeout via scripts/do_closeout.py.",
                "tags": ["closeout", "session-closeout"],
                "context": {
                    "files_changed": ["scripts/autonomous_campaign_audit.py"],
                    "verbatim_payload": {
                        "loop_id": PARENT_LOOP_ID,
                        "session_id": CHILD_SESSION_ID,
                        "approval_basis": "Operator approved parent campaign.",
                        "completion_reason": "budget_exhausted",
                        "vision": {
                            "current_band": "yellow",
                            "target_band": "green",
                            "score": 0.72,
                        },
                        "evaluator_scores": [0.84],
                        "ux_anchor_scorecard": {
                            "operator_traceability": "yellow",
                            "learning_closure": "red",
                        },
                        "verification_commands": [
                            "python3 scripts/autonomous_loop.py campaign-audit --loop-id parent-campaign-loop --json"
                        ],
                        "autonomy_budget": {
                            "max_iterations": 4,
                            "replay_threshold": 1,
                            "stop_conditions": ["budget_exhausted"],
                        },
                        "loop_decision": {
                            "action": "ship_task",
                            "candidate_id": "T-029",
                            "reason": "Selected ready campaign audit task.",
                            "architect_judgment": {
                                "selected": {
                                    "candidate_id": "T-029",
                                    "source": "roadmap",
                                }
                            },
                        },
                        "delegation_plan": {
                            "plan_id": "parent-child-delegation",
                            "run_ledger_evidence": {"run_id": CHILD_SESSION_ID},
                            "stages": [
                                {
                                    "stage_id": "autonomous_auto_s1_architect",
                                    "subagent_type": "architect",
                                },
                                {
                                    "stage_id": "autonomous_auto_s2_evaluator",
                                    "subagent_type": "evaluator",
                                },
                            ],
                        },
                    },
                },
            }
        ],
    )

    report = build_campaign_audit(tmp_path, PARENT_LOOP_ID, **paths)

    assert report["campaign"]["loop_id"] == PARENT_LOOP_ID
    assert report["campaign"]["provenance"] == "repo_native"
    assert report["campaign"]["objective"] != (
        "Fresh campaign that must not override parent evidence"
    )
    assert report["campaign"]["status"] == "observed_from_closeout"
    assert report["campaign"]["iteration"] == 1
    assert report["campaign"]["completion_reason"] == "budget_exhausted"
    assert report["campaign"]["vision_band"] == "yellow"
    assert report["campaign"]["vision_score"] == 0.72
    assert report["campaign"]["approval_basis"] == "Operator approved parent campaign."
    assert report["campaign"]["stop_conditions"] == ["budget_exhausted"]
    assert report["campaign"]["selected_candidate"]["candidate_id"] == "T-029"
    assert report["campaign"]["route_rationale"] == "Selected ready campaign audit task."
    assert report["campaign"]["closeout_episode_ids"] == ["ep-parent-closeout"]
    assert report["child_scopes"][0]["session_id"] == CHILD_SESSION_ID
    assert report["child_scopes"][0]["run_id"] == CHILD_SESSION_ID
    assert report["child_scopes"][0]["closeout_episode_id"] == "ep-parent-closeout"
    assert report["child_scopes"][0]["changed_files"] == [
        "scripts/autonomous_campaign_audit.py"
    ]
    assert report["stage_evidence"]["provenance"] == "repo_native"
    assert report["stage_evidence"]["stages"]["autonomous_auto_s2_evaluator"][
        "run_id"
    ] == CHILD_SESSION_ID
    assert report["evaluator_evidence"]["provenance"] == "repo_native"
    assert report["evaluator_evidence"]["structured_scores"] == [0.84]
    assert report["evaluator_evidence"]["ux_scorecards"] == [
        {"operator_traceability": "yellow", "learning_closure": "red"}
    ]
    assert report["verification_commands"] == [
        "python3 scripts/autonomous_loop.py campaign-audit --loop-id parent-campaign-loop --json"
    ]
    assert "missing run ledger entry for campaign" not in report["residual_risks"]


def test_campaign_audit_cli_json_and_plain_are_read_only(
    tmp_path: Path, capsys
) -> None:
    paths = _write_complete_campaign(tmp_path)
    before = _snapshot_files(tmp_path)

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "campaign-audit",
                "--loop-id",
                LOOP_ID,
                "--state",
                str(paths["state_path"]),
                "--ledger",
                str(paths["ledger_path"]),
                "--episodes",
                str(paths["episodes_path"]),
                "--inbox-dir",
                str(paths["inbox_dir"]),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["campaign"]["loop_id"] == LOOP_ID
    assert payload["validation"]["read_only"] is True

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "campaign-audit",
                "--loop-id",
                LOOP_ID,
                "--state",
                str(paths["state_path"]),
                "--ledger",
                str(paths["ledger_path"]),
                "--episodes",
                str(paths["episodes_path"]),
                "--inbox-dir",
                str(paths["inbox_dir"]),
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert f"Campaign audit: {LOOP_ID}" in out
    assert "Next route: stop" in out
    assert _snapshot_files(tmp_path) == before

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import autonomous_loop  # noqa: E402
from autonomous_campaign_audit import (  # noqa: E402
    build_campaign_audit,
    build_nightly_automation_audit_bundle,
)


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


def _remove_evaluator_stage_evidence(ledger: dict) -> dict:
    run = ledger["runs"][0]
    run["stages_completed"] = [
        stage for stage in run.get("stages_completed", []) if "evaluator" not in stage
    ]
    run["stage_spawns"] = [
        row
        for row in run.get("stage_spawns", [])
        if row.get("stage_id") != "autonomous_auto_s4_evaluator"
    ]
    run["stage_summaries"] = [
        row
        for row in run.get("stage_summaries", [])
        if row.get("stage_id") != "autonomous_auto_s4_evaluator"
    ]
    return ledger


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
    assert report["executive_read"] == {
        "change_summary": "Campaign vision_realized with green UX vision evidence.",
        "quality_assessment": "Evaluator scores: 0.91; UX Anchor Scorecard present.",
        "residual_risk": "none",
        "next_route": "stop",
        "operator_implication": "Campaign evidence is complete enough to stop without repair.",
        "evidence_contract": [
            "campaign declaration and budget",
            "delegated stage evidence",
            "evaluator scores and UX Anchor Scorecard",
            "verification commands",
            "learning closure",
        ],
    }
    assert report["campaign_implications"] == [
        "Campaign can stop cleanly; no repair route is recommended.",
        "Operator-facing evidence is repo-native and complete enough for audit without raw ledger spelunking.",
    ]
    assert report["ux_anchor_fit"]["band"] == "green"
    assert "UX Anchor Scorecard present" in report["ux_anchor_fit"]["evidence"]
    assert report["operator_packet_parity"]["next_likely_move"] == "stop"
    assert report["operator_packet_parity"]["residual_risk"] == "none"
    assert report["residual_risks"] == []
    assert report["validation"]["read_only"] is True


def test_build_campaign_audit_normalizes_retrospective_evaluator_evidence(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    ledger = yaml.safe_load(paths["ledger_path"].read_text(encoding="utf-8"))
    _write_yaml(paths["ledger_path"], _remove_evaluator_stage_evidence(ledger))
    _write_jsonl(
        paths["inbox_dir"] / "session-reflection-2026-04-26-retrospective-eval.jsonl",
        [
            {
                "id": "retro-eval-001",
                "session_id": LOOP_ID,
                "learning_state": "verified",
                "summary": "Retrospective evaluator judged campaign report quality.",
                "tags": ["autonomous-auto", "learning-closure", "evaluator", "ux-scorecard"],
                "score": 0.88,
                "ux_anchor_scorecard": {
                    "operator_read": "yellow",
                    "learning_closure": "green",
                },
                "verification_commands": [
                    "python3 -m pytest tests/test_autonomous_campaign_audit.py"
                ],
            }
        ],
    )
    before = _snapshot_files(tmp_path)

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert _snapshot_files(tmp_path) == before
    assert report["evaluator_evidence"]["provenance"] == "repo_native"
    assert report["evaluator_evidence"]["retrospective_evidence_count"] == 1
    assert report["evaluator_evidence"]["structured_scores"] == [0.88]
    assert report["evaluator_evidence"]["ux_scorecards"] == [
        {"operator_read": "yellow", "learning_closure": "green"}
    ]
    assert report["executive_read"]["quality_assessment"] == (
        "Evaluator scores: 0.88; UX Anchor Scorecard present."
    )


def test_build_campaign_audit_ignores_unrelated_retrospective_evaluator_evidence(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    ledger = yaml.safe_load(paths["ledger_path"].read_text(encoding="utf-8"))
    _write_yaml(paths["ledger_path"], _remove_evaluator_stage_evidence(ledger))
    _write_jsonl(
        paths["inbox_dir"] / "session-reflection-unrelated-retrospective-eval.jsonl",
        [
            {
                "id": "retro-eval-unrelated",
                "session_id": "other-loop",
                "learning_state": "verified",
                "summary": "Unrelated evaluator evidence must not satisfy this campaign.",
                "tags": ["autonomous-auto", "learning-closure", "evaluator"],
                "score": 0.99,
                "ux_anchor_scorecard": {"operator_read": "green"},
                "verification_commands": ["python3 -m pytest unrelated.py"],
            }
        ],
    )

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert report["evaluator_evidence"]["provenance"] == "missing"
    assert report["evaluator_evidence"].get("retrospective_evidence_count", 0) == 0
    assert report["evaluator_evidence"]["structured_scores"] == []


def test_build_campaign_audit_normalizes_retrospective_evaluator_aliases(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    ledger = yaml.safe_load(paths["ledger_path"].read_text(encoding="utf-8"))
    ledger["runs"][0]["stage_summaries"] = [
        row
        for row in ledger["runs"][0]["stage_summaries"]
        if row["stage_id"] != "autonomous_auto_s4_evaluator"
    ]
    _write_yaml(paths["ledger_path"], ledger)
    _write_jsonl(
        paths["inbox_dir"] / "session-reflection-2026-04-26-retrospective-aliases.jsonl",
        [
            {
                "id": "retro-eval-aliases",
                "session_id": LOOP_ID,
                "learning_state": "verified",
                "summary": "Retrospective evaluator evidence with alias fields.",
                "tags": ["autonomous-auto", "learning-closure", "evaluator"],
                "evaluator_scores": [0.87],
                "scorecard": {
                    "overall": 0.87,
                    "ux_operator_read": "yellow",
                },
                "verification": {
                    "commands": ["python3 -m pytest tests/test_autonomous_campaign_audit.py"]
                },
            }
        ],
    )

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert report["evaluator_evidence"]["structured_scores"] == [0.87, 0.87]
    assert report["evaluator_evidence"]["ux_scorecards"] == [
        {"overall": 0.87, "ux_operator_read": "yellow"}
    ]
    assert report["evaluator_evidence"]["verification_commands"] == [
        "python3 -m pytest tests/test_autonomous_campaign_audit.py"
    ]


def test_build_campaign_audit_retrospective_evidence_preserves_base_conflict(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    ledger = yaml.safe_load(paths["ledger_path"].read_text(encoding="utf-8"))
    ledger["runs"][0]["stage_summaries"] = [
        row
        for row in ledger["runs"][0]["stage_summaries"]
        if row["stage_id"] != "autonomous_auto_s4_evaluator"
    ]
    _write_yaml(paths["ledger_path"], ledger)
    _write_jsonl(
        paths["inbox_dir"] / "session-reflection-2026-04-26-conflict-retro-eval.jsonl",
        [
            {
                "id": "retro-eval-conflict",
                "session_id": LOOP_ID,
                "learning_state": "verified",
                "summary": "Matching retrospective evidence must not hide ledger conflict.",
                "tags": ["autonomous-auto", "learning-closure", "evaluator"],
                "score": 0.92,
                "ux_anchor_scorecard": {"operator_read": "green"},
                "verification_commands": [
                    "python3 -m pytest tests/test_autonomous_campaign_audit.py"
                ],
            }
        ],
    )

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert report["evaluator_evidence"]["provenance"] == "conflict"
    assert report["evaluator_evidence"]["retrospective_evidence_count"] == 1
    assert report["evaluator_evidence"]["structured_scores"] == [0.92]
    assert report["next_route_recommendation"]["route"] == "repair_evidence"


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


def test_build_campaign_audit_routes_latest_blocking_stage_summary_to_repair_evidence(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    ledger = yaml.safe_load(paths["ledger_path"].read_text(encoding="utf-8"))
    ledger["runs"][0]["stage_summaries"].append(
        {
            "run_id": LOOP_ID,
            "stage_id": "autonomous_auto_s1_architect",
            "subagent_type": "architect",
            "trigger": "campaign-plan",
            "role_hint": "Approve read-only audit boundary.",
            "dependency_summary_refs": [],
            "summary_recorded_at": "2026-04-26T11:10:00+00:00",
            "summary_status": "blocked",
            "summary_disposition": "needs-input",
        }
    )
    _write_yaml(paths["ledger_path"], ledger)

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    stage = report["stage_evidence"]["stages"]["autonomous_auto_s1_architect"]
    assert stage["provenance"] == "conflict"
    assert stage["spawn_provenance"] == "repo_native"
    assert stage["summary_provenance"] == "repo_native"
    assert stage["summary_status"] == "blocked"
    assert stage["summary_disposition"] == "needs-input"
    assert report["traceability_scorecard"]["stage_evidence"] == "conflict"
    assert (
        "blocking stage summary for autonomous_auto_s1_architect: "
        "status=blocked, disposition=needs-input"
    ) in report["residual_risks"]
    assert report["next_route_recommendation"]["route"] == "repair_evidence"


def test_build_campaign_audit_accepts_truthful_inline_stage_absence(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    ledger = yaml.safe_load(paths["ledger_path"].read_text(encoding="utf-8"))
    ledger["runs"][0]["stages_completed"] = []
    ledger["runs"][0]["stage_spawns"] = []
    ledger["runs"][0]["stage_summaries"] = []
    _write_yaml(paths["ledger_path"], ledger)
    _write_jsonl(
        paths["inbox_dir"] / "session-reflection-2026-04-26-inline-exception.jsonl",
        [
            {
                "id": "inline-exception-verified",
                "session_id": LOOP_ID,
                "learning_state": "implemented",
                "summary": (
                    "Implemented inline execution exception: no fake stage evidence "
                    "should be backfilled when subagents were not spawned."
                ),
                "tags": [
                    "autonomous-auto",
                    "learning-closure",
                    "stage-evidence",
                    "inline-exception",
                ],
            }
        ],
    )

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert report["stage_evidence"]["provenance"] == "missing"
    assert report["stage_evidence"]["stages"] == {}
    assert report["stage_evidence"]["truthful_absence"]["accepted"] is True
    assert report["evaluator_evidence"]["truthful_absence"]["accepted"] is True
    assert report["accepted_absence_residuals"] == [
        "missing stage evidence for child scope 2026-04-26-autonomous-auto-t-029-1"
    ]
    assert report["traceability_scorecard"]["stage_evidence"] == "repo_native"
    assert report["traceability_scorecard"]["evaluator_evidence"] == "repo_native"
    assert report["traceability_scorecard"]["overall_provenance"] == "repo_native"
    assert report["next_route_recommendation"]["route"] == "stop"
    assert report["residual_risks"] == []


def test_build_campaign_audit_preserves_ledger_lock_file(tmp_path: Path) -> None:
    paths = _write_complete_campaign(tmp_path)
    lock_path = paths["ledger_path"].with_name(f"{paths['ledger_path'].name}.lock")
    lock_path.write_text("sentinel lock content\n", encoding="utf-8")

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert lock_path.read_text(encoding="utf-8") == "sentinel lock content\n"
    assert report["next_route_recommendation"]["route"] == "stop"


def test_truthful_inline_absence_does_not_mask_partial_stage_conflict(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    ledger = yaml.safe_load(paths["ledger_path"].read_text(encoding="utf-8"))
    ledger["runs"][0]["stage_summaries"] = [
        summary
        for summary in ledger["runs"][0]["stage_summaries"]
        if summary["stage_id"] != "autonomous_auto_s1_architect"
    ]
    _write_yaml(paths["ledger_path"], ledger)
    _write_jsonl(
        paths["inbox_dir"] / "session-reflection-2026-04-26-inline-exception.jsonl",
        [
            {
                "id": "inline-exception-verified",
                "session_id": LOOP_ID,
                "learning_state": "implemented",
                "summary": (
                    "Implemented inline execution exception: no fake stage evidence "
                    "should be backfilled when subagents were not spawned."
                ),
                "tags": ["autonomous-auto", "learning-closure", "stage-evidence"],
            }
        ],
    )

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)

    assert report["stage_evidence"]["provenance"] == "conflict"
    assert report["traceability_scorecard"]["stage_evidence"] == "conflict"
    assert report["next_route_recommendation"]["route"] == "repair_evidence"
    assert any("missing stage summary" in risk for risk in report["residual_risks"])


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


def test_build_campaign_audit_includes_learning_harvester_routes(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    state = yaml.safe_load(paths["state_path"].read_text(encoding="utf-8"))
    state["autonomy_budget"] = {
        "approval_basis": "Approved autonomous-auto internal self-heal campaign."
    }
    _write_yaml(paths["state_path"], state)
    _write_jsonl(
        paths["inbox_dir"] / "session-reflection-2026-04-26-harvester.jsonl",
        [
            {
                "id": "safe-route-failure",
                "session_id": LOOP_ID,
                "learning_state": "captured",
                "summary": "low autonomous-auto lifecycle-route readiness defect",
                "tags": ["autonomous-auto", "learning-closure"],
            },
            {
                "id": "safe-route-failure-duplicate",
                "session_id": LOOP_ID,
                "learning_state": "captured",
                "summary": "low autonomous-auto lifecycle-route readiness defect",
                "tags": ["autonomous-auto", "learning-closure"],
            },
            {
                "id": "protected-network",
                "session_id": LOOP_ID,
                "learning_state": "captured",
                "summary": "network credential protected improvement must stop",
                "tags": ["autonomous-auto", "learning-closure"],
            },
            {
                "id": "cross-system",
                "session_id": LOOP_ID,
                "learning_state": "captured",
                "summary": "cross-system user-governed improvement belongs in inbox/intake",
                "tags": ["autonomous-auto", "learning-closure"],
            },
            {
                "id": "stale-signal",
                "session_id": LOOP_ID,
                "learning_state": "stale_or_rejected",
                "summary": "stale duplicate learning signal",
                "tags": ["autonomous-auto", "learning-closure"],
            },
        ],
    )

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)
    harvester = report["learning_harvester"]
    decisions = harvester["decisions"]

    assert harvester["write_authority"] == "advisory_only_strategy_preflight_still_required"
    assert harvester["route_counts"]["auto_self_heal_now"] >= 1
    assert harvester["route_counts"]["human_gate_required"] == 1
    assert harvester["route_counts"]["defer_to_intake"] == 1
    assert harvester["route_counts"]["stale_or_rejected"] == 1
    assert (
        sum(
            1
            for decision in decisions
            if decision["signal_id"] == "low autonomous-auto lifecycle-route readiness defect"
        )
        == 1
    )
    assert any(
        decision["protected_gate_required"] and decision["route"] == "human_gate_required"
        for decision in decisions
    )


def test_learning_harvester_reads_proposals_route_failures_and_cross_source_duplicates(
    tmp_path: Path,
) -> None:
    paths = _write_complete_campaign(tmp_path)
    state = yaml.safe_load(paths["state_path"].read_text(encoding="utf-8"))
    state["autonomy_budget"] = {
        "approval_basis": "Approved autonomous-auto internal self-heal campaign."
    }
    state["history"].append(
        {
            "strategy_preflight": {
                "verdict": "stop_route_conflict",
                "mismatch_reason": "strategy-preflight lifecycle-route failure",
            }
        }
    )
    _write_yaml(paths["state_path"], state)
    _write_jsonl(
        paths["episodes_path"],
        [
            {
                "id": "shared-signal-episode",
                "session_id": LOOP_ID,
                "learning_state": "captured",
                "summary": "shared autonomous-auto route failure signal",
                "tags": ["autonomous-auto", "learning-closure"],
            }
        ],
    )
    _write_jsonl(
        paths["inbox_dir"] / "session-reflection-2026-04-26-shared.jsonl",
        [
            {
                "id": "shared-signal-inbox",
                "session_id": LOOP_ID,
                "learning_state": "captured",
                "summary": "shared autonomous-auto route failure signal",
                "tags": ["autonomous-auto", "learning-closure"],
            }
        ],
    )
    _write_yaml(
        tmp_path / ".azoth/proposals/autonomous-auto-learning-proposal.yaml",
        {
            "title": "Autonomous-auto proposal refinement learning output",
            "summary": "proposal refinement output for autonomous-auto learning closure",
            "loop_id": LOOP_ID,
            "status": "draft",
        },
    )

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)
    decisions = report["learning_harvester"]["decisions"]

    assert report["source_artifacts"]["proposals"]["exists"] is True
    assert any(
        ".azoth/proposals/autonomous-auto-learning-proposal.yaml" in decision["source_refs"]
        for decision in decisions
    )
    assert any(
        ".azoth/autonomous-loop-state.local.yaml" in source
        for decision in decisions
        for source in decision["source_refs"]
    )
    shared = [
        decision
        for decision in decisions
        if decision["signal_id"] == "shared autonomous-auto route failure signal"
    ]
    assert len(shared) == 1
    assert len(shared[0]["source_refs"]) == 2


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

    assert [scope["session_id"] for scope in report["child_scopes"]] == [child_session_id]
    assert report["child_scopes"][0]["action"] == "ship_task"
    assert report["stage_evidence"]["provenance"] == "repo_native"
    assert (
        report["stage_evidence"]["stages"]["autonomous_auto_s4_evaluator"]["run_id"]
        == child_session_id
    )
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
    assert report["child_scopes"][0]["changed_files"] == ["scripts/autonomous_campaign_audit.py"]
    assert report["stage_evidence"]["provenance"] == "repo_native"
    assert (
        report["stage_evidence"]["stages"]["autonomous_auto_s2_evaluator"]["run_id"]
        == CHILD_SESSION_ID
    )
    assert report["evaluator_evidence"]["provenance"] == "repo_native"
    assert report["evaluator_evidence"]["structured_scores"] == [0.84]
    assert report["evaluator_evidence"]["ux_scorecards"] == [
        {"operator_traceability": "yellow", "learning_closure": "red"}
    ]
    assert report["verification_commands"] == [
        "python3 scripts/autonomous_loop.py campaign-audit --loop-id parent-campaign-loop --json"
    ]
    assert "missing run ledger entry for campaign" not in report["residual_risks"]


def test_campaign_audit_cli_json_and_plain_are_read_only(tmp_path: Path, capsys) -> None:
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
    assert "Executive read: Campaign vision_realized with green UX vision evidence." in out
    assert "Quality: Evaluator scores: 0.91; UX Anchor Scorecard present." in out
    assert "UX Anchor Fit: green" in out
    assert "Operator next move: stop" in out
    assert _snapshot_files(tmp_path) == before


def test_build_campaign_audit_includes_nightly_bundle_contract(tmp_path: Path) -> None:
    paths = _write_complete_campaign(tmp_path)

    report = build_campaign_audit(tmp_path, LOOP_ID, **paths)
    bundle = report["nightly_audit_bundle"]
    contract = bundle["approval_contract"]

    assert bundle["schema_version"] == 1
    assert bundle["bundle_id"].startswith("nightly-automation-audit-")
    assert bundle["validation"]["read_only"] is True
    assert bundle["validation"]["applies_actions"] is False
    assert "worktree_sync" in bundle["validation"]["forbidden_side_effects"]
    assert contract["apply_authority"] is False
    assert contract["side_effects_authorized"] == []
    assert "approve the audit" in contract["invalid_reply_examples"]
    assert bundle["items"]
    for item in bundle["items"]:
        assert item["item_id"].startswith("A-")
        assert item["item_class"] in {
            "insight-only",
            "proposal",
            "code-salvage",
            "cleanup-only",
            "no-action",
        }
        assert item["recommended_disposition"] in {
            "approve",
            "skip",
            "defer",
            "cleanup",
            "blocked",
        }
        assert item["source_refs"]
        assert item["blocked_alternatives"]
    assert "does not run apply" in bundle["recommended_operator_reply"]


def test_automation_audit_bundle_cli_json_and_plain_are_read_only(tmp_path: Path, capsys) -> None:
    paths = _write_complete_campaign(tmp_path)
    before = _snapshot_files(tmp_path)

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "automation-audit-bundle",
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
    assert payload["validation"]["read_only"] is True
    assert payload["approval_contract"]["apply_authority"] is False

    assert (
        autonomous_loop.main(
            [
                "--root",
                str(tmp_path),
                "automation-audit-bundle",
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
    assert "Automation audit bundle:" in out
    assert "Recommended reply:" in out
    assert "Read-only: yes" in out
    assert _snapshot_files(tmp_path) == before


def test_nightly_bundle_replays_2026_04_21_audit_without_direct_integration() -> None:
    report = {
        "generated_at": "2026-04-21T18:20:00Z",
        "campaign": {
            "loop_id": "automation-worktree-audit-20260421",
            "branch": "phase/v0.2.0-p3",
        },
        "traceability_scorecard": {"overall_provenance": "repo_native"},
        "learning_harvester": {
            "decisions": [
                {
                    "signal_id": "worktree-1325-yaml-loader-salvage",
                    "source_refs": [
                        ".azoth/handoffs/2026-04-21-automation-worktree-audit-architect-note.md"
                    ],
                    "dedupe_key": "stale detached worktree 1325 direct integration rejection",
                    "severity": "medium",
                    "route": "capture_only",
                    "selected_action": "capture_only",
                    "rejected_alternatives": ["direct integration"],
                    "verification_requirement": (
                        "verify replay from the current target branch before producer handoff"
                    ),
                    "residual_risk": (
                        "stale detached worktree cannot be integrated directly through worktree-sync"
                    ),
                },
                {
                    "signal_id": "nightly-ci-preflight-insight",
                    "source_refs": [
                        ".azoth/inbox/processed/session-reflection-automation-audit-2026-04-21.jsonl:1"
                    ],
                    "dedupe_key": "pre-ci fast-fail insight-harvest candidate",
                    "severity": "medium",
                    "route": "capture_only",
                    "selected_action": "capture_only",
                    "rejected_alternatives": ["direct_m3_write"],
                    "verification_requirement": "verify source refs before governed intake capture",
                },
                {
                    "signal_id": "skill-progression-seam-coverage-insight",
                    "source_refs": [
                        ".azoth/inbox/processed/session-reflection-automation-audit-2026-04-21.jsonl:2"
                    ],
                    "dedupe_key": "adapter parity and seam coverage insight-harvest candidate",
                    "severity": "medium",
                    "route": "capture_only",
                    "selected_action": "capture_only",
                    "rejected_alternatives": ["direct_backlog_write"],
                    "verification_requirement": "verify source refs before governed intake capture",
                },
            ]
        },
    }

    bundle = build_nightly_automation_audit_bundle(
        report,
        audit_window={
            "start": "2026-04-21T18:00:00Z",
            "end": "2026-04-21T18:20:00Z",
        },
        target_branch="phase/v0.2.0-p3",
        generated_at="2026-04-21T18:20:00Z",
    )

    code_item = next(item for item in bundle["items"] if item["item_class"] == "code-salvage")
    insight_items = [item for item in bundle["items"] if item["item_class"] == "insight-only"]
    assert code_item["recommended_disposition"] == "defer"
    assert code_item["apply_target"] == "future_fresh_producer_handoff_request"
    assert "direct_integration" in code_item["blocked_alternatives"]
    assert "worktree_sync_during_audit" in code_item["blocked_alternatives"]
    assert "fresh producer replay" in code_item["least_powerful_action"]
    assert len(insight_items) == 2
    assert {item["recommended_disposition"] for item in insight_items} == {"approve"}
    assert {item["apply_target"] for item in insight_items} == {"future_inbox_intake_candidate"}
    assert bundle["approval_contract"]["apply_authority"] is False
    assert bundle["validation"]["forbidden_side_effects"] == [
        "producer_worktree_creation",
        "inbox_write",
        "worktree_sync",
        "apply_routing",
        "handoff_integration",
        "trusted_source_registry_change",
        "roadmap_or_backlog_mutation",
    ]

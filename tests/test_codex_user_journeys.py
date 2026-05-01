from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from codex_journey_harness import (
    REPO,
    capture_plain_welcome,
    copy_codex_router_fixture,
    extract_start_block,
    future_timestamp,
    run_router,
    seed_azoth_repo,
)

sys.path.insert(0, str(REPO / "scripts"))

import do_closeout  # noqa: E402
import park_session  # noqa: E402
from codex_control_plane import directive_for_prompt  # noqa: E402

DELIVER_FULL_STAGE2_RULE = "deliver_full_s2_architect"
DELIVER_FULL_STAGE2_NEGATIVE = "inline architecture prose does not satisfy Stage 2"
DELIVER_FULL_STAGE2_DECLARATION_ONLY = (
    "Declaration, gate write, or status card does not count as Stage 2 execution"
)


def test_pipeline_aliases_normalize_to_the_same_start_centered_route() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    canonical = "$azoth-start pipeline_command=deliver-full harden codex adapter"
    prompts = (
        "/deliver-full harden codex adapter",
        "$azoth-deliver-full harden codex adapter",
        "$azoth-start pipeline_command=deliver-full harden codex adapter",
    )

    for prompt in prompts:
        payload = run_router(router, prompt, cwd=REPO)
        hook = payload["hookSpecificOutput"]
        assert hook["updatedInput"] == canonical
        assert "pipeline_command=deliver-full" in hook["additionalContext"]
        assert DELIVER_FULL_STAGE2_RULE in hook["additionalContext"]
        assert DELIVER_FULL_STAGE2_NEGATIVE in hook["additionalContext"]
        assert DELIVER_FULL_STAGE2_DECLARATION_ONLY in hook["additionalContext"]


@pytest.mark.parametrize(
    "prompt",
    (
        "/deliver-full harden codex adapter",
        "$azoth-deliver-full harden codex adapter",
        "$azoth-start pipeline_command=deliver-full harden codex adapter",
    ),
)
def test_governed_deliver_full_aliases_share_stage2_invariant(prompt: str) -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    payload = run_router(router, prompt, cwd=REPO)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert DELIVER_FULL_STAGE2_RULE in ctx
    assert DELIVER_FULL_STAGE2_NEGATIVE in ctx
    assert DELIVER_FULL_STAGE2_DECLARATION_ONLY in ctx


def test_freeform_continue_and_new_goal_receive_continuity_guidance(tmp_path: Path) -> None:
    session_id = "sess-live"
    seed_azoth_repo(
        tmp_path,
        scope={
            "approved": True,
            "expires_at": future_timestamp(hours=2),
            "goal": "BL-123: Continue calm flow work",
            "session_id": session_id,
            "backlog_id": "BL-123",
            "governance_mode": "standard",
            "pipeline_command": "auto",
        },
        session_state={
            "session_id": session_id,
            "state": "active",
            "last_ide": "codex",
            "timestamp": "2026-04-15T00:00:00+00:00",
            "active_task": "In progress",
            "active_files": [],
            "pending_decisions": [],
            "approved_scope": "BL-123: Continue calm flow work",
            "next_action": "Continue current scope",
        },
    )

    continue_directive = directive_for_prompt(tmp_path, "continue this task")
    new_goal_directive = directive_for_prompt(
        tmp_path, "start a new goal: BL-456 modernize calm flow"
    )

    assert continue_directive is not None
    assert "resume/continue decision" in continue_directive.additional_context
    assert new_goal_directive is not None
    assert "replace decision" in new_goal_directive.additional_context


def test_freeform_continue_without_live_session_stays_noop(tmp_path: Path) -> None:
    directive = directive_for_prompt(tmp_path, "continue this task")

    assert directive is None
    assert not (tmp_path / ".azoth" / "session-gate.json").exists()


def test_freeform_exploratory_goal_opens_session_gate_and_routes_through_start(
    tmp_path: Path,
) -> None:
    router = copy_codex_router_fixture(tmp_path, with_agents=True)
    payload = run_router(router, "explore the closeout UX architecture", cwd=tmp_path)
    hook = payload["hookSpecificOutput"]

    assert hook["updatedInput"] == "$azoth-start explore the closeout UX architecture"
    assert "Exploratory intent detected" in hook["additionalContext"]

    session_gate = json.loads(
        (tmp_path / ".azoth" / "session-gate.json").read_text(encoding="utf-8")
    )
    assert session_gate["status"] == "active"
    assert session_gate["session_mode"] == "exploratory"
    assert session_gate["goal"] == "explore the closeout UX architecture"

    scope_gate = json.loads((tmp_path / ".azoth" / "scope-gate.json").read_text(encoding="utf-8"))
    assert scope_gate == {}


def test_profile_advisory_surfaces_read_only_without_changing_start_route(
    tmp_path: Path,
) -> None:
    router = copy_codex_router_fixture(tmp_path, with_agents=True)
    payload = run_router(router, "explain current repo status", cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]

    assert hook["updatedInput"] == "$azoth-start explain current repo status"
    assert (
        "profile_suggestion: stock-lite" in ctx or "profile_suggestion: azoth-lite" in ctx
    )
    assert "side_effect_class: read_only" in ctx
    assert "stop_state: done" in ctx


def test_profile_advisory_surfaces_focused_verification_without_changing_start_route(
    tmp_path: Path,
) -> None:
    router = copy_codex_router_fixture(tmp_path, with_agents=True)
    prompt = "diagnose by running focused verification for tests/test_azoth_lite_classifier.py"
    payload = run_router(router, prompt, cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]

    assert hook["updatedInput"] == f"$azoth-start {prompt}"
    assert "profile_suggestion: azoth-lite" in ctx
    assert "side_effect_class: read_only" in ctx
    assert "stop_state: done" in ctx


def test_profile_advisory_surfaces_local_edit_without_changing_d23_route(
    tmp_path: Path,
) -> None:
    router = copy_codex_router_fixture(tmp_path, with_agents=True)
    prompt = "fix typo in scripts/example_helper.py"
    payload = run_router(router, prompt, cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]

    assert hook["updatedInput"] == f"$azoth-start pipeline_command=auto {prompt}"
    assert "Delivery intent detected" in ctx
    assert "profile_suggestion: azoth-lite" in ctx
    assert "side_effect_class: local_edit" in ctx
    assert "stop_state: done" in ctx


def test_profile_advisory_escalates_governed_state_without_changing_d23_route(
    tmp_path: Path,
) -> None:
    router = copy_codex_router_fixture(tmp_path, with_agents=True)
    prompt = "update .azoth/roadmap.yaml task state"
    payload = run_router(router, prompt, cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]

    assert hook["updatedInput"] == f"$azoth-start pipeline_command=auto {prompt}"
    assert "profile_suggestion: azoth-full" in ctx
    assert "side_effect_class: governed_state" in ctx
    assert "stop_state: escalate" in ctx
    assert "escalation_reasons: governed_state_change" in ctx
    assert "handoff_note: stop before mutation; recommended_route: azoth-full" in ctx


def test_profile_advisory_escalates_finality_without_changing_routed_command(
    tmp_path: Path,
) -> None:
    router = copy_codex_router_fixture(tmp_path, with_agents=True)
    prompt = "update final delivery package status"
    payload = run_router(router, prompt, cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]

    assert hook["updatedInput"] == f"$azoth-start pipeline_command=auto {prompt}"
    assert "profile_suggestion: azoth-full" in ctx
    assert "side_effect_class: external_or_destructive" in ctx
    assert "stop_state: escalate" in ctx
    assert "finality_or_packaging_requested" in ctx
    assert "handoff_note: stop before mutation; recommended_route: azoth-full" in ctx


@pytest.mark.parametrize(
    ("prompt", "expected_input"),
    [
        ("/auto investigate drift", "$azoth-start pipeline_command=auto investigate drift"),
        ("/start next", "$azoth-start next"),
        ("/session-closeout", "$azoth-session-closeout"),
    ],
)
def test_profile_advisory_keeps_existing_command_routes_unchanged(
    tmp_path: Path,
    prompt: str,
    expected_input: str,
) -> None:
    router = copy_codex_router_fixture(tmp_path, with_agents=True)
    payload = run_router(router, prompt, cwd=tmp_path)
    hook = payload["hookSpecificOutput"]

    assert hook["updatedInput"] == expected_input
    assert "profile_suggestion:" in hook["additionalContext"]


def test_delivery_route_carries_matching_exploratory_session_id_in_routed_input(
    tmp_path: Path,
) -> None:
    seed_azoth_repo(
        tmp_path,
        session_gate={
            "session_id": "sess-explore",
            "goal": "fix closeout control plane",
            "session_mode": "exploratory",
            "opened_at": "2026-04-20T10:00:00+00:00",
            "updated_at": "2026-04-20T10:00:00+00:00",
            "status": "active",
            "approved_by": "system",
        },
    )

    directive = directive_for_prompt(tmp_path, "fix closeout control plane")
    assert directive is not None
    assert (
        directive.updated_input
        == "$azoth-start pipeline_command=auto session_id=sess-explore fix closeout control plane"
    )
    assert "Carry its `session_id` forward" in directive.additional_context


def test_start_route_preserves_explicit_session_id_in_canonical_input() -> None:
    directive = directive_for_prompt(
        REPO,
        "$azoth-start pipeline_command=auto session_id=sess-explore fix closeout control plane",
    )

    assert directive is not None
    assert (
        directive.updated_input
        == "$azoth-start pipeline_command=auto session_id=sess-explore fix closeout control plane"
    )


def test_start_route_respects_explicit_session_id_for_continuity_conflicts(tmp_path: Path) -> None:
    seed_azoth_repo(
        tmp_path,
        scope={
            "approved": True,
            "expires_at": future_timestamp(hours=2),
            "goal": "BL-123: Continue calm flow work",
            "session_id": "sess-live",
            "backlog_id": "BL-123",
            "governance_mode": "standard",
            "pipeline_command": "auto",
        },
    )

    directive = directive_for_prompt(
        tmp_path,
        "$azoth-start pipeline_command=auto session_id=sess-other BL-123: Continue calm flow work",
    )

    assert directive is not None
    assert "Do not silently retarget it" in directive.additional_context


def test_normalized_governed_state_renders_pipeline_gate_and_start_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = "sess-governed"
    seed_azoth_repo(
        tmp_path,
        scope={
            "approved": True,
            "expires_at": "2099-04-18T11:00:00+00:00",
            "goal": "BL-321: Governed journey test",
            "session_id": session_id,
            "backlog_id": "BL-321",
            "governance_mode": "governed",
            "pipeline_command": "deliver-full",
        },
        pipeline_gate={
            "approved": True,
            "session_id": session_id,
            "expires_at": "2099-04-18T10:00:00+00:00",
            "pipeline_command": "deliver-full",
        },
        session_state={
            "session_id": session_id,
            "state": "active",
            "last_ide": "codex",
            "timestamp": "2099-04-18T09:00:00+00:00",
            "active_task": "Governed work in progress",
            "active_files": [],
            "pending_decisions": [],
            "approved_scope": "BL-321: Governed journey test",
            "next_action": "Continue governed scope",
        },
    )

    out = capture_plain_welcome(tmp_path, monkeypatch)
    assert "Pipeline gate: OK  (deliver-full)" in out
    assert "Continuity: OK  (sess-governed)" in out
    start_block = extract_start_block(out)
    assert "resume   → continue approved scope" in start_block
    assert "codex    → primary: /skills or $azoth-resume / $azoth-next / $azoth-auto" in start_block


def test_resume_closeout_loop_reports_truthful_handoff_when_stage_evidence_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_id = "sess-governed"
    seed_azoth_repo(
        tmp_path,
        scope={
            "approved": True,
            "expires_at": "2099-04-18T11:00:00+00:00",
            "goal": "BL-654: Governed closeout journey",
            "session_id": session_id,
            "backlog_id": "BL-654",
            "governance_mode": "governed",
            "pipeline_command": "deliver-full",
        },
        pipeline_gate={
            "approved": True,
            "session_id": session_id,
            "expires_at": "2099-04-18T10:00:00+00:00",
            "pipeline_command": "deliver-full",
        },
        session_state={
            "session_id": session_id,
            "state": "active",
            "last_ide": "codex",
            "timestamp": "2099-04-18T09:00:00+00:00",
            "active_task": "Governed closeout journey",
            "active_files": [],
            "pending_decisions": [],
            "approved_scope": "BL-654: Governed closeout journey",
            "next_action": "Finish closeout",
            "pipeline": "deliver-full",
            "pipeline_position": 4,
            "current_stage_id": "closeout_ready",
            "completed_stages": ["planner", "builder", "reviewer_gate"],
            "pending_stages": [],
            "active_run_id": "run-654",
        },
        run_ledger={
            "schema_version": 1,
            "sessions": [
                {
                    "session_id": session_id,
                    "backlog_id": "BL-654",
                    "goal": "BL-654: Governed closeout journey",
                    "status": "active",
                    "ide": "codex",
                    "next_action": "Finish closeout",
                    "updated_at": "2099-04-18T09:00:00+00:00",
                    "active_run_id": "run-654",
                }
            ],
            "runs": [
                {
                    "run_id": "run-654",
                    "session_id": session_id,
                    "backlog_id": "BL-654",
                    "ide": "codex",
                    "mode": "deliver-full",
                    "goal": "BL-654: Governed closeout journey",
                    "status": "paused",
                    "created_at": "2099-04-18T09:00:00+00:00",
                    "updated_at": "2099-04-18T09:00:00+00:00",
                    "next_action": "Finish closeout",
                    "stages_completed": ["planner", "builder", "reviewer_gate"],
                    "stage_spawns": [
                        {
                            "run_id": "run-654",
                            "stage_id": "planner",
                            "subagent_type": "planner",
                            "trigger": "context-isolation",
                            "role_hint": (
                                "Agent(subagent_type=planner): Plan governed closeout "
                                "journey - trigger: context-isolation"
                            ),
                            "dependency_summary_refs": [],
                            "spawned_at": "2099-04-18T09:01:00+00:00",
                        },
                        {
                            "run_id": "run-654",
                            "stage_id": "builder",
                            "subagent_type": "builder",
                            "trigger": "context-budget",
                            "role_hint": (
                                "Agent(subagent_type=builder): Implement governed "
                                "closeout journey - trigger: context-budget"
                            ),
                            "dependency_summary_refs": ["planner"],
                            "spawned_at": "2099-04-18T09:02:00+00:00",
                        },
                        {
                            "run_id": "run-654",
                            "stage_id": "reviewer_gate",
                            "subagent_type": "reviewer",
                            "trigger": "review-independence",
                            "role_hint": (
                                "Agent(subagent_type=reviewer): Review governed "
                                "closeout journey - trigger: review-independence"
                            ),
                            "dependency_summary_refs": ["planner", "builder"],
                            "spawned_at": "2099-04-18T09:03:00+00:00",
                        },
                    ],
                    "stage_summaries": [
                        {
                            "run_id": "run-654",
                            "stage_id": "planner",
                            "subagent_type": "planner",
                            "trigger": "context-isolation",
                            "role_hint": (
                                "Agent(subagent_type=planner): Plan governed closeout "
                                "journey - trigger: context-isolation"
                            ),
                            "dependency_summary_refs": [],
                            "summary_recorded_at": "2099-04-18T09:04:00+00:00",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                        },
                        {
                            "run_id": "run-654",
                            "stage_id": "builder",
                            "subagent_type": "builder",
                            "trigger": "context-budget",
                            "role_hint": (
                                "Agent(subagent_type=builder): Implement governed "
                                "closeout journey - trigger: context-budget"
                            ),
                            "dependency_summary_refs": ["planner"],
                            "summary_recorded_at": "2099-04-18T09:05:00+00:00",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                        },
                        {
                            "run_id": "run-654",
                            "stage_id": "reviewer_gate",
                            "subagent_type": "reviewer",
                            "trigger": "review-independence",
                            "role_hint": (
                                "Agent(subagent_type=reviewer): Review governed "
                                "closeout journey - trigger: review-independence"
                            ),
                            "dependency_summary_refs": ["planner", "builder"],
                            "summary_recorded_at": "2099-04-18T09:06:00+00:00",
                            "summary_status": "complete",
                            "summary_disposition": "approved",
                        },
                    ],
                    "waves": [],
                    "branches": [],
                }
            ],
            "write_claim": {
                "session_id": session_id,
                "expires_at": "2099-04-18T11:00:00+00:00",
                "acquired_at": "2099-04-18T09:00:00+00:00",
            },
        },
        final_delivery_approvals=[
            {
                "session_id": session_id,
                "gate": "final-delivery",
                "actor_type": "human",
                "approved": True,
                "decision": "approved",
            }
        ],
    )

    monkeypatch.setattr(
        do_closeout.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )
    monkeypatch.setattr(
        do_closeout,
        "write_claude_memory_mirror",
        lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("blocked")),
    )

    do_closeout.run_closeout(tmp_path)
    out = capsys.readouterr().out
    assert ".azoth/session-state.md" in out
    assert "W3 deferred" in out
    assert "Next operator action:" in out

    welcome_out = capture_plain_welcome(tmp_path, monkeypatch)
    assert "Continuity: MISMATCH" not in welcome_out
    assert "Scope: NONE  (run /next to open a scope card)" in welcome_out


def test_router_level_closeout_entry_stays_explicit(tmp_path: Path) -> None:
    router = copy_codex_router_fixture(tmp_path, with_agents=True)
    payload = run_router(router, "/session-closeout", cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    assert hook["updatedInput"] == "$azoth-session-closeout"
    assert ".azoth/session-state.md" in hook["additionalContext"]
    assert "W3 deferred" in hook["additionalContext"]


@pytest.mark.parametrize(
    ("prompt", "expected_input"),
    [
        ("/start next", "$azoth-start next"),
        ("/start closeout", "$azoth-session-closeout"),
        (
            "/start pipeline_command=deliver-full govern kernel change",
            "$azoth-start pipeline_command=deliver-full govern kernel change",
        ),
    ],
)
def test_start_variants_normalize_to_calm_flow(
    prompt: str,
    expected_input: str,
) -> None:
    directive = directive_for_prompt(REPO, prompt)
    assert directive is not None
    assert directive.updated_input == expected_input


def _seed_replayed_human_gate_repo(tmp_path: Path) -> str:
    session_id = "sess-replay"
    seed_azoth_repo(
        tmp_path,
        scope={
            "approved": False,
            "expires_at": "2099-04-18T11:00:00+00:00",
            "goal": "T-006: Replay continuity journey",
            "session_id": session_id,
            "backlog_id": "T-006",
            "governance_mode": "governed",
            "pipeline_command": "deliver-full",
        },
        session_state={
            "session_id": session_id,
            "state": "parked",
            "last_ide": "codex",
            "timestamp": "2099-04-18T09:00:00+00:00",
            "active_task": "Parked replay queue",
            "active_files": [],
            "pending_decisions": [],
            "approved_scope": "T-006: Replay continuity journey",
            "next_action": "Resume later with /resume sess-replay.",
            "pipeline": "deliver-full",
            "pipeline_position": 5,
            "current_stage_id": "deliver_full_s5",
            "completed_stages": [
                "deliver_full_s2_architect",
                "deliver_full_s3",
                "deliver_full_s4",
            ],
            "pending_stages": [
                "deliver_full_s4",
                "deliver_full_s5",
                "deliver_full_s6",
                "deliver_full_s7_architect_review",
            ],
            "pause_reason": "human-gate",
            "active_run_id": "run-replay",
        },
        backlog_items=[
            {
                "id": "T-006",
                "status": "active",
                "title": "Replay continuity journey",
                "target_layer": "M1",
                "delivery_pipeline": "governed",
            }
        ],
        run_ledger={
            "schema_version": 1,
            "sessions": [
                {
                    "session_id": session_id,
                    "backlog_id": "T-006",
                    "goal": "T-006: Replay continuity journey",
                    "status": "parked",
                    "ide": "codex",
                    "next_action": "Resume later with /resume sess-replay.",
                    "updated_at": "2099-04-18T09:00:00+00:00",
                    "active_run_id": "run-replay",
                }
            ],
            "runs": [
                {
                    "run_id": "run-replay",
                    "session_id": session_id,
                    "backlog_id": "T-006",
                    "ide": "codex",
                    "mode": "deliver-full",
                    "goal": "T-006: Replay continuity journey",
                    "status": "paused",
                    "created_at": "2099-04-18T09:00:00+00:00",
                    "updated_at": "2099-04-18T09:00:00+00:00",
                    "next_action": "Await human approval before replay.",
                    "stages_completed": [
                        "deliver_full_s2_architect",
                        "deliver_full_s3",
                        "deliver_full_s4",
                    ],
                    "active_stage_id": "deliver_full_s5",
                    "pending_stage_ids": [
                        "deliver_full_s4",
                        "deliver_full_s5",
                        "deliver_full_s6",
                        "deliver_full_s7_architect_review",
                    ],
                    "pause_reason": "human-gate",
                    "waves": [],
                    "branches": [],
                }
            ],
        },
    )
    return session_id


def _stub_restore_pipeline_gate(
    repo_root: Path,
    *,
    session_id: str,
    pipeline: str,
    expires_at: str,
    require: bool = True,
    research_required: bool = False,
    research_evidence: dict | None = None,
) -> None:
    del require
    payload = {
        "session_id": session_id,
        "pipeline": pipeline,
        "approved": True,
        "expires_at": expires_at,
        "opened_at": "2099-04-18T09:00:00+00:00",
        "research_required": research_required,
    }
    if research_evidence is not None:
        payload["research_evidence"] = research_evidence
    (repo_root / ".azoth" / "pipeline-gate.json").write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )


def test_welcome_surfaces_saved_human_gate_replay_target_after_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = _seed_replayed_human_gate_repo(tmp_path)
    monkeypatch.setattr(park_session, "_restore_pipeline_gate", _stub_restore_pipeline_gate)

    result = park_session.resume_session(
        tmp_path,
        session_id=session_id,
        ide="codex",
        timestamp="2099-04-18T10:00:00+00:00",
    )

    assert result["human_gate"] is True
    directive = directive_for_prompt(tmp_path, "continue this task")
    assert directive is not None
    assert "resume/continue decision" in directive.additional_context

    out = capture_plain_welcome(tmp_path, monkeypatch)
    assert "Continuity: OK  (sess-replay)" in out
    assert "deliver_full_s4" in out


def test_welcome_surfaces_promoted_revision_without_stale_human_gate_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = _seed_replayed_human_gate_repo(tmp_path)
    monkeypatch.setattr(park_session, "_restore_pipeline_gate", _stub_restore_pipeline_gate)

    result = park_session.resume_session(
        tmp_path,
        session_id=session_id,
        ide="codex",
        timestamp="2099-04-18T10:05:00+00:00",
        approve_human_gate=True,
    )

    assert result["human_gate"] is False
    assert result["current_stage_id"] == "deliver_full_s4"

    out = capture_plain_welcome(tmp_path, monkeypatch)
    assert "deliver_full_s4" in out
    assert "Resume at human gate for stage `deliver_full_s5`" not in out

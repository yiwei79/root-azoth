from __future__ import annotations

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
from codex_control_plane import directive_for_prompt  # noqa: E402


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


def test_resume_closeout_loop_reports_truthful_handoff_and_no_false_mismatch(
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
            "current_stage_id": "reviewer_gate",
            "completed_stages": ["planner", "builder"],
            "pending_stages": ["closeout"],
            "pause_reason": "human-gate",
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
                    "stages_completed": ["planner", "builder"],
                    "active_stage_id": "reviewer_gate",
                    "pending_stage_ids": ["closeout"],
                    "pause_reason": "human-gate",
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

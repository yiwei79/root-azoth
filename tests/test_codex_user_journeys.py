"""Journey-level Codex calm-flow simulations."""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_journey_harness import (  # noqa: E402
    copy_codex_router_fixture,
    future_timestamp,
    run_router,
    seed_azoth_repo,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import do_closeout  # noqa: E402
import park_session  # noqa: E402
import welcome  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def _capture_plain_welcome(
    repo_root: Path,
    monkeypatch,
    *,
    now: datetime | None = None,
) -> str:
    buf = io.StringIO()
    monkeypatch.setattr(welcome, "ROOT", repo_root)
    monkeypatch.setattr(welcome, "console", Console(file=buf, force_terminal=False, width=220))
    monkeypatch.setattr(welcome, "git_info", lambda: ("root-azoth", "main"))
    if now is not None:
        monkeypatch.setattr(welcome, "utc_now", lambda: now)
    welcome.render_dashboard_plain(welcome.gather_dashboard_state())
    return buf.getvalue()


def _extract_start_block(text: str) -> str:
    prefix = "── START (what to type) ──\n"
    assert prefix in text
    return prefix + text.split(prefix, 1)[1].split("\n" + ("═" * 72), 1)[0].rstrip()


def _closeout_semantics(*, next_action: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "session_summary": {
            "summary": "Completed the governed Codex journey proof and refreshed the operator handoff.",
        },
        "episode": {
            "type": "success",
            "summary": "Completed the governed Codex journey proof and refreshed the operator handoff.",
            "lessons": ["Codex journey tests should assert the operator-facing handoff."],
            "tags": ["codex-journey"],
            "context": {"surface": "codex"},
        },
        "handoff": {
            "next_action": next_action,
            "pending_decisions": ["Confirm whether the docs batch is ready to promote."],
            "files_changed": ["tests/test_codex_user_journeys.py"],
        },
        "w3": {
            "mode": "defer",
            "reason": "Codex keeps W3 supplemental during journey simulation.",
        },
    }


def test_pipeline_aliases_normalize_to_the_same_start_centered_route() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    expected = "$azoth-start pipeline_command=deliver-full harden codex adapter"
    for prompt in (
        "/deliver-full harden codex adapter",
        "$azoth-deliver-full harden codex adapter",
        "/start pipeline_command=deliver-full harden codex adapter",
    ):
        payload = run_router(router, prompt, cwd=REPO)
        hook = payload["hookSpecificOutput"]
        assert hook["updatedInput"] == expected
        assert "pipeline_command=deliver-full" in hook["additionalContext"]


def test_freeform_continue_and_new_goal_receive_continuity_guidance(tmp_path: Path) -> None:
    router = copy_codex_router_fixture(tmp_path, "start")
    seed_azoth_repo(
        tmp_path,
        scope={
            "approved": True,
            "expires_at": "2099-04-16T19:17:45+00:00",
            "goal": "BL-123: Active scope",
            "session_id": "sess-active",
            "approved_by": "human",
            "backlog_id": "BL-123",
            "governance_mode": "standard",
            "pipeline_command": "auto",
            "target_layer": "application",
        },
    )

    resume_payload = run_router(router, "continue this task", cwd=tmp_path)
    assert "resume/continue decision" in resume_payload["hookSpecificOutput"]["additionalContext"]

    replace_payload = run_router(
        router,
        "start a new goal: BL-456 modernize calm flow",
        cwd=tmp_path,
    )
    assert "replace decision" in replace_payload["hookSpecificOutput"]["additionalContext"]


def test_normalized_governed_state_renders_pipeline_gate_and_start_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    fixed_now = datetime(2030, 4, 11, 12, 0, tzinfo=timezone.utc)
    seed_azoth_repo(
        tmp_path,
        backlog_items=[
            {
                "id": "BL-321",
                "title": "Governed start-centered task",
                "status": "pending",
                "priority": 1,
                "target_layer": "M1",
                "delivery_pipeline": "governed",
            }
        ],
        scope={
            "approved": True,
            "expires_at": "2030-04-11T14:00:00+00:00",
            "goal": "BL-321: Governed start-centered task",
            "session_id": "sess-governed",
            "approved_by": "human",
            "backlog_id": "BL-321",
            "governance_mode": "governed",
            "pipeline_command": "deliver-full",
            "target_layer": "M1",
        },
        pipeline_gate={
            "session_id": "sess-governed",
            "approved": True,
            "expires_at": "2030-04-11T13:00:00+00:00",
            "opened_at": "2030-04-11T12:00:00+00:00",
            "pipeline_command": "deliver-full",
        },
        session_state={
            "session_id": "sess-governed",
            "state": "active",
            "last_ide": "codex",
            "timestamp": "2030-04-11T12:00:00+00:00",
            "approved_scope": "BL-321: Governed start-centered task",
            "next_action": "Continue the governed start-centered task.",
        },
        sessions=[
            {
                "session_id": "sess-governed",
                "status": "active",
                "ide": "codex",
                "backlog_id": "BL-321",
                "next_action": "Continue the governed start-centered task.",
            }
        ],
    )

    out = _capture_plain_welcome(tmp_path, monkeypatch, now=fixed_now)
    assert "Pipeline gate: OK  (deliver-full)  [1h 00m remaining]" in out
    assert "Continuity: OK  (sess-governed)" in out
    assert _extract_start_block(out) == "\n".join(
        [
            "── START (what to type) ──",
            "  resume   → continue approved scope: BL-321: Governed start-centered task",
            "  next     → /next — scope card for next priority task",
            "  intake   → /intake — process .azoth/inbox/",
            "  promote  → /promote — M2→M1 promotion review",
            "  eval     → /eval — quality gate",
            "  roadmap  → /roadmap — versioned roadmap dashboard (D48)",
            "  plan     → /plan — structured autonomy / planning",
            "  remember → /remember — quick M3 capture (no full closeout)",
            "  closeout → /session-closeout — episodes W1–W4 + handoff capsule",
            "  <goal>   → /auto — auto-pipeline for a custom goal",
            "  codex    → start with $azoth-start; then use /skills or $azoth-resume / $azoth-next / $azoth-auto. Literal /start /resume /next /auto normalize to $azoth-* or block when the canonical skill surface is missing",
        ]
    )


def test_resume_closeout_loop_reports_truthful_handoff_and_no_false_mismatch(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    session_id = "sess-journey"
    next_action = "Run `/next` to select the next scoped task."
    seed_azoth_repo(
        tmp_path,
        azoth_version="0.1.1.29",
        phase=1,
        backlog_items=[
            {
                "id": "BL-777",
                "title": "Journey proof closeout",
                "status": "active",
                "priority": 1,
                "target_layer": "M1",
                "delivery_pipeline": "governed",
            }
        ],
        scope={
            "approved": True,
            "expires_at": "2099-04-18T14:15:00+00:00",
            "goal": "BL-777: Journey proof closeout",
            "session_id": session_id,
            "approved_by": "human",
            "backlog_id": "BL-777",
            "governance_mode": "governed",
            "pipeline_command": "deliver-full",
            "target_layer": "M1",
        },
        pipeline_gate={
            "session_id": session_id,
            "approved": True,
            "expires_at": "2099-04-18T14:15:00+00:00",
            "opened_at": "2026-04-18T12:00:00+00:00",
            "pipeline_command": "deliver-full",
        },
        session_state={
            "session_id": session_id,
            "state": "active",
            "last_ide": "codex",
            "timestamp": "2026-04-18T12:00:00+00:00",
            "approved_scope": "BL-777: Journey proof closeout",
            "next_action": "Continue the governed session.",
            "pipeline": "deliver-full",
            "pipeline_position": 2,
            "current_stage_id": "review",
            "completed_stages": ["planner"],
            "pending_stages": ["builder_apply", "reviewer_gate"],
            "active_run_id": "run-777",
        },
        sessions=[
            {
                "session_id": session_id,
                "status": "active",
                "ide": "codex",
                "backlog_id": "BL-777",
                "goal": "BL-777: Journey proof closeout",
                "next_action": "Continue the governed session.",
                "active_run_id": "run-777",
                "updated_at": "2026-04-18T12:00:00+00:00",
            }
        ],
        runs=[
            {
                "run_id": "run-777",
                "session_id": session_id,
                "backlog_id": "BL-777",
                "ide": "codex",
                "mode": "deliver-full",
                "pipeline_command": "deliver-full",
                "governance_mode": "governed",
                "goal": "BL-777: Journey proof closeout",
                "status": "paused",
                "created_at": "2026-04-18T12:00:00+00:00",
                "updated_at": "2026-04-18T12:05:00+00:00",
                "next_action": "Resume the governed run.",
                "stages_completed": ["planner"],
                "active_stage_id": "review",
                "pending_stage_ids": ["builder_apply", "reviewer_gate"],
                "pause_reason": "human-gate",
                "waves": [],
                "branches": [],
            }
        ],
        write_claim={
            "session_id": session_id,
            "expires_at": "2099-04-18T14:15:00+00:00",
            "acquired_at": "2026-04-18T12:00:00+00:00",
        },
        roadmap={
            "active_version": "v0.2.0-p1",
            "versions": [
                {
                    "id": "v0.2.0-p1",
                    "status": "active",
                    "current_patch": 29,
                    "tasks": [
                        {
                            "id": "BL-777",
                            "title": "Journey proof closeout",
                            "decision_ref": ["D50"],
                        }
                    ],
                    "completed_tasks": [],
                }
            ],
        },
        session_orientation_text="cached\n",
    )
    (tmp_path / ".azoth" / "final-delivery-approvals.jsonl").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "gate": "final-delivery",
                "actor_type": "human",
                "approved": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    park_session.park_session(
        tmp_path,
        next_action="Resume later with /resume sess-journey.",
        timestamp="2099-04-18T12:10:00+00:00",
    )
    monkeypatch.setattr(
        park_session.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )
    park_session.resume_session(
        tmp_path,
        ide="codex",
        timestamp="2099-04-18T12:15:00+00:00",
    )
    monkeypatch.setattr(do_closeout.subprocess, "run", lambda *args, **kwargs: None)

    do_closeout.run_closeout(
        tmp_path,
        closeout_semantics=_closeout_semantics(next_action=next_action),
    )
    closeout_out = capsys.readouterr().out
    welcome_out = _capture_plain_welcome(tmp_path, monkeypatch)

    assert ".azoth/session-state.md" in closeout_out
    assert "W3 deferred" in closeout_out
    assert "Next operator action:" in closeout_out
    assert "Continuity: MISMATCH" not in welcome_out
    assert "Scope: NONE  (run /next to open a scope card)" in welcome_out


def test_router_level_closeout_entry_stays_explicit() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    payload = run_router(router, "/session-closeout", cwd=REPO)
    hook = payload["hookSpecificOutput"]
    assert hook["updatedInput"] == "$azoth-session-closeout"
    assert ".azoth/session-state.md" in hook["additionalContext"]
    assert "W3 deferred" in hook["additionalContext"]

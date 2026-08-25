#!/usr/bin/env python3
"""Park or resume a scoped session."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from check_gates import extract_structural_research_gate_payload
from do_closeout import (
    close_scope_gate,
    extract_session_checkpoint,
    load_json,
    load_yaml,
    write_session_state,
)
from run_ledger import (
    acquire_write_claim,
    consume_human_gate_approval,
    load_run,
    load_session,
    release_write_claim,
    upsert_run,
    upsert_session,
)
from session_continuity import active_scope, scope_conflict_message

ROOT = Path(__file__).resolve().parent.parent


class ParkSessionError(RuntimeError):
    """Raised when parking preconditions are not met."""


_STRUCTURAL_RESEARCH_GATE_FIELDS = ("research_required", "research_evidence")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _coerce_string(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _coerce_stage_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _checkpoint_from_run(run_entry: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(run_entry, dict):
        return {}

    checkpoint: dict[str, Any] = {}
    pipeline = _coerce_string(run_entry.get("mode"))
    if pipeline:
        checkpoint["pipeline"] = pipeline

    completed_stages = _coerce_stage_list(run_entry.get("stages_completed"))
    if completed_stages:
        checkpoint["completed_stages"] = completed_stages

    current_stage_id = _coerce_string(run_entry.get("active_stage_id"))
    if current_stage_id:
        checkpoint["current_stage_id"] = current_stage_id

    pending_stages = _coerce_stage_list(run_entry.get("pending_stage_ids"))
    if pending_stages:
        checkpoint["pending_stages"] = pending_stages

    pause_reason = _coerce_string(run_entry.get("pause_reason"))
    if pause_reason:
        checkpoint["pause_reason"] = pause_reason

    active_run_id = _coerce_string(run_entry.get("run_id"))
    if active_run_id:
        checkpoint["active_run_id"] = active_run_id

    if (current_stage_id or pending_stages) and completed_stages:
        checkpoint["pipeline_position"] = len(completed_stages) + 1
    elif current_stage_id or pending_stages:
        checkpoint["pipeline_position"] = 1

    structural_payload = _extract_structural_research_payload(
        run_entry,
        session_id=_coerce_string(run_entry.get("session_id")),
    )
    if structural_payload:
        checkpoint.update(structural_payload)

    return checkpoint


def _extract_structural_research_payload(
    source: dict[str, Any] | None,
    *,
    session_id: str,
    required: bool = False,
    source_name: str = "checkpoint",
) -> dict[str, Any]:
    if not isinstance(source, dict):
        if required:
            raise ParkSessionError(
                f"Cannot recover structural research gate from {source_name}: missing source data."
            )
        return {}

    if not any(field in source for field in _STRUCTURAL_RESEARCH_GATE_FIELDS):
        if required:
            raise ParkSessionError(
                f"Cannot recover structural research gate from {source_name}: "
                "research_required is missing."
            )
        return {}

    gate_payload = {"session_id": session_id}
    for field in _STRUCTURAL_RESEARCH_GATE_FIELDS:
        if field in source:
            gate_payload[field] = source[field]

    ok, payload, message = extract_structural_research_gate_payload(gate_payload)
    if not ok:
        if required:
            detail = message.replace("pipeline-gate.json ", "", 1)
            raise ParkSessionError(
                f"Cannot recover structural research gate from {source_name}: {detail}"
            )
        return {}
    return payload


def _governed_resume_requires_structural_research_payload(
    *,
    run_entry: dict[str, Any] | None,
    pipeline: str,
    delivery_pipeline: str,
    target_layer: str,
) -> bool:
    if not (run_entry and pipeline):
        return False
    return target_layer == "M1" or delivery_pipeline == "governed"


def _read_live_structural_research_payload(
    repo_root: Path,
    *,
    session_id: str,
) -> dict[str, Any]:
    pipeline_gate_path = repo_root / ".azoth" / "pipeline-gate.json"
    if not pipeline_gate_path.exists():
        return {}

    gate = load_json(pipeline_gate_path)
    if _coerce_string(gate.get("session_id")) != session_id:
        return {}
    if not any(field in gate for field in _STRUCTURAL_RESEARCH_GATE_FIELDS):
        return {}

    ok, payload, message = extract_structural_research_gate_payload(gate)
    if not ok:
        raise ParkSessionError(message.replace("pipeline-gate.json ", "", 1))
    return payload


def _persist_structural_research_checkpoint(
    repo_root: Path,
    *,
    session_id: str,
    active_run_id: str | None,
    payload: dict[str, Any],
) -> None:
    if not payload:
        return

    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    ledger = load_yaml(ledger_path)
    runs = ledger.get("runs")
    if isinstance(runs, list) and active_run_id:
        for run in runs:
            if not isinstance(run, dict):
                continue
            if _coerce_string(run.get("run_id")) != active_run_id:
                continue
            run.update(payload)
            break
        ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")

    session_state_path = repo_root / ".azoth" / "session-state.md"
    session_state = load_yaml(session_state_path)
    if _coerce_string(session_state.get("session_id")) != session_id:
        return
    session_state.update(payload)
    session_state_path.write_text(yaml.safe_dump(session_state, sort_keys=False), encoding="utf-8")


def _merge_checkpoint(
    *,
    run_entry: dict[str, Any] | None,
    existing_state: dict[str, Any],
    existing_matches: bool,
    active_run_id: str | None = None,
    default_pause_reason: str | None = None,
) -> dict[str, Any]:
    checkpoint = _checkpoint_from_run(run_entry)
    if existing_matches:
        checkpoint.update(extract_session_checkpoint(existing_state))

    if active_run_id:
        checkpoint["active_run_id"] = active_run_id

    if not checkpoint.get("pause_reason") and default_pause_reason:
        checkpoint["pause_reason"] = default_pause_reason

    if "pipeline_position" not in checkpoint and (
        checkpoint.get("current_stage_id") or checkpoint.get("pending_stages")
    ):
        checkpoint["pipeline_position"] = len(checkpoint.get("completed_stages") or []) + 1

    return checkpoint


def _checkpoint_active_task(goal: str, checkpoint: dict[str, Any], parked: bool) -> str:
    prefix = "Parked" if parked else "Resumed"
    current_stage_id = _coerce_string(checkpoint.get("current_stage_id"))
    if current_stage_id:
        return f"{prefix} — {goal} (stage: {current_stage_id})"
    return f"{prefix} — {goal}"


def _resume_next_action(
    *,
    goal: str,
    run_entry: dict[str, Any] | None,
    checkpoint: dict[str, Any],
) -> str:
    current_stage_id = _coerce_string(checkpoint.get("current_stage_id"))
    pipeline = _coerce_string(
        checkpoint.get("pipeline")
        or (run_entry.get("mode") if isinstance(run_entry, dict) else None)
    )
    pause_reason = _coerce_string(checkpoint.get("pause_reason"))
    pending_stages = _coerce_stage_list(checkpoint.get("pending_stages"))
    replay_target = ""
    if pause_reason == "human-gate" and current_stage_id and pending_stages:
        candidate = pending_stages[0]
        if candidate and candidate != current_stage_id:
            replay_target = candidate

    if run_entry is None:
        return (
            "Continue the resumed parked scope. If no delivery pipeline is explicitly chosen, "
            "use /auto and run Stage 0 before implementation."
        )
    if pause_reason == "human-gate":
        if current_stage_id:
            if replay_target:
                return (
                    f"Resume at human gate for stage `{current_stage_id}` in pipeline "
                    f"`{pipeline}`; approval replays `{replay_target}`."
                )
            return f"Resume at human gate for stage `{current_stage_id}` in pipeline `{pipeline}`."
        return f"Resume at the saved human gate in pipeline `{pipeline or 'unknown'}`."
    if current_stage_id:
        return f"Continue pipeline `{pipeline or 'unknown'}` at stage `{current_stage_id}`."
    if pipeline:
        return f"Continue the resumed parked scope through pipeline `{pipeline}`."
    return f"Continue the resumed parked scope for {goal}."


def _restore_pipeline_gate(
    repo_root: Path,
    *,
    session_id: str,
    pipeline: str,
    expires_at: str,
    require: bool = True,
    research_required: bool = False,
    research_evidence: dict[str, Any] | None = None,
) -> None:
    pipeline_gate = {
        "session_id": session_id,
        "pipeline": pipeline,
        "approved": True,
        "expires_at": expires_at,
        "opened_at": utc_now_iso(),
        "research_required": research_required,
    }
    if research_evidence is not None:
        pipeline_gate["research_evidence"] = research_evidence
    (repo_root / ".azoth" / "pipeline-gate.json").write_text(
        json.dumps(pipeline_gate, indent=2) + "\n",
        encoding="utf-8",
    )
    command = [
        sys.executable,
        str(ROOT / "scripts" / "check_gates.py"),
        "--session-id",
        session_id,
        "--root",
        str(repo_root),
    ]
    if require:
        command.append("--require-pipeline-gate")
    result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=repo_root)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "gate verification failed"
        raise ParkSessionError(f"Cannot restore pipeline gate for session '{session_id}': {detail}")


def _normalize_pipeline_command(
    *,
    checkpoint: dict[str, Any],
    run_entry: dict[str, Any] | None,
    delivery_pipeline: str,
    target_layer: str,
) -> str:
    for candidate in (
        _coerce_string(checkpoint.get("pipeline")),
        _coerce_string(run_entry.get("mode") if isinstance(run_entry, dict) else ""),
        _coerce_string(delivery_pipeline),
    ):
        if candidate in {"auto", "autonomous-auto", "dynamic-full-auto", "deliver", "deliver-full"}:
            return candidate
    if target_layer == "M1" or delivery_pipeline == "governed":
        return "deliver-full"
    return ""


def park_session(
    repo_root: Path,
    *,
    next_action: str,
    ide: str | None = None,
    active_run_id: str | None = None,
    active_files: list[str] | None = None,
    pending_decisions: list[str] | None = None,
    session_id: str | None = None,
    backlog_id: str | None = None,
    goal: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    scope = load_json(repo_root / ".azoth" / "scope-gate.json")
    resolved_session_id = _coerce_string(session_id or scope.get("session_id"))
    if not resolved_session_id:
        raise ParkSessionError("Cannot park session: scope-gate.json missing session_id.")

    resolved_goal = _coerce_string(goal or scope.get("goal"), "Parked session")
    resolved_backlog_id = _coerce_string(backlog_id or scope.get("backlog_id"), "AD-HOC")
    when = timestamp or utc_now_iso()

    session_state_path = repo_root / ".azoth" / "session-state.md"
    existing_state = load_yaml(session_state_path)
    existing_matches = (
        session_state_path.exists()
        and _coerce_string(existing_state.get("session_id")) == resolved_session_id
        and _coerce_string(existing_state.get("state")) != "empty"
    )
    selected_ide = _coerce_string(
        ide or existing_state.get("last_ide"),
        "unknown",
    )
    existing_session = load_session(repo_root, resolved_session_id) or {}
    resolved_active_run_id = (
        _coerce_string(
            active_run_id
            or existing_state.get("active_run_id")
            or existing_session.get("active_run_id")
        )
        or None
    )
    run_entry = load_run(repo_root, resolved_active_run_id) if resolved_active_run_id else None
    checkpoint = _merge_checkpoint(
        run_entry=run_entry,
        existing_state=existing_state,
        existing_matches=existing_matches,
        active_run_id=resolved_active_run_id,
        default_pause_reason="handoff",
    )
    checkpoint.update(
        _extract_structural_research_payload(
            existing_state if existing_matches else None,
            session_id=resolved_session_id,
            source_name="session-state.md",
        )
    )
    checkpoint.update(
        _read_live_structural_research_payload(
            repo_root,
            session_id=resolved_session_id,
        )
    )
    resolved_active_files = (
        list(active_files)
        if active_files is not None
        else (
            list(existing_state.get("active_files"))
            if existing_matches and isinstance(existing_state.get("active_files"), list)
            else []
        )
    )
    resolved_pending_decisions = (
        list(pending_decisions)
        if pending_decisions is not None
        else (
            list(existing_state.get("pending_decisions"))
            if existing_matches and isinstance(existing_state.get("pending_decisions"), list)
            else []
        )
    )

    created, _ = upsert_session(
        repo_root,
        session_id=resolved_session_id,
        backlog_id=resolved_backlog_id,
        goal=resolved_goal,
        status="parked",
        ide=selected_ide,
        next_action=next_action,
        session_mode="delivery",
        updated_at=when,
        active_run_id=resolved_active_run_id,
    )

    if resolved_active_run_id:
        upsert_run(
            repo_root,
            run_id=resolved_active_run_id,
            session_id=resolved_session_id,
            backlog_id=resolved_backlog_id,
            ide=selected_ide,
            mode=_coerce_string(checkpoint.get("pipeline"), "auto"),
            goal=resolved_goal,
            status="paused",
            next_action=next_action,
            updated_at=when,
            stages_completed=checkpoint.get("completed_stages", []),
            active_stage_id=checkpoint.get("current_stage_id"),
            pending_stage_ids=checkpoint.get("pending_stages", []),
            pause_reason=_coerce_string(checkpoint.get("pause_reason"), "handoff"),
        )

    released_claim = release_write_claim(repo_root, resolved_session_id)
    close_scope_gate(repo_root, when)
    write_session_state(
        repo_root,
        session_id=resolved_session_id,
        state="parked",
        timestamp=when,
        active_task=_checkpoint_active_task(resolved_goal, checkpoint, True),
        active_files=resolved_active_files,
        pending_decisions=resolved_pending_decisions,
        approved_scope=resolved_goal,
        next_action=next_action,
        selected_ide=selected_ide,
        create_if_missing=True,
        checkpoint=checkpoint,
    )
    _persist_structural_research_checkpoint(
        repo_root,
        session_id=resolved_session_id,
        active_run_id=resolved_active_run_id,
        payload=_extract_structural_research_payload(
            checkpoint,
            session_id=resolved_session_id,
            source_name="park checkpoint",
        ),
    )

    return {
        "session_id": resolved_session_id,
        "backlog_id": resolved_backlog_id,
        "goal": resolved_goal,
        "status": "parked",
        "ide": selected_ide,
        "created": created,
        "write_claim_released": released_claim,
        "scope_closed": True,
        "active_run_id": resolved_active_run_id,
        "pause_reason": checkpoint.get("pause_reason"),
        "current_stage_id": checkpoint.get("current_stage_id"),
    }


def _resolve_resume_target(
    repo_root: Path, session_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    existing_state = load_yaml(repo_root / ".azoth" / "session-state.md")
    live_scope = active_scope(repo_root)
    resolved_session_id = _coerce_string(session_id)
    if not resolved_session_id and live_scope:
        resolved_session_id = _coerce_string(live_scope.get("session_id"))
    if not resolved_session_id and _coerce_string(existing_state.get("state")) == "parked":
        resolved_session_id = _coerce_string(existing_state.get("session_id"))
    if not resolved_session_id:
        raise ParkSessionError(
            "Cannot resume session: no session_id provided and session-state.md is not parked."
        )

    conflict = scope_conflict_message(
        repo_root,
        command_name="resume",
        requested_session_id=resolved_session_id,
    )
    if conflict:
        raise ParkSessionError(f"{conflict} Options: park current, close current, or abort.")

    session_entry = load_session(repo_root, resolved_session_id)
    if session_entry is None and live_scope:
        live_scope_session_id = _coerce_string(live_scope.get("session_id"))
        if live_scope_session_id == resolved_session_id:
            session_entry = _synthesize_live_scope_session_entry(
                repo_root,
                live_scope=live_scope,
                existing_state=existing_state,
            )
    if session_entry is None:
        raise ParkSessionError(
            f"Cannot resume session: no run-ledger entry found for '{resolved_session_id}'."
        )

    status = _coerce_string(session_entry.get("status"))
    if status not in {"active", "parked"}:
        raise ParkSessionError(
            f"Cannot resume session '{resolved_session_id}': status is {status or 'unknown'}."
        )
    return resolved_session_id, session_entry


def _matching_resume_run(repo_root: Path, *, session_id: str) -> dict[str, Any] | None:
    ledger = load_yaml(repo_root / ".azoth" / "run-ledger.local.yaml")
    runs = ledger.get("runs")
    if not isinstance(runs, list):
        return None
    for entry in reversed(runs):
        if not isinstance(entry, dict):
            continue
        if _coerce_string(entry.get("session_id")) != session_id:
            continue
        if _coerce_string(entry.get("status")) not in {"active", "paused"}:
            continue
        return entry
    return None


def _synthesize_live_scope_session_entry(
    repo_root: Path,
    *,
    live_scope: dict[str, Any],
    existing_state: dict[str, Any],
) -> dict[str, Any]:
    session_id = _coerce_string(live_scope.get("session_id"))
    goal = _coerce_string(live_scope.get("goal"), "Resumed session")
    backlog_id = _coerce_string(live_scope.get("backlog_id"), "AD-HOC")
    run_entry = _matching_resume_run(repo_root, session_id=session_id)
    checkpoint = _checkpoint_from_run(run_entry)
    selected_ide = _coerce_string(
        run_entry.get("ide") if isinstance(run_entry, dict) else "",
        _coerce_string(existing_state.get("last_ide"), "unknown"),
    )
    session_entry = {
        "session_id": session_id,
        "backlog_id": backlog_id,
        "goal": goal,
        "status": "active",
        "ide": selected_ide,
        "next_action": _resume_next_action(
            goal=goal,
            run_entry=run_entry,
            checkpoint=checkpoint,
        ),
        "updated_at": utc_now_iso(),
    }
    active_run_id = _coerce_string(run_entry.get("run_id") if isinstance(run_entry, dict) else "")
    if active_run_id:
        session_entry["active_run_id"] = active_run_id
    return session_entry


def _matching_pipeline_gate(repo_root: Path, *, session_id: str) -> dict[str, Any]:
    gate = load_json(repo_root / ".azoth" / "pipeline-gate.json")
    if _coerce_string(gate.get("session_id")) != session_id:
        return {}
    return gate


def _scope_shape_for_resume(
    repo_root: Path,
    *,
    session_id: str,
    backlog_id: str,
    goal: str,
) -> tuple[str, str]:
    current_scope = load_json(repo_root / ".azoth" / "scope-gate.json")
    if _coerce_string(current_scope.get("session_id")) == session_id:
        delivery_pipeline = _coerce_string(current_scope.get("delivery_pipeline"), "standard")
        target_layer = _coerce_string(current_scope.get("target_layer"), "infrastructure")
        return delivery_pipeline, target_layer

    backlog = load_yaml(repo_root / ".azoth" / "backlog.yaml")
    items = backlog.get("items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            if _coerce_string(item.get("id")) != backlog_id:
                continue
            delivery_pipeline = _coerce_string(item.get("delivery_pipeline"), "standard")
            target_layer = _coerce_string(item.get("target_layer"), "infrastructure")
            return delivery_pipeline, target_layer

    return "standard", "infrastructure"


def resume_session(
    repo_root: Path,
    *,
    session_id: str | None = None,
    ide: str | None = None,
    timestamp: str | None = None,
    approve_human_gate: bool = False,
) -> dict[str, Any]:
    resolved_session_id, session_entry = _resolve_resume_target(repo_root, session_id=session_id)
    when = timestamp or utc_now_iso()
    backlog_id = _coerce_string(session_entry.get("backlog_id"), "AD-HOC")
    goal = _coerce_string(session_entry.get("goal"), "Resumed session")
    active_run_id = _coerce_string(session_entry.get("active_run_id")) or None
    delivery_pipeline, target_layer = _scope_shape_for_resume(
        repo_root,
        session_id=resolved_session_id,
        backlog_id=backlog_id,
        goal=goal,
    )
    selected_ide = _coerce_string(ide or session_entry.get("ide"), "unknown")

    existing_state = load_yaml(repo_root / ".azoth" / "session-state.md")
    existing_matches = _coerce_string(existing_state.get("session_id")) == resolved_session_id
    pending_decisions = (
        list(existing_state.get("pending_decisions"))
        if existing_matches and isinstance(existing_state.get("pending_decisions"), list)
        else []
    )
    active_files = (
        list(existing_state.get("active_files"))
        if existing_matches and isinstance(existing_state.get("active_files"), list)
        else []
    )
    run_entry = load_run(repo_root, active_run_id) if active_run_id else None
    live_pipeline_gate = _matching_pipeline_gate(repo_root, session_id=resolved_session_id)
    live_pipeline_command = _coerce_string(
        live_pipeline_gate.get("pipeline_command") or live_pipeline_gate.get("pipeline")
    )
    checkpoint = _merge_checkpoint(
        run_entry=run_entry,
        existing_state=existing_state,
        existing_matches=existing_matches,
        active_run_id=active_run_id,
    )

    expires_at = (
        (datetime.fromisoformat(when.replace("Z", "+00:00")) + timedelta(hours=2))
        .astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )
    next_action = _resume_next_action(goal=goal, run_entry=run_entry, checkpoint=checkpoint)

    scope = {
        "approved": True,
        "expires_at": expires_at,
        "goal": goal,
        "session_id": resolved_session_id,
        "approved_by": "human",
        "backlog_id": backlog_id,
        "delivery_pipeline": delivery_pipeline,
        "target_layer": target_layer,
    }
    (repo_root / ".azoth" / "scope-gate.json").write_text(
        json.dumps(scope, indent=2) + "\n",
        encoding="utf-8",
    )

    pipeline = _normalize_pipeline_command(
        checkpoint=checkpoint,
        run_entry=run_entry,
        delivery_pipeline=delivery_pipeline,
        target_layer=target_layer,
    )
    if not pipeline and live_pipeline_command in {
        "auto",
        "autonomous-auto",
        "dynamic-full-auto",
        "deliver",
        "deliver-full",
    }:
        pipeline = live_pipeline_command
    if pipeline:
        checkpoint["pipeline"] = pipeline
    structural_research_payload = _extract_structural_research_payload(
        checkpoint,
        session_id=resolved_session_id,
        source_name="parked checkpoint",
    )
    if (
        not structural_research_payload
        and pipeline
        and _governed_resume_requires_structural_research_payload(
            run_entry=run_entry,
            pipeline=pipeline,
            delivery_pipeline=delivery_pipeline,
            target_layer=target_layer,
        )
    ):
        structural_research_payload = _read_live_structural_research_payload(
            repo_root,
            session_id=resolved_session_id,
        )
        if not structural_research_payload:
            raise ParkSessionError(
                "Cannot recover structural research gate from parked checkpoint: "
                "research_required is missing."
            )
    if pipeline:
        _restore_pipeline_gate(
            repo_root,
            session_id=resolved_session_id,
            pipeline=pipeline,
            expires_at=expires_at,
            require=True,
            research_required=bool(structural_research_payload.get("research_required", False)),
            research_evidence=structural_research_payload.get("research_evidence"),
        )
    else:
        pipeline_gate_path = repo_root / ".azoth" / "pipeline-gate.json"
        if pipeline_gate_path.exists() and live_pipeline_command not in {
            "auto",
            "dynamic-full-auto",
            "deliver",
            "deliver-full",
        }:
            pipeline_gate_path.unlink()

    created, _ = upsert_session(
        repo_root,
        session_id=resolved_session_id,
        backlog_id=backlog_id,
        goal=goal,
        status="active",
        ide=selected_ide,
        next_action=next_action,
        session_mode="delivery",
        updated_at=when,
        active_run_id=active_run_id,
    )

    pause_reason = _coerce_string(checkpoint.get("pause_reason"))
    if run_entry and pipeline:
        upsert_run(
            repo_root,
            run_id=_coerce_string(run_entry.get("run_id")),
            session_id=resolved_session_id,
            backlog_id=backlog_id,
            ide=selected_ide,
            mode=pipeline,
            goal=goal,
            status="paused" if pause_reason == "human-gate" else "active",
            next_action=next_action,
            updated_at=when,
            stages_completed=checkpoint.get("completed_stages", []),
            active_stage_id=checkpoint.get("current_stage_id"),
            pending_stage_ids=checkpoint.get("pending_stages", []),
            pause_reason=pause_reason if pause_reason == "human-gate" else None,
        )
        if pause_reason == "human-gate" and approve_human_gate:
            updated_run = consume_human_gate_approval(
                repo_root,
                run_id=_coerce_string(run_entry.get("run_id")),
            )
            checkpoint["completed_stages"] = list(updated_run.get("stages_completed") or [])
            checkpoint["current_stage_id"] = updated_run.get("active_stage_id")
            checkpoint["pending_stages"] = list(updated_run.get("pending_stage_ids") or [])
            checkpoint.pop("pause_reason", None)
            pause_reason = ""
            next_action = str(updated_run.get("next_action") or next_action)
            upsert_session(
                repo_root,
                session_id=resolved_session_id,
                backlog_id=backlog_id,
                goal=goal,
                status="active",
                ide=selected_ide,
                next_action=next_action,
                session_mode="delivery",
                updated_at=when,
                active_run_id=active_run_id,
            )

    ok, claim_info = acquire_write_claim(
        repo_root, resolved_session_id, expires_at, harness=selected_ide
    )
    if not ok:
        raise ParkSessionError(f"Cannot resume session '{resolved_session_id}': {claim_info}")

    write_session_state(
        repo_root,
        session_id=resolved_session_id,
        state="active",
        timestamp=when,
        active_task=_checkpoint_active_task(goal, checkpoint, False),
        active_files=active_files,
        pending_decisions=pending_decisions,
        approved_scope=goal,
        next_action=next_action,
        selected_ide=selected_ide,
        create_if_missing=True,
        checkpoint=checkpoint,
    )
    _persist_structural_research_checkpoint(
        repo_root,
        session_id=resolved_session_id,
        active_run_id=active_run_id,
        payload=structural_research_payload,
    )

    return {
        "session_id": resolved_session_id,
        "backlog_id": backlog_id,
        "goal": goal,
        "status": "active",
        "ide": selected_ide,
        "created": created,
        "write_claim": claim_info,
        "expires_at": expires_at,
        "resume_type": "stage-aware" if run_entry and pipeline else "scope-only",
        "pipeline": pipeline or None,
        "current_stage_id": checkpoint.get("current_stage_id"),
        "pending_stage_ids": checkpoint.get("pending_stages", []),
        "pause_reason": pause_reason or None,
        "human_gate": pause_reason == "human-gate",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Park the current scoped session for later /resume, or resume a parked session.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a parked session instead of parking the current one.",
    )
    parser.add_argument(
        "--next-action",
        default=None,
        metavar="TEXT",
        help="Resume instruction shown in the parked session registry.",
    )
    parser.add_argument(
        "--ide", metavar="IDE", default=None, help="Harness label for the parked session."
    )
    parser.add_argument(
        "--active-run-id",
        metavar="RUN_ID",
        default=None,
        help="Optional resumable run linked to the parked session.",
    )
    parser.add_argument(
        "--active-file",
        action="append",
        dest="active_files",
        default=None,
        metavar="PATH",
        help="Tracked active file for the handoff capsule (repeatable).",
    )
    parser.add_argument(
        "--pending-decision",
        action="append",
        dest="pending_decisions",
        default=None,
        metavar="TEXT",
        help="Pending decision for the handoff capsule (repeatable).",
    )
    parser.add_argument(
        "--session-id",
        metavar="SESSION_ID",
        default=None,
        help="Override session_id from scope-gate.",
    )
    parser.add_argument(
        "--approve-human-gate",
        action="store_true",
        help="When resuming a paused human-gate run, consume that approval and advance to the next executable stage.",
    )
    parser.add_argument(
        "--backlog-id",
        metavar="BACKLOG_ID",
        default=None,
        help="Override backlog_id from scope-gate.",
    )
    parser.add_argument(
        "--goal", metavar="GOAL", default=None, help="Override goal from scope-gate."
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.resume:
        result = resume_session(
            ROOT,
            session_id=args.session_id,
            ide=args.ide,
            approve_human_gate=args.approve_human_gate,
        )
    else:
        if not args.next_action:
            parser.error("--next-action is required unless --resume is used")
        result = park_session(
            ROOT,
            next_action=args.next_action,
            ide=args.ide,
            active_run_id=args.active_run_id,
            active_files=args.active_files,
            pending_decisions=args.pending_decisions,
            session_id=args.session_id,
            backlog_id=args.backlog_id,
            goal=args.goal,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

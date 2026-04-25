#!/usr/bin/env python3
"""Autonomous-auto loop governor.

The governor is intentionally deterministic: it reads a local loop-state file,
decides the next safe Azoth self-development action, and can open the next
scope gate for a bounded autonomous-auto iteration.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from planning_bank_validate import build_initiative_readiness_report
from run_ledger import acquire_write_claim, load_write_claim, release_write_claim, upsert_run
from session_gate import active_session_gate, normalized_session_mode
from yaml_helpers import safe_load_yaml_path

STATE_REL = ".azoth/autonomous-loop-state.local.yaml"
SCOPE_GATE_REL = ".azoth/scope-gate.json"
INBOX_DIR_REL = ".azoth/inbox"
HANDOFFS_DIR_REL = ".azoth/handoffs"
DECISION_SCHEMA_VERSION = 1
VALID_ACTIONS = {
    "ship_task",
    "hydrate_task",
    "research_initiative",
    "refine_proposal",
    "capture_self_improvement",
    "stop",
}
DEFAULT_ALLOWED_ACTIONS = [
    "ship_task",
    "hydrate_task",
    "research_initiative",
    "refine_proposal",
    "capture_self_improvement",
]
SAFE_BACKLOG_STATUSES = {"pending", "planned", "ready", "todo"}
READY_INITIATIVE_STATUSES = {"active_refinement", "ready", "ready_to_hydrate"}
PROPOSAL_STATUSES = {"draft", "active_refinement", "submitted", "proposed"}
PROTECTED_TARGET_LAYERS = {"m1", "kernel", "governance"}
PROTECTED_PIPELINES = {"governed", "deliver-full"}
PROTECTED_GOVERNANCE_MODES = {"governed"}
PROTECTED_BOOLEAN_FLAGS = {
    "protected",
    "protected_gate_required",
    "requires_protected_gate",
    "requires_human_gate",
    "human_gate_required",
    "requires_human_approval",
    "manual_approval_required",
    "requires_pipeline_gate",
    "destructive",
    "requires_destructive_action",
    "credential_required",
    "credentials_required",
    "requires_credentials",
    "network_required",
    "requires_network",
    "external_network_required",
}
PROTECTED_FLAG_VALUES = {
    "protected",
    "protected-gate",
    "protected-gate-required",
    "human-gate",
    "human-gate-required",
    "manual-approval",
    "requires-approval",
    "requires-human-approval",
    "destructive",
    "requires-destructive-action",
    "credential",
    "credentials",
    "credential-required",
    "credentials-required",
    "requires-credentials",
    "network",
    "network-required",
    "requires-network",
    "external-network",
    "external-network-required",
}
ALIGNMENT_PACKET_TYPES = {"async_advisory", "async_override", "async_stop", "approval_basis"}
ALIGNMENT_DISPOSITIONS = {"pending", "applied", "deferred", "rejected"}
DEFAULT_ALIGNMENT_CHECKPOINT = "next_safe_checkpoint"
VISION_BANDS = {"red": 0, "yellow": 1, "green": 2}
DEFAULT_VISION_ANCHOR = ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md"
DEFAULT_VISION_TARGET_BAND = "green"
DEFAULT_STOP_CONDITIONS = [
    "active_scope_present",
    "active_session_gate_conflict",
    "active_write_claim_present",
    "budget_exhausted",
    "protected_gate_required",
    "async_stop_packet",
    "no_safe_candidate",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(raw: str) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = safe_load_yaml_path(path)
    return data if isinstance(data, dict) else {}


def _write_yaml_mapping(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _write_json_mapping(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _current_branch(root: Path) -> str:
    git_path = root / ".git"
    head_path = git_path / "HEAD"
    if git_path.is_file():
        text = git_path.read_text(encoding="utf-8").strip()
        prefix = "gitdir:"
        if text.startswith(prefix):
            git_dir = Path(text[len(prefix) :].strip())
            if not git_dir.is_absolute():
                git_dir = (root / git_dir).resolve()
            head_path = git_dir / "HEAD"
    if not head_path.exists():
        return ""
    head = head_path.read_text(encoding="utf-8").strip()
    ref_prefix = "ref: refs/heads/"
    if head.startswith(ref_prefix):
        return head[len(ref_prefix) :]
    return "detached"


def _state_path(root: Path, state_arg: str | None) -> Path:
    if state_arg:
        candidate = Path(state_arg)
        return candidate if candidate.is_absolute() else root / candidate
    return root / STATE_REL


def _active_scope(root: Path) -> dict[str, Any]:
    gate_path = root / SCOPE_GATE_REL
    if not gate_path.exists():
        return {}
    try:
        data = json.loads(gate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict) or data.get("approved") is not True:
        return {}
    if str(data.get("scope_status") or "active").strip() not in {"", "active"}:
        return {}
    expires = _parse_iso(str(data.get("expires_at") or ""))
    if expires is None or expires <= _utc_now():
        return {}
    return data


def _active_session_conflict(
    root: Path,
    active_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session_gate = active_session_gate(root)
    if not session_gate:
        return {}
    if not active_scope:
        return session_gate
    session_id = str(session_gate.get("session_id") or "").strip()
    scope_session_id = str(active_scope.get("session_id") or "").strip()
    return session_gate if session_id != scope_session_id else {}


def _session_conflict_detail(
    session_gate: dict[str, Any],
    active_scope: dict[str, Any] | None = None,
) -> str:
    session_id = str(session_gate.get("session_id") or "unknown-session")
    mode = normalized_session_mode(session_gate)
    if active_scope:
        scope_id = str(active_scope.get("session_id") or "unknown-scope")
        return (
            f"Active session-gate {session_id} ({mode}) conflicts with "
            f"scope-gate session {scope_id}; close or reconcile it before continuing."
        )
    return (
        f"Active session-gate {session_id} ({mode}) must close before opening "
        "the next autonomous-auto iteration."
    )


def _write_claim_status(root: Path) -> dict[str, Any]:
    claim = load_write_claim(root)
    if not isinstance(claim, dict):
        return {"held": False, "stale": False}
    expires_at = str(claim.get("expires_at") or "")
    expiry = _parse_iso(expires_at)
    stale = bool(expiry and expiry <= _utc_now())
    return {
        "held": True,
        "stale": stale,
        "session_id": str(claim.get("session_id") or ""),
        "expires_at": expires_at,
        "worktree_path": str(claim.get("worktree_path") or ""),
        "branch": str(claim.get("branch") or ""),
    }


def _blocking_write_claim(root: Path) -> dict[str, Any] | None:
    claim = _write_claim_status(root)
    if claim.get("held") and not claim.get("stale"):
        return claim
    return None


def _approval_basis(state: dict[str, Any]) -> str:
    budget = state.get("autonomy_budget")
    if isinstance(budget, dict):
        basis = str(budget.get("approval_basis") or "").strip()
        if basis:
            return basis
    return "Autonomous-auto loop state did not record an approval_basis; stop before opening scope."


def _max_iterations(state: dict[str, Any]) -> int:
    budget = state.get("autonomy_budget")
    raw = budget.get("max_iterations") if isinstance(budget, dict) else None
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _allowed_actions(state: dict[str, Any]) -> set[str]:
    budget = state.get("autonomy_budget")
    raw = budget.get("allowed_actions") if isinstance(budget, dict) else None
    if not isinstance(raw, list):
        return set(VALID_ACTIONS) - {"stop"}
    return {str(item).strip() for item in raw if str(item).strip() in VALID_ACTIONS}


def _stop_conditions_for_read(budget: dict[str, Any]) -> list[str]:
    raw = budget.get("stop_conditions") if isinstance(budget, dict) else None
    conditions = [str(item) for item in raw] if isinstance(raw, list) else list(DEFAULT_STOP_CONDITIONS)
    for condition in DEFAULT_STOP_CONDITIONS:
        if condition not in conditions:
            conditions.append(condition)
    return conditions


def _budget_mapping(state: dict[str, Any]) -> dict[str, Any]:
    budget = state.setdefault("autonomy_budget", {})
    if not isinstance(budget, dict):
        budget = {}
        state["autonomy_budget"] = budget
    return budget


def _alignment_packets(state: dict[str, Any]) -> list[dict[str, Any]]:
    packets = state.get("alignment_packets")
    if not isinstance(packets, list):
        return []
    return [packet for packet in packets if isinstance(packet, dict)]


def _alignment_dispositions(state: dict[str, Any]) -> list[dict[str, Any]]:
    dispositions = state.get("alignment_dispositions")
    if not isinstance(dispositions, list):
        return []
    return [item for item in dispositions if isinstance(item, dict)]


def _next_alignment_packet_id(state: dict[str, Any]) -> str:
    existing = {
        str(packet.get("packet_id") or "")
        for packet in _alignment_packets(state)
        if str(packet.get("packet_id") or "")
    }
    index = len(existing) + 1
    while True:
        packet_id = f"align-{index:03d}"
        if packet_id not in existing:
            return packet_id
        index += 1


def classify_alignment_packet(message: str, packet_type: str | None = None) -> str:
    explicit = str(packet_type or "").strip()
    if explicit in ALIGNMENT_PACKET_TYPES:
        return explicit
    text = str(message or "").strip().lower()
    if any(marker in text for marker in ("stop", "abort", "do not continue", "pause", "halt")):
        return "async_stop"
    if any(
        marker in text
        for marker in ("approval_basis", "approved", "approval basis", "autonomy budget")
    ):
        return "approval_basis"
    if any(
        marker in text
        for marker in ("override", "instead", "change scope", "acceptance", "priority", "pivot")
    ):
        return "async_override"
    return "async_advisory"


def record_alignment_packet(
    state_path: Path,
    *,
    message: str,
    packet_type: str | None = None,
    source: str = "operator",
    checkpoint: str = DEFAULT_ALIGNMENT_CHECKPOINT,
    packet_id: str | None = None,
) -> dict[str, Any]:
    state = _load_yaml_mapping(state_path)
    packets = state.setdefault("alignment_packets", [])
    if not isinstance(packets, list):
        packets = []
        state["alignment_packets"] = packets
    resolved_id = str(packet_id or "").strip() or _next_alignment_packet_id(state)
    for packet in packets:
        if isinstance(packet, dict) and str(packet.get("packet_id") or "") == resolved_id:
            return packet
    packet = {
        "packet_id": resolved_id,
        "packet_type": classify_alignment_packet(message, packet_type),
        "source": str(source or "operator"),
        "message": str(message or "").strip(),
        "received_at": _iso(_utc_now()),
        "applies_at_checkpoint": str(checkpoint or DEFAULT_ALIGNMENT_CHECKPOINT),
        "disposition": "pending",
        "affected_artifact": "",
        "replay_required": False,
    }
    packets.append(packet)
    _write_yaml_mapping(state_path, state)
    return packet


def apply_alignment_packet(
    state_path: Path,
    *,
    packet_id: str,
    disposition: str,
    affected_artifact: str = "",
    replay_required: bool = False,
    note: str = "",
    approval_basis: str = "",
) -> dict[str, Any]:
    if disposition not in ALIGNMENT_DISPOSITIONS:
        raise SystemExit(f"invalid alignment disposition: {disposition}")
    state = _load_yaml_mapping(state_path)
    packets = state.setdefault("alignment_packets", [])
    if not isinstance(packets, list):
        raise SystemExit("alignment_packets must be a list before applying packets")
    packet: dict[str, Any] | None = None
    for item in packets:
        if isinstance(item, dict) and str(item.get("packet_id") or "") == packet_id:
            packet = item
            break
    if packet is None:
        raise SystemExit(f"alignment packet not found: {packet_id}")
    packet["disposition"] = disposition
    packet["disposition_at"] = _iso(_utc_now())
    packet["affected_artifact"] = affected_artifact
    packet["replay_required"] = bool(replay_required)
    if note:
        packet["disposition_note"] = note

    dispositions = state.setdefault("alignment_dispositions", [])
    if not isinstance(dispositions, list):
        dispositions = []
        state["alignment_dispositions"] = dispositions
    disposition_record = {
        "packet_id": packet_id,
        "packet_type": packet.get("packet_type"),
        "disposition": disposition,
        "affected_artifact": affected_artifact,
        "replay_required": bool(replay_required),
        "recorded_at": packet["disposition_at"],
    }
    if note:
        disposition_record["note"] = note
    dispositions.append(disposition_record)

    if packet.get("packet_type") == "approval_basis" and disposition == "applied":
        budget = _budget_mapping(state)
        budget["approval_basis"] = str(approval_basis or packet.get("message") or "").strip()
    _write_yaml_mapping(state_path, state)
    return packet


def _blocking_alignment_packet(state: dict[str, Any]) -> dict[str, Any] | None:
    for packet in _alignment_packets(state):
        if packet.get("packet_type") != "async_stop":
            continue
        if str(packet.get("disposition") or "pending") != "rejected":
            return packet
    return None


def _alignment_summary(state: dict[str, Any]) -> dict[str, Any]:
    packets = _alignment_packets(state)
    pending = [
        packet for packet in packets if str(packet.get("disposition") or "pending") == "pending"
    ]
    latest = packets[-1] if packets else {}
    return {
        "packet_count": len(packets),
        "pending_count": len(pending),
        "latest_packet_id": str(latest.get("packet_id") or ""),
        "latest_packet_type": str(latest.get("packet_type") or ""),
        "latest_disposition": str(latest.get("disposition") or ""),
        "disposition_count": len(_alignment_dispositions(state)),
    }


def _vision_state(state: dict[str, Any]) -> dict[str, Any]:
    raw = state.get("vision")
    vision = raw if isinstance(raw, dict) else {}
    target_band = str(vision.get("target_band") or DEFAULT_VISION_TARGET_BAND).strip().lower()
    current_band = str(vision.get("current_band") or "unevaluated").strip().lower()
    target_rank = VISION_BANDS.get(target_band, VISION_BANDS[DEFAULT_VISION_TARGET_BAND])
    current_rank = VISION_BANDS.get(current_band)
    realized = bool(current_rank is not None and current_rank >= target_rank)
    return {
        "anchor": str(vision.get("anchor") or DEFAULT_VISION_ANCHOR),
        "target_band": target_band if target_band in VISION_BANDS else DEFAULT_VISION_TARGET_BAND,
        "current_band": current_band,
        "realized": realized,
        "updated_at": str(vision.get("updated_at") or ""),
        "note": str(vision.get("note") or ""),
    }


def _normalize_vision_declaration(
    raw: dict[str, Any] | None,
    *,
    approval_basis: str,
    objective: str,
    allowed_actions: list[str],
    locked_at: str,
) -> dict[str, Any]:
    declaration = raw if isinstance(raw, dict) else {}
    summary = str(
        declaration.get("summary")
        or declaration.get("vision")
        or declaration.get("campaign_vision")
        or objective
    ).strip()
    selected_seed = str(
        declaration.get("selected_seed")
        or declaration.get("initiative_id")
        or declaration.get("candidate_id")
        or ""
    ).strip()
    selected_seed_type = str(
        declaration.get("selected_seed_type")
        or declaration.get("seed_type")
        or ("initiative" if selected_seed.startswith("INI-") else "")
    ).strip()
    scope_notes = str(
        declaration.get("scope_notes")
        or declaration.get("scope")
        or declaration.get("discussion_summary")
        or ""
    ).strip()
    return {
        "status": str(declaration.get("status") or "approved").strip(),
        "summary": summary,
        "selected_seed": selected_seed,
        "selected_seed_type": selected_seed_type,
        "scope_notes": scope_notes,
        "allowed_actions": list(allowed_actions),
        "approval_basis": str(declaration.get("approval_basis") or approval_basis).strip(),
        "locked_at": str(declaration.get("locked_at") or locked_at).strip(),
    }


def _completion_reason(state: dict[str, Any]) -> str:
    if not state:
        return ""
    explicit = str(state.get("completion_reason") or "").strip()
    if explicit:
        return explicit
    if _vision_state(state).get("realized"):
        return "vision_realized"
    return ""


def _continuation_summary(
    state: dict[str, Any],
    status: dict[str, Any],
    decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not state:
        return {"required": False, "reason": "missing_loop_state"}
    vision = (
        status.get("vision") if isinstance(status.get("vision"), dict) else _vision_state(state)
    )
    if vision.get("realized"):
        return {"required": False, "reason": "vision_realized"}
    stop_reason = str(status.get("stop_reason") or "")
    if stop_reason:
        return {"required": False, "reason": f"blocked:{stop_reason}"}
    if decision and decision.get("action") == "stop":
        return {"required": False, "reason": str(decision.get("stop_reason") or "stop_decision")}
    if int(status.get("remaining_iterations") or 0) <= 0:
        return {"required": False, "reason": "budget_exhausted"}
    if not status.get("can_continue"):
        return {"required": False, "reason": "not_continuable"}
    return {"required": True, "reason": "vision_not_realized"}


def _priority(item: dict[str, Any]) -> tuple[int, str]:
    raw = item.get("priority")
    try:
        priority = int(raw)
    except (TypeError, ValueError):
        priority = 9999
    return priority, str(item.get("id") or item.get("candidate_id") or "")


def _normalized_gate_value(raw: Any) -> str:
    return re.sub(r"[\s_]+", "-", str(raw or "").strip().lower())


def _is_truthy(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return raw != 0
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "y", "on", "required"}
    return False


def _has_protected_flag_values(raw: Any) -> bool:
    if isinstance(raw, dict):
        return any(
            _normalized_gate_value(key) in PROTECTED_FLAG_VALUES and _is_truthy(value)
            for key, value in raw.items()
        )
    if isinstance(raw, list):
        return any(_normalized_gate_value(item) in PROTECTED_FLAG_VALUES for item in raw)
    if isinstance(raw, str):
        values = [part for part in re.split(r"[,;\s]+", raw) if part]
        return any(_normalized_gate_value(value) in PROTECTED_FLAG_VALUES for value in values)
    return False


def _is_protected(candidate: dict[str, Any]) -> bool:
    target = _normalized_gate_value(candidate.get("target_layer"))
    pipeline = _normalized_gate_value(candidate.get("delivery_pipeline"))
    governance_mode = _normalized_gate_value(candidate.get("governance_mode"))
    if (
        target in PROTECTED_TARGET_LAYERS
        or pipeline in PROTECTED_PIPELINES
        or governance_mode in PROTECTED_GOVERNANCE_MODES
    ):
        return True
    if any(_is_truthy(candidate.get(flag)) for flag in PROTECTED_BOOLEAN_FLAGS):
        return True
    return any(
        _has_protected_flag_values(candidate.get(field))
        for field in ("flags", "risk_flags", "tags", "requires", "gate_flags")
    )


def _governance_mode(target_layer: str, delivery_pipeline: str, candidate: dict[str, Any]) -> str:
    explicit = str(candidate.get("governance_mode") or "").strip()
    if explicit:
        return explicit
    if _normalized_gate_value(delivery_pipeline) in PROTECTED_PIPELINES:
        return "governed"
    if _normalized_gate_value(target_layer) in PROTECTED_TARGET_LAYERS:
        return "governed"
    return "standard"


def _slug(value: str, fallback: str = "item") -> str:
    text = re.sub(r"[^a-z0-9-]+", "-", str(value or "").lower()).strip("-")
    return text or fallback


def _candidate_identity(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("candidate_id")
        or candidate.get("id")
        or candidate.get("backlog_id")
        or candidate.get("proposed_task_id")
        or ""
    ).strip()


def _candidate_title(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("title") or candidate.get("proposed_title") or _candidate_identity(candidate)
    ).strip()


def _score_candidate(action: str, candidate: dict[str, Any], source: str) -> dict[str, Any]:
    status = str(candidate.get("status") or "").strip()
    priority = _priority(candidate)[0]
    protected = _is_protected(candidate)
    readiness = 55
    if source == "queue":
        readiness = 95
    elif source == "self-capture":
        readiness = 88
    elif status == "ready":
        readiness = 86
    elif status in {"planned", "pending", "todo"}:
        readiness = 76
    elif action == "hydrate_task":
        readiness = 82
    elif action == "research_initiative":
        readiness = 64
    elif action == "refine_proposal":
        readiness = 58

    ux_anchor_value = {
        "capture_self_improvement": 95,
        "hydrate_task": 78,
        "research_initiative": 74,
        "ship_task": 70,
        "refine_proposal": 66,
    }.get(action, 50)
    risk = 0 if protected else 85
    dependency_state = 85 if source in {"queue", "self-capture", "backlog"} else 70
    if action == "hydrate_task":
        dependency_state = 82
    priority_bias = max(0, 20 - min(priority, 20)) if priority != 9999 else 0
    stop_cost = 80 if action in {"capture_self_improvement", "ship_task", "hydrate_task"} else 65
    total = readiness + ux_anchor_value + risk + dependency_state + priority_bias + stop_cost
    return {
        "readiness": readiness,
        "ux_anchor_value": ux_anchor_value,
        "risk": risk,
        "dependency_state": dependency_state,
        "priority_bias": priority_bias,
        "stop_cost": stop_cost,
        "total": total,
    }


def _candidate_snapshot(action: str, candidate: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "action": action,
        "candidate_id": _candidate_identity(candidate),
        "title": _candidate_title(candidate),
        "source": source,
        "scorecard": _score_candidate(action, candidate, source),
        "protected": _is_protected(candidate),
    }


def _delegation_stage(stage_id: str, subagent_type: str, trigger: str, purpose: str) -> dict[str, str]:
    return {
        "stage_id": stage_id,
        "subagent_type": subagent_type,
        "trigger": trigger,
        "purpose": purpose,
    }


def _delegation_plan_for_decision(decision: dict[str, Any], *, session_id: str) -> dict[str, Any]:
    """Return model-guidance for child-scope orchestration, not a hard scheduler."""
    action = str(decision.get("action") or "").strip()
    base_prefix = "autonomous_auto"
    stage_map: dict[str, list[dict[str, str]]] = {
        "ship_task": [
            _delegation_stage(
                f"{base_prefix}_s1_architect",
                "architect",
                "context-isolation",
                "Confirm scope, UX-anchor fit, dependencies, and protected boundaries.",
            ),
            _delegation_stage(
                f"{base_prefix}_s2_planner",
                "planner",
                "context-isolation",
                "Convert the selected task into deterministic implementation and test steps.",
            ),
            _delegation_stage(
                f"{base_prefix}_s3_builder",
                "builder",
                "context-budget",
                "Implement the scoped change and run focused verification.",
            ),
            _delegation_stage(
                f"{base_prefix}_s4_evaluator",
                "evaluator",
                "review-independence",
                "Evaluate output against acceptance, UX anchor, and replay threshold.",
            ),
        ],
        "hydrate_task": [
            _delegation_stage(
                f"{base_prefix}_s1_architect",
                "architect",
                "context-isolation",
                "Confirm readiness, approval_basis, hydration boundary, and non-goals.",
            ),
            _delegation_stage(
                f"{base_prefix}_s2_planner",
                "planner",
                "context-isolation",
                "Prepare the hydration plan and task-spec acceptance payload.",
            ),
            _delegation_stage(
                f"{base_prefix}_s3_reviewer",
                "reviewer",
                "review-independence",
                "Review the planned roadmap/backlog/spec write boundary before mutation.",
            ),
        ],
        "research_initiative": [
            _delegation_stage(
                f"{base_prefix}_s1_architect",
                "architect",
                "context-isolation",
                "Define research questions, freshness needs, and stop conditions.",
            ),
            _delegation_stage(
                f"{base_prefix}_s2_researcher",
                "researcher",
                "context-isolation",
                "Gather or refresh evidence without mutating executable backlog state.",
            ),
            _delegation_stage(
                f"{base_prefix}_s3_evaluator",
                "evaluator",
                "review-independence",
                "Judge research completeness and whether hydration is now justified.",
            ),
        ],
        "refine_proposal": [
            _delegation_stage(
                f"{base_prefix}_s1_architect",
                "architect",
                "context-isolation",
                "Reframe the proposal against current roadmap truth and UX-anchor value.",
            ),
            _delegation_stage(
                f"{base_prefix}_s2_reviewer",
                "reviewer",
                "review-independence",
                "Check for overreach, missing gates, stale evidence, and boundary drift.",
            ),
            _delegation_stage(
                f"{base_prefix}_s3_evaluator",
                "evaluator",
                "review-independence",
                "Score readiness/richness and decide whether a follow-on hydration is safe.",
            ),
        ],
        "capture_self_improvement": [
            _delegation_stage(
                f"{base_prefix}_s1_reviewer",
                "reviewer",
                "review-independence",
                "Validate the captured lesson as a real process defect or improvement signal.",
            ),
            _delegation_stage(
                f"{base_prefix}_s2_builder",
                "builder",
                "context-budget",
                "Materialize the smallest repo-native inbox/proposal/backlog artifact.",
            ),
        ],
    }
    stages = stage_map.get(action, [])
    return {
        "plan_schema_version": 1,
        "plan_id": f"{session_id}-delegation",
        "mode": "guidance",
        "principle": (
            "Use model judgment for orchestration, but do not silently collapse required "
            "fresh-context or review-independence stages inline."
        ),
        "inline_policy": (
            "Inline is acceptable only for a bounded trivial slice with an explicit "
            "justification and no required context-isolation, review-independence, "
            "context-budget, or protected gate."
        ),
        "run_ledger_evidence": {
            "run_id": session_id,
            "record_spawn": "python3 scripts/run_ledger.py record-spawn",
            "record_summary": "python3 scripts/run_ledger.py record-summary",
            "require_evidence": "python3 scripts/run_ledger.py require-stage-evidence",
        },
        "stages": stages,
    }


def _possible_alternatives(
    root: Path, state: dict[str, Any], selected_id: str
) -> list[dict[str, Any]]:
    alternatives: list[dict[str, Any]] = []
    self_capture = state.get("self_capture_queue")
    if isinstance(self_capture, list) and self_capture:
        first = (
            self_capture[0]
            if isinstance(self_capture[0], dict)
            else {"title": str(self_capture[0])}
        )
        candidate = {
            "candidate_id": str(first.get("candidate_id") or "self-capture"),
            "title": str(first.get("title") or "Capture autonomous-auto self-improvement"),
            "source": "self-capture",
        }
        alternatives.append(
            _candidate_snapshot("capture_self_improvement", candidate, "self-capture")
        )
    for action, candidate, source in (
        ("ship_task", _first_backlog_candidate(root), "backlog"),
        ("hydrate_task", _first_ready_initiative_candidate(root), "initiative-bank"),
        ("research_initiative", _first_research_initiative_candidate(root), "initiative-bank"),
        ("refine_proposal", _first_proposal_candidate(root), "proposal"),
    ):
        if candidate:
            alternatives.append(_candidate_snapshot(action, candidate, source))
    selected = str(selected_id or "")
    filtered = [
        item
        for item in alternatives
        if str(item.get("candidate_id") or "") and str(item.get("candidate_id") or "") != selected
    ]
    filtered.sort(key=lambda item: int(item.get("scorecard", {}).get("total") or 0), reverse=True)
    return filtered[:3]


def _architect_judgment(
    root: Path | None,
    state: dict[str, Any],
    *,
    action: str,
    candidate: dict[str, Any],
    source: str,
    reason: str,
) -> dict[str, Any]:
    candidate_id = _candidate_identity(candidate)
    selected = _candidate_snapshot(action, candidate, source)
    rejected = _possible_alternatives(root, state, candidate_id) if root is not None else []
    return {
        "decision": action,
        "rationale": reason,
        "selected": selected,
        "rejected_alternatives": rejected,
        "selection_basis": [
            "readiness",
            "ux_anchor_value",
            "risk",
            "dependency_state",
            "priority_bias",
            "stop_cost",
        ],
    }


def _stop_decision(
    state: dict[str, Any],
    reason: str,
    *,
    detail: str = "",
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    residual_risk = (
        "Campaign reached its completion condition; open a fresh budget to continue."
        if reason == "vision_realized"
        else "Continuation blocked until the stop reason is resolved."
    )
    return {
        "decision_schema_version": DECISION_SCHEMA_VERSION,
        "loop_id": str(state.get("loop_id") or ""),
        "iteration": int(state.get("iteration") or 0),
        "action": "stop",
        "candidate_id": str(
            (candidate or {}).get("id") or (candidate or {}).get("candidate_id") or ""
        ),
        "source": str((candidate or {}).get("source") or "governor"),
        "goal": detail or reason,
        "backlog_id": str((candidate or {}).get("id") or "AD-HOC"),
        "target_layer": str((candidate or {}).get("target_layer") or ""),
        "delivery_pipeline": str((candidate or {}).get("delivery_pipeline") or ""),
        "governance_mode": str((candidate or {}).get("governance_mode") or ""),
        "pipeline_command": "autonomous-auto",
        "approval_basis": _approval_basis(state),
        "reason": detail or reason,
        "stop_reason": reason,
        "architect_judgment": {
            "decision": "stop",
            "rationale": detail or reason,
            "residual_risk": residual_risk,
        },
        "alignment_checkpoint_summary": _alignment_summary(state),
    }


def _action_decision(
    state: dict[str, Any],
    *,
    action: str,
    candidate: dict[str, Any],
    source: str,
    reason: str,
    root: Path | None = None,
) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or candidate.get("id") or "").strip()
    title = str(candidate.get("title") or candidate.get("proposed_title") or candidate_id).strip()
    target_layer = str(candidate.get("target_layer") or "infrastructure").strip()
    delivery_pipeline = str(candidate.get("delivery_pipeline") or "standard").strip()
    governance_mode = _governance_mode(target_layer, delivery_pipeline, candidate)
    backlog_id = str(
        candidate.get("backlog_id") or candidate.get("proposed_task_id") or candidate_id or "AD-HOC"
    ).strip()
    return {
        "decision_schema_version": DECISION_SCHEMA_VERSION,
        "loop_id": str(state.get("loop_id") or ""),
        "iteration": int(state.get("iteration") or 0) + 1,
        "action": action,
        "candidate_id": candidate_id,
        "source": source,
        "goal": str(candidate.get("goal") or title),
        "backlog_id": backlog_id,
        "target_layer": target_layer,
        "delivery_pipeline": delivery_pipeline,
        "governance_mode": governance_mode,
        "pipeline_command": "autonomous-auto",
        "approval_basis": _approval_basis(state),
        "reason": reason,
        "stop_reason": None,
        "architect_judgment": _architect_judgment(
            root,
            state,
            action=action,
            candidate=candidate,
            source=source,
            reason=reason,
        ),
        "alignment_checkpoint_summary": _alignment_summary(state),
    }


def _queued_candidate(state: dict[str, Any]) -> dict[str, Any] | None:
    queue = state.get("queue")
    if not isinstance(queue, list) or not queue:
        return None
    first = queue[0]
    return first if isinstance(first, dict) else {"action": str(first)}


def _candidate_ids(raw: Any) -> set[str]:
    if isinstance(raw, dict):
        return {
            str(raw.get(field) or "").strip()
            for field in ("candidate_id", "id", "backlog_id", "proposed_task_id")
            if str(raw.get(field) or "").strip()
        }
    text = str(raw or "").strip()
    return {text} if text else set()


def _matches_decision(raw: Any, decision: dict[str, Any]) -> bool:
    if isinstance(raw, dict):
        action = str(raw.get("action") or "").strip()
        if action and action != str(decision.get("action") or "").strip():
            return False
    elif str(raw or "").strip() == str(decision.get("action") or "").strip():
        return True

    decision_ids = _candidate_ids(decision)
    item_ids = _candidate_ids(raw)
    return bool(decision_ids and item_ids and decision_ids.intersection(item_ids))


def _consume_opened_candidate(state: dict[str, Any], decision: dict[str, Any]) -> None:
    queue = state.get("queue")
    if isinstance(queue, list) and queue and _matches_decision(queue[0], decision):
        del queue[0]
        return

    if str(decision.get("source") or "").strip() != "self-capture":
        return
    self_capture = state.get("self_capture_queue")
    if isinstance(self_capture, list) and self_capture:
        del self_capture[0]


def _first_backlog_candidate(root: Path) -> dict[str, Any] | None:
    data = _load_yaml_mapping(root / ".azoth/backlog.yaml")
    items = data.get("items")
    if not isinstance(items, list):
        return None
    candidates = [
        item
        for item in items
        if isinstance(item, dict) and str(item.get("status") or "").strip() in SAFE_BACKLOG_STATUSES
    ]
    if not candidates:
        return None
    candidates.sort(key=_priority)
    candidate = dict(candidates[0])
    candidate["source"] = "backlog"
    return candidate


def _first_ready_initiative_candidate(root: Path) -> dict[str, Any] | None:
    bank_dir = root / ".azoth/initiative-banks"
    if not bank_dir.is_dir():
        return None
    for path in sorted(bank_dir.glob("*.yaml")):
        data = _load_yaml_mapping(path)
        readiness = data.get("readiness")
        if not isinstance(readiness, dict):
            continue
        if str(readiness.get("readiness_status") or "").strip() != "ready_to_hydrate":
            continue
        if str(readiness.get("human_decision") or "").strip() != "approved":
            continue
        if str(data.get("status") or "").strip() not in READY_INITIATIVE_STATUSES:
            continue
        slice_id = str(readiness.get("candidate_first_slice") or "").strip()
        slices = data.get("candidate_slices")
        selected: dict[str, Any] | None = None
        if isinstance(slices, list):
            for item in slices:
                if isinstance(item, dict) and str(item.get("candidate_id") or "") == slice_id:
                    selected = dict(item)
                    break
        candidate = selected or {}
        if str(candidate.get("status") or "").strip() in {"complete", "hydrated"}:
            continue
        candidate.setdefault(
            "candidate_id", slice_id or str(data.get("initiative_id") or path.stem)
        )
        candidate.setdefault("title", str(data.get("title") or candidate["candidate_id"]))
        candidate.setdefault("target_layer", readiness.get("target_layer") or "infrastructure")
        candidate.setdefault("delivery_pipeline", readiness.get("delivery_pipeline") or "standard")
        candidate.setdefault("proposed_task_id", str(candidate.get("proposed_task_id") or "AD-HOC"))
        candidate["source"] = "initiative-bank"
        return candidate
    return None


def _first_research_initiative_candidate(root: Path) -> dict[str, Any] | None:
    bank_dir = root / ".azoth/initiative-banks"
    if not bank_dir.is_dir():
        return None
    for path in sorted(bank_dir.glob("*.yaml")):
        data = _load_yaml_mapping(path)
        if str(data.get("status") or "").strip() in {"active_refinement", "research_needed"}:
            return {
                "candidate_id": str(data.get("initiative_id") or path.stem),
                "title": str(data.get("title") or path.stem),
                "target_layer": "planning",
                "delivery_pipeline": "standard",
                "source": "initiative-bank",
            }
    return None


def _first_proposal_candidate(root: Path) -> dict[str, Any] | None:
    proposal_dir = root / ".azoth/proposals"
    if not proposal_dir.is_dir():
        return None
    for path in sorted(proposal_dir.glob("*.yaml")):
        data = _load_yaml_mapping(path)
        if str(data.get("status") or "").strip() in PROPOSAL_STATUSES:
            return {
                "candidate_id": path.stem,
                "title": str(data.get("title") or path.stem),
                "target_layer": "planning",
                "delivery_pipeline": "standard",
                "source": "proposal",
            }
    return None


def decide_next(root: Path, state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return _stop_decision(
            {}, "missing_loop_state", detail=f"Loop state missing at {state_path}"
        )
    state = _load_yaml_mapping(state_path)
    if int(state.get("schema_version") or 0) != 1:
        return _stop_decision(
            state, "invalid_loop_state", detail="Loop state schema_version must be 1."
        )
    completion_reason = _completion_reason(state)
    if completion_reason:
        return _stop_decision(
            state,
            completion_reason,
            detail="Autonomous-auto campaign has reached its completion condition.",
        )
    if str(state.get("status") or "").strip() != "active":
        return _stop_decision(state, "loop_not_active", detail="Loop state is not active.")
    if not _approval_basis(state) or _approval_basis(state).startswith(
        "Autonomous-auto loop state did not"
    ):
        return _stop_decision(state, "missing_approval_basis")
    if int(state.get("iteration") or 0) >= _max_iterations(state):
        return _stop_decision(state, "budget_exhausted")
    active = _active_scope(root)
    session_conflict = _active_session_conflict(root, active)
    if session_conflict:
        return _stop_decision(
            state,
            "active_session_gate_conflict",
            detail=_session_conflict_detail(session_conflict, active),
        )
    if active:
        return _stop_decision(
            state,
            "active_scope_present",
            detail=f"Live scope {active.get('session_id')} must close before opening the next autonomous-auto iteration.",
        )
    write_claim = _blocking_write_claim(root)
    if write_claim:
        return _stop_decision(
            state,
            "active_write_claim_present",
            detail=(
                "Live write claim "
                f"{write_claim.get('session_id')} remains until {write_claim.get('expires_at')}; "
                "release or resolve it before opening the next autonomous-auto iteration."
            ),
        )
    blocking_packet = _blocking_alignment_packet(state)
    if blocking_packet:
        return _stop_decision(
            state,
            "async_stop_packet",
            detail=(
                "Pending async_stop alignment packet blocks continuation: "
                f"{blocking_packet.get('packet_id')}"
            ),
        )

    allowed = _allowed_actions(state)
    queued = _queued_candidate(state)
    if queued:
        action = str(queued.get("action") or "").strip()
        if action not in VALID_ACTIONS:
            return _stop_decision(
                state, "invalid_queued_action", detail=f"Invalid queued action: {action}"
            )
        if action == "stop":
            return _stop_decision(state, str(queued.get("stop_reason") or "queued_stop"))
        if action not in allowed:
            return _stop_decision(state, "action_not_in_budget", candidate=queued)
        if _is_protected(queued):
            return _stop_decision(state, "protected_gate_required", candidate=queued)
        return _action_decision(
            state,
            action=action,
            candidate=queued,
            source=str(queued.get("source") or "queue"),
            reason="Selected first queued autonomous-auto candidate inside the autonomy budget.",
            root=root,
        )

    self_capture = state.get("self_capture_queue")
    if isinstance(self_capture, list) and self_capture and "capture_self_improvement" in allowed:
        first = (
            self_capture[0]
            if isinstance(self_capture[0], dict)
            else {"title": str(self_capture[0])}
        )
        candidate = {
            "candidate_id": str(first.get("candidate_id") or "self-capture"),
            "title": str(first.get("title") or "Capture autonomous-auto self-improvement"),
            "target_layer": "planning",
            "delivery_pipeline": "standard",
            "source": "self-capture",
        }
        return _action_decision(
            state,
            action="capture_self_improvement",
            candidate=candidate,
            source="self-capture",
            reason="Captured a self-improvement signal before selecting more product work.",
            root=root,
        )

    backlog_candidate = _first_backlog_candidate(root)
    if backlog_candidate:
        if _is_protected(backlog_candidate):
            return _stop_decision(state, "protected_gate_required", candidate=backlog_candidate)
        if "ship_task" in allowed:
            return _action_decision(
                state,
                action="ship_task",
                candidate=backlog_candidate,
                source="backlog",
                reason="Selected the highest-priority ready backlog task.",
                root=root,
            )

    hydrate_candidate = _first_ready_initiative_candidate(root)
    if hydrate_candidate and "hydrate_task" in allowed:
        if _is_protected(hydrate_candidate):
            return _stop_decision(state, "protected_gate_required", candidate=hydrate_candidate)
        return _action_decision(
            state,
            action="hydrate_task",
            candidate=hydrate_candidate,
            source="initiative-bank",
            reason="Selected a ready-to-hydrate initiative-bank slice with approved readiness.",
            root=root,
        )

    research_candidate = _first_research_initiative_candidate(root)
    if research_candidate and "research_initiative" in allowed:
        return _action_decision(
            state,
            action="research_initiative",
            candidate=research_candidate,
            source="initiative-bank",
            reason="Selected an initiative bank that still needs research or refinement.",
            root=root,
        )

    proposal_candidate = _first_proposal_candidate(root)
    if proposal_candidate and "refine_proposal" in allowed:
        return _action_decision(
            state,
            action="refine_proposal",
            candidate=proposal_candidate,
            source="proposal",
            reason="Selected the first draft proposal for refinement.",
            root=root,
        )

    return _stop_decision(state, "no_safe_candidate")


def _session_id_for_decision(decision: dict[str, Any]) -> str:
    candidate = re.sub(r"[^a-z0-9-]+", "-", str(decision.get("candidate_id") or "adhoc").lower())
    candidate = candidate.strip("-") or "adhoc"
    return f"{_utc_now().strftime('%Y-%m-%d')}-autonomous-auto-{candidate}-{int(decision.get('iteration') or 0)}"


def _validate_decision_is_current(root: Path, state_path: Path, decision: dict[str, Any]) -> None:
    expected = decide_next(root, state_path)
    if expected.get("action") == "stop":
        stop_reason = str(expected.get("stop_reason") or "")
        readable_reason = (
            "active session-gate conflict"
            if stop_reason == "active_session_gate_conflict"
            else stop_reason
        )
        raise SystemExit(
            "refusing to open next scope because current loop state refuses continuation: "
            f"{readable_reason}"
        )

    compared_fields = (
        "loop_id",
        "iteration",
        "action",
        "candidate_id",
        "source",
        "backlog_id",
        "target_layer",
        "delivery_pipeline",
        "governance_mode",
        "approval_basis",
    )
    for field in compared_fields:
        if str(decision.get(field) or "") != str(expected.get(field) or ""):
            raise SystemExit(
                "refusing to open stale or mismatched autonomous-auto decision: "
                f"{field} is {decision.get(field)!r}, expected {expected.get(field)!r}"
            )


def _selected_self_capture_item(state: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    captures = state.get("self_capture_queue")
    decision_id = str(decision.get("candidate_id") or "")
    if isinstance(captures, list):
        for item in captures:
            capture = item if isinstance(item, dict) else {"title": str(item)}
            capture_id = str(capture.get("candidate_id") or capture.get("id") or "self-capture")
            if capture_id == decision_id:
                return dict(capture)
    return {
        "candidate_id": decision_id or "self-capture",
        "title": str(decision.get("goal") or "Capture autonomous-auto self-improvement"),
    }


def _self_capture_entry(decision: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(
        item.get("candidate_id") or item.get("id") or decision.get("candidate_id") or "self-capture"
    )
    entry_id = str(
        item.get("entry_id")
        or f"SRF-{_utc_now().strftime('%Y-%m-%d')}-AUTOAUTO-{_slug(candidate_id, 'self-capture').upper()}"
    )
    summary = str(
        item.get("summary")
        or item.get("title")
        or decision.get("goal")
        or "Autonomous-auto self-improvement capture."
    )
    return {
        "id": entry_id,
        "source": "autonomous-auto-loop",
        "source_type": "agent",
        "timestamp": _iso(_utc_now()),
        "category": str(item.get("category") or "process"),
        "severity": str(item.get("severity") or "medium"),
        "target": str(item.get("target") or "autonomous-auto"),
        "summary": summary,
        "evidence": str(item.get("evidence") or decision.get("reason") or ""),
        "recommended_action": str(item.get("recommended_action") or item.get("action") or summary),
        "auto_applicable": bool(item.get("auto_applicable", True)),
        "requires_human_gate": bool(item.get("requires_human_gate", False)),
        "related_sessions": item.get("related_sessions")
        if isinstance(item.get("related_sessions"), list)
        else [],
        "tags": item.get("tags")
        if isinstance(item.get("tags"), list)
        else ["autonomous-auto", "self-capture"],
    }


def _append_jsonl_once(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry_id = str(entry.get("id") or "")
    if path.exists() and entry_id:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(existing.get("id") or "") == entry_id:
                return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=False) + "\n")


def materialize_self_capture(
    root: Path,
    state: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    item = _selected_self_capture_item(state, decision)
    entry = _self_capture_entry(decision, item)
    rel_path = (
        Path(INBOX_DIR_REL)
        / f"session-reflection-{_utc_now().strftime('%Y-%m-%d')}-autonomous-auto-self-capture.jsonl"
    )
    artifact_path = root / rel_path
    _append_jsonl_once(artifact_path, entry)
    return {
        "materialized": True,
        "artifact_path": rel_path.as_posix(),
        "entry_id": entry["id"],
        "materialized_at": entry["timestamp"],
    }


def _load_json_argument(raw: str, *, label: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} must be a JSON object: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{label} must be a JSON object")
    return data


def _latest_autonomous_handoff(root: Path) -> Path | None:
    handoffs_dir = root / HANDOFFS_DIR_REL
    if not handoffs_dir.is_dir():
        return None
    candidates = [
        path
        for path in handoffs_dir.glob("*autonomous-auto*handoff*.md")
        if path.is_file()
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.name)[-1]


def _markdown_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = match.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def _clean_markdown_value(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 2 and text.startswith("`") and text.endswith("`"):
        text = text[1:-1]
    return text.replace("`", "").strip()


def _markdown_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _parse_current_truth(lines: list[str]) -> dict[str, str]:
    truth: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^\s*[-*]\s+([^:]+):\s*(.+?)\s*$", line)
        if not match:
            continue
        key = _markdown_key(match.group(1))
        if key:
            truth[key] = _clean_markdown_value(match.group(2))
    return truth


def _parse_markdown_list(lines: list[str]) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    for line in lines:
        match = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.+?)\s*$", line)
        if match:
            if current:
                items.append(_clean_markdown_value(" ".join(current)))
            current = [match.group(1)]
            continue
        stripped = line.strip()
        if current and stripped and not stripped.startswith("#") and not stripped.startswith("```"):
            current.append(stripped)
    if current:
        items.append(_clean_markdown_value(" ".join(current)))
    return items


def _parse_safe_continuation_commands(lines: list[str]) -> list[str]:
    commands: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence and stripped:
            commands.append(stripped)
    return commands


def _parse_recommended_options(lines: list[str]) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    body: list[str] = []
    for line in lines:
        match = re.match(r"^###\s+(.+?)\s*$", line)
        if match:
            if current is not None:
                current["body"] = "\n".join(body).strip()
                options.append(current)
            current = {"title": match.group(1).strip()}
            body = []
            continue
        if current is not None:
            body.append(line)
    if current is not None:
        current["body"] = "\n".join(body).strip()
        options.append(current)
    return options


def _parse_handoff_campaign(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "observable": False,
            "path": "",
            "failure_reason": "missing_handoff",
            "current_truth": {},
            "completion_reason": "",
            "vision_band": "",
            "known_residuals": [],
            "safe_continuation_commands": [],
            "recommended_options": [],
        }
    if not path.exists():
        return {
            "observable": False,
            "path": str(path),
            "failure_reason": "missing_handoff",
            "current_truth": {},
            "completion_reason": "",
            "vision_band": "",
            "known_residuals": [],
            "safe_continuation_commands": [],
            "recommended_options": [],
        }
    sections = _markdown_sections(path.read_text(encoding="utf-8"))
    current_truth = _parse_current_truth(sections.get("Current Truth", []))
    return {
        "observable": True,
        "path": str(path),
        "failure_reason": "",
        "current_truth": current_truth,
        "completion_reason": current_truth.get("completion_reason", ""),
        "vision_band": current_truth.get("vision_band", ""),
        "known_residuals": _parse_markdown_list(sections.get("Known Residuals", [])),
        "safe_continuation_commands": _parse_safe_continuation_commands(
            sections.get("Safe Continuation Checks", [])
        ),
        "recommended_options": _parse_recommended_options(
            sections.get("Recommended Next Development Options", [])
        ),
    }


def _current_loop_report(root: Path, state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {
            "state_path": str(state_path),
            "status": "missing_state",
            "observable": False,
            "failure_reason": "missing_loop_state",
            "completion_reason": "",
            "operator_read": {},
        }
    try:
        report = loop_status(root, state_path)
        report["operator_read"] = operator_read(root, state_path)
    except Exception as exc:
        return {
            "state_path": str(state_path),
            "status": "malformed_state",
            "observable": False,
            "failure_reason": f"malformed_loop_state: {exc}",
            "completion_reason": "",
            "operator_read": {},
        }
    report["observable"] = True
    report.setdefault("failure_reason", "")
    return report


def campaign_report(
    root: Path,
    state_path: Path,
    handoff_path: Path | None = None,
) -> dict[str, Any]:
    root = Path(root)
    state_path = Path(state_path)
    current_loop = _current_loop_report(root, state_path)

    resolved_handoff = (
        Path(handoff_path) if handoff_path is not None else _latest_autonomous_handoff(root)
    )
    if resolved_handoff is not None and not resolved_handoff.is_absolute():
        resolved_handoff = root / resolved_handoff
    handoff_campaign = _parse_handoff_campaign(resolved_handoff)
    completion_reason = str(handoff_campaign.get("completion_reason") or "")
    fail_closed = not current_loop.get("observable") or not handoff_campaign.get("observable")
    vision_realized = completion_reason == "vision_realized"
    observed_old_campaign = bool(handoff_campaign.get("observable"))
    ambiguous_observation = observed_old_campaign and not completion_reason
    return {
        "report_schema_version": 1,
        "current_loop": current_loop,
        "handoff_campaign": handoff_campaign,
        "observation": {
            "fresh_budget_required": bool(
                fail_closed or observed_old_campaign or ambiguous_observation
            ),
            "safe_to_continue_old_campaign": False,
            "reason": "vision_realized"
            if vision_realized
            else "fail_closed"
            if fail_closed
            else "missing_completion_reason"
            if ambiguous_observation
            else "handoff_observed",
        },
    }


def _repo_artifact_ref(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    resolved_root = Path(root).resolve()
    resolved_path = Path(path).resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        return str(resolved_path)


def _resolve_report_path(root: Path, value: Path | str | None) -> Path | None:
    if value is None or str(value) == "":
        return None
    path = Path(value)
    return path if path.is_absolute() else Path(root) / path


def _load_jsonl_mappings(path: Path | None) -> tuple[list[dict[str, Any]], list[str]]:
    if path is None:
        return [], ["not_requested"]
    if not path.exists():
        return [], ["missing_reflection"]

    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line_{line_number}: invalid_json: {exc.msg}")
            continue
        if not isinstance(parsed, dict):
            errors.append(f"line_{line_number}: entry_must_be_object")
            continue
        entries.append(parsed)
    return entries, errors


def _selected_lifecycle_candidate(
    doc: dict[str, Any],
    readiness_report: dict[str, Any],
) -> dict[str, Any]:
    candidate_id = str(readiness_report.get("candidate_id") or "")
    candidates = doc.get("candidate_slices") if isinstance(doc.get("candidate_slices"), list) else []
    candidate = next(
        (
            item
            for item in candidates
            if isinstance(item, dict) and str(item.get("candidate_id") or "") == candidate_id
        ),
        {},
    )
    if not isinstance(candidate, dict):
        candidate = {}
    acceptance = candidate.get("acceptance_criteria")
    non_goals = candidate.get("known_non_goals")
    open_questions = candidate.get("open_questions")
    evidence_refs = candidate.get("research_evidence_refs")
    return {
        "candidate_id": candidate.get("candidate_id") or readiness_report.get("candidate_id"),
        "title": candidate.get("title") or readiness_report.get("proposed_title"),
        "proposed_task_id": candidate.get("proposed_task_id")
        or readiness_report.get("candidate_task_ref"),
        "status": candidate.get("status") or readiness_report.get("candidate_status"),
        "target_layer": candidate.get("target_layer") or readiness_report.get("target_layer"),
        "delivery_pipeline": candidate.get("delivery_pipeline")
        or readiness_report.get("delivery_pipeline"),
        "summary": candidate.get("summary") or "",
        "acceptance_criteria_count": len(acceptance) if isinstance(acceptance, list) else 0,
        "non_goals_count": len(non_goals) if isinstance(non_goals, list) else 0,
        "open_questions": open_questions if isinstance(open_questions, list) else [],
        "research_evidence_refs": evidence_refs if isinstance(evidence_refs, list) else [],
    }


def _lifecycle_next_safe_actions(
    doc: dict[str, Any],
    readiness_report: dict[str, Any],
    reflections: list[dict[str, Any]],
) -> list[dict[str, str]]:
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    next_gate = str(readiness.get("next_readiness_gate") or "")
    recommendation = str(readiness.get("hydration_recommendation") or "")
    blockers = readiness_report.get("blocking_reasons")
    blocker_text = "; ".join(str(item) for item in blockers) if isinstance(blockers, list) else ""

    if readiness_report.get("approval_scope") == "planning_seed_only_no_hydration":
        actions = [
            {
                "action": "refine_proposal" if "refine" in next_gate else "research_initiative",
                "basis": (
                    "approval_scope planning_seed_only_no_hydration permits "
                    "discovery/planning only"
                ),
                "approval_needed": "new hydration or delivery approval_basis required before writes",
            }
        ]
    elif str(readiness_report.get("candidate_status") or "") == "hydrated":
        task_ref = str(readiness_report.get("candidate_task_ref") or "").strip()
        actions = [
            {
                "action": "ship_task",
                "basis": f"candidate is hydrated as {task_ref or 'an executable task'}",
                "approval_needed": "open a normal scoped delivery run before implementation",
            }
        ]
    elif readiness_report.get("ready_to_hydrate"):
        actions = [
            {
                "action": "hydrate_task",
                "basis": "readiness report is green and candidate has an executable scaffold command",
                "approval_needed": "explicit hydration approval_basis remains required at the write edge",
            }
        ]
    elif "refine" in next_gate:
        actions = [
            {
                "action": "refine_proposal",
                "basis": next_gate,
                "approval_needed": "covered by planning/refinement scope only",
            }
        ]
    else:
        actions = [
            {
                "action": "research_initiative",
                "basis": recommendation or blocker_text or "readiness is not green",
                "approval_needed": "covered by discovery/research scope only",
            }
        ]

    if reflections:
        actions.append(
            {
                "action": "capture_self_improvement",
                "basis": "operator feedback/reflection artifact is present and should influence future reports",
                "approval_needed": "not required for inbox-first self-improvement capture",
            }
        )
    return actions


def _lifecycle_blocked_actions(readiness_report: dict[str, Any]) -> list[dict[str, str]]:
    blockers = readiness_report.get("blocking_reasons")
    reason = "; ".join(str(item) for item in blockers) if isinstance(blockers, list) else ""
    if readiness_report.get("approval_scope") == "planning_seed_only_no_hydration":
        return [
            {
                "action": "hydrate_task",
                "reason": "approval_scope planning_seed_only_no_hydration does not authorize hydration",
            },
            {
                "action": "ship_task",
                "reason": "approval_scope planning_seed_only_no_hydration does not authorize delivery",
            },
        ]
    blocked: list[dict[str, str]] = []
    if not readiness_report.get("ready_to_hydrate"):
        blocked.append(
            {
                "action": "hydrate_task",
                "reason": reason or "readiness report is not green",
            }
        )
    if str(readiness_report.get("candidate_status") or "") != "hydrated":
        blocked.append(
            {
                "action": "ship_task",
                "reason": "candidate is not hydrated into an executable roadmap/backlog/spec task",
            }
        )
    return blocked


def _quality_signals_from_reflections(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    for entry in entries:
        signals.append(
            {
                "id": str(entry.get("id") or ""),
                "severity": str(entry.get("severity") or "unknown"),
                "summary": str(entry.get("summary") or ""),
                "recommended_action": str(entry.get("recommended_action") or ""),
            }
        )
    return signals


def build_initiative_lifecycle_report(
    root: Path,
    initiative_path: Path,
    *,
    reflection_path: Path | None = None,
    state_path: Path | None = None,
    handoff_path: Path | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    initiative_path = _resolve_report_path(root, initiative_path)
    if initiative_path is None:
        raise ValueError("initiative_path is required")
    reflection_path = _resolve_report_path(root, reflection_path)
    state_path = _resolve_report_path(root, state_path) or (root / STATE_REL)
    handoff_path = _resolve_report_path(root, handoff_path)

    doc = safe_load_yaml_path(initiative_path)
    if not isinstance(doc, dict):
        doc = {}
    readiness_report = build_initiative_readiness_report(
        initiative_path,
        repo_root=root,
        candidate_id=candidate_id,
    )
    reflections, reflection_errors = _load_jsonl_mappings(reflection_path)
    candidate = _selected_lifecycle_candidate(doc, readiness_report)
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    campaign = campaign_report(root, state_path, handoff_path=handoff_path)
    target_layer = str(readiness_report.get("target_layer") or "").lower()
    delivery_pipeline = str(readiness_report.get("delivery_pipeline") or "").lower()
    protected_gate_required = (
        target_layer in PROTECTED_TARGET_LAYERS or delivery_pipeline in PROTECTED_PIPELINES
    )
    reflection_observable = reflection_path is not None and reflection_path.exists()

    if str(readiness_report.get("candidate_status") or "") == "hydrated":
        readiness_meaning = (
            "The selected candidate is hydrated into an executable task; repeat hydration is "
            "blocked and the next safe move is scoped delivery."
        )
    elif readiness_report.get("ready_to_hydrate"):
        readiness_meaning = (
            "The selected candidate is ready to approach hydration, but the write edge still "
            "requires explicit approval_basis."
        )
    else:
        readiness_meaning = (
            "The initiative is still in discovery/refinement; hydration and delivery remain blocked."
        )
    quality_meaning = (
        "Operator feedback is available and should be carried into future report/evaluator contracts."
        if reflection_observable
        else "No reflection artifact was available, so report-quality implications are limited."
    )

    return {
        "report_schema_version": 1,
        "report_type": "initiative_lifecycle_report",
        "source_artifacts": {
            "initiative_bank": _repo_artifact_ref(root, initiative_path),
            "reflection": {
                "observable": reflection_observable,
                "path": _repo_artifact_ref(root, reflection_path),
                "entry_count": len(reflections),
                "failure_reasons": reflection_errors,
            },
            "loop_state": _repo_artifact_ref(root, state_path),
        },
        "scope_boundary": {
            "read_only": True,
            "mutates_planning_state": False,
            "allowed_actions_observed": [
                "research_initiative",
                "refine_proposal",
                "hydrate_task",
                "ship_task",
                "capture_self_improvement",
            ],
            "protected_boundaries": [
                "kernel/governance/M1/destructive/network expansion still stops",
                "hydration requires green readiness and explicit approval_basis at the write edge",
            ],
        },
        "initiative": {
            "initiative_id": doc.get("initiative_id"),
            "title": doc.get("title"),
            "status": doc.get("status"),
            "owner": doc.get("owner"),
            "source_proposal_refs": doc.get("source_proposal_refs")
            if isinstance(doc.get("source_proposal_refs"), list)
            else [],
            "local_findings_count": len(doc.get("local_findings") or [])
            if isinstance(doc.get("local_findings"), list)
            else 0,
        },
        "candidate": candidate,
        "readiness": {
            **readiness_report,
            "approval_basis": readiness.get("approval_basis") or "",
            "approval_scope": readiness.get("approval_scope") or "",
            "next_readiness_gate": readiness.get("next_readiness_gate") or "",
        },
        "campaign_context": {
            "current_loop_status": campaign.get("current_loop", {}).get("status"),
            "handoff_observable": campaign.get("handoff_campaign", {}).get("observable"),
            "fresh_budget_required": campaign.get("observation", {}).get(
                "fresh_budget_required"
            ),
            "observation_reason": campaign.get("observation", {}).get("reason"),
        },
        "quality": {
            "reflection_observable": reflection_observable,
            "quality_signals": _quality_signals_from_reflections(reflections),
            "evaluator_scores": [
                {
                    "name": "autonomous_auto_campaign_orchestrator_report",
                    "score": None,
                    "status": "not_recorded_in_source_artifacts",
                    "meaning": "No evaluator score artifact was provided; quality must be treated as unscored.",
                }
            ],
            "meaning": quality_meaning,
        },
        "operator_implications": [
            {
                "area": "readiness",
                "meaning": readiness_meaning,
            },
            {
                "area": "quality",
                "meaning": quality_meaning,
            },
            {
                "area": "next_move",
                "meaning": "Use the report to pick the next safe action; do not infer write authority from initiative presence alone.",
            },
        ],
        "safety": {
            "protected_gate_required": protected_gate_required,
            "hydration_safe_now": bool(readiness_report.get("ready_to_hydrate"))
            and not protected_gate_required,
            "approval_basis": readiness.get("approval_basis") or "",
            "human_decision": readiness_report.get("human_decision"),
        },
        "next_safe_actions": _lifecycle_next_safe_actions(doc, readiness_report, reflections),
        "blocked_actions": _lifecycle_blocked_actions(readiness_report),
    }


def _format_lifecycle_report(payload: dict[str, Any]) -> str:
    initiative = payload.get("initiative") if isinstance(payload.get("initiative"), dict) else {}
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
    safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else {}
    quality = payload.get("quality") if isinstance(payload.get("quality"), dict) else {}
    next_actions = payload.get("next_safe_actions")
    blocked_actions = payload.get("blocked_actions")
    next_action_items = next_actions if isinstance(next_actions, list) else []
    blocked_action_items = blocked_actions if isinstance(blocked_actions, list) else []
    next_text = ", ".join(
        f"{item.get('action')} (approval_needed={item.get('approval_needed')})"
        for item in next_action_items
        if isinstance(item, dict)
    )
    blocked_text = ", ".join(
        str(item.get("action"))
        for item in blocked_action_items
        if isinstance(item, dict)
    )
    return "\n".join(
        [
            "Autonomous-auto initiative lifecycle report",
            f"Initiative: {initiative.get('initiative_id')} - {initiative.get('title')}",
            f"Candidate: {candidate.get('candidate_id')} - {candidate.get('title')}",
            f"Readiness: {readiness.get('readiness_status')} (hydrate={readiness.get('ready_to_hydrate')})",
            f"Human decision: {readiness.get('human_decision')} ({readiness.get('approval_scope') or 'no scope'})",
            f"Quality: {'observed' if quality.get('reflection_observable') else 'not observed'}; evaluator score recorded=False",
            f"Protected gate required: {safety.get('protected_gate_required')}",
            f"Next safe actions: {next_text or 'none'}",
            f"Blocked actions: {blocked_text or 'none'}",
        ]
    )


def cmd_lifecycle_report(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    result = build_initiative_lifecycle_report(
        root,
        Path(args.initiative),
        reflection_path=Path(args.reflection) if args.reflection else None,
        state_path=_state_path(root, args.state),
        handoff_path=Path(args.handoff) if args.handoff else None,
        candidate_id=args.candidate_id,
    )
    print(
        json.dumps(result, indent=2, sort_keys=False)
        if args.json
        else _format_lifecycle_report(result)
    )


def init_loop(
    root: Path,
    state_path: Path,
    *,
    approval_basis: str,
    objective: str,
    loop_id: str,
    branch: str,
    max_iterations: int,
    replay_threshold: int,
    allowed_actions: list[str],
    queue: list[dict[str, Any]] | None = None,
    self_capture_queue: list[dict[str, Any]] | None = None,
    vision_declaration: dict[str, Any] | None = None,
    parent_session_id: str = "",
    replace: bool = False,
) -> dict[str, Any]:
    if state_path.exists() and not replace:
        raise SystemExit(
            f"loop state already exists at {state_path}; use --replace to overwrite it"
        )
    basis = str(approval_basis or "").strip()
    if not basis:
        raise SystemExit("--approval-basis is required")
    if max_iterations < 1:
        raise SystemExit("--max-iterations must be at least 1")
    if replay_threshold < 0:
        raise SystemExit("--replay-threshold must be zero or greater")
    resolved_actions = allowed_actions or DEFAULT_ALLOWED_ACTIONS
    invalid_actions = [
        action for action in resolved_actions if action not in DEFAULT_ALLOWED_ACTIONS
    ]
    if invalid_actions:
        raise SystemExit(f"invalid allowed action(s): {', '.join(invalid_actions)}")

    now = _iso(_utc_now())
    state = {
        "schema_version": 1,
        "loop_id": loop_id or f"autonomous-auto-{_utc_now().strftime('%Y%m%d%H%M%S')}",
        "objective": str(objective or "autonomous-auto loop"),
        "status": "active",
        "branch": branch or _current_branch(root),
        "autonomy_budget": {
            "approval_basis": basis,
            "max_iterations": max_iterations,
            "replay_threshold": replay_threshold,
            "allowed_actions": resolved_actions,
            "stop_conditions": DEFAULT_STOP_CONDITIONS,
        },
        "iteration": 0,
        "last_session_id": None,
        "parent_session_id": parent_session_id or None,
        "queue": queue or [],
        "self_capture_queue": self_capture_queue or [],
        "alignment_packets": [
            {
                "packet_id": "align-001",
                "packet_type": "approval_basis",
                "source": "operator",
                "message": basis,
                "received_at": now,
                "applies_at_checkpoint": "loop_init",
                "disposition": "applied",
                "disposition_at": now,
                "affected_artifact": STATE_REL,
                "replay_required": False,
                "disposition_note": "Initial branch-local autonomy budget recorded during loop initialization.",
            }
        ],
        "alignment_dispositions": [
            {
                "packet_id": "align-001",
                "packet_type": "approval_basis",
                "disposition": "applied",
                "affected_artifact": STATE_REL,
                "replay_required": False,
                "recorded_at": now,
                "note": "Initial branch-local autonomy budget recorded during loop initialization.",
            }
        ],
        "vision": {
            "anchor": DEFAULT_VISION_ANCHOR,
            "target_band": DEFAULT_VISION_TARGET_BAND,
            "current_band": "unevaluated",
            "realized": False,
            "updated_at": "",
            "note": "Vision score is unevaluated until an autonomous-auto closeout records it.",
            "declaration": _normalize_vision_declaration(
                vision_declaration,
                approval_basis=basis,
                objective=str(objective or "autonomous-auto loop"),
                allowed_actions=resolved_actions,
                locked_at=now,
            ),
        },
        "history": [],
        "next_candidate": {
            "status": "unresolved",
            "note": "Run decide-next after initialization to select the first eligible child scope.",
        },
        "stop_reason": None,
        "automation": {
            "recommended_driver": "codex-cron",
            "run_policy": "one_bounded_iteration_per_wakeup",
            "heartbeat_policy": "short_same_thread_experiments_only",
        },
    }
    _write_yaml_mapping(state_path, state)
    return {
        "initialized": True,
        "state_path": str(state_path),
        "loop_id": state["loop_id"],
        "objective": state["objective"],
        "max_iterations": max_iterations,
        "allowed_actions": resolved_actions,
        "queue_count": len(state["queue"]),
        "self_capture_count": len(state["self_capture_queue"]),
    }


def record_vision_score(
    state_path: Path,
    *,
    band: str,
    note: str = "",
    scorecard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = _load_yaml_mapping(state_path)
    if not state:
        raise SystemExit(f"loop state missing at {state_path}")
    normalized_band = str(band or "").strip().lower()
    if normalized_band not in VISION_BANDS:
        raise SystemExit(f"invalid vision band: {band}")
    vision = state.setdefault("vision", {})
    if not isinstance(vision, dict):
        vision = {}
        state["vision"] = vision
    target_band = str(vision.get("target_band") or DEFAULT_VISION_TARGET_BAND).strip().lower()
    if target_band not in VISION_BANDS:
        target_band = DEFAULT_VISION_TARGET_BAND
    updated_at = _iso(_utc_now())
    realized = VISION_BANDS[normalized_band] >= VISION_BANDS[target_band]
    vision.update(
        {
            "anchor": str(vision.get("anchor") or DEFAULT_VISION_ANCHOR),
            "target_band": target_band,
            "current_band": normalized_band,
            "realized": realized,
            "updated_at": updated_at,
            "note": str(note or ""),
            "scorecard": scorecard or {},
        }
    )
    history = state.setdefault("vision_history", [])
    if isinstance(history, list):
        history.append(
            {
                "band": normalized_band,
                "target_band": target_band,
                "realized": realized,
                "recorded_at": updated_at,
                "note": str(note or ""),
                "scorecard": scorecard or {},
            }
        )
    if realized:
        state["status"] = "completed"
        state["completion_reason"] = "vision_realized"
        state["stop_reason"] = None
    _write_yaml_mapping(state_path, state)
    return _vision_state(state)


def open_next(
    root: Path, state_path: Path, decision_path: Path, expires_at: str | None
) -> dict[str, Any]:
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    if decision.get("action") == "stop":
        raise SystemExit(f"refusing to open stopped decision: {decision.get('stop_reason')}")
    _validate_decision_is_current(root, state_path, decision)
    active = _active_scope(root)
    session_conflict = _active_session_conflict(root, active)
    if session_conflict:
        raise SystemExit(
            "refusing to open next scope while an active session-gate conflict is present: "
            f"{_session_conflict_detail(session_conflict, active)}"
        )
    if active:
        raise SystemExit("refusing to open next scope while an active scope is present")
    if _is_protected(decision):
        raise SystemExit("refusing to open protected decision without a fresh human gate")

    session_id = _session_id_for_decision(decision)
    expiry = expires_at or _iso(_utc_now() + timedelta(hours=2))
    target_layer = str(decision.get("target_layer") or "infrastructure")
    delivery_pipeline = str(decision.get("delivery_pipeline") or "standard")
    state = _load_yaml_mapping(state_path)
    delegation_plan = _delegation_plan_for_decision(decision, session_id=session_id)
    stage_ids = [
        str(stage.get("stage_id") or "")
        for stage in delegation_plan.get("stages", [])
        if isinstance(stage, dict) and str(stage.get("stage_id") or "")
    ]
    scope = {
        "approved": True,
        "expires_at": expiry,
        "goal": decision["goal"],
        "session_id": session_id,
        "approved_by": "autonomous-auto-loop",
        "approval_basis": decision["approval_basis"],
        "backlog_id": decision.get("backlog_id") or "AD-HOC",
        "delivery_pipeline": delivery_pipeline,
        "governance_mode": _governance_mode(target_layer, delivery_pipeline, decision),
        "pipeline_command": "autonomous-auto",
        "target_layer": target_layer,
        "autonomy_mode": "autonomous-auto",
        "alignment_mode": "async",
        "operator_lines_are_sequential_gates": False,
        "delegation_plan": delegation_plan,
        "loop_id": decision.get("loop_id"),
        "loop_iteration": decision.get("iteration"),
        "autonomy_budget": state.get("autonomy_budget", {}),
        "loop_decision": {
            "action": decision.get("action"),
            "candidate_id": decision.get("candidate_id"),
            "source": decision.get("source"),
            "reason": decision.get("reason"),
            "architect_judgment": decision.get("architect_judgment"),
            "alignment_checkpoint_summary": decision.get("alignment_checkpoint_summary"),
        },
    }
    ok, info = acquire_write_claim(root, session_id, expiry, harness="autonomous-loop")
    if not ok:
        raise SystemExit(f"write claim denied: {info}")
    try:
        upsert_run(
            root,
            run_id=session_id,
            mode="autonomous-auto",
            goal=str(decision["goal"]),
            status="active",
            next_action=(
                "Execute child scope using scope-gate delegation_plan; record "
                "stage_spawns and stage_summaries for delegated stages."
            ),
            session_id=session_id,
            backlog_id=str(decision.get("backlog_id") or "AD-HOC"),
            ide="codex",
            active_stage_id=stage_ids[0] if stage_ids else None,
            pending_stage_ids=stage_ids or None,
        )
    except Exception:
        release_write_claim(root, session_id)
        raise
    _write_json_mapping(root / SCOPE_GATE_REL, scope)

    materialization: dict[str, Any] | None = None
    if decision.get("action") == "capture_self_improvement":
        materialization = materialize_self_capture(root, state, decision)
    history = state.setdefault("history", [])
    if isinstance(history, list):
        entry = {
            "opened_at": _iso(_utc_now()),
            "session_id": session_id,
            "action": decision.get("action"),
            "candidate_id": decision.get("candidate_id"),
            "decision_path": str(decision_path),
            "architect_judgment": decision.get("architect_judgment"),
            "alignment_checkpoint_summary": decision.get("alignment_checkpoint_summary"),
            "delegation_plan_id": delegation_plan.get("plan_id"),
        }
        if materialization:
            entry["self_capture_materialization"] = materialization
        history.append(entry)
    _consume_opened_candidate(state, decision)
    state["iteration"] = int(decision.get("iteration") or int(state.get("iteration") or 0) + 1)
    state["last_session_id"] = session_id
    state["next_candidate"] = None
    _write_yaml_mapping(state_path, state)
    return {"opened": True, "session_id": session_id, "scope_gate": str(root / SCOPE_GATE_REL)}


def stop_loop(state_path: Path, reason: str) -> dict[str, Any]:
    state = _load_yaml_mapping(state_path)
    state.setdefault("schema_version", 1)
    state["status"] = "stopped"
    state["stop_reason"] = reason
    state["stopped_at"] = _iso(_utc_now())
    _write_yaml_mapping(state_path, state)
    return {"stopped": True, "reason": reason, "state_path": str(state_path)}


def loop_status(root: Path, state_path: Path) -> dict[str, Any]:
    path = state_path
    state = _load_yaml_mapping(path)
    active = _active_scope(root)
    session_conflict = _active_session_conflict(root, active)
    write_claim = _write_claim_status(root)
    blocking_write_claim = bool(write_claim.get("held") and not write_claim.get("stale"))
    blocking_packet = _blocking_alignment_packet(state) if state else None
    vision = _vision_state(state) if state else _vision_state({})
    completion_reason = _completion_reason(state) if state else ""
    budget_exhausted = bool(state and int(state.get("iteration") or 0) >= _max_iterations(state))
    missing_basis = bool(
        state
        and (
            not _approval_basis(state)
            or _approval_basis(state).startswith("Autonomous-auto loop state did not")
        )
    )
    explicit_stop_reason = str(state.get("stop_reason") or "") if state else "missing_loop_state"
    stop_reason = explicit_stop_reason
    if completion_reason:
        stop_reason = None
    elif not explicit_stop_reason and session_conflict:
        stop_reason = "active_session_gate_conflict"
    elif not explicit_stop_reason and active:
        stop_reason = "active_scope_present"
    elif not explicit_stop_reason and blocking_write_claim:
        stop_reason = "active_write_claim_present"
    elif not explicit_stop_reason and budget_exhausted:
        stop_reason = "budget_exhausted"
    elif not explicit_stop_reason and missing_basis:
        stop_reason = "missing_approval_basis"
    elif not explicit_stop_reason and blocking_packet:
        stop_reason = "async_stop_packet"
    iteration = int(state.get("iteration") or 0) if state else 0
    max_iterations = _max_iterations(state) if state else 0
    raw_status = str(state.get("status") or "") if state else "missing_state"
    status = "completed" if completion_reason else raw_status
    return {
        "state_path": str(path),
        "status": status,
        "raw_status": raw_status,
        "loop_id": state.get("loop_id") if state else "",
        "iteration": iteration,
        "max_iterations": max_iterations,
        "remaining_iterations": max(0, max_iterations - iteration),
        "active_scope_id": active.get("session_id", ""),
        "active_session_id": session_conflict.get("session_id", ""),
        "active_session_conflict": bool(session_conflict),
        "can_continue": bool(
            state
            and state.get("status") == "active"
            and not completion_reason
            and not active
            and not session_conflict
            and not blocking_write_claim
            and not budget_exhausted
            and not missing_basis
            and not blocking_packet
        ),
        "stop_reason": stop_reason,
        "completion_reason": completion_reason,
        "alignment": _alignment_summary(state) if state else _alignment_summary({}),
        "vision": vision,
        "write_claim": write_claim,
        "next_candidate": state.get("next_candidate") if state else None,
    }


def operator_read(root: Path, state_path: Path) -> dict[str, Any]:
    state = _load_yaml_mapping(state_path)
    status = loop_status(root, state_path)
    budget = state.get("autonomy_budget") if isinstance(state.get("autonomy_budget"), dict) else {}
    decision: dict[str, Any] = {}
    if status.get("can_continue"):
        decision = decide_next(root, state_path)
    next_move = ""
    if decision:
        next_move = str(decision.get("action") or "")
        candidate = str(decision.get("candidate_id") or "")
        if candidate:
            next_move = f"{next_move} ({candidate})"
    elif status.get("completion_reason"):
        next_move = f"complete: {status.get('completion_reason')}"
    elif status.get("stop_reason"):
        next_move = f"blocked: {status.get('stop_reason')}"
    continuation = _continuation_summary(state, status, decision)
    vision = status.get("vision", {})
    write_claim = status.get("write_claim") if isinstance(status.get("write_claim"), dict) else {}
    write_claim_read = (
        f"held by {write_claim.get('session_id')} until {write_claim.get('expires_at')}"
        if write_claim.get("held") and not write_claim.get("stale")
        else f"stale claim by {write_claim.get('session_id')}"
        if write_claim.get("held")
        else "none"
    )
    residual_risk = (
        f"Live write claim remains: {write_claim_read}."
        if write_claim.get("held") and not write_claim.get("stale")
        else "Green-ready only for branch-local, non-protected iterations."
        if status.get("can_continue")
        else "Campaign reached its completion condition; open a fresh budget to continue."
        if status.get("completion_reason")
        else "Continuation is blocked until the stop reason is resolved."
    )
    return {
        "title": "Autonomous-auto operator read",
        "objective": str(state.get("objective") or state.get("loop_id") or "autonomous-auto loop"),
        "loop_state": str(status.get("status") or "missing_state"),
        "iteration": status.get("iteration"),
        "max_iterations": status.get("max_iterations"),
        "remaining_iterations": status.get("remaining_iterations"),
        "can_continue": status.get("can_continue"),
        "next_likely_move": next_move,
        "approval_basis": _approval_basis(state) if state else "",
        "pending_alignment_packets": status.get("alignment", {}).get("pending_count", 0),
        "latest_alignment_packet": status.get("alignment", {}).get("latest_packet_id", ""),
        "vision_band": vision.get("current_band", "unevaluated"),
        "vision_target": vision.get("target_band", DEFAULT_VISION_TARGET_BAND),
        "vision_realized": vision.get("realized", False),
        "write_claim": write_claim_read,
        "continuation_required": continuation["required"],
        "continuation_reason": continuation["reason"],
        "stop_reason": status.get("stop_reason"),
        "completion_reason": status.get("completion_reason"),
        "stop_conditions": _stop_conditions_for_read(budget),
        "residual_risk": residual_risk,
    }


def _format_operator_read(payload: dict[str, Any]) -> str:
    stop_conditions = ", ".join(str(item) for item in payload.get("stop_conditions") or [])
    continuation = "required" if payload.get("continuation_required") else "not required"
    return "\n".join(
        [
            str(payload.get("title") or "Autonomous-auto operator read"),
            f"Objective: {payload.get('objective')}",
            f"Loop: {payload.get('loop_state')} ({payload.get('iteration')}/{payload.get('max_iterations')})",
            f"Vision: {payload.get('vision_band')} -> target {payload.get('vision_target')} (realized={payload.get('vision_realized')})",
            f"Next: {payload.get('next_likely_move')}",
            f"Continue: {continuation} ({payload.get('continuation_reason')})",
            f"Approval basis: {payload.get('approval_basis')}",
            f"Pending alignment packets: {payload.get('pending_alignment_packets')}",
            f"Write claim: {payload.get('write_claim')}",
            f"Completion reason: {payload.get('completion_reason') or 'none'}",
            f"Stop reason: {payload.get('stop_reason') or 'none'}",
            f"Stop conditions: {stop_conditions}",
            f"Residual risk: {payload.get('residual_risk')}",
        ]
    )


def cmd_status(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    path = _state_path(root, args.state)
    if args.operator_read:
        payload = operator_read(root, path)
        print(
            json.dumps(payload, indent=2, sort_keys=False)
            if args.json
            else _format_operator_read(payload)
        )
        return
    payload = {
        **loop_status(root, path),
    }
    print(json.dumps(payload, indent=2, sort_keys=False) if args.json else payload)


def cmd_init(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state_path = _state_path(root, args.state)
    queue = [_load_json_argument(item, label="--queue-json") for item in args.queue_json]
    self_capture_queue = [
        _load_json_argument(item, label="--self-capture-json") for item in args.self_capture_json
    ]
    result = init_loop(
        root,
        state_path,
        approval_basis=args.approval_basis,
        objective=args.objective,
        loop_id=args.loop_id,
        branch=args.branch,
        max_iterations=args.max_iterations,
        replay_threshold=args.replay_threshold,
        allowed_actions=args.allowed_action or DEFAULT_ALLOWED_ACTIONS,
        queue=queue,
        self_capture_queue=self_capture_queue,
        vision_declaration=_load_json_argument(
            args.vision_declaration_json,
            label="--vision-declaration-json",
        ),
        parent_session_id=args.parent_session_id,
        replace=args.replace,
    )
    print(json.dumps(result, indent=2, sort_keys=False))


def cmd_decide_next(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    path = _state_path(root, args.state)
    decision = decide_next(root, path)
    text = json.dumps(decision, indent=2, sort_keys=False)
    if args.decision_out:
        out = Path(args.decision_out)
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text if args.json else f"{decision['action']}: {decision['reason']}")


def cmd_open_next(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state_path = _state_path(root, args.state)
    decision_path = Path(args.decision)
    if not decision_path.is_absolute():
        decision_path = root / decision_path
    result = open_next(root, state_path, decision_path, args.expires_at)
    print(json.dumps(result, indent=2, sort_keys=False))


def cmd_stop(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state_path = _state_path(root, args.state)
    result = stop_loop(state_path, args.reason)
    print(json.dumps(result, indent=2, sort_keys=False))


def cmd_record_alignment(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state_path = _state_path(root, args.state)
    packet = record_alignment_packet(
        state_path,
        message=args.message,
        packet_type=args.packet_type,
        source=args.source,
        checkpoint=args.checkpoint,
        packet_id=args.packet_id,
    )
    print(json.dumps(packet, indent=2, sort_keys=False))


def cmd_apply_alignment(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state_path = _state_path(root, args.state)
    packet = apply_alignment_packet(
        state_path,
        packet_id=args.packet_id,
        disposition=args.disposition,
        affected_artifact=args.affected_artifact,
        replay_required=args.replay_required,
        note=args.note,
        approval_basis=args.approval_basis,
    )
    print(json.dumps(packet, indent=2, sort_keys=False))


def cmd_record_vision_score(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state_path = _state_path(root, args.state)
    scorecard = _load_json_argument(args.scorecard_json, label="--scorecard-json")
    result = record_vision_score(
        state_path,
        band=args.band,
        note=args.note,
        scorecard=scorecard,
    )
    print(json.dumps(result, indent=2, sort_keys=False))


def cmd_materialize_self_capture(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state_path = _state_path(root, args.state)
    state = _load_yaml_mapping(state_path)
    decision = decide_next(root, state_path)
    if decision.get("action") != "capture_self_improvement":
        raise SystemExit(f"next decision is not capture_self_improvement: {decision.get('action')}")
    result = materialize_self_capture(root, state, decision)
    history = state.setdefault("history", [])
    if isinstance(history, list):
        history.append({"self_capture_materialization": result, "recorded_at": _iso(_utc_now())})
    _consume_opened_candidate(state, decision)
    _write_yaml_mapping(state_path, state)
    print(json.dumps(result, indent=2, sort_keys=False))


def _format_campaign_report(payload: dict[str, Any]) -> str:
    current = payload.get("current_loop") if isinstance(payload.get("current_loop"), dict) else {}
    handoff = (
        payload.get("handoff_campaign")
        if isinstance(payload.get("handoff_campaign"), dict)
        else {}
    )
    observation = (
        payload.get("observation") if isinstance(payload.get("observation"), dict) else {}
    )
    return "\n".join(
        [
            "Autonomous-auto campaign report",
            f"Current loop: {current.get('status', 'unknown')}",
            f"Handoff: {handoff.get('path') or 'none'}",
            f"Completion reason: {handoff.get('completion_reason') or 'unknown'}",
            f"Vision band: {handoff.get('vision_band') or 'unknown'}",
            f"Fresh budget required: {observation.get('fresh_budget_required')}",
            f"Safe to continue old campaign: {observation.get('safe_to_continue_old_campaign')}",
        ]
    )


def cmd_campaign_report(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state_path = _state_path(root, args.state)
    handoff_path = Path(args.handoff) if args.handoff else None
    if handoff_path is not None and not handoff_path.is_absolute():
        handoff_path = root / handoff_path
    result = campaign_report(root, state_path, handoff_path=handoff_path)
    print(
        json.dumps(result, indent=2, sort_keys=False)
        if args.json
        else _format_campaign_report(result)
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--state", default=None, help=f"Loop state path, default {STATE_REL}.")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Print loop status.")
    status.add_argument("--json", action="store_true")
    status.add_argument(
        "--operator-read", action="store_true", help="Print concise operator status."
    )
    status.set_defaults(func=cmd_status)

    init = sub.add_parser("init", help="Initialize a local autonomous-auto loop state.")
    init.add_argument("--approval-basis", required=True)
    init.add_argument("--objective", default="autonomous-auto loop")
    init.add_argument("--loop-id", default="")
    init.add_argument("--branch", default="")
    init.add_argument("--max-iterations", type=int, default=1)
    init.add_argument("--replay-threshold", type=int, default=1)
    init.add_argument(
        "--allowed-action",
        action="append",
        choices=DEFAULT_ALLOWED_ACTIONS,
        default=None,
        help="Allowed action for the initialized budget; repeat to narrow the budget.",
    )
    init.add_argument(
        "--queue-json", action="append", default=[], help="Seed one queued JSON object."
    )
    init.add_argument(
        "--self-capture-json",
        action="append",
        default=[],
        help="Seed one self-capture JSON object.",
    )
    init.add_argument(
        "--vision-declaration-json",
        default="{}",
        help="Locked campaign vision declaration JSON captured after operator approval.",
    )
    init.add_argument("--parent-session-id", default="")
    init.add_argument("--replace", action="store_true", help="Overwrite an existing loop state.")
    init.set_defaults(func=cmd_init)

    decide = sub.add_parser("decide-next", help="Decide the next autonomous-auto action.")
    decide.add_argument("--json", action="store_true")
    decide.add_argument("--decision-out", default=None)
    decide.set_defaults(func=cmd_decide_next)

    open_cmd = sub.add_parser("open-next", help="Open the next autonomous-auto scope.")
    open_cmd.add_argument("--decision", required=True, help="Decision JSON path.")
    open_cmd.add_argument("--expires-at", default=None, help="Scope expiry ISO timestamp.")
    open_cmd.set_defaults(func=cmd_open_next)

    stop = sub.add_parser("stop", help="Stop the autonomous-auto loop.")
    stop.add_argument("--reason", required=True)
    stop.set_defaults(func=cmd_stop)

    record = sub.add_parser("record-alignment", help="Record an async alignment packet.")
    record.add_argument("--message", required=True)
    record.add_argument("--packet-type", choices=sorted(ALIGNMENT_PACKET_TYPES), default=None)
    record.add_argument("--source", default="operator")
    record.add_argument("--checkpoint", default=DEFAULT_ALIGNMENT_CHECKPOINT)
    record.add_argument("--packet-id", default=None)
    record.set_defaults(func=cmd_record_alignment)

    apply = sub.add_parser("apply-alignment", help="Apply or dispose an async alignment packet.")
    apply.add_argument("--packet-id", required=True)
    apply.add_argument("--disposition", choices=sorted(ALIGNMENT_DISPOSITIONS), required=True)
    apply.add_argument("--affected-artifact", default="")
    apply.add_argument("--replay-required", action="store_true")
    apply.add_argument("--note", default="")
    apply.add_argument("--approval-basis", default="")
    apply.set_defaults(func=cmd_apply_alignment)

    vision = sub.add_parser(
        "record-vision-score", help="Record the latest autonomous-auto UX vision score."
    )
    vision.add_argument("--band", choices=sorted(VISION_BANDS), required=True)
    vision.add_argument("--note", default="")
    vision.add_argument("--scorecard-json", default="{}")
    vision.set_defaults(func=cmd_record_vision_score)

    materialize = sub.add_parser(
        "materialize-self-capture", help="Write the next self-capture candidate to inbox."
    )
    materialize.set_defaults(func=cmd_materialize_self_capture)

    campaign = sub.add_parser("campaign-report", help="Observe an autonomous-auto handoff.")
    campaign.add_argument("--handoff", default=None, help="Handoff markdown path.")
    campaign.add_argument("--json", action="store_true")
    campaign.set_defaults(func=cmd_campaign_report)

    lifecycle = sub.add_parser(
        "lifecycle-report",
        help="Build a read-only initiative lifecycle report for autonomous-auto routing.",
    )
    lifecycle.add_argument("--initiative", required=True, help="Initiative bank YAML path.")
    lifecycle.add_argument("--reflection", default=None, help="Optional reflection JSONL path.")
    lifecycle.add_argument("--handoff", default=None, help="Optional autonomous-auto handoff path.")
    lifecycle.add_argument("--candidate-id", default=None, help="Optional candidate_slices id.")
    lifecycle.add_argument("--json", action="store_true")
    lifecycle.set_defaults(func=cmd_lifecycle_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

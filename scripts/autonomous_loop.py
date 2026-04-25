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

from run_ledger import acquire_write_claim
from session_gate import active_session_gate, normalized_session_mode
from yaml_helpers import safe_load_yaml_path

STATE_REL = ".azoth/autonomous-loop-state.local.yaml"
SCOPE_GATE_REL = ".azoth/scope-gate.json"
INBOX_DIR_REL = ".azoth/inbox"
DECISION_SCHEMA_VERSION = 1
VALID_ACTIONS = {
    "ship_task",
    "hydrate_task",
    "research_initiative",
    "refine_proposal",
    "capture_self_improvement",
    "stop",
}
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
DEFAULT_STOP_CONDITIONS = [
    "active_scope_present",
    "active_session_gate_conflict",
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
    if any(marker in text for marker in ("approval_basis", "approved", "approval basis", "autonomy budget")):
        return "approval_basis"
    if any(marker in text for marker in ("override", "instead", "change scope", "acceptance", "priority", "pivot")):
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
    pending = [packet for packet in packets if str(packet.get("disposition") or "pending") == "pending"]
    latest = packets[-1] if packets else {}
    return {
        "packet_count": len(packets),
        "pending_count": len(pending),
        "latest_packet_id": str(latest.get("packet_id") or ""),
        "latest_packet_type": str(latest.get("packet_type") or ""),
        "latest_disposition": str(latest.get("disposition") or ""),
        "disposition_count": len(_alignment_dispositions(state)),
    }


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
    return str(candidate.get("title") or candidate.get("proposed_title") or _candidate_identity(candidate)).strip()


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


def _possible_alternatives(root: Path, state: dict[str, Any], selected_id: str) -> list[dict[str, Any]]:
    alternatives: list[dict[str, Any]] = []
    self_capture = state.get("self_capture_queue")
    if isinstance(self_capture, list) and self_capture:
        first = self_capture[0] if isinstance(self_capture[0], dict) else {"title": str(self_capture[0])}
        candidate = {
            "candidate_id": str(first.get("candidate_id") or "self-capture"),
            "title": str(first.get("title") or "Capture autonomous-auto self-improvement"),
            "source": "self-capture",
        }
        alternatives.append(_candidate_snapshot("capture_self_improvement", candidate, "self-capture"))
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
    return {
        "decision_schema_version": DECISION_SCHEMA_VERSION,
        "loop_id": str(state.get("loop_id") or ""),
        "iteration": int(state.get("iteration") or 0),
        "action": "stop",
        "candidate_id": str((candidate or {}).get("id") or (candidate or {}).get("candidate_id") or ""),
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
            "residual_risk": "Continuation blocked until the stop reason is resolved.",
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
    backlog_id = str(candidate.get("backlog_id") or candidate.get("proposed_task_id") or candidate_id or "AD-HOC").strip()
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
        if isinstance(item, dict)
        and str(item.get("status") or "").strip() in SAFE_BACKLOG_STATUSES
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
        candidate.setdefault("candidate_id", slice_id or str(data.get("initiative_id") or path.stem))
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
        return _stop_decision({}, "missing_loop_state", detail=f"Loop state missing at {state_path}")
    state = _load_yaml_mapping(state_path)
    if int(state.get("schema_version") or 0) != 1:
        return _stop_decision(state, "invalid_loop_state", detail="Loop state schema_version must be 1.")
    if str(state.get("status") or "").strip() != "active":
        return _stop_decision(state, "loop_not_active", detail="Loop state is not active.")
    if not _approval_basis(state) or _approval_basis(state).startswith("Autonomous-auto loop state did not"):
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
            return _stop_decision(state, "invalid_queued_action", detail=f"Invalid queued action: {action}")
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
        first = self_capture[0] if isinstance(self_capture[0], dict) else {"title": str(self_capture[0])}
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
    candidate_id = str(item.get("candidate_id") or item.get("id") or decision.get("candidate_id") or "self-capture")
    entry_id = str(item.get("entry_id") or f"SRF-{_utc_now().strftime('%Y-%m-%d')}-AUTOAUTO-{_slug(candidate_id, 'self-capture').upper()}")
    summary = str(item.get("summary") or item.get("title") or decision.get("goal") or "Autonomous-auto self-improvement capture.")
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
        "related_sessions": item.get("related_sessions") if isinstance(item.get("related_sessions"), list) else [],
        "tags": item.get("tags") if isinstance(item.get("tags"), list) else ["autonomous-auto", "self-capture"],
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
    rel_path = Path(INBOX_DIR_REL) / f"session-reflection-{_utc_now().strftime('%Y-%m-%d')}-autonomous-auto-self-capture.jsonl"
    artifact_path = root / rel_path
    _append_jsonl_once(artifact_path, entry)
    return {
        "materialized": True,
        "artifact_path": rel_path.as_posix(),
        "entry_id": entry["id"],
        "materialized_at": entry["timestamp"],
    }


def open_next(root: Path, state_path: Path, decision_path: Path, expires_at: str | None) -> dict[str, Any]:
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
    blocking_packet = _blocking_alignment_packet(state) if state else None
    budget_exhausted = bool(state and int(state.get("iteration") or 0) >= _max_iterations(state))
    missing_basis = bool(
        state
        and (not _approval_basis(state) or _approval_basis(state).startswith("Autonomous-auto loop state did not"))
    )
    stop_reason = state.get("stop_reason") if state else "missing_loop_state"
    if session_conflict:
        stop_reason = "active_session_gate_conflict"
    elif active:
        stop_reason = "active_scope_present"
    elif budget_exhausted:
        stop_reason = "budget_exhausted"
    elif missing_basis:
        stop_reason = "missing_approval_basis"
    elif blocking_packet:
        stop_reason = "async_stop_packet"
    return {
        "state_path": str(path),
        "status": state.get("status") if state else "missing_state",
        "loop_id": state.get("loop_id") if state else "",
        "iteration": state.get("iteration") if state else 0,
        "max_iterations": _max_iterations(state) if state else 0,
        "active_scope_id": active.get("session_id", ""),
        "active_session_id": session_conflict.get("session_id", ""),
        "active_session_conflict": bool(session_conflict),
        "can_continue": bool(
            state
            and state.get("status") == "active"
            and not active
            and not session_conflict
            and not budget_exhausted
            and not missing_basis
            and not blocking_packet
        ),
        "stop_reason": stop_reason,
        "alignment": _alignment_summary(state) if state else _alignment_summary({}),
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
    elif status.get("stop_reason"):
        next_move = f"blocked: {status.get('stop_reason')}"
    return {
        "title": "Autonomous-auto operator read",
        "objective": str(state.get("objective") or state.get("loop_id") or "autonomous-auto loop"),
        "loop_state": str(status.get("status") or "missing_state"),
        "iteration": status.get("iteration"),
        "max_iterations": status.get("max_iterations"),
        "can_continue": status.get("can_continue"),
        "next_likely_move": next_move,
        "approval_basis": _approval_basis(state) if state else "",
        "pending_alignment_packets": status.get("alignment", {}).get("pending_count", 0),
        "latest_alignment_packet": status.get("alignment", {}).get("latest_packet_id", ""),
        "stop_reason": status.get("stop_reason"),
        "stop_conditions": budget.get("stop_conditions") if isinstance(budget.get("stop_conditions"), list) else DEFAULT_STOP_CONDITIONS,
        "residual_risk": (
            "Green-ready only for branch-local, non-protected iterations."
            if status.get("can_continue")
            else "Continuation is blocked until the stop reason is resolved."
        ),
    }


def _format_operator_read(payload: dict[str, Any]) -> str:
    stop_conditions = ", ".join(str(item) for item in payload.get("stop_conditions") or [])
    return "\n".join(
        [
            str(payload.get("title") or "Autonomous-auto operator read"),
            f"Objective: {payload.get('objective')}",
            f"Loop: {payload.get('loop_state')} ({payload.get('iteration')}/{payload.get('max_iterations')})",
            f"Next: {payload.get('next_likely_move')}",
            f"Approval basis: {payload.get('approval_basis')}",
            f"Pending alignment packets: {payload.get('pending_alignment_packets')}",
            f"Stop reason: {payload.get('stop_reason')}",
            f"Stop conditions: {stop_conditions}",
            f"Residual risk: {payload.get('residual_risk')}",
        ]
    )


def cmd_status(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    path = _state_path(root, args.state)
    if args.operator_read:
        payload = operator_read(root, path)
        print(json.dumps(payload, indent=2, sort_keys=False) if args.json else _format_operator_read(payload))
        return
    payload = {
        **loop_status(root, path),
    }
    print(json.dumps(payload, indent=2, sort_keys=False) if args.json else payload)


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--state", default=None, help=f"Loop state path, default {STATE_REL}.")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Print loop status.")
    status.add_argument("--json", action="store_true")
    status.add_argument("--operator-read", action="store_true", help="Print concise operator status.")
    status.set_defaults(func=cmd_status)

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

    materialize = sub.add_parser("materialize-self-capture", help="Write the next self-capture candidate to inbox.")
    materialize.set_defaults(func=cmd_materialize_self_capture)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

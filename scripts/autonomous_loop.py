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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from autonomous_campaign_audit import build_campaign_audit, learning_harvester_decision
from planning_bank_validate import build_initiative_readiness_report
from run_ledger import acquire_write_claim, load_write_claim, release_write_claim, upsert_run
from session_gate import active_session_gate, normalized_session_mode
from yaml_helpers import safe_load_yaml_path

STATE_REL = ".azoth/autonomous-loop-state.local.yaml"
SCOPE_GATE_REL = ".azoth/scope-gate.json"
PIPELINE_GATE_REL = ".azoth/pipeline-gate.json"
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
ROUTE_TABLE_STATES = [
    "raw_initiative",
    "discovery_active",
    "candidate_ready_for_review",
    "approved_for_hydration",
    "awaiting_hydration_approval",
    "delivery_ready",
    "campaign_strategy_preflight",
    "refresh_initiative_candidate",
    "completed_or_stale_campaign",
    "high_severity_self_capture",
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
    conditions = (
        [str(item) for item in raw] if isinstance(raw, list) else list(DEFAULT_STOP_CONDITIONS)
    )
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
    normalized = {
        "status": str(declaration.get("status") or "approved").strip(),
        "summary": summary,
        "selected_seed": selected_seed,
        "selected_seed_type": selected_seed_type,
        "scope_notes": scope_notes,
        "allowed_actions": list(allowed_actions),
        "approval_basis": str(declaration.get("approval_basis") or approval_basis).strip(),
        "locked_at": str(declaration.get("locked_at") or locked_at).strip(),
    }
    lifecycle_route = declaration.get("lifecycle_route")
    if not isinstance(lifecycle_route, dict):
        lifecycle_route = declaration.get("route_preflight")
    if isinstance(lifecycle_route, dict):
        normalized["lifecycle_route"] = lifecycle_route
    return normalized


def _reject_advisory_vision_declaration(raw: dict[str, Any] | None) -> None:
    if not isinstance(raw, dict):
        return
    status = str(raw.get("status") or "").strip().lower()
    mode = str(raw.get("mode") or "").strip().lower()
    packet_type = str(raw.get("packet_type") or "").strip()
    if (
        bool(raw.get("fresh_operator_approval_required"))
        or raw.get("may_open_scope") is False
        or status in {"advisory_only", "recommendation_only"}
        or mode == "recommendation_only"
        or packet_type == "autonomous_auto_next_campaign_recommendation"
    ):
        raise SystemExit(
            "advisory recommendation cannot initialize an autonomous-auto loop; "
            "record fresh operator approval first"
        )


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


def _recommendation_action_for_candidate(candidate: dict[str, Any], source: str) -> str:
    if source == "backlog":
        return "ship_task"
    if source == "initiative-bank":
        return "hydrate_task" if candidate.get("proposed_task_id") else "research_initiative"
    if source == "proposal":
        return (
            "hydrate_task"
            if str(candidate.get("recommended_route") or "") == "hydrate_task"
            else "refine_proposal"
        )
    return str(candidate.get("action") or "stop")


def _next_campaign_recommendation(
    root: Path, state: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    if not state:
        return {"available": False, "reason": "missing_loop_state", "ranked_recommendations": []}
    if str(status.get("completion_reason") or "") != "vision_realized":
        return {
            "available": False,
            "reason": str(status.get("stop_reason") or "loop_not_completed_green"),
            "ranked_recommendations": [],
        }
    if status.get("active_scope_id") or status.get("active_session_conflict"):
        return {
            "available": False,
            "reason": "active_scope_or_session_gate",
            "ranked_recommendations": [],
        }
    write_claim = status.get("write_claim") if isinstance(status.get("write_claim"), dict) else {}
    if write_claim.get("held") and not write_claim.get("stale"):
        return {
            "available": False,
            "reason": "active_write_claim_present",
            "ranked_recommendations": [],
        }

    raw_candidates: list[tuple[str, dict[str, Any], str]] = []
    for candidate, source in (
        (_first_backlog_candidate(root), "backlog"),
        (_first_ready_initiative_candidate(root), "initiative-bank"),
        (_first_research_initiative_candidate(root), "initiative-bank"),
        (_first_proposal_candidate(root), "proposal"),
    ):
        if candidate:
            raw_candidates.append(
                (_recommendation_action_for_candidate(candidate, source), candidate, source)
            )

    ranked: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for action, candidate, source in raw_candidates:
        snapshot = _candidate_snapshot(action, candidate, source, root)
        if snapshot.get("protected"):
            blocked.append(
                {
                    "action": action,
                    "candidate_id": snapshot.get("candidate_id"),
                    "reason": "protected boundary requires a fresh human gate",
                }
            )
            continue
        ranked.append(snapshot)
    ranked.sort(key=lambda item: int(item.get("scorecard", {}).get("total") or 0), reverse=True)
    selected = ranked[0] if ranked else None
    if not selected:
        return {
            "available": False,
            "reason": "no_non_protected_candidate",
            "ranked_recommendations": [],
            "blocked_recommendations": blocked,
        }
    route_preflight = (
        selected.get("route_preflight") if isinstance(selected.get("route_preflight"), dict) else {}
    )
    draft_declaration = {
        "goal": f"Prepare next autonomous-auto campaign for {selected.get('title')}.",
        "selected_mode": "autonomous-auto",
        "pipeline_command": "autonomous-auto",
        "alignment_mode": "async",
        "selected_seed": selected.get("candidate_id"),
        "allowed_action_classes": [selected.get("action"), "capture_self_improvement"],
        "budget": {"max_iterations": 3, "replay_threshold": 1},
        "protected_boundaries": [
            "kernel/governance/M1",
            "destructive actions",
            "credential/network expansion",
            "active scope or write claim",
            "unbounded hidden continuation",
        ],
        "fresh_operator_approval_required": True,
    }
    if route_preflight:
        lifecycle_route = {
            "verdict": route_preflight.get("verdict"),
            "selected_route": route_preflight.get("selected_route"),
            "route_state": route_preflight.get("route_state"),
            "approval_scope": route_preflight.get("approval_scope"),
            "approval_needed": route_preflight.get("approval_needed"),
            "readiness_evidence": route_preflight.get("readiness_evidence") or {},
            "source_artifacts": route_preflight.get("source_artifacts") or {},
            "blocked_actions": route_preflight.get("blocked_actions") or [],
        }
        draft_declaration.update(
            {
                "strategy_preflight_verdict": route_preflight.get("verdict"),
                "selected_route": route_preflight.get("selected_route"),
                "route_state": route_preflight.get("route_state"),
                "approval_scope": route_preflight.get("approval_scope"),
                "blocked_alternatives": route_preflight.get("blocked_actions") or [],
                "lifecycle_route": lifecycle_route,
            }
        )
    return {
        "available": True,
        "reason": "completed_green_campaign_ready_for_fresh_budget",
        "selection_basis": [
            "repo_native_candidate_surfaces",
            "ux_anchor_gap_continuation_after_closeout",
            "risk",
            "readiness",
            "fresh_budget_required",
        ],
        "evidence_refs": [
            ".azoth/autonomous-loop-state.local.yaml",
            ".azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md",
            ".azoth/initiative-banks/",
            ".azoth/proposals/",
            ".azoth/backlog.yaml",
        ],
        "ux_anchor_gaps": [
            "continuation_after_closeout",
            "direction_over_micromanagement",
            "architect_level_orchestration",
        ],
        "ranked_recommendations": ranked[:3],
        "blocked_recommendations": blocked,
        "draft_campaign_declaration": draft_declaration,
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


def _initiative_candidate_route_preflight(
    root: Path, candidate: dict[str, Any], source: str
) -> dict[str, Any]:
    if source != "initiative-bank":
        return {}
    source_bank_ref = str(candidate.get("source_bank_ref") or "").strip()
    initiative_ref = str(candidate.get("initiative_ref") or "").strip()
    if source_bank_ref:
        initiative_path = root / source_bank_ref
    elif initiative_ref:
        initiative_path = root / ".azoth" / "initiative-banks" / f"{initiative_ref}.yaml"
    else:
        return {}
    if not initiative_path.exists():
        return {
            "verdict": "stop_missing_initiative_bank",
            "initiative_ref": initiative_ref,
            "selected_route": "stop",
            "route_state": "missing_initiative_bank",
        }
    route_candidate_id = str(candidate.get("route_candidate_id") or "").strip() or None
    try:
        capsule = build_initiative_route_decision_capsule(
            root,
            initiative_path,
            candidate_id=route_candidate_id,
        )
    except Exception as exc:
        return {
            "verdict": "stop_lifecycle_route_unreadable",
            "initiative_ref": initiative_ref or initiative_path.stem,
            "selected_route": "stop",
            "route_state": "lifecycle_route_unreadable",
            "reason": str(exc),
        }
    selected_route = str(capsule.get("selected_route") or "")
    route_state = str(capsule.get("route_state") or "")
    readiness = (
        capsule.get("readiness_evidence")
        if isinstance(capsule.get("readiness_evidence"), dict)
        else {}
    )
    if selected_route == "research_initiative" and route_state in {
        "campaign_strategy_preflight",
        "refresh_initiative_candidate",
        "discovery_active",
        "raw_initiative",
    }:
        verdict = "can_initialize_research_campaign"
    elif selected_route == "stop":
        verdict = "stop_route_conflict"
    else:
        verdict = f"route_{selected_route or 'unknown'}"
    return {
        "verdict": verdict,
        "selected_route": selected_route,
        "route_state": route_state,
        "approval_scope": str(readiness.get("approval_scope") or ""),
        "approval_basis_present": bool(readiness.get("approval_basis_present")),
        "fresh_research_to_readiness_approval": bool(
            readiness.get("fresh_research_to_readiness_approval")
        ),
        "strategy_preflight_required": bool(readiness.get("strategy_preflight_required")),
        "candidate_id": str(readiness.get("candidate_id") or ""),
        "refresh_candidate_id": str(readiness.get("refresh_candidate_id") or ""),
        "approval_needed": capsule.get("approval_needed"),
        "readiness_evidence": readiness,
        "source_artifacts": capsule.get("source_artifacts") or {},
        "rejected_alternatives": capsule.get("rejected_alternatives") or [],
        "blocked_actions": capsule.get("blocked_actions") or [],
    }


def _candidate_snapshot(
    action: str, candidate: dict[str, Any], source: str, root: Path | None = None
) -> dict[str, Any]:
    snapshot = {
        "action": action,
        "candidate_id": _candidate_identity(candidate),
        "title": _candidate_title(candidate),
        "source": source,
        "scorecard": _score_candidate(action, candidate, source),
        "protected": _is_protected(candidate),
    }
    preflight = (
        _initiative_candidate_route_preflight(root, candidate, source) if root is not None else {}
    )
    if preflight:
        snapshot["route_preflight"] = preflight
    return snapshot


def _strategy_route_state_for_action(action: str, candidate: dict[str, Any]) -> str:
    if action == "ship_task":
        return "delivery_ready"
    if action == "hydrate_task":
        return "approved_for_hydration"
    if action == "research_initiative":
        return "discovery_active"
    if action == "refine_proposal":
        return "candidate_ready_for_review"
    if action == "capture_self_improvement":
        return "high_severity_self_capture"
    return str(candidate.get("route_state") or "unknown")


def _strategy_target_classification(
    action: str,
    candidate: dict[str, Any],
    *,
    protected: bool,
    route_conflict: bool,
) -> str:
    if protected:
        return "protected"
    if route_conflict:
        return "route-conflicted"
    if action == "research_initiative":
        return "research-only"
    if action == "hydrate_task":
        return "hydration-ready"
    if action == "ship_task":
        return "delivery-ready"
    return "live"


def _strategy_next_safe_action(
    *,
    action: str,
    route_selected: str,
    route_state: str,
    blocked: list[dict[str, str]],
) -> str:
    if not blocked:
        return action
    if route_selected and route_selected != action:
        return "stop_and_reconcile_lifecycle_route"
    if any(item.get("reason", "").startswith("active scope") for item in blocked):
        return "close_active_scope_before_open_next"
    if any(item.get("reason", "").startswith("active write claim") for item in blocked):
        return "release_or_resolve_write_claim_before_open_next"
    if any("protected boundary" in item.get("reason", "") for item in blocked):
        return "request_protected_human_gate"
    if any("approval_basis" in item.get("reason", "") for item in blocked):
        return "record_fresh_approval_basis"
    return f"stop_before_{route_state or route_selected or 'unknown'}"


def _strategy_preflight_for_decision(
    root: Path | None,
    state: dict[str, Any],
    *,
    action: str,
    candidate: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    route_decision = (
        candidate.get("route_decision") if isinstance(candidate.get("route_decision"), dict) else {}
    )
    route_selected = str(route_decision.get("selected_route") or action)
    route_state = str(route_decision.get("route_state") or _strategy_route_state_for_action(action, candidate))
    route_conflict = bool(route_decision and route_selected and route_selected != action)
    protected = _is_protected(candidate)
    completion_reason = _completion_reason(state)
    raw_loop_status = str(state.get("status") or "missing").strip() or "missing"
    current_loop_authority = "completed" if completion_reason else raw_loop_status
    approval_basis = _approval_basis(state)
    approval_basis_is_present = bool(approval_basis) and not approval_basis.startswith(
        "Autonomous-auto loop state did not"
    )
    active_approved_campaign = current_loop_authority == "active" and approval_basis_is_present
    harvester_decision = learning_harvester_decision(
        {
            "id": _candidate_identity(candidate),
            "source": source,
            "summary": _candidate_title(candidate),
            "reason": candidate.get("reason"),
            "protected_gate_required": protected,
            "learning_state": candidate.get("learning_state"),
            "tags": candidate.get("tags"),
        },
        approval_basis=approval_basis if active_approved_campaign else "",
        selected_action=action,
    )
    corpus_harvester: dict[str, Any] = {}
    if root is not None and state.get("loop_id"):
        try:
            corpus_harvester = build_campaign_audit(
                root,
                str(state.get("loop_id")),
                state_path=root / STATE_REL,
                ledger_path=root / ".azoth/run-ledger.local.yaml",
                episodes_path=root / ".azoth/memory/episodes.jsonl",
                inbox_dir=root / INBOX_DIR_REL,
            ).get("learning_harvester", {})
        except Exception:
            corpus_harvester = {}
    write_claim = _write_claim_status(root) if root is not None else {"held": False}
    active_scope = _active_scope(root) if root is not None else {}
    approval_basis_present = approval_basis_is_present
    blocked: list[dict[str, str]] = []
    mismatch_reason = ""
    if current_loop_authority != "active":
        blocked.append(
            {
                "action": action,
                "reason": (
                    f"current loop authority {current_loop_authority} requires fresh campaign approval"
                ),
            }
        )
    if protected:
        blocked.append(
            {
                "action": action,
                "reason": "protected boundary requires a fresh human gate",
            }
        )
    if active_scope:
        blocked.append(
            {
                "action": action,
                "reason": f"active scope {active_scope.get('session_id') or 'unknown'} blocks opening",
            }
        )
    if write_claim.get("held") and not write_claim.get("stale"):
        blocked.append(
            {
                "action": action,
                "reason": f"active write claim {write_claim.get('session_id') or 'unknown'} blocks opening",
            }
        )
    if not approval_basis_present:
        blocked.append({"action": action, "reason": "approval_basis is missing"})
    harvester_route = str(harvester_decision.get("route") or "")
    if harvester_route in {"human_gate_required", "defer_to_intake"}:
        blocked.append(
            {
                "action": action,
                "reason": (
                    "learning harvester routed signal to "
                    f"{harvester_route}; do not open autonomous self-heal"
                ),
            }
        )
    corpus_route = str(corpus_harvester.get("selected_learning_route") or "")
    if corpus_route in {"human_gate_required", "defer_to_intake"}:
        blocked.append(
            {
                "action": action,
                "reason": (
                    "learning harvester corpus recommendation is "
                    f"{corpus_route}; route through inbox/intake or human gate first"
                ),
            }
        )
    if route_conflict:
        mismatch_reason = (
            f"selected action {action} does not match lifecycle-route {route_selected}:{route_state}"
        )
        blocked.append({"action": action, "reason": mismatch_reason})

    verdict = "allow_open" if not blocked else "stop_route_conflict" if route_conflict else "stop_blocked"
    candidate_id = _candidate_identity(candidate)
    readiness = (
        route_decision.get("readiness_evidence")
        if isinstance(route_decision.get("readiness_evidence"), dict)
        else {}
    )
    return {
        "packet_schema_version": 1,
        "packet_type": "autonomous_auto_strategy_preflight",
        "edge": "open_next",
        "verdict": verdict,
        "may_open_scope": verdict == "allow_open",
        "selected_action": action,
        "candidate_id": candidate_id,
        "source": source,
        "target_classification": _strategy_target_classification(
            action,
            candidate,
            protected=protected,
            route_conflict=route_conflict,
        ),
        "selected_route": route_selected,
        "route_state": route_state,
        "route_authority": f"{route_selected}:{route_state}" if route_selected and route_state else action,
        "approval_scope": str(readiness.get("approval_scope") or route_decision.get("approval_scope") or ""),
        "approval_basis_present": approval_basis_present,
        "freshness_status": str(
            readiness.get("freshness_status") or "current_route_gate_and_claim_state"
        ),
        "fresh_campaign_authority": active_approved_campaign,
        "current_loop_authority": current_loop_authority,
        "source_artifacts": route_decision.get("source_artifacts") or {},
        "learning_harvester": {
            "consumed": True,
            "decision": harvester_decision,
            "campaign_recommendation": corpus_harvester,
            "write_authority": "advisory_only_scope_gates_still_required",
        },
        "gate_status": {
            "active_scope": bool(active_scope),
            "active_scope_id": str(active_scope.get("session_id") or ""),
            "active_write_claim": bool(write_claim.get("held") and not write_claim.get("stale")),
            "write_claim_session_id": str(write_claim.get("session_id") or ""),
            "protected": protected,
        },
        "blocked_alternatives": _dedupe_action_reasons(blocked),
        "mismatch_reason": mismatch_reason,
        "next_safe_action": _strategy_next_safe_action(
            action=action,
            route_selected=route_selected,
            route_state=route_state,
            blocked=blocked,
        ),
        "ux_anchor_fit": (
            "Strategy preflight reconciles route authority, approval basis, gates, "
            "write claims, and candidate classification before opening work."
        ),
    }


def _stable_strategy_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _strategy_preflight_signature(
    preflight: dict[str, Any],
) -> tuple[str, str, str, str, str, str, str, str, str, str, str]:
    return (
        str(preflight.get("verdict") or ""),
        str(preflight.get("selected_action") or ""),
        str(preflight.get("candidate_id") or ""),
        str(preflight.get("source") or ""),
        str(preflight.get("selected_route") or ""),
        str(preflight.get("route_state") or ""),
        str(preflight.get("approval_scope") or ""),
        str(preflight.get("freshness_status") or ""),
        str(preflight.get("next_safe_action") or ""),
        _stable_strategy_value(preflight.get("gate_status") or {}),
        _stable_strategy_value(preflight.get("blocked_alternatives") or []),
    )


def _reject_advisory_decision_payload(decision: dict[str, Any]) -> None:
    status = str(decision.get("status") or "").strip().lower()
    mode = str(decision.get("mode") or "").strip().lower()
    packet_type = str(decision.get("packet_type") or "").strip()
    if (
        bool(decision.get("fresh_operator_approval_required"))
        or decision.get("may_open_scope") is False
        or status in {"advisory_only", "recommendation_only"}
        or mode == "recommendation_only"
        or packet_type == "autonomous_auto_next_campaign_recommendation"
    ):
        raise SystemExit(
            "refusing to open advisory recommendation as a scope decision; "
            "record fresh operator approval and run decide-next first"
        )


def _validate_strategy_preflight_evidence(
    decision: dict[str, Any], expected: dict[str, Any]
) -> None:
    expected_preflight = (
        expected.get("strategy_preflight")
        if isinstance(expected.get("strategy_preflight"), dict)
        else {}
    )
    if not expected_preflight:
        return
    actual_preflight = (
        decision.get("strategy_preflight")
        if isinstance(decision.get("strategy_preflight"), dict)
        else {}
    )
    if not actual_preflight:
        raise SystemExit(
            "refusing to open decision with missing strategy-preflight evidence"
        )
    if actual_preflight.get("packet_type") != "autonomous_auto_strategy_preflight":
        raise SystemExit("refusing to open decision with invalid strategy-preflight packet")
    if actual_preflight.get("may_open_scope") is not True:
        raise SystemExit("refusing to open decision because strategy-preflight blocks opening")
    if str(actual_preflight.get("verdict") or "") != "allow_open":
        raise SystemExit("refusing to open decision because strategy-preflight did not allow opening")
    if _strategy_preflight_signature(actual_preflight) != _strategy_preflight_signature(
        expected_preflight
    ):
        raise SystemExit("refusing to open stale or conflicting strategy-preflight evidence")


def _delegation_stage(
    stage_id: str, subagent_type: str, trigger: str, purpose: str
) -> dict[str, str]:
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


def _next_campaign_recommendation_packet(
    state: dict[str, Any],
    reason: str,
    status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    vision = _vision_state(state)
    if (
        reason != "vision_realized"
        or vision.get("current_band") != "green"
        or vision.get("target_band") != "green"
        or not vision.get("realized")
    ):
        return {}
    status = status or {}
    write_claim = status.get("write_claim") if isinstance(status.get("write_claim"), dict) else {}
    return {
        "packet_schema_version": 1,
        "packet_type": "autonomous_auto_next_campaign_recommendation",
        "mode": "recommendation_only",
        "status": "advisory_only",
        "source": "completed_green_loop",
        "requires_fresh_approval": True,
        "may_open_scope": False,
        "hidden_continuation": False,
        "current_loop_authority": "closed",
        "fresh_budget_required": True,
        "safe_to_continue_current_loop": False,
        "hidden_continuation_allowed": False,
        "completed_loop": {
            "loop_id": str(state.get("loop_id") or ""),
            "iteration": int(status.get("iteration") or state.get("iteration") or 0),
            "completion_reason": "vision_realized",
            "vision_band": str(vision.get("current_band") or ""),
            "vision_target": str(vision.get("target_band") or ""),
        },
        "safety_preflight": {
            "active_scope": bool(status.get("active_scope_id")),
            "active_scope_id": str(status.get("active_scope_id") or ""),
            "active_session_conflict": bool(status.get("active_session_conflict")),
            "active_write_claim": bool(write_claim.get("held") and not write_claim.get("stale")),
            "safe_to_open_without_approval": False,
        },
        "recommended_operator_action": (
            "Review and approve a fresh autonomous-auto campaign declaration before opening "
            "another child scope."
        ),
        "recommended_commands": [
            "python3 scripts/autonomous_loop.py status --operator-read",
            "python3 scripts/autonomous_loop.py campaign-report --json",
            "python3 scripts/run_ledger.py status",
        ],
        "blocked_actions": [
            {
                "action": "open_next",
                "reason": "fresh approval required after vision_realized",
            },
            {
                "action": "continue_old_campaign",
                "reason": "completed campaign evidence is not continuation authority",
            },
        ],
        "approval_boundary": (
            "This packet may recommend the next campaign, but it must not initialize a new "
            "loop or open scope without a fresh operator-approved declaration."
        ),
    }


def _next_campaign_recommendation_report_packet(
    root: Path,
    state: dict[str, Any],
    status: dict[str, Any],
) -> dict[str, Any]:
    packet = _next_campaign_recommendation_packet(
        state,
        str(status.get("completion_reason") or ""),
        status,
    )
    if not packet:
        return {}
    strategy = _next_campaign_recommendation(root, state, status)
    packet["available"] = bool(strategy.get("available"))
    packet["candidate_strategy"] = strategy
    for field in (
        "reason",
        "selection_basis",
        "evidence_refs",
        "ux_anchor_gaps",
        "ranked_recommendations",
        "blocked_recommendations",
    ):
        if field in strategy:
            packet[field] = strategy[field]
    declaration = strategy.get("draft_campaign_declaration")
    if isinstance(declaration, dict):
        packet["draft_campaign_declaration"] = declaration
    return packet


def _stop_decision(
    state: dict[str, Any],
    reason: str,
    *,
    detail: str = "",
    candidate: dict[str, Any] | None = None,
    root: Path | None = None,
    status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    residual_risk = (
        "Campaign reached its completion condition; open a fresh budget to continue."
        if reason == "vision_realized"
        else "Continuation blocked until the stop reason is resolved."
    )
    decision = {
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
        "route_decision": (candidate or {}).get("route_decision"),
        "architect_judgment": {
            "decision": "stop",
            "rationale": detail or reason,
            "residual_risk": residual_risk,
        },
        "alignment_checkpoint_summary": _alignment_summary(state),
    }
    packet = _next_campaign_recommendation_packet(state, reason, status)
    if packet and root is not None:
        report_status = status or {
            "completion_reason": reason,
            "iteration": int(state.get("iteration") or 0),
            "write_claim": {},
        }
        enriched = _next_campaign_recommendation_report_packet(root, state, report_status)
        if enriched:
            packet = enriched
    if packet:
        decision["next_campaign_recommendation"] = packet
    return decision


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
    strategy_preflight = _strategy_preflight_for_decision(
        root,
        state,
        action=action,
        candidate=candidate,
        source=source,
    )
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
        "route_decision": candidate.get("route_decision"),
        "strategy_preflight": strategy_preflight,
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
        candidate["source_bank_ref"] = _repo_artifact_ref(root, path)
        candidate["initiative_ref"] = str(data.get("initiative_id") or path.stem)
        return candidate
    return None


def _first_research_initiative_candidate(root: Path) -> dict[str, Any] | None:
    bank_dir = root / ".azoth/initiative-banks"
    if not bank_dir.is_dir():
        return None
    for path in sorted(bank_dir.glob("*.yaml")):
        data = _load_yaml_mapping(path)
        if str(data.get("status") or "").strip() in {"active_refinement", "research_needed"}:
            readiness = data.get("readiness") if isinstance(data.get("readiness"), dict) else {}
            route_candidate_id = str(
                readiness.get("candidate_first_slice") or readiness.get("next_candidate_ref") or ""
            ).strip()
            return {
                "candidate_id": str(data.get("initiative_id") or path.stem),
                "title": str(data.get("title") or path.stem),
                "target_layer": "planning",
                "delivery_pipeline": "standard",
                "source": "initiative-bank",
                "source_bank_ref": _repo_artifact_ref(root, path),
                "initiative_ref": str(data.get("initiative_id") or path.stem),
                "route_candidate_id": route_candidate_id,
            }
    return None


def _first_proposal_candidate(root: Path) -> dict[str, Any] | None:
    proposal_dir = root / ".azoth/proposals"
    if not proposal_dir.is_dir():
        return None
    for path in sorted(proposal_dir.glob("*.yaml")):
        data = _load_yaml_mapping(path)
        if str(data.get("status") or "").strip() in PROPOSAL_STATUSES:
            hydration_slice = _proposal_hydration_slice(data)
            placement = (
                hydration_slice.get("placement")
                if isinstance(hydration_slice.get("placement"), dict)
                else {}
            )
            return {
                "candidate_id": path.stem,
                "title": str(
                    hydration_slice.get("exact_title")
                    or hydration_slice.get("title")
                    or data.get("title")
                    or path.stem
                ),
                "target_layer": str(placement.get("target_layer") or "planning"),
                "delivery_pipeline": str(placement.get("delivery_pipeline") or "standard"),
                "source": "proposal",
                "proposal_ref": _repo_artifact_ref(root, path),
                "proposed_task_id": str(hydration_slice.get("proposed_task_id") or ""),
                "recommended_route": str(hydration_slice.get("route") or ""),
            }
    return None


def _proposal_path_for_candidate(root: Path, candidate: dict[str, Any]) -> Path | None:
    for field in ("proposal_ref", "proposal_path", "source_ref", "source"):
        value = str(candidate.get(field) or "").strip()
        if not value:
            continue
        path = root / value
        if value.startswith(".azoth/proposals/") and path.exists():
            return path
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    if str(candidate.get("source") or "").strip() == "proposal" and candidate_id:
        path = root / ".azoth/proposals" / f"{candidate_id}.yaml"
        if path.exists():
            return path
    if candidate_id.startswith("proposal-"):
        path = root / ".azoth/proposals" / f"{candidate_id.removeprefix('proposal-')}.yaml"
        if path.exists():
            return path
    return None


def _proposal_titles_for_hydration(data: dict[str, Any]) -> set[str]:
    titles: set[str] = set()
    details = data.get("details") if isinstance(data.get("details"), dict) else {}
    selected_hydration = _proposal_hydration_slice(data)
    for field in ("exact_title", "title"):
        titles.add(str(selected_hydration.get(field) or "").strip())
    placement = (
        selected_hydration.get("placement")
        if isinstance(selected_hydration.get("placement"), dict)
        else {}
    )
    titles.add(str(placement.get("title") or "").strip())
    titles = {title for title in titles if title}
    if titles:
        return titles
    for section_name in ("recommended_next_slice", "recommended_first_slice"):
        section = details.get(section_name) if isinstance(details.get(section_name), dict) else {}
        for field in ("exact_title", "title"):
            titles.add(str(section.get(field) or "").strip())
        placement = section.get("placement") if isinstance(section.get("placement"), dict) else {}
        titles.add(str(placement.get("title") or "").strip())
    titles = {title for title in titles if title}
    if titles:
        return titles
    return {str(data.get("title") or "").strip()} - {""}


def _proposal_hydration_slice(data: dict[str, Any]) -> dict[str, Any]:
    details = data.get("details") if isinstance(data.get("details"), dict) else {}
    for section_name in ("recommended_next_slice", "recommended_first_slice"):
        section = details.get(section_name)
        if isinstance(section, dict) and str(section.get("route") or "") == "hydrate_task":
            return section
    for section in _walk_mapping_values(details):
        if not isinstance(section, dict):
            continue
        route = str(section.get("route") or "").strip()
        plan = (
            section.get("proposed_hydration_plan")
            if isinstance(section.get("proposed_hydration_plan"), dict)
            else {}
        )
        if route not in {"hydrate_task", "hydrate_task_after_refinement"} and not plan:
            continue
        normalized = dict(section)
        normalized["route"] = "hydrate_task"
        normalized.setdefault("exact_title", section.get("title") or data.get("title"))
        if plan:
            normalized.setdefault(
                "proposed_task_id",
                plan.get("hydrated_task_ref") or plan.get("proposed_task_id") or "",
            )
            placement = (
                normalized.get("placement") if isinstance(normalized.get("placement"), dict) else {}
            )
            normalized["placement"] = {
                **placement,
                "target_layer": placement.get("target_layer")
                or section.get("target_layer")
                or plan.get("target_layer")
                or "infrastructure",
                "delivery_pipeline": placement.get("delivery_pipeline")
                or section.get("delivery_pipeline")
                or plan.get("delivery_pipeline")
                or "standard",
            }
            if plan.get("scaffold_command"):
                normalized["scaffold_command"] = plan.get("scaffold_command")
        return normalized
    return {}


def _walk_task_nodes(data: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if any(str(data.get(field) or "").strip() for field in ("id", "task_ref", "roadmap_ref")):
            nodes.append(data)
        for value in data.values():
            nodes.extend(_walk_task_nodes(value))
    elif isinstance(data, list):
        for item in data:
            nodes.extend(_walk_task_nodes(item))
    return nodes


def _walk_mapping_values(data: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if isinstance(data, dict):
        nodes.append(data)
        for value in data.values():
            nodes.extend(_walk_mapping_values(value))
    elif isinstance(data, list):
        for item in data:
            nodes.extend(_walk_mapping_values(item))
    return nodes


def _slug_tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.lower()) if token}


def _proposal_matches_seed(path: Path, proposal: dict[str, Any], seed: str) -> bool:
    seed_text = str(seed or "").strip().lower()
    if not seed_text:
        return False
    exact_ids = {
        path.stem.lower(),
        f"proposal-{path.stem}".lower(),
        str(proposal.get("id") or "").strip().lower(),
        str(proposal.get("proposal_id") or "").strip().lower(),
        str(proposal.get("backlog_id") or "").strip().lower(),
    }
    if seed_text in exact_ids:
        return True
    seed_tokens = _slug_tokens(seed_text)
    seed_tokens.discard("proposal")
    if not seed_tokens:
        return False
    searchable = " ".join(
        [
            path.stem,
            str(proposal.get("title") or ""),
            str(proposal.get("summary") or ""),
            json.dumps(proposal.get("details") or {}, sort_keys=True, default=str),
        ]
    )
    return seed_tokens.issubset(_slug_tokens(searchable))


def _declared_proposal_candidate(root: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    vision = state.get("vision") if isinstance(state.get("vision"), dict) else {}
    declaration = (
        vision.get("declaration") if isinstance(vision.get("declaration"), dict) else {}
    )
    if str(declaration.get("selected_seed_type") or "").strip() != "proposal":
        return None
    seed = str(declaration.get("selected_seed") or "").strip()
    proposal_dir = root / ".azoth/proposals"
    if not seed or not proposal_dir.is_dir():
        return None
    for path in sorted(proposal_dir.glob("*.yaml")):
        data = _load_yaml_mapping(path)
        if not _proposal_matches_seed(path, data, seed):
            continue
        hydration_slice = _proposal_hydration_slice(data)
        placement = (
            hydration_slice.get("placement")
            if isinstance(hydration_slice.get("placement"), dict)
            else {}
        )
        return {
            "candidate_id": seed,
            "title": str(
                hydration_slice.get("exact_title")
                or hydration_slice.get("title")
                or data.get("title")
                or seed
            ),
            "target_layer": str(placement.get("target_layer") or "planning"),
            "delivery_pipeline": str(placement.get("delivery_pipeline") or "standard"),
            "source": "proposal",
            "proposal_ref": _repo_artifact_ref(root, path),
            "proposed_task_id": str(hydration_slice.get("proposed_task_id") or ""),
            "recommended_route": str(hydration_slice.get("route") or ""),
            "scaffold_command": str(hydration_slice.get("scaffold_command") or ""),
        }
    return None


def _proposal_task_match(
    root: Path, proposal_path: Path, candidate: dict[str, Any]
) -> dict[str, Any] | None:
    proposal = _load_yaml_mapping(proposal_path)
    hydration_slice = _proposal_hydration_slice(proposal)
    if not hydration_slice:
        return None
    titles = _proposal_titles_for_hydration(proposal)
    placement = (
        hydration_slice.get("placement")
        if isinstance(hydration_slice.get("placement"), dict)
        else {}
    )
    proposal_sources = {
        proposal_path.stem,
        f"proposal-{proposal_path.stem}",
        str(placement.get("source") or "").strip(),
        str(candidate.get("candidate_id") or "").strip(),
    }
    proposal_sources = {source for source in proposal_sources if source}
    initiative_ref = str(placement.get("initiative_ref") or candidate.get("initiative_ref") or "")
    proposed_task_id = str(candidate.get("proposed_task_id") or "").strip()
    for rel_path in (".azoth/backlog.yaml", ".azoth/roadmap.yaml"):
        path = root / rel_path
        if not path.exists():
            continue
        for item in _walk_task_nodes(safe_load_yaml_path(path)):
            task_id = str(item.get("id") or item.get("task_ref") or item.get("roadmap_ref") or "")
            title = str(item.get("title") or "").strip()
            source = str(item.get("source") or "").strip()
            task_initiative = str(item.get("initiative_ref") or "").strip()
            task_matches = bool(
                (title and title in titles)
                or (source and source in proposal_sources)
                or (proposed_task_id and task_id == proposed_task_id)
            )
            if not task_matches:
                continue
            if initiative_ref and task_initiative and task_initiative != initiative_ref:
                continue
            status = str(item.get("status") or "").strip().lower()
            complete = bool(
                status in TERMINAL_TASK_STATUSES
                or item.get("completed_date")
                or (task_id and _hydrated_task_is_complete(root, task_id))
            )
            return {
                "task_id": task_id or "matched-task",
                "title": title or task_id or proposal_path.stem,
                "source": source or proposal_path.stem,
                "status": status or ("completed" if complete else "pending"),
                "initiative_ref": task_initiative,
                "complete": complete,
                "artifacts_exist": _hydrated_task_artifacts_exist(root, task_id),
            }
    return None


def _queued_proposal_hydration_decision(
    root: Path, state: dict[str, Any], candidate: dict[str, Any], allowed: set[str]
) -> dict[str, Any] | None:
    proposal_path = _proposal_path_for_candidate(root, candidate)
    if not proposal_path:
        return None
    match = _proposal_task_match(root, proposal_path, candidate)
    if not match:
        return None
    task_id = match["task_id"]
    proposal_ref = str(proposal_path.relative_to(root))
    source_artifacts = {
        "proposal_ref": proposal_ref,
        "existing_task_id": task_id,
        "task_artifacts_exist": bool(match.get("artifacts_exist")),
        "exact_scaffold_command_present": bool(str(candidate.get("scaffold_command") or "")),
    }
    stale_route = candidate.get("stale_initiative_route_decision")
    if isinstance(stale_route, dict):
        source_artifacts["stale_initiative_route"] = stale_route.get("route_decision") or stale_route
    if match.get("complete"):
        return _stop_decision(
            state,
            "proposal_hydration_already_completed",
            detail=(
                "Proposal-backed hydration candidate "
                f"{proposal_ref} already maps to completed task {task_id}; "
                "refresh route state instead of opening duplicate hydration."
            ),
            candidate={
                **candidate,
                "id": task_id,
                "candidate_id": task_id,
                "backlog_id": task_id,
                "route_decision": {
                    "selected_route": "stop",
                    "route_state": "completed_or_stale_campaign",
                    "proposal_ref": proposal_ref,
                    "existing_task_id": task_id,
                    "live_task_truth": match,
                    "source_artifacts": source_artifacts,
                    "blocked_actions": [
                        {
                            "action": "hydrate_task",
                            "reason": f"proposal-backed task {task_id} is already complete",
                        }
                    ],
                },
            },
        )
    if match.get("artifacts_exist") and "ship_task" in allowed:
        ship_candidate = {
            **candidate,
            "id": task_id,
            "candidate_id": task_id,
            "backlog_id": task_id,
            "title": match.get("title") or task_id,
            "source": proposal_ref,
            "route_decision": {
                "selected_route": "ship_task",
                "route_state": "delivery_ready",
                "proposal_ref": proposal_ref,
                "existing_task_id": task_id,
                "live_task_truth": match,
                "source_artifacts": source_artifacts,
                "blocked_actions": [
                    {
                        "action": "hydrate_task",
                        "reason": f"proposal-backed task {task_id} is already hydrated",
                    }
                ],
            },
        }
        if _is_protected(ship_candidate):
            return _stop_decision(state, "protected_gate_required", candidate=ship_candidate)
        return _action_decision(
            state,
            action="ship_task",
            candidate=ship_candidate,
            source=str(proposal_path.relative_to(root)),
            reason=(
                "Proposal-backed hydration target already exists as an executable task; "
                "routing to scoped delivery instead of duplicate hydration."
            ),
            root=root,
        )
    return _stop_decision(
        state,
        "proposal_hydration_existing_task_requires_ship_approval",
            detail=(
                "Proposal-backed hydration candidate "
                f"{proposal_ref} maps to existing task {task_id}; "
                "ship_task approval and hydrated artifacts are required before delivery."
            ),
        candidate={
            **candidate,
            "id": task_id,
            "candidate_id": task_id,
            "backlog_id": task_id,
            "route_decision": {
                "selected_route": "stop",
                "route_state": "delivery_ready_without_approval",
                "proposal_ref": proposal_ref,
                "existing_task_id": task_id,
                "live_task_truth": match,
                "source_artifacts": source_artifacts,
            },
        },
    )


def _proposal_discovery_decision(
    root: Path, state: dict[str, Any], candidate: dict[str, Any], allowed: set[str]
) -> dict[str, Any] | None:
    if str(candidate.get("recommended_route") or "") != "hydrate_task":
        return None
    hydration_candidate = {**candidate, "action": "hydrate_task"}
    live_truth_decision = _queued_proposal_hydration_decision(
        root, state, hydration_candidate, allowed
    )
    if live_truth_decision:
        return live_truth_decision
    if "hydrate_task" not in allowed:
        return _stop_decision(
            state,
            "proposal_hydration_requires_approval",
            detail=(
                "Discovered proposal-backed hydration recommendation requires "
                "hydrate_task approval before opening work."
            ),
            candidate=hydration_candidate,
        )
    return _action_decision(
        state,
        action="hydrate_task",
        candidate=hydration_candidate,
        source="proposal",
        reason="Selected a discovered proposal-backed hydration recommendation.",
        root=root,
    )


def _initiative_route_stop_decision(
    root: Path,
    state_path: Path,
    state: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any] | None:
    capsule = _initiative_route_capsule(root, state_path, state, candidate)
    if not isinstance(capsule, dict):
        return capsule
    if capsule.get("action") == "stop":
        return capsule
    if str(capsule.get("selected_route") or "") != "stop":
        return None
    route_state = str(capsule.get("route_state") or "unknown")
    route_label = str(candidate.get("initiative_ref") or candidate.get("candidate_id") or "")
    reason = f"Lifecycle route for {route_label or 'initiative'} selected stop ({route_state})."
    return _stop_decision(
        state,
        f"lifecycle_route_stop_{route_state}",
        detail=reason,
        candidate={
            **candidate,
            "route_decision": capsule,
            "governance_mode": str(candidate.get("governance_mode") or "standard"),
        },
    )


def _initiative_route_capsule(
    root: Path,
    state_path: Path,
    state: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any] | None:
    source_bank_ref = str(candidate.get("source_bank_ref") or "").strip()
    initiative_ref = str(candidate.get("initiative_ref") or "").strip()
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    if source_bank_ref:
        initiative_path = root / source_bank_ref
    elif initiative_ref:
        initiative_path = root / ".azoth" / "initiative-banks" / f"{initiative_ref}.yaml"
    elif candidate_id:
        initiative_path = root / ".azoth" / "initiative-banks" / f"{candidate_id}.yaml"
    else:
        return None
    if not initiative_path.exists():
        return None
    route_label = initiative_ref or candidate_id or initiative_path.stem
    try:
        route_candidate_id = str(candidate.get("route_candidate_id") or "").strip() or None
        return build_initiative_route_decision_capsule(
            root,
            initiative_path,
            state_path=state_path,
            candidate_id=route_candidate_id,
        )
    except Exception as exc:
        return _stop_decision(
            state,
            "lifecycle_route_unreadable",
            detail=f"Lifecycle route for {route_label} could not be read: {exc}",
            candidate=candidate,
        )


def _implicit_initiative_route_stop_decision(
    root: Path, state_path: Path, state: dict[str, Any]
) -> dict[str, Any] | None:
    if _first_ready_initiative_candidate(root):
        return None
    candidate = _first_research_initiative_candidate(root)
    if not candidate:
        return None
    route_stop = _initiative_route_stop_decision(root, state_path, state, candidate)
    if route_stop:
        return route_stop
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
        status = loop_status(root, state_path)
        return _stop_decision(
            state,
            completion_reason,
            detail="Autonomous-auto campaign has reached its completion condition.",
            root=root,
            status=status,
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
        if action == "hydrate_task":
            proposal_decision = _queued_proposal_hydration_decision(root, state, queued, allowed)
            if proposal_decision:
                return proposal_decision
        return _action_decision(
            state,
            action=action,
            candidate=queued,
            source=str(queued.get("source") or "queue"),
            reason="Selected first queued autonomous-auto candidate inside the autonomy budget.",
            root=root,
        )

    declared_proposal = _declared_proposal_candidate(root, state)
    if declared_proposal:
        stale_route_stop = _implicit_initiative_route_stop_decision(root, state_path, state)
        if stale_route_stop:
            declared_proposal = {
                **declared_proposal,
                "stale_initiative_route_decision": stale_route_stop,
            }
        proposal_decision = _proposal_discovery_decision(root, state, declared_proposal, allowed)
        if proposal_decision:
            return proposal_decision
        if "refine_proposal" in allowed:
            return _action_decision(
                state,
                action="refine_proposal",
                candidate=declared_proposal,
                source="proposal",
                reason=(
                    "Selected the campaign-declared proposal before stale initiative "
                    "readiness fallback."
                ),
                root=root,
            )

    route_stop = _implicit_initiative_route_stop_decision(root, state_path, state)
    if route_stop:
        return route_stop

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
        route_capsule = _initiative_route_capsule(root, state_path, state, research_candidate)
        if isinstance(route_capsule, dict) and route_capsule.get("action") == "stop":
            return route_capsule
        if isinstance(route_capsule, dict):
            selected_route = str(route_capsule.get("selected_route") or "")
            route_state = str(route_capsule.get("route_state") or "")
            if selected_route == "stop":
                return _initiative_route_stop_decision(root, state_path, state, research_candidate)
            if selected_route not in {"research_initiative", "refine_proposal"}:
                return _stop_decision(
                    state,
                    f"lifecycle_route_conflict_{route_state or selected_route or 'unknown'}",
                    detail=(
                        "Lifecycle route did not agree with the discovered research "
                        f"candidate: {selected_route or 'unknown'} ({route_state or 'unknown'})."
                    ),
                    candidate={**research_candidate, "route_decision": route_capsule},
                )
            if selected_route == "research_initiative":
                research_candidate = {**research_candidate, "route_decision": route_capsule}
        return _action_decision(
            state,
            action="research_initiative",
            candidate=research_candidate,
            source="initiative-bank",
            reason="Selected an initiative bank that still needs research or refinement.",
            root=root,
        )

    proposal_candidate = _first_proposal_candidate(root)
    if proposal_candidate:
        proposal_decision = _proposal_discovery_decision(
            root, state, proposal_candidate, allowed
        )
        if proposal_decision:
            return proposal_decision
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
    _reject_advisory_decision_payload(decision)
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
    _validate_lifecycle_route_evidence(decision, expected)
    _validate_strategy_preflight_evidence(decision, expected)


def _route_signature(route: dict[str, Any]) -> tuple[str, str, str, str, str]:
    readiness = (
        route.get("readiness_evidence") if isinstance(route.get("readiness_evidence"), dict) else {}
    )
    return (
        str(route.get("selected_route") or ""),
        str(route.get("route_state") or ""),
        str(route.get("approval_needed") or ""),
        str(readiness.get("candidate_id") or ""),
        str(readiness.get("candidate_task_ref") or ""),
    )


def _validate_lifecycle_route_evidence(
    decision: dict[str, Any], expected: dict[str, Any]
) -> None:
    if str(expected.get("source") or "") != "initiative-bank":
        return
    expected_route = (
        expected.get("route_decision")
        if isinstance(expected.get("route_decision"), dict)
        else {}
    )
    if not expected_route:
        return
    actual_route = (
        decision.get("route_decision")
        if isinstance(decision.get("route_decision"), dict)
        else {}
    )
    if not actual_route:
        raise SystemExit(
            "refusing to open initiative decision with missing lifecycle-route evidence"
        )
    if _route_signature(actual_route) != _route_signature(expected_route):
        raise SystemExit(
            "refusing to open initiative decision with lifecycle-route conflict"
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
        "session_id": str(item.get("session_id") or decision.get("loop_id") or ""),
        "loop_id": str(item.get("loop_id") or decision.get("loop_id") or ""),
        "learning_state": str(item.get("learning_state") or "captured"),
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
        path for path in handoffs_dir.glob("*autonomous-auto*handoff*.md") if path.is_file()
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


def _current_loop_report(
    root: Path, state_path: Path, *, include_next_campaign_recommendation: bool = True
) -> dict[str, Any]:
    if not state_path.exists():
        return {
            "state_path": str(state_path),
            "status": "missing_state",
            "observable": False,
            "failure_reason": "missing_loop_state",
            "completion_reason": "",
            "operator_read": {},
            "next_campaign_recommendation": {},
        }
    try:
        report = loop_status(root, state_path)
        report["operator_read"] = {
            "title": "Autonomous-auto operator read",
            "objective": str(report.get("loop_id") or "autonomous-auto loop"),
            "loop_state": str(report.get("status") or "missing_state"),
            "iteration": report.get("iteration"),
            "max_iterations": report.get("max_iterations"),
            "remaining_iterations": report.get("remaining_iterations"),
            "can_continue": report.get("can_continue"),
            "next_likely_move": "not-evaluated",
            "route_authority": "not-evaluated",
            "stop_reason": report.get("stop_reason"),
            "completion_reason": report.get("completion_reason"),
        }
        state = _load_yaml_mapping(state_path)
        report["next_campaign_recommendation"] = (
            _next_campaign_recommendation_report_packet(root, state, report)
            if include_next_campaign_recommendation
            else {}
        )
    except Exception as exc:
        return {
            "state_path": str(state_path),
            "status": "malformed_state",
            "observable": False,
            "failure_reason": f"malformed_loop_state: {exc}",
            "completion_reason": "",
            "operator_read": {},
            "next_campaign_recommendation": {},
        }
    report["observable"] = True
    report.setdefault("failure_reason", "")
    return report


def campaign_report(
    root: Path,
    state_path: Path,
    handoff_path: Path | None = None,
    include_next_campaign_recommendation: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    state_path = Path(state_path)
    current_loop = _current_loop_report(
        root,
        state_path,
        include_next_campaign_recommendation=include_next_campaign_recommendation,
    )

    resolved_handoff = (
        Path(handoff_path) if handoff_path is not None else _latest_autonomous_handoff(root)
    )
    if resolved_handoff is not None and not resolved_handoff.is_absolute():
        resolved_handoff = root / resolved_handoff
    handoff_campaign = _parse_handoff_campaign(resolved_handoff)
    state_snapshot, state_error = _safe_state_snapshot(state_path)
    learning_harvester: dict[str, Any] = {}
    loop_id = str(state_snapshot.get("loop_id") or "")
    if loop_id and not state_error:
        try:
            learning_harvester = build_campaign_audit(
                root,
                loop_id,
                state_path=state_path,
                ledger_path=root / ".azoth/run-ledger.local.yaml",
                episodes_path=root / ".azoth/memory/episodes.jsonl",
                inbox_dir=root / INBOX_DIR_REL,
            ).get("learning_harvester", {})
        except Exception as exc:
            learning_harvester = {
                "selected_learning_route": "unknown",
                "rejected_alternatives": [],
                "route_counts": {},
                "error": str(exc),
            }
    completion_reason = str(handoff_campaign.get("completion_reason") or "")
    fail_closed = not current_loop.get("observable") or not handoff_campaign.get("observable")
    vision_realized = completion_reason == "vision_realized"
    observed_old_campaign = bool(handoff_campaign.get("observable"))
    ambiguous_observation = observed_old_campaign and not completion_reason
    return {
        "report_schema_version": 1,
        "current_loop": current_loop,
        "handoff_campaign": handoff_campaign,
        "learning_harvester": learning_harvester,
        "next_campaign_recommendation": current_loop.get("next_campaign_recommendation", {}),
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


def _safe_state_snapshot(state_path: Path) -> tuple[dict[str, Any], str]:
    if not state_path.exists():
        return {}, "missing_loop_state"
    try:
        data = safe_load_yaml_path(state_path)
    except Exception:
        return {}, "malformed_loop_state"
    if not isinstance(data, dict):
        return {}, "malformed_loop_state"
    return data, ""


def _safe_loop_status(root: Path, state_path: Path) -> tuple[dict[str, Any], str]:
    try:
        return loop_status(root, state_path), ""
    except Exception:
        return {
            "state_path": str(state_path),
            "status": "malformed_state",
            "raw_status": "malformed_state",
            "loop_id": "",
            "iteration": 0,
            "max_iterations": 0,
            "remaining_iterations": 0,
            "active_scope_id": "",
            "active_session_id": "",
            "active_session_conflict": False,
            "can_continue": False,
            "stop_reason": "malformed_loop_state",
            "completion_reason": "",
            "alignment": _alignment_summary({}),
            "vision": _vision_state({}),
            "write_claim": _write_claim_status(root),
            "next_candidate": None,
        }, "malformed_loop_state"


def _safe_operator_read(root: Path, state_path: Path) -> dict[str, Any]:
    try:
        return operator_read(root, state_path)
    except Exception:
        return {
            "title": "Autonomous-auto operator read",
            "objective": "autonomous-auto loop",
            "loop_state": "malformed_state",
            "iteration": 0,
            "max_iterations": 0,
            "remaining_iterations": 0,
            "can_continue": False,
            "next_likely_move": "blocked: malformed_loop_state",
            "route_authority": "not-evaluated",
            "approval_basis": "",
            "pending_alignment_packets": 0,
            "latest_alignment_packet": "",
            "vision_band": "unevaluated",
            "vision_target": DEFAULT_VISION_TARGET_BAND,
            "vision_realized": False,
            "write_claim": "unknown",
            "continuation_required": False,
            "continuation_reason": "blocked:malformed_loop_state",
            "stop_reason": "malformed_loop_state",
            "completion_reason": "",
            "stop_conditions": DEFAULT_STOP_CONDITIONS,
            "residual_risk": "Loop state is malformed; wakeup must fail closed.",
            "next_campaign_recommendation": {},
        }


def _safe_campaign_report(
    root: Path,
    state_path: Path,
    handoff_path: Path | None,
) -> dict[str, Any]:
    try:
        return campaign_report(root, state_path, handoff_path=handoff_path)
    except Exception as exc:
        return {
            "report_schema_version": 1,
            "current_loop": {
                "state_path": str(state_path),
                "status": "malformed_state",
                "observable": False,
                "failure_reason": f"malformed_loop_state: {exc}",
                "completion_reason": "",
                "operator_read": {},
            },
            "handoff_campaign": {
                "observable": False,
                "path": str(handoff_path or ""),
                "failure_reason": "campaign_report_failed",
                "current_truth": {},
                "completion_reason": "",
                "vision_band": "",
                "known_residuals": [],
                "safe_continuation_commands": [],
                "recommended_options": [],
            },
            "observation": {
                "fresh_budget_required": True,
                "safe_to_continue_old_campaign": False,
                "reason": "fail_closed",
            },
            "next_campaign_recommendation": {},
        }


def _wakeup_fresh_budget_required(
    status: dict[str, Any],
    report: dict[str, Any],
    handoff_path: Path | None,
) -> bool:
    observation = report.get("observation") if isinstance(report.get("observation"), dict) else {}
    if not observation.get("fresh_budget_required"):
        return False
    handoff = (
        report.get("handoff_campaign") if isinstance(report.get("handoff_campaign"), dict) else {}
    )
    if status.get("completion_reason"):
        return True
    if str(status.get("status") or "") not in {"active"}:
        return True
    if handoff.get("observable") and handoff_path is not None:
        return True
    if handoff_path is not None and not handoff.get("observable"):
        return True
    return False


def _wakeup_gate_status(status: dict[str, Any]) -> dict[str, Any]:
    active_scope_id = str(status.get("active_scope_id") or "")
    active_session_id = str(status.get("active_session_id") or "")
    return {
        "active_scope": bool(active_scope_id),
        "active_scope_id": active_scope_id,
        "active_session_conflict": bool(status.get("active_session_conflict")),
        "active_session_id": active_session_id,
        "blocked": bool(active_scope_id or status.get("active_session_conflict")),
    }


def _wakeup_stop_reason(
    *,
    state_failure: str,
    status: dict[str, Any],
    decision: dict[str, Any],
    fresh_budget_required: bool,
) -> str | None:
    if state_failure:
        return state_failure
    if fresh_budget_required:
        if status.get("completion_reason"):
            return str(status.get("completion_reason") or "completed_or_stale_campaign")
        return "completed_or_stale_campaign"
    if status.get("completion_reason"):
        return str(status.get("completion_reason"))
    if status.get("stop_reason"):
        return str(status.get("stop_reason"))
    if decision.get("action") == "stop":
        return str(decision.get("stop_reason") or "stop_decision")
    return None


def _wakeup_residual_risk(
    stop_reason: str | None,
    operator: dict[str, Any],
    fresh_budget_required: bool,
) -> str:
    if not stop_reason:
        return "Report-only unless --open is provided; one safe scope may be opened."
    if fresh_budget_required:
        return "Completed or stale campaign evidence requires a fresh budget before wakeup opens scope."
    if stop_reason in {"missing_loop_state", "malformed_loop_state", "invalid_loop_state"}:
        return "Loop state is missing or malformed; wakeup must fail closed."
    return str(
        operator.get("residual_risk")
        or "Continuation is blocked until the stop reason is resolved."
    )


def _default_wakeup_decision_path(root: Path) -> Path:
    return root / ".azoth" / "autonomous-wakeup-decision.json"


def wakeup(
    root: Path,
    state_path: Path,
    *,
    open_scope: bool = False,
    decision_out: Path | None = None,
    report_out: Path | None = None,
    expires_at: str | None = None,
    handoff_path: Path | None = None,
) -> dict[str, Any]:
    root = Path(root)
    state_path = Path(state_path)
    if handoff_path is not None and not handoff_path.is_absolute():
        handoff_path = root / handoff_path
    state, state_failure = _safe_state_snapshot(state_path)
    status, status_failure = _safe_loop_status(root, state_path)
    if status_failure and not state_failure:
        state_failure = status_failure
    campaign = _safe_campaign_report(root, state_path, handoff_path)
    operator = _safe_operator_read(root, state_path)
    try:
        decision = decide_next(root, state_path)
    except Exception as exc:
        decision = _stop_decision(
            state,
            "malformed_loop_state",
            detail=f"Could not decide next wakeup action: {exc}",
        )
        state_failure = state_failure or "malformed_loop_state"

    fresh_budget_required = _wakeup_fresh_budget_required(status, campaign, handoff_path)
    stop_reason = _wakeup_stop_reason(
        state_failure=state_failure,
        status=status,
        decision=decision,
        fresh_budget_required=fresh_budget_required,
    )
    residual_risk = _wakeup_residual_risk(stop_reason, operator, fresh_budget_required)
    report = {
        "report_schema_version": 1,
        "loop_status": status,
        "campaign_report": campaign,
        "operator_read": operator,
        "next_campaign_recommendation": campaign.get("next_campaign_recommendation")
        or operator.get("next_campaign_recommendation")
        or decision.get("next_campaign_recommendation")
        or {},
        "gate_status": _wakeup_gate_status(status),
        "write_claim": status.get("write_claim") or _write_claim_status(root),
        "autonomy_budget": state.get("autonomy_budget", {}) if state else {},
        "alignment": status.get("alignment", _alignment_summary(state)),
        "decision": decision,
        "opened": False,
        "session_id": "",
        "stop_reason": stop_reason,
        "fresh_budget_required": fresh_budget_required,
        "residual_risk": residual_risk,
    }

    if open_scope and stop_reason is None:
        out_path = decision_out or _default_wakeup_decision_path(root)
        _write_json_mapping(out_path, decision)
        try:
            opened = open_next(root, state_path, out_path, expires_at)
        except SystemExit as exc:
            report["stop_reason"] = "open_next_failed"
            report["residual_risk"] = str(exc)
        else:
            report["opened"] = bool(opened.get("opened"))
            report["session_id"] = str(opened.get("session_id") or "")
    elif decision_out is not None:
        _write_json_mapping(decision_out, decision)

    if report_out is not None:
        _write_json_mapping(report_out, report)
    return report


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
    candidates = (
        doc.get("candidate_slices") if isinstance(doc.get("candidate_slices"), list) else []
    )
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
    hydration_plan = candidate.get("hydration_plan")
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
        "hydration_plan": hydration_plan if isinstance(hydration_plan, dict) else {},
    }


def _candidate_hydrated_task_ref(candidate: dict[str, Any]) -> str:
    hydration_plan = (
        candidate.get("hydration_plan") if isinstance(candidate.get("hydration_plan"), dict) else {}
    )
    return str(hydration_plan.get("hydrated_task_ref") or candidate.get("proposed_task_id") or "")


def _candidate_hydrated_spec_ref(candidate: dict[str, Any], task_ref: str) -> str:
    hydration_plan = (
        candidate.get("hydration_plan") if isinstance(candidate.get("hydration_plan"), dict) else {}
    )
    if hydration_plan.get("hydrated_spec_ref"):
        return str(hydration_plan.get("hydrated_spec_ref"))
    if task_ref:
        return f".azoth/roadmap-specs/v0.2.0/{task_ref}.yaml"
    return ""


def _candidate_planning_vs_executable_status(
    root: Path,
    candidate: dict[str, Any],
    task_ref: str,
) -> str:
    status = str(candidate.get("status") or "").strip().lower()
    task_complete = _hydrated_task_is_complete(root, task_ref)
    artifacts_exist = _hydrated_task_artifacts_exist(root, task_ref)
    if task_complete or status == "complete":
        return "completed_hydrated_task"
    if status == "hydrated" and artifacts_exist:
        return "executable_hydrated_task"
    if status == "hydrated":
        return "hydrated_missing_executable_artifacts"
    if artifacts_exist:
        return "executable_artifacts_present"
    if status == "candidate":
        return "planning_candidate"
    if status in {"parked", "rejected"}:
        return f"planning_{status}"
    return "planning_status_unknown"


def _candidate_slice_rows(root: Path, doc: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = (
        doc.get("candidate_slices") if isinstance(doc.get("candidate_slices"), list) else []
    )
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        task_ref = _candidate_hydrated_task_ref(candidate)
        artifacts_exist = _hydrated_task_artifacts_exist(root, task_ref)
        task_complete = _hydrated_task_is_complete(root, task_ref)
        status = str(candidate.get("status") or "").strip().lower()
        rows.append(
            {
                "candidate_id": str(candidate.get("candidate_id") or ""),
                "title": str(candidate.get("title") or ""),
                "initiative_ref": str(candidate.get("initiative_ref") or ""),
                "status": status or "missing",
                "hydrated_task_ref": task_ref,
                "hydrated_spec_ref": _candidate_hydrated_spec_ref(candidate, task_ref),
                "target_layer": str(candidate.get("target_layer") or ""),
                "delivery_pipeline": str(candidate.get("delivery_pipeline") or ""),
                "planning_vs_executable_status": _candidate_planning_vs_executable_status(
                    root, candidate, task_ref
                ),
                "task_artifacts_exist": artifacts_exist,
                "task_complete": task_complete,
                "repeat_hydration_blocked": bool(
                    status in {"hydrated", "complete"} or artifacts_exist or task_complete
                ),
                "ship_blocked": bool(
                    task_complete or (status == "hydrated" and not artifacts_exist)
                ),
            }
        )
    return rows


def _hydration_history_rows(root: Path, doc: dict[str, Any]) -> list[dict[str, Any]]:
    history = doc.get("hydration_history") if isinstance(doc.get("hydration_history"), list) else []
    rows: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        task_ref = str(item.get("task_ref") or item.get("hydrated_task_ref") or "")
        row = dict(item)
        row["task_ref"] = task_ref
        row["task_artifacts_exist"] = _hydrated_task_artifacts_exist(root, task_ref)
        row["task_complete"] = _hydrated_task_is_complete(root, task_ref)
        rows.append(row)
    return rows


def _initiative_bank_rows(root: Path) -> list[dict[str, Any]]:
    bank_dir = root / ".azoth/initiative-banks"
    if not bank_dir.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(bank_dir.glob("*.yaml")):
        doc = _load_yaml_mapping(path)
        if doc.get("bank_type") != "initiative":
            continue
        readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
        candidates = (
            doc.get("candidate_slices") if isinstance(doc.get("candidate_slices"), list) else []
        )
        rows.append(
            {
                "initiative_id": str(doc.get("initiative_id") or path.stem),
                "title": str(doc.get("title") or ""),
                "status": str(doc.get("status") or ""),
                "path": _repo_artifact_ref(root, path),
                "proposal_refs": doc.get("source_proposal_refs")
                if isinstance(doc.get("source_proposal_refs"), list)
                else [],
                "readiness_status": str(readiness.get("readiness_status") or ""),
                "candidate_first_slice": str(readiness.get("candidate_first_slice") or ""),
                "candidate_count": len([item for item in candidates if isinstance(item, dict)]),
                "hydration_history_count": len(doc.get("hydration_history") or [])
                if isinstance(doc.get("hydration_history"), list)
                else 0,
            }
        )
    return rows


def _active_run_status(root: Path) -> dict[str, Any]:
    ledger = _load_yaml_mapping(root / ".azoth/run-ledger.local.yaml")
    runs = ledger.get("runs") if isinstance(ledger.get("runs"), list) else []
    for run in runs:
        if isinstance(run, dict) and str(run.get("status") or "") == "active":
            return {
                "present": True,
                "run_id": str(run.get("run_id") or ""),
                "mode": str(run.get("mode") or ""),
                "goal": str(run.get("goal") or ""),
                "active_stage_id": str(run.get("active_stage_id") or ""),
                "pending_stage_ids": run.get("pending_stage_ids")
                if isinstance(run.get("pending_stage_ids"), list)
                else [],
            }
    return {"present": False}


def _pipeline_gate_status(root: Path, active_scope: dict[str, Any]) -> dict[str, Any]:
    path = root / PIPELINE_GATE_REL
    if not path.exists():
        return {"present": False, "active": False, "path": PIPELINE_GATE_REL}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "present": True,
            "active": False,
            "path": PIPELINE_GATE_REL,
            "malformed": True,
            "failure_reason": f"invalid_json: {exc.msg}",
        }
    if not isinstance(data, dict):
        return {
            "present": True,
            "active": False,
            "path": PIPELINE_GATE_REL,
            "malformed": True,
            "failure_reason": "pipeline_gate_must_be_object",
        }
    expires_at = str(data.get("expires_at") or "")
    expiry = _parse_iso(expires_at)
    expired = bool(expiry and expiry <= _utc_now())
    session_id = str(data.get("session_id") or "")
    active_scope_session = str(active_scope.get("session_id") or "")
    session_matches_scope = bool(
        session_id and active_scope_session and session_id == active_scope_session
    )
    approved = data.get("approved") is True
    return {
        "present": True,
        "active": bool(approved and not expired),
        "path": PIPELINE_GATE_REL,
        "approved": approved,
        "expired": expired,
        "session_id": session_id,
        "expires_at": expires_at,
        "pipeline_command": str(data.get("pipeline_command") or data.get("pipeline") or ""),
        "session_matches_active_scope": session_matches_scope,
    }


def _lifecycle_gate_status(root: Path) -> dict[str, Any]:
    active_scope = _active_scope(root)
    return {
        "active_scope": active_scope,
        "active_session_conflict": _active_session_conflict(root, active_scope),
        "pipeline_gate": _pipeline_gate_status(root, active_scope),
        "active_run": _active_run_status(root),
    }


def _protected_gate_status(readiness_report: dict[str, Any]) -> dict[str, Any]:
    target_layer = str(readiness_report.get("target_layer") or "").lower()
    delivery_pipeline = str(readiness_report.get("delivery_pipeline") or "").lower()
    reasons: list[str] = []
    if target_layer in PROTECTED_TARGET_LAYERS:
        reasons.append(f"target_layer {target_layer} requires protected gate")
    if delivery_pipeline in PROTECTED_PIPELINES:
        reasons.append(f"delivery_pipeline {delivery_pipeline} requires protected gate")
    return {"required": bool(reasons), "reasons": reasons}


def _evaluator_evidence_status(
    reflections: list[dict[str, Any]],
    reflection_errors: list[str],
) -> dict[str, Any]:
    evidence_entries: list[dict[str, str]] = []
    for entry in reflections:
        tags = entry.get("tags") if isinstance(entry.get("tags"), list) else []
        tag_text = " ".join(str(tag).lower() for tag in tags)
        if (
            "eval" in tag_text
            or "evaluator" in str(entry.get("source") or "").lower()
            or entry.get("score") is not None
        ):
            evidence_entries.append(
                {
                    "id": str(entry.get("id") or ""),
                    "summary": str(entry.get("summary") or ""),
                    "score": str(entry.get("score") or ""),
                }
            )
    status = "recorded" if evidence_entries else "not_recorded"
    return {
        "status": status,
        "evidence_count": len(evidence_entries),
        "entries": evidence_entries,
        "reflection_failure_reasons": reflection_errors,
    }


def _lifecycle_residual_risks(
    *,
    candidate_rows: list[dict[str, Any]],
    route_decision: dict[str, Any],
    gate_status: dict[str, Any],
    write_claim: dict[str, Any],
    evaluator_evidence: dict[str, Any],
    campaign: dict[str, Any],
) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_risk(risk: str, basis: str, mitigation: str) -> None:
        key = (risk, mitigation)
        if key in seen:
            return
        seen.add(key)
        risks.append({"risk": risk, "basis": basis, "mitigation": mitigation})

    for row in candidate_rows:
        if row.get("task_complete"):
            task_ref = str(row.get("hydrated_task_ref") or "hydrated task")
            add_risk(
                f"Completed hydrated task {task_ref} blocks hidden continuation "
                "and repeat hydration.",
                "candidate task is terminal in roadmap/backlog truth",
                "Select a fresh candidate or refresh initiative readiness.",
            )
    if gate_status.get("active_scope"):
        add_risk(
            "Active scope gate is present.",
            "scope-gate reports a live session",
            "Close or reconcile the active scope before opening another child.",
        )
    if gate_status.get("active_session_conflict"):
        add_risk(
            "Active session gate conflicts with the lifecycle report context.",
            "session-gate session does not match the active scope",
            "Resolve session-gate state before continuing.",
        )
    if write_claim.get("held") and not write_claim.get("stale"):
        add_risk(
            "Active write claim is held.",
            "run-ledger write claim is not stale",
            "Do not open write work until the claim is released or expires.",
        )
    if evaluator_evidence.get("status") != "recorded":
        add_risk(
            "Evaluator evidence is not recorded in the lifecycle inputs.",
            "reflection/evaluator evidence was absent or unscored",
            "Treat route quality as unscored until evaluator evidence is attached.",
        )
    observation = (
        campaign.get("observation") if isinstance(campaign.get("observation"), dict) else {}
    )
    if observation.get("fresh_budget_required"):
        add_risk(
            "Campaign report requires a fresh budget or explicit continuation authority.",
            str(observation.get("reason") or "campaign observation is stale or incomplete"),
            "Do not infer authority from stale handoff or completed campaign evidence.",
        )
    if route_decision.get("selected_route") == "stop":
        add_risk(
            "Selected route is stop.",
            str(route_decision.get("route_state") or "route decision stopped"),
            str(route_decision.get("approval_needed") or "Resolve blockers first."),
        )
    return risks


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
                    "approval_scope planning_seed_only_no_hydration permits discovery/planning only"
                ),
                "approval_needed": "new hydration or delivery approval_basis required before writes",
            }
        ]
    elif bool(readiness_report.get("candidate_task_complete")):
        task_ref = str(readiness_report.get("candidate_task_ref") or "").strip()
        actions = [
            {
                "action": "research_initiative",
                "basis": f"hydrated task {task_ref or 'candidate task'} is already complete",
                "approval_needed": "select a fresh candidate or refresh initiative readiness",
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
    if bool(readiness_report.get("candidate_task_complete")):
        task_ref = str(readiness_report.get("candidate_task_ref") or "").strip()
        blocked.append(
            {
                "action": "ship_task",
                "reason": f"hydrated task {task_ref or 'candidate task'} is already complete",
            }
        )
        return _dedupe_action_reasons(blocked)
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


def _hydration_scope_for_candidate(candidate_id: str) -> str:
    return f"hydration_specific_{_markdown_key(candidate_id)}"


def _scaffold_command_names_candidate(readiness: dict[str, Any]) -> bool:
    candidate_id = str(readiness.get("candidate_id") or "").strip()
    command = str(readiness.get("scaffold_command") or "").strip()
    return bool(candidate_id and command and candidate_id in command)


def _candidate_scaffold_command(candidate: dict[str, Any]) -> str:
    hydration_plan = candidate.get("hydration_plan")
    if not isinstance(hydration_plan, dict):
        return ""
    return str(hydration_plan.get("scaffold_command") or "").strip()


def _awaiting_hydration_approval(
    readiness: dict[str, Any],
    candidate: dict[str, Any],
    *,
    expected_scope: str,
) -> bool:
    if str(readiness.get("readiness_status") or "").strip() != "continue_research":
        return False
    if str(readiness.get("approval_scope") or "").strip().startswith("hydration_specific_"):
        return False
    if not expected_scope:
        return False
    next_gate = str(readiness.get("next_readiness_gate") or "").strip()
    if expected_scope not in next_gate:
        return False
    blockers = readiness.get("blocking_reasons")
    if blockers != ["readiness.readiness_status must be ready_to_hydrate"]:
        return False
    command = _candidate_scaffold_command(candidate)
    candidate_id = str(readiness.get("candidate_id") or "").strip()
    return bool(command and candidate_id and candidate_id in command)


def _yaml_tree_contains_task_ref(data: Any, task_ref: str) -> bool:
    if isinstance(data, dict):
        if str(data.get("id") or "") == task_ref or str(data.get("task_ref") or "") == task_ref:
            return True
        return any(_yaml_tree_contains_task_ref(value, task_ref) for value in data.values())
    if isinstance(data, list):
        return any(_yaml_tree_contains_task_ref(item, task_ref) for item in data)
    return False


TERMINAL_TASK_STATUSES = {"complete", "completed", "closed", "shipped"}


def _yaml_tree_matching_task_nodes(data: Any, task_ref: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    if isinstance(data, dict):
        identifiers = {
            str(data.get("id") or ""),
            str(data.get("task_ref") or ""),
            str(data.get("roadmap_ref") or ""),
        }
        if task_ref in identifiers:
            matches.append(data)
        for value in data.values():
            matches.extend(_yaml_tree_matching_task_nodes(value, task_ref))
    elif isinstance(data, list):
        for item in data:
            matches.extend(_yaml_tree_matching_task_nodes(item, task_ref))
    return matches


def _hydrated_task_is_complete(root: Path, task_ref: str) -> bool:
    task_id = str(task_ref or "").strip()
    if not task_id:
        return False
    for rel_path in (".azoth/backlog.yaml", ".azoth/roadmap.yaml"):
        path = root / rel_path
        if not path.exists():
            continue
        data = safe_load_yaml_path(path)
        for node in _yaml_tree_matching_task_nodes(data, task_id):
            status = str(node.get("status") or "").strip().lower()
            if status in TERMINAL_TASK_STATUSES or node.get("completed_date"):
                return True
    return False


def _hydrated_task_artifacts_exist(root: Path, task_ref: str) -> bool:
    task_id = str(task_ref or "").strip()
    if not task_id:
        return False
    spec_path = root / ".azoth" / "roadmap-specs" / "v0.2.0" / f"{task_id}.yaml"
    if not spec_path.exists():
        return False
    for rel_path in (".azoth/roadmap.yaml", ".azoth/backlog.yaml"):
        path = root / rel_path
        if not path.exists():
            return False
        data = safe_load_yaml_path(path)
        if not _yaml_tree_contains_task_ref(data, task_id):
            return False
    return True


def _high_severity_quality_signal(report: dict[str, Any]) -> dict[str, str] | None:
    quality = report.get("quality") if isinstance(report.get("quality"), dict) else {}
    consumed_ids = set()
    raw_consumed = quality.get("consumed_signal_ids")
    if isinstance(raw_consumed, list):
        consumed_ids = {str(item) for item in raw_consumed if str(item)}
    signals = quality.get("quality_signals")
    if not isinstance(signals, list):
        return None
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        if str(signal.get("id") or "") in consumed_ids:
            continue
        if str(signal.get("severity") or "").lower() in {"high", "critical"}:
            return {str(key): str(value) for key, value in signal.items()}
    return None


def _consumed_self_capture_ids(state: dict[str, Any]) -> list[str]:
    consumed: list[str] = []
    history = state.get("history")
    if not isinstance(history, list):
        return consumed
    for item in history:
        if not isinstance(item, dict):
            continue
        materialization = item.get("self_capture_materialization")
        if not isinstance(materialization, dict):
            continue
        entry_id = str(materialization.get("entry_id") or "")
        if entry_id and entry_id not in consumed:
            consumed.append(entry_id)
    return consumed


def _campaign_requires_fresh_budget(report: dict[str, Any]) -> bool:
    campaign = (
        report.get("campaign_context") if isinstance(report.get("campaign_context"), dict) else {}
    )
    current_status = str(campaign.get("current_loop_status") or "").strip()
    return bool(campaign.get("fresh_budget_required")) and current_status not in {"active"}


def _research_to_readiness_refresh_target(readiness: dict[str, Any]) -> str:
    approval_scope = str(readiness.get("approval_scope") or "").strip()
    prefix = "research_to_readiness_"
    if not approval_scope.startswith(prefix):
        return ""
    target_key = approval_scope.removeprefix(prefix)
    for field in ("candidate_first_slice", "next_candidate_ref", "candidate_id"):
        value = str(readiness.get(field) or "").strip()
        if value and _markdown_key(value) == target_key:
            return value
    return target_key.replace("_", "-")


def _fresh_research_to_readiness_approval(readiness: dict[str, Any]) -> bool:
    return bool(
        _research_to_readiness_refresh_target(readiness)
        and str(readiness.get("approval_basis") or "").strip()
        and str(readiness.get("human_decision") or "").strip() == "approved"
    )


def _strategy_preflight_required(readiness: dict[str, Any], candidate_id: str) -> bool:
    refresh_target = _research_to_readiness_refresh_target(readiness)
    if not refresh_target or _markdown_key(refresh_target) != _markdown_key(candidate_id):
        return False
    fields = (
        readiness.get("next_readiness_gate"),
        readiness.get("hydration_recommendation"),
        readiness.get("goal_clarity"),
        readiness.get("freshness_status"),
    )
    text = " ".join(str(value or "").lower() for value in fields)
    return "strategy" in text or "preflight" in text or "open_next" in text


def _action_from_report_actions(report: dict[str, Any], action: str) -> dict[str, str] | None:
    actions = report.get("next_safe_actions")
    if not isinstance(actions, list):
        return None
    for item in actions:
        if isinstance(item, dict) and str(item.get("action") or "") == action:
            return {str(key): str(value) for key, value in item.items()}
    return None


def _dedupe_action_reasons(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for item in items:
        action = str(item.get("action") or "").strip()
        reason = str(item.get("reason") or item.get("basis") or "").strip()
        key = (action, reason)
        if not action or key in seen:
            continue
        seen.add(key)
        result.append(dict(item))
    return result


def _route_rejected_alternatives(
    selected_route: str,
    report: dict[str, Any],
    blocked_actions: list[dict[str, str]],
) -> list[dict[str, str]]:
    alternatives: list[dict[str, str]] = []
    for item in report.get("next_safe_actions") or []:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "")
        if action and action != selected_route:
            alternatives.append(
                {
                    "route": action,
                    "reason": str(item.get("basis") or item.get("approval_needed") or ""),
                }
            )
    for item in blocked_actions:
        action = str(item.get("action") or "")
        if action and action != selected_route:
            alternatives.append(
                {
                    "route": action,
                    "reason": str(item.get("reason") or item.get("basis") or ""),
                }
            )
    return _dedupe_action_reasons(
        [{"action": item["route"], "reason": item["reason"]} for item in alternatives]
    )


def _route_decision_from_lifecycle_report(root: Path, report: dict[str, Any]) -> dict[str, Any]:
    readiness = report.get("readiness") if isinstance(report.get("readiness"), dict) else {}
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    candidate = report.get("candidate") if isinstance(report.get("candidate"), dict) else {}
    high_severity = _high_severity_quality_signal(report)
    protected_gate_required = bool(safety.get("protected_gate_required"))
    candidate_status = str(readiness.get("candidate_status") or "")
    readiness_status = str(readiness.get("readiness_status") or "")
    approval_scope = str(readiness.get("approval_scope") or "")
    candidate_id = str(readiness.get("candidate_id") or "")
    expected_scope = _hydration_scope_for_candidate(candidate_id)
    refresh_target = _research_to_readiness_refresh_target(readiness)
    fresh_research_to_readiness = _fresh_research_to_readiness_approval(readiness)
    strategy_preflight_required = _strategy_preflight_required(readiness, candidate_id)
    task_ref = str(readiness.get("candidate_task_ref") or candidate.get("proposed_task_id") or "")
    blocked_actions = [
        dict(item) for item in report.get("blocked_actions") or [] if isinstance(item, dict)
    ]
    protected_stops: list[str] = []
    selected_route = "stop"
    route_state = "raw_initiative"
    approval_needed = "discovery or proposal-refinement approval"
    ux_basis = "Autonomous-auto should expose why an initiative is or is not safe to continue."

    if protected_gate_required:
        selected_route = "stop"
        route_state = "raw_initiative"
        approval_needed = "protected human gate required"
        protected_stops.append("protected target layer or governed delivery pipeline")
        blocked_actions.extend(
            [
                {
                    "action": "hydrate_task",
                    "reason": "protected scope expansion requires a human gate",
                },
                {
                    "action": "ship_task",
                    "reason": "protected scope expansion requires a human gate",
                },
            ]
        )
        ux_basis = "Protected expansion stops before autonomous execution."
    elif high_severity:
        selected_route = "capture_self_improvement"
        route_state = "high_severity_self_capture"
        approval_needed = "inbox-first capture allowed unless protected boundary expands"
        ux_basis = "High-severity operator feedback is surfaced before more continuation."
    elif readiness_status == "complete":
        selected_route = "stop"
        route_state = "completed_or_stale_campaign"
        approval_needed = "fresh initiative, proposal, or improvement campaign"
        blocked_actions.extend(
            [
                {
                    "action": "hydrate_task",
                    "reason": "initiative readiness is complete; no hydration action remains",
                },
                {
                    "action": "ship_task",
                    "reason": "initiative readiness is complete; no delivery action remains",
                },
            ]
        )
        ux_basis = "Terminal initiative truth blocks stale autonomous delivery."
    elif _awaiting_hydration_approval(
        readiness,
        candidate,
        expected_scope=expected_scope,
    ):
        selected_route = "stop"
        route_state = "awaiting_hydration_approval"
        approval_needed = expected_scope
        blocked_actions.extend(
            [
                {
                    "action": "hydrate_task",
                    "reason": (
                        f"fresh {expected_scope} approval_basis must name the exact "
                        "scaffold command before roadmap/backlog/spec hydration"
                    ),
                },
                {
                    "action": "research_initiative",
                    "reason": (
                        "strategy-preflight research is complete; repeated research "
                        "will not resolve the missing hydration approval"
                    ),
                },
            ]
        )
        ux_basis = (
            "Strategy-preflight research is complete, so the autonomous loop stops with "
            "a precise hydration approval request instead of opening another research child."
        )
    elif (
        fresh_research_to_readiness
        and strategy_preflight_required
        and candidate_status not in {"hydrated", "complete", "completed", "closed", "shipped"}
        and readiness_status == "continue_research"
    ):
        selected_route = "research_initiative"
        route_state = "campaign_strategy_preflight"
        approval_needed = "covered by research-to-readiness scope only"
        blocked_actions.extend(
            [
                {
                    "action": "hydrate_task",
                    "reason": "strategy preflight is research-only until readiness is refreshed",
                },
                {
                    "action": "ship_task",
                    "reason": "strategy preflight is research-only and has no executable task",
                },
                {
                    "action": "open_next_without_strategy_preflight",
                    "reason": (
                        "recommendation, lifecycle-route, readiness, and approval scope must "
                        "be reconciled before opening delivery"
                    ),
                },
            ]
        )
        ux_basis = (
            "Old completed loop evidence cannot authorize continuation, but a fresh "
            "research-to-readiness approval can route this candidate into campaign strategy "
            "preflight before any init/open-next edge."
        )
    elif _campaign_requires_fresh_budget(report):
        selected_route = "stop"
        route_state = "completed_or_stale_campaign"
        approval_needed = "fresh or continuing autonomous-auto budget"
        blocked_actions.append(
            {
                "action": "open_next_without_budget",
                "reason": "completed or stale campaign requires a fresh budget",
            }
        )
        ux_basis = "Old campaign evidence cannot silently authorize continuation."
    elif approval_scope == "planning_seed_only_no_hydration":
        action = _action_from_report_actions(
            report, "refine_proposal"
        ) or _action_from_report_actions(report, "research_initiative")
        selected_route = str(action.get("action") if action else "research_initiative")
        route_state = (
            "candidate_ready_for_review"
            if selected_route == "refine_proposal"
            else "discovery_active"
        )
        approval_needed = str(
            (action or {}).get("approval_needed")
            or "new hydration or delivery approval_basis required before writes"
        )
        ux_basis = "Seed-only approval remains visible and blocks delivery writes."
    elif candidate_status == "hydrated":
        if bool(readiness.get("candidate_task_complete")):
            blocked_actions.append(
                {
                    "action": "ship_task",
                    "reason": f"hydrated task {task_ref or 'candidate task'} is already complete",
                }
            )
            blocked_actions.append(
                {
                    "action": "hydrate_task",
                    "reason": "repeat hydration is blocked for an already completed candidate",
                }
            )
            if refresh_target and readiness.get("approval_basis"):
                selected_route = "research_initiative"
                route_state = "refresh_initiative_candidate"
                approval_needed = "covered by research-to-readiness scope only"
                ux_basis = (
                    "Completed task truth blocks stale delivery, but fresh "
                    "research-to-readiness approval can refresh initiative candidate state."
                )
            else:
                selected_route = "stop"
                route_state = "completed_or_stale_campaign"
                approval_needed = "fresh initiative candidate or readiness refresh"
                ux_basis = "Completed task truth blocks stale autonomous delivery."
        elif _hydrated_task_artifacts_exist(root, task_ref):
            selected_route = "ship_task"
            route_state = "delivery_ready"
            approval_needed = "normal scoped delivery approval"
            blocked_actions.append(
                {
                    "action": "hydrate_task",
                    "reason": "repeat hydration is blocked for an already hydrated candidate",
                }
            )
            ux_basis = "Hydrated roadmap/backlog/spec truth can route to scoped delivery."
        else:
            selected_route = "stop"
            route_state = "completed_or_stale_campaign"
            approval_needed = "repair hydrated task artifact truth before delivery"
            blocked_actions.append(
                {
                    "action": "ship_task",
                    "reason": "hydrated candidate is missing roadmap/backlog/spec task artifacts",
                }
            )
            ux_basis = "Delivery is blocked until hydrated task artifacts are all present."
    elif (
        bool(readiness.get("ready_to_hydrate"))
        and approval_scope == expected_scope
        and bool(readiness.get("approval_basis"))
        and _scaffold_command_names_candidate(readiness)
    ):
        selected_route = "hydrate_task"
        route_state = "approved_for_hydration"
        approval_needed = expected_scope
        ux_basis = "Green readiness plus exact hydration approval can route to hydration only."
    elif readiness_status in {"missing", ""}:
        selected_route = "research_initiative"
        route_state = "raw_initiative"
        approval_needed = "discovery or proposal-refinement approval"
        blocked_actions.extend(
            [
                {
                    "action": "hydrate_task",
                    "reason": "missing readiness evidence blocks hydration",
                },
                {
                    "action": "ship_task",
                    "reason": "missing readiness evidence blocks delivery",
                },
            ]
        )
        ux_basis = "Raw or incomplete initiative evidence routes to discovery, not writes."
    elif readiness_status in {"continue_research", "ready_to_hydrate"}:
        selected_route = (
            "refine_proposal"
            if _action_from_report_actions(report, "refine_proposal")
            else "research_initiative"
        )
        route_state = (
            "candidate_ready_for_review"
            if selected_route == "refine_proposal"
            else "discovery_active"
        )
        action = _action_from_report_actions(report, selected_route) or {}
        approval_needed = str(
            action.get("approval_needed") or "covered by discovery/refinement scope only"
        )
        if readiness_status == "ready_to_hydrate":
            blocked_actions.append(
                {
                    "action": "hydrate_task",
                    "reason": (
                        "approved hydration requires human_decision approved, "
                        f"approval_scope {expected_scope}, approval_basis, and a "
                        "scaffold command naming the candidate"
                    ),
                }
            )
        ux_basis = "Unmet readiness evidence routes to research or proposal refinement."

    blocked_actions = _dedupe_action_reasons(blocked_actions)
    return {
        "capsule_schema_version": 1,
        "capsule_type": "autonomous_auto_initiative_route_decision",
        "selected_route": selected_route,
        "route_state": route_state,
        "rejected_alternatives": _route_rejected_alternatives(
            selected_route, report, blocked_actions
        ),
        "source_artifacts": report.get("source_artifacts") or {},
        "readiness_evidence": {
            "readiness_status": readiness.get("readiness_status"),
            "ready_to_hydrate": readiness.get("ready_to_hydrate"),
            "human_decision": readiness.get("human_decision"),
            "approval_scope": readiness.get("approval_scope"),
            "approval_basis_present": bool(readiness.get("approval_basis")),
            "candidate_id": readiness.get("candidate_id"),
            "candidate_status": readiness.get("candidate_status"),
            "candidate_task_ref": readiness.get("candidate_task_ref"),
            "candidate_task_complete": bool(readiness.get("candidate_task_complete")),
            "refresh_candidate_id": refresh_target,
            "fresh_research_to_readiness_approval": fresh_research_to_readiness,
            "strategy_preflight_required": strategy_preflight_required,
            "scaffold_command": readiness.get("scaffold_command"),
        },
        "ux_anchor_rationale": {
            "anchor": DEFAULT_VISION_ANCHOR,
            "route_basis": ux_basis,
        },
        "protected_stops": protected_stops,
        "blocked_actions": blocked_actions,
        "approval_needed": approval_needed,
        "evaluator_scores": (report.get("quality") or {}).get("evaluator_scores") or [],
        "route_table_coverage": ROUTE_TABLE_STATES,
        "lifecycle_report_type": report.get("report_type"),
    }


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
    task_ref = str(
        readiness_report.get("candidate_task_ref") or candidate.get("proposed_task_id") or ""
    )
    candidate_task_complete = _hydrated_task_is_complete(root, task_ref)
    loop_state = _load_yaml_mapping(state_path)
    consumed_signal_ids = _consumed_self_capture_ids(loop_state)
    lifecycle_readiness = {
        **readiness_report,
        "approval_basis": readiness.get("approval_basis") or "",
        "approval_scope": readiness.get("approval_scope") or "",
        "next_readiness_gate": readiness.get("next_readiness_gate") or "",
        "candidate_task_complete": candidate_task_complete,
    }
    campaign = campaign_report(
        root,
        state_path,
        handoff_path=handoff_path,
        include_next_campaign_recommendation=False,
    )
    reflection_observable = reflection_path is not None and reflection_path.exists()

    if candidate_task_complete:
        readiness_meaning = (
            "The selected candidate is hydrated, but its task is already complete; "
            "stale delivery is blocked."
        )
    elif str(readiness_report.get("candidate_status") or "") == "hydrated":
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
        readiness_meaning = "The initiative is still in discovery/refinement; hydration and delivery remain blocked."
    quality_meaning = (
        "Operator feedback is available and should be carried into future report/evaluator contracts."
        if reflection_observable
        else "No reflection artifact was available, so report-quality implications are limited."
    )
    candidate_rows = _candidate_slice_rows(root, doc)
    initiative_rows = _initiative_bank_rows(root)
    hydration_history = _hydration_history_rows(root, doc)
    gate_status = _lifecycle_gate_status(root)
    write_claim = _write_claim_status(root)
    protected_gate_status = _protected_gate_status(readiness_report)
    evaluator_evidence = _evaluator_evidence_status(reflections, reflection_errors)

    report = {
        "report_schema_version": 1,
        "report_type": "initiative_lifecycle_report",
        "source_artifacts": {
            "initiative_bank": _repo_artifact_ref(root, initiative_path),
            "initiative_bank_count": len(initiative_rows),
            "proposal_refs": doc.get("source_proposal_refs")
            if isinstance(doc.get("source_proposal_refs"), list)
            else [],
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
            "proposal_refs": doc.get("source_proposal_refs")
            if isinstance(doc.get("source_proposal_refs"), list)
            else [],
            "local_findings_count": len(doc.get("local_findings") or [])
            if isinstance(doc.get("local_findings"), list)
            else 0,
        },
        "initiative_banks": initiative_rows,
        "candidate": candidate,
        "candidate_slices": candidate_rows,
        "hydration_history": hydration_history,
        "readiness": {
            **lifecycle_readiness,
        },
        "readiness_blockers": lifecycle_readiness.get("blocking_reasons")
        if isinstance(lifecycle_readiness.get("blocking_reasons"), list)
        else [],
        "campaign_context": {
            "current_loop_status": campaign.get("current_loop", {}).get("status"),
            "handoff_observable": campaign.get("handoff_campaign", {}).get("observable"),
            "fresh_budget_required": campaign.get("observation", {}).get("fresh_budget_required"),
            "observation_reason": campaign.get("observation", {}).get("reason"),
            "campaign_report": campaign,
        },
        "evaluator_evidence": evaluator_evidence,
        "quality": {
            "reflection_observable": reflection_observable,
            "quality_signals": _quality_signals_from_reflections(reflections),
            "consumed_signal_ids": consumed_signal_ids,
            "evaluator_scores": [
                {
                    "name": "autonomous_auto_campaign_orchestrator_report",
                    "score": None,
                    "status": evaluator_evidence["status"],
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
            "protected_gate_required": protected_gate_status["required"],
            "hydration_safe_now": bool(readiness_report.get("ready_to_hydrate"))
            and not protected_gate_status["required"],
            "approval_basis": readiness.get("approval_basis") or "",
            "human_decision": readiness_report.get("human_decision"),
        },
        "gate_status": gate_status,
        "write_claim": write_claim,
        "protected_gate_status": protected_gate_status,
        "next_safe_actions": _lifecycle_next_safe_actions(doc, lifecycle_readiness, reflections),
        "blocked_actions": _lifecycle_blocked_actions(lifecycle_readiness),
    }
    route_decision = _route_decision_from_lifecycle_report(root, report)
    report["selected_route_decision"] = route_decision
    report["residual_risks"] = _lifecycle_residual_risks(
        candidate_rows=candidate_rows,
        route_decision=route_decision,
        gate_status=gate_status,
        write_claim=write_claim,
        evaluator_evidence=evaluator_evidence,
        campaign=campaign,
    )
    return report


def build_initiative_route_decision_capsule(
    root: Path,
    initiative_path: Path,
    *,
    reflection_path: Path | None = None,
    state_path: Path | None = None,
    handoff_path: Path | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    """Build the read-only T-024 route decision capsule from normalized reports."""
    report = build_initiative_lifecycle_report(
        root,
        initiative_path,
        reflection_path=reflection_path,
        state_path=state_path,
        handoff_path=handoff_path,
        candidate_id=candidate_id,
    )
    return _route_decision_from_lifecycle_report(Path(root), report)


def _format_lifecycle_report(payload: dict[str, Any]) -> str:
    initiative = payload.get("initiative") if isinstance(payload.get("initiative"), dict) else {}
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
    safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else {}
    quality = payload.get("quality") if isinstance(payload.get("quality"), dict) else {}
    evaluator = (
        payload.get("evaluator_evidence")
        if isinstance(payload.get("evaluator_evidence"), dict)
        else {}
    )
    route = (
        payload.get("selected_route_decision")
        if isinstance(payload.get("selected_route_decision"), dict)
        else {}
    )
    gates = payload.get("gate_status") if isinstance(payload.get("gate_status"), dict) else {}
    active_scope = gates.get("active_scope") if isinstance(gates.get("active_scope"), dict) else {}
    session_conflict = (
        gates.get("active_session_conflict")
        if isinstance(gates.get("active_session_conflict"), dict)
        else {}
    )
    pipeline_gate = (
        gates.get("pipeline_gate") if isinstance(gates.get("pipeline_gate"), dict) else {}
    )
    write_claim = payload.get("write_claim") if isinstance(payload.get("write_claim"), dict) else {}
    residual_risks = (
        payload.get("residual_risks") if isinstance(payload.get("residual_risks"), list) else []
    )
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
        str(item.get("action")) for item in blocked_action_items if isinstance(item, dict)
    )
    gate_text = (
        f"scope={active_scope.get('session_id') or 'none'}, "
        f"session_conflict={session_conflict.get('session_id') or 'none'}, "
        f"pipeline={pipeline_gate.get('pipeline_command') or 'none'}"
    )
    claim_text = f"held by {write_claim.get('session_id')}" if write_claim.get("held") else "none"
    risk_text = "; ".join(
        str(item.get("risk") or "")
        for item in residual_risks
        if isinstance(item, dict) and str(item.get("risk") or "")
    )
    return "\n".join(
        [
            "Autonomous-auto initiative lifecycle report",
            f"Initiative: {initiative.get('initiative_id')} - {initiative.get('title')}",
            f"Candidate: {candidate.get('candidate_id')} - {candidate.get('title')}",
            f"Readiness: {readiness.get('readiness_status')} (hydrate={readiness.get('ready_to_hydrate')})",
            f"Human decision: {readiness.get('human_decision')} ({readiness.get('approval_scope') or 'no scope'})",
            f"Quality: {'observed' if quality.get('reflection_observable') else 'not observed'}; evaluator score recorded=False",
            f"Evaluator evidence: {evaluator.get('status') or 'unknown'}",
            f"Selected route: {route.get('selected_route') or 'unknown'} ({route.get('route_state') or 'unknown'})",
            f"Protected gate required: {safety.get('protected_gate_required')}",
            f"Gate summary: {gate_text}",
            f"Write claim: {claim_text}",
            f"Next safe actions: {next_text or 'none'}",
            f"Blocked actions: {blocked_text or 'none'}",
            f"Residual risks: {risk_text or 'none'}",
        ]
    )


def _format_route_decision_capsule(payload: dict[str, Any]) -> str:
    readiness = (
        payload.get("readiness_evidence")
        if isinstance(payload.get("readiness_evidence"), dict)
        else {}
    )
    blocked = (
        payload.get("blocked_actions") if isinstance(payload.get("blocked_actions"), list) else []
    )
    blocked_actions = list(
        dict.fromkeys(
            str(item.get("action") or "")
            for item in blocked
            if isinstance(item, dict) and str(item.get("action") or "")
        )
    )
    return "\n".join(
        [
            "Autonomous-auto initiative route decision",
            f"Selected route: {payload.get('selected_route')} ({payload.get('route_state')})",
            f"Candidate: {readiness.get('candidate_id')} -> {readiness.get('candidate_task_ref')}",
            f"Readiness: {readiness.get('readiness_status')} (hydrate={readiness.get('ready_to_hydrate')})",
            f"Approval needed: {payload.get('approval_needed')}",
            f"Blocked actions: {', '.join(blocked_actions) if blocked_actions else 'none'}",
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


def cmd_route_decision(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    result = build_initiative_route_decision_capsule(
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
        else _format_route_decision_capsule(result)
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
    _reject_advisory_vision_declaration(vision_declaration)
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
            "route_decision": decision.get("route_decision"),
            "strategy_preflight": decision.get("strategy_preflight"),
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
            "strategy_preflight": decision.get("strategy_preflight"),
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


def _route_authority_read(decision: dict[str, Any]) -> str:
    stop_reason = str(decision.get("stop_reason") or "")
    if stop_reason.startswith("lifecycle_route_stop_"):
        return f"stop:{stop_reason.removeprefix('lifecycle_route_stop_')}"
    if stop_reason == "lifecycle_route_unreadable":
        return "stop:lifecycle_route_unreadable"
    source = str(decision.get("source") or "")
    if source == "initiative-bank":
        route_decision = (
            decision.get("route_decision") if isinstance(decision.get("route_decision"), dict) else {}
        )
        selected_route = str(route_decision.get("selected_route") or "")
        route_state = str(route_decision.get("route_state") or "")
        if selected_route and route_state:
            return f"{selected_route}:{route_state}"
        return "checked:continue"
    if source in {"queue", "campaign-strategy"}:
        return "queued-override"
    return "not-applicable"


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
    recommendation_packet = _next_campaign_recommendation_report_packet(root, state, status)
    return {
        "title": "Autonomous-auto operator read",
        "objective": str(state.get("objective") or state.get("loop_id") or "autonomous-auto loop"),
        "loop_state": str(status.get("status") or "missing_state"),
        "iteration": status.get("iteration"),
        "max_iterations": status.get("max_iterations"),
        "remaining_iterations": status.get("remaining_iterations"),
        "can_continue": status.get("can_continue"),
        "next_likely_move": next_move,
        "route_authority": _route_authority_read(decision) if decision else "not-evaluated",
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
        "next_campaign_recommendation": recommendation_packet,
    }


def _format_operator_read(payload: dict[str, Any]) -> str:
    stop_conditions = ", ".join(str(item) for item in payload.get("stop_conditions") or [])
    continuation = "required" if payload.get("continuation_required") else "not required"
    recommendation = (
        payload.get("next_campaign_recommendation")
        if isinstance(payload.get("next_campaign_recommendation"), dict)
        else {}
    )
    ranked = (
        recommendation.get("ranked_recommendations")
        if isinstance(recommendation.get("ranked_recommendations"), list)
        else []
    )
    top = ranked[0] if ranked and isinstance(ranked[0], dict) else {}
    recommendation_read = "none"
    if recommendation:
        recommendation_read = (
            f"{recommendation.get('status') or 'available'}; "
            f"fresh_approval={recommendation.get('requires_fresh_approval')}; "
            f"may_open_scope={recommendation.get('may_open_scope')}; "
            f"top={top.get('action') or 'none'}:{top.get('candidate_id') or 'none'}"
        )
    return "\n".join(
        [
            str(payload.get("title") or "Autonomous-auto operator read"),
            f"Objective: {payload.get('objective')}",
            f"Loop: {payload.get('loop_state')} ({payload.get('iteration')}/{payload.get('max_iterations')})",
            f"Vision: {payload.get('vision_band')} -> target {payload.get('vision_target')} (realized={payload.get('vision_realized')})",
            f"Next: {payload.get('next_likely_move')}",
            f"Route authority: {payload.get('route_authority')}",
            f"Continue: {continuation} ({payload.get('continuation_reason')})",
            f"Approval basis: {payload.get('approval_basis')}",
            f"Pending alignment packets: {payload.get('pending_alignment_packets')}",
            f"Write claim: {payload.get('write_claim')}",
            f"Completion reason: {payload.get('completion_reason') or 'none'}",
            f"Stop reason: {payload.get('stop_reason') or 'none'}",
            f"Next campaign recommendation: {recommendation_read}",
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
        payload.get("handoff_campaign") if isinstance(payload.get("handoff_campaign"), dict) else {}
    )
    observation = payload.get("observation") if isinstance(payload.get("observation"), dict) else {}
    harvester = (
        payload.get("learning_harvester")
        if isinstance(payload.get("learning_harvester"), dict)
        else {}
    )
    recommendation = (
        payload.get("next_campaign_recommendation")
        if isinstance(payload.get("next_campaign_recommendation"), dict)
        else {}
    )
    ranked = (
        recommendation.get("ranked_recommendations")
        if isinstance(recommendation.get("ranked_recommendations"), list)
        else []
    )
    top = ranked[0] if ranked and isinstance(ranked[0], dict) else {}
    recommendation_read = "none"
    if recommendation:
        recommendation_read = (
            f"{recommendation.get('status') or 'available'}; "
            f"fresh_approval={recommendation.get('requires_fresh_approval')}; "
            f"may_open_scope={recommendation.get('may_open_scope')}; "
            f"top={top.get('action') or 'none'}:{top.get('candidate_id') or 'none'}"
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
            f"Learning route: {harvester.get('selected_learning_route') or 'unknown'}",
            f"Learning rejected alternatives: {', '.join(harvester.get('rejected_alternatives') or []) or 'none'}",
            f"Next campaign recommendation: {recommendation_read}",
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


def _format_campaign_audit(payload: dict[str, Any]) -> str:
    campaign = payload.get("campaign") if isinstance(payload.get("campaign"), dict) else {}
    route = (
        payload.get("next_route_recommendation")
        if isinstance(payload.get("next_route_recommendation"), dict)
        else {}
    )
    scorecard = (
        payload.get("traceability_scorecard")
        if isinstance(payload.get("traceability_scorecard"), dict)
        else {}
    )
    residuals = (
        payload.get("residual_risks")
        if isinstance(payload.get("residual_risks"), list)
        else []
    )
    harvester = (
        payload.get("learning_harvester")
        if isinstance(payload.get("learning_harvester"), dict)
        else {}
    )
    return "\n".join(
        [
            f"Campaign audit: {campaign.get('loop_id') or 'unknown'}",
            f"Campaign status: {campaign.get('status') or 'unknown'}",
            f"Overall provenance: {scorecard.get('overall_provenance') or 'unknown'}",
            f"Next route: {route.get('route') or 'unknown'}",
            f"Learning route: {harvester.get('selected_learning_route') or 'unknown'}",
            f"Learning rejected alternatives: {', '.join(harvester.get('rejected_alternatives') or []) or 'none'}",
            f"Residual risks: {len(residuals)}",
        ]
    )


def cmd_campaign_audit(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    result = build_campaign_audit(
        root,
        args.loop_id,
        state_path=args.audit_state,
        ledger_path=args.ledger,
        episodes_path=args.episodes,
        inbox_dir=args.inbox_dir,
    )
    print(
        json.dumps(result, indent=2, sort_keys=False)
        if args.json
        else _format_campaign_audit(result)
    )


def _resolve_optional_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def _format_wakeup_report(payload: dict[str, Any]) -> str:
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    status = payload.get("loop_status") if isinstance(payload.get("loop_status"), dict) else {}
    return "\n".join(
        [
            "Autonomous-auto wakeup report",
            f"Loop: {status.get('status', 'unknown')} ({status.get('iteration', 0)}/{status.get('max_iterations', 0)})",
            f"Decision: {decision.get('action', 'unknown')} ({decision.get('candidate_id') or decision.get('stop_reason') or 'none'})",
            f"Opened: {payload.get('opened')} ({payload.get('session_id') or 'none'})",
            f"Fresh budget required: {payload.get('fresh_budget_required')}",
            f"Stop reason: {payload.get('stop_reason') or 'none'}",
            f"Residual risk: {payload.get('residual_risk')}",
        ]
    )


def cmd_wakeup(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state_path = _state_path(root, args.state)
    result = wakeup(
        root,
        state_path,
        open_scope=args.open,
        decision_out=_resolve_optional_path(root, args.decision_out),
        report_out=_resolve_optional_path(root, args.report_out),
        expires_at=args.expires_at,
        handoff_path=_resolve_optional_path(root, args.handoff),
    )
    print(
        json.dumps(result, indent=2, sort_keys=False)
        if args.json
        else _format_wakeup_report(result)
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

    audit = sub.add_parser(
        "campaign-audit", help="Build a read-only autonomous-auto campaign audit report."
    )
    audit.add_argument("--loop-id", required=True, help="Autonomous-auto loop/campaign id.")
    audit.add_argument("--json", action="store_true")
    audit.add_argument(
        "--state",
        dest="audit_state",
        default=None,
        help=f"Loop state path, default {STATE_REL}.",
    )
    audit.add_argument("--ledger", default=None, help="Run ledger path.")
    audit.add_argument("--episodes", default=None, help="Memory episodes JSONL path.")
    audit.add_argument("--inbox-dir", default=None, help="Inbox directory path.")
    audit.set_defaults(func=cmd_campaign_audit)

    wake = sub.add_parser(
        "wakeup",
        help="Build a one-shot autonomous-auto wakeup report and optionally open one scope.",
    )
    wake.add_argument("--json", action="store_true")
    wake.add_argument("--open", action="store_true", help="Open one scope if the report is safe.")
    wake.add_argument("--decision-out", default=None, help="Decision JSON output path.")
    wake.add_argument("--report-out", default=None, help="Wakeup report JSON output path.")
    wake.add_argument("--expires-at", default=None, help="Scope expiry ISO timestamp.")
    wake.add_argument("--handoff", default=None, help="Optional autonomous-auto handoff path.")
    wake.set_defaults(func=cmd_wakeup)

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

    route = sub.add_parser(
        "lifecycle-route",
        help="Build a read-only initiative route decision capsule for autonomous-auto.",
    )
    route.add_argument("--initiative", required=True, help="Initiative bank YAML path.")
    route.add_argument("--reflection", default=None, help="Optional reflection JSONL path.")
    route.add_argument("--handoff", default=None, help="Optional autonomous-auto handoff path.")
    route.add_argument("--candidate-id", default=None, help="Optional candidate_slices id.")
    route.add_argument("--json", action="store_true")
    route.set_defaults(func=cmd_route_decision)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

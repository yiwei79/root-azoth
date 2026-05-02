#!/usr/bin/env python3
"""Validate Azoth planning banks and roadmap references."""

from __future__ import annotations

import argparse
import json
import shlex
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
import research_sufficiency

ROOT = Path(__file__).resolve().parent.parent

DESIGN_BANK_DIR = Path(".azoth/design-banks")
INITIATIVE_BANK_DIR = Path(".azoth/initiative-banks")
PROPOSAL_DIR = Path(".azoth/proposals")

DESIGN_REQUIRED_FIELDS = {
    "schema_version",
    "bank_type",
    "id",
    "title",
    "status",
    "source_proposal_refs",
    "related_initiative_refs",
    "related_decision_refs",
    "problem",
    "design_thesis",
    "options",
    "tradeoffs",
    "open_questions",
    "research_refs",
    "challenge_log",
    "routing_candidates",
    "readiness",
    "closeout_history_policy",
    "history",
}

INITIATIVE_REQUIRED_FIELDS = {
    "schema_version",
    "bank_type",
    "initiative_id",
    "title",
    "status",
    "contacts",
    "source_proposal_refs",
    "research_questions",
    "research_refs",
    "local_findings",
    "external_findings",
    "assumptions",
    "contradictions",
    "challenge_log",
    "candidate_slices",
    "readiness",
    "hydration_history",
}

INITIATIVE_SLICE_REQUIRED_FIELDS = {
    "candidate_id",
    "proposed_task_id",
    "title",
    "initiative_ref",
    "status",
    "target_layer",
    "delivery_pipeline",
    "summary",
    "acceptance_criteria",
    "research_evidence_refs",
    "known_non_goals",
    "open_questions",
    "recommended_phase",
}

DESIGN_READINESS = {"continue_refinement", "ready_to_route", "defer", "reject"}
INITIATIVE_READINESS = {"continue_research", "ready_to_hydrate", "complete", "defer", "reject"}
INITIATIVE_SLICE_STATUS = {"candidate", "hydrated", "complete", "parked", "rejected"}
DESIGN_BANK_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CLOSEOUT_HISTORY_POLICY_ID = "planning_bank_closeout_history_merge_policy_v1"
CLOSEOUT_HISTORY_REQUIRED_METADATA = [
    "hydrated_at",
    "session_id",
    "candidate_slice_ref",
    "task_ref",
    "spec_ref",
    "approval_scope",
    "approval_basis",
    "append_policy_ref",
    "append_mode",
    "merge_key",
]

INITIATIVE_SLICE_STRING_FIELDS = {
    "candidate_id",
    "proposed_task_id",
    "title",
    "initiative_ref",
    "status",
    "target_layer",
    "delivery_pipeline",
    "summary",
    "recommended_phase",
}

INITIATIVE_SLICE_LIST_FIELDS = {
    "acceptance_criteria",
    "research_evidence_refs",
    "known_non_goals",
    "open_questions",
}

PROTECTED_DERIVED_CAPSULE_LAYERS = {
    "kernel",
    "governance",
    "m1",
    "release",
    "deployment",
    "personal-root",
    "personal_root",
}


class PlanningBankValidationError(Exception):
    pass


def _repo_rel(path: Path, *, repo_root: Path) -> Path:
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise PlanningBankValidationError(f"{path}: must live under {repo_root}") from exc


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise PlanningBankValidationError(f"{path}: root must be a mapping")
    return loaded


def _non_empty_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _list_or_empty(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _freshness_blocking_reason(freshness_status: Any) -> str | None:
    value = _non_empty_string(freshness_status)
    if value is None:
        return "readiness.freshness_status must be present and non-stale"
    normalized = value.strip().lower()
    if normalized == "stale" or normalized.startswith(("stale_", "stale-")):
        return "readiness.freshness_status must not be stale"
    return None


def _require_fields(doc: dict[str, Any], required: set[str], *, label: str) -> None:
    missing = sorted(required - set(doc))
    if missing:
        raise PlanningBankValidationError(f"{label}: missing required field(s): {missing}")


def _require_list(doc: dict[str, Any], key: str, *, label: str) -> list[Any]:
    value = doc.get(key)
    if not isinstance(value, list):
        raise PlanningBankValidationError(f"{label}: {key} must be a list")
    return value


def _require_string(doc: dict[str, Any], key: str, *, label: str) -> str:
    value = doc.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PlanningBankValidationError(f"{label}: {key} must be a non-empty string")
    return value


def _require_mapping(doc: dict[str, Any], key: str, *, label: str) -> dict[str, Any]:
    value = doc.get(key)
    if not isinstance(value, dict):
        raise PlanningBankValidationError(f"{label}: {key} must be a mapping")
    return value


def _validate_readiness(
    readiness: Any,
    *,
    label: str,
    allowed: set[str],
    ready_status: str,
) -> None:
    if not isinstance(readiness, dict):
        raise PlanningBankValidationError(f"{label}: readiness must be a mapping")
    status = readiness.get("readiness_status")
    if status not in allowed:
        raise PlanningBankValidationError(
            f"{label}: readiness_status must be one of {sorted(allowed)}, got {status!r}"
        )
    human_decision = readiness.get("human_decision")
    if not isinstance(human_decision, str) or not human_decision.strip():
        raise PlanningBankValidationError(f"{label}: readiness.human_decision is required")
    if status == ready_status and human_decision != "approved":
        raise PlanningBankValidationError(
            f"{label}: {ready_status} requires readiness.human_decision == 'approved'"
        )


def _validate_closeout_history_policy(policy: Any, *, label: str) -> None:
    if not isinstance(policy, dict):
        raise PlanningBankValidationError(f"{label}: closeout_history_policy must be a mapping")
    if policy.get("policy_id") != CLOSEOUT_HISTORY_POLICY_ID:
        raise PlanningBankValidationError(
            f"{label}: closeout_history_policy.policy_id must be {CLOSEOUT_HISTORY_POLICY_ID!r}"
        )
    if policy.get("merge_strategy") != "append_only":
        raise PlanningBankValidationError(
            f"{label}: closeout_history_policy.merge_strategy must be 'append_only'"
        )

    routine_closeout = _require_mapping(
        policy,
        "routine_closeout",
        label=f"{label}: closeout_history_policy",
    )
    if routine_closeout.get("planning_bank_write_mode") != "forbidden":
        raise PlanningBankValidationError(
            f"{label}: closeout_history_policy.routine_closeout.planning_bank_write_mode "
            "must be 'forbidden'"
        )

    explicit_history = _require_mapping(
        policy,
        "explicit_hydration_history",
        label=f"{label}: closeout_history_policy",
    )
    if explicit_history.get("append_path") != "hydration_history":
        raise PlanningBankValidationError(
            f"{label}: closeout_history_policy.explicit_hydration_history.append_path "
            "must be 'hydration_history'"
        )
    if explicit_history.get("append_position") != "append_tail":
        raise PlanningBankValidationError(
            f"{label}: closeout_history_policy.explicit_hydration_history.append_position "
            "must be 'append_tail'"
        )
    if explicit_history.get("required_metadata") != CLOSEOUT_HISTORY_REQUIRED_METADATA:
        raise PlanningBankValidationError(
            f"{label}: closeout_history_policy.explicit_hydration_history.required_metadata "
            "must match the validated append metadata contract"
        )
    non_laundering_rule = _non_empty_string(policy.get("non_laundering_rule"))
    if (
        non_laundering_rule is None
        or "historical" not in non_laundering_rule
        or "non retroactive pipeline compliance" not in non_laundering_rule
    ):
        raise PlanningBankValidationError(
            f"{label}: closeout_history_policy.non_laundering_rule must preserve "
            "historical/non retroactive pipeline compliance language"
        )


def validate_design_bank(path: Path, *, repo_root: Path = ROOT) -> None:
    rel = _repo_rel(path, repo_root=repo_root)
    if not rel.is_relative_to(DESIGN_BANK_DIR):
        raise PlanningBankValidationError(f"{rel}: design banks must live under {DESIGN_BANK_DIR}")
    doc = _load_yaml(path)
    _require_fields(doc, DESIGN_REQUIRED_FIELDS, label=str(rel))
    if doc.get("schema_version") != 1:
        raise PlanningBankValidationError(f"{rel}: schema_version must be 1")
    if doc.get("bank_type") != "design":
        raise PlanningBankValidationError(f"{rel}: bank_type must be 'design'")
    bank_id = _require_string(doc, "id", label=str(rel))
    if not DESIGN_BANK_ID_RE.fullmatch(bank_id):
        raise PlanningBankValidationError(f"{rel}: id must be slug-style lowercase kebab-case")
    if bank_id != rel.stem:
        raise PlanningBankValidationError(f"{rel}: id must match filename stem")
    for key in (
        "source_proposal_refs",
        "related_initiative_refs",
        "related_decision_refs",
        "options",
        "tradeoffs",
        "open_questions",
        "research_refs",
        "challenge_log",
        "routing_candidates",
        "history",
    ):
        _require_list(doc, key, label=str(rel))
    _validate_readiness(
        doc.get("readiness"),
        label=str(rel),
        allowed=DESIGN_READINESS,
        ready_status="ready_to_route",
    )
    _validate_closeout_history_policy(doc.get("closeout_history_policy"), label=str(rel))


def validate_initiative_bank(path: Path, *, repo_root: Path = ROOT) -> None:
    rel = _repo_rel(path, repo_root=repo_root)
    if not rel.is_relative_to(INITIATIVE_BANK_DIR):
        raise PlanningBankValidationError(
            f"{rel}: initiative banks must live under {INITIATIVE_BANK_DIR}"
        )
    doc = _load_yaml(path)
    _require_fields(doc, INITIATIVE_REQUIRED_FIELDS, label=str(rel))
    if doc.get("schema_version") != 1:
        raise PlanningBankValidationError(f"{rel}: schema_version must be 1")
    if doc.get("bank_type") != "initiative":
        raise PlanningBankValidationError(f"{rel}: bank_type must be 'initiative'")
    initiative_id = _require_string(doc, "initiative_id", label=str(rel))
    if initiative_id != rel.stem:
        raise PlanningBankValidationError(f"{rel}: initiative_id must match filename stem")
    for key in (
        "contacts",
        "source_proposal_refs",
        "research_questions",
        "research_refs",
        "local_findings",
        "external_findings",
        "assumptions",
        "contradictions",
        "challenge_log",
        "candidate_slices",
        "hydration_history",
    ):
        _require_list(doc, key, label=str(rel))
    _validate_readiness(
        doc.get("readiness"),
        label=str(rel),
        allowed=INITIATIVE_READINESS,
        ready_status="ready_to_hydrate",
    )
    candidate_ids: set[str] = set()
    for index, candidate in enumerate(doc.get("candidate_slices") or []):
        if not isinstance(candidate, dict):
            raise PlanningBankValidationError(f"{rel}: candidate_slices[{index}] must be a mapping")
        _require_fields(
            candidate,
            INITIATIVE_SLICE_REQUIRED_FIELDS,
            label=f"{rel}: candidate_slices[{index}]",
        )
        candidate_label = f"{rel}: candidate_slices[{index}]"
        for key in sorted(INITIATIVE_SLICE_STRING_FIELDS):
            _require_string(candidate, key, label=candidate_label)
        for key in sorted(INITIATIVE_SLICE_LIST_FIELDS):
            _require_list(candidate, key, label=candidate_label)
        if candidate.get("status") not in INITIATIVE_SLICE_STATUS:
            raise PlanningBankValidationError(
                f"{rel}: candidate_slices[{index}].status must be one of "
                f"{sorted(INITIATIVE_SLICE_STATUS)}, got {candidate.get('status')!r}"
            )
        candidate_id = str(candidate.get("candidate_id"))
        if candidate_id in candidate_ids:
            raise PlanningBankValidationError(
                f"{rel}: candidate_slices[{index}].candidate_id must be unique"
            )
        candidate_ids.add(candidate_id)
        if candidate.get("initiative_ref") != initiative_id:
            raise PlanningBankValidationError(
                f"{rel}: candidate_slices[{index}].initiative_ref must match initiative_id"
            )


def build_initiative_readiness_report(
    path: Path,
    *,
    repo_root: Path = ROOT,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    """Build a read-only hydration readiness report for an initiative bank."""
    rel = _repo_rel(path, repo_root=repo_root)
    if not rel.is_relative_to(INITIATIVE_BANK_DIR):
        raise PlanningBankValidationError(
            f"{rel}: initiative readiness reports require a bank under {INITIATIVE_BANK_DIR}"
        )

    doc = _load_yaml(path)
    if doc.get("schema_version") != 1 or doc.get("bank_type") != "initiative":
        raise PlanningBankValidationError(f"{rel}: bank must be a schema_version 1 initiative bank")

    readiness = doc.get("readiness")
    if not isinstance(readiness, dict):
        readiness = {}

    candidates = doc.get("candidate_slices")
    if not isinstance(candidates, list):
        candidates = []

    candidate_first_slice = readiness.get("candidate_first_slice")
    selected_candidate_id = candidate_id or candidate_first_slice
    candidate = next(
        (
            item
            for item in candidates
            if isinstance(item, dict) and item.get("candidate_id") == selected_candidate_id
        ),
        None,
    )
    if (
        candidate is None
        and selected_candidate_id is None
        and candidates
        and isinstance(candidates[0], dict)
    ):
        candidate = candidates[0]

    candidate_doc = candidate if isinstance(candidate, dict) else {}
    hydration_plan = candidate_doc.get("hydration_plan")
    if not isinstance(hydration_plan, dict):
        hydration_plan = {}

    human_decision = readiness.get("human_decision")
    readiness_status = readiness.get("readiness_status")
    freshness_status = readiness.get("freshness_status")
    approval_basis = _non_empty_string(readiness.get("approval_basis"))
    approval_scope = _non_empty_string(readiness.get("approval_scope"))
    acceptance_criteria = candidate_doc.get("acceptance_criteria")
    non_goals = candidate_doc.get("known_non_goals")
    open_questions = candidate_doc.get("open_questions")
    candidate_status = candidate_doc.get("status")
    initiative_ref = candidate_doc.get("initiative_ref") or doc.get("initiative_id")
    candidate_slice_ref = candidate_doc.get("candidate_id") or selected_candidate_id
    target_layer = _non_empty_string(candidate_doc.get("target_layer"))
    delivery_pipeline = _non_empty_string(candidate_doc.get("delivery_pipeline"))
    proposed_title = _non_empty_string(hydration_plan.get("proposed_title"))
    scaffold_command_candidate = _non_empty_string(hydration_plan.get("scaffold_command"))
    acceptance = _list_or_empty(acceptance_criteria)
    goals_to_exclude = _list_or_empty(non_goals)
    blocking_reasons: list[str] = []
    use_readiness_candidate_status = selected_candidate_id == candidate_first_slice
    terminal_readiness = readiness_status == "complete"

    if terminal_readiness:
        blocking_reasons.append(
            "readiness.readiness_status is complete; no hydration action remains"
        )
    if isinstance(candidate, dict) and candidate_status is None:
        blocking_reasons.append("candidate.status must be present")
    elif candidate_status in {"hydrated", "complete"}:
        blocking_reasons.append(
            f"candidate.status is {candidate_status}; no hydration action remains"
        )
    elif candidate_status is not None and candidate_status != "candidate":
        blocking_reasons.append("candidate.status must be candidate")
    if readiness_status != "ready_to_hydrate":
        blocking_reasons.append("readiness.readiness_status must be ready_to_hydrate")
    if human_decision != "approved":
        blocking_reasons.append("readiness.human_decision must be approved")
    if readiness_status == "ready_to_hydrate" and approval_basis is None:
        blocking_reasons.append("readiness.approval_basis must be present before hydration")
    if approval_scope == "planning_seed_only_no_hydration":
        blocking_reasons.append(
            "readiness.approval_scope planning_seed_only_no_hydration does not authorize hydration"
        )
    if not isinstance(candidate, dict) and not terminal_readiness:
        if selected_candidate_id:
            blocking_reasons.append(
                f"candidate_slices must include selected candidate_id {selected_candidate_id!r}"
            )
        else:
            blocking_reasons.append("candidate_slices must include a selected candidate")
    if not terminal_readiness and (
        not isinstance(acceptance_criteria, list) or not acceptance_criteria
    ):
        blocking_reasons.append("candidate.acceptance_criteria must be a non-empty list")
    if not terminal_readiness and (not isinstance(non_goals, list) or not non_goals):
        blocking_reasons.append("candidate.known_non_goals must be a non-empty list")
    if isinstance(open_questions, list) and open_questions:
        blocking_reasons.append("candidate.open_questions must be empty")
    elif not terminal_readiness and not isinstance(open_questions, list):
        blocking_reasons.append("candidate.open_questions must be a list")
    if not terminal_readiness and target_layer is None:
        blocking_reasons.append("candidate.target_layer must be a non-empty string")
    if not terminal_readiness and delivery_pipeline is None:
        blocking_reasons.append("candidate.delivery_pipeline must be a non-empty string")
    if not terminal_readiness and proposed_title is None:
        blocking_reasons.append(
            "candidate.hydration_plan.proposed_title must be a non-empty string"
        )
    if (
        not terminal_readiness
        and isinstance(candidate, dict)
        and scaffold_command_candidate is None
    ):
        blocking_reasons.append(
            "candidate.hydration_plan.scaffold_command must be a non-empty string"
        )
    freshness_blocker = _freshness_blocking_reason(freshness_status)
    if freshness_blocker is not None:
        blocking_reasons.append(freshness_blocker)

    ready_to_hydrate = not blocking_reasons
    acceptance_criteria_status = (
        readiness.get("acceptance_criteria_status") if use_readiness_candidate_status else None
    )
    non_goals_status = readiness.get("non_goals_status") if use_readiness_candidate_status else None
    scaffold_command = scaffold_command_candidate if ready_to_hydrate else None

    report = {
        "initiative_id": doc.get("initiative_id"),
        "initiative_ref": initiative_ref,
        "source_bank_ref": rel.as_posix(),
        "readiness_status": readiness_status or "missing",
        "human_decision": human_decision or "missing",
        "approval_scope": approval_scope,
        "approval_basis": approval_basis,
        "candidate_first_slice": candidate_first_slice or candidate_doc.get("candidate_id"),
        "candidate_id": candidate_doc.get("candidate_id") or selected_candidate_id or "missing",
        "candidate_slice_ref": candidate_slice_ref or "missing",
        "candidate_task_ref": candidate_doc.get("proposed_task_id"),
        "candidate_status": candidate_status or "missing",
        "proposed_title": proposed_title,
        "target_layer": target_layer,
        "delivery_pipeline": delivery_pipeline,
        "acceptance": acceptance,
        "acceptance_criteria_status": acceptance_criteria_status
        or ("present" if acceptance_criteria else "missing"),
        "non_goals": goals_to_exclude,
        "non_goals_status": non_goals_status or ("present" if non_goals else "missing"),
        "freshness_status": freshness_status or "missing",
        "hydration_recommendation": readiness.get("hydration_recommendation") or "missing",
        "blocking_reasons": blocking_reasons,
        "ready_to_hydrate": ready_to_hydrate,
        "scaffold_command": scaffold_command,
    }
    non_laundering_note = _non_empty_string(readiness.get("non_laundering_note"))
    if non_laundering_note:
        report["non_laundering_note"] = non_laundering_note
    return report


def _find_research_question(doc: dict[str, Any], question_id: str) -> dict[str, Any] | None:
    for question in _list_or_empty(doc.get("research_questions")):
        if isinstance(question, dict) and question.get("question_id") == question_id:
            return question
    return None


def _derive_task_capsule_questions(
    *,
    source_question: dict[str, Any] | None,
    goal: str,
    backlog_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(source_question, dict):
        return []

    answered_at = source_question.get("answered_at")
    fresh_until = source_question.get("fresh_until")
    if not _non_empty_string(answered_at) or not _non_empty_string(fresh_until):
        return []

    status = _non_empty_string(source_question.get("status")) or ""
    question_text = _non_empty_string(source_question.get("question")) or (
        "Can initiative-bank evidence derive a task-specific research capsule?"
    )
    answer = _non_empty_string(source_question.get("answer")) or question_text
    questions: list[dict[str, Any]] = []
    for question_id in research_sufficiency.derive_required_questions(
        goal=goal,
        backlog_id=backlog_id,
    ):
        questions.append(
            {
                "question_id": question_id,
                "question": question_text,
                "status": status,
                "answered_at": answered_at,
                "fresh_until": fresh_until,
                "derived_from_question_id": source_question.get("question_id"),
                "answer": answer,
            }
        )
    return questions


def build_derived_task_capsule_report(
    path: Path,
    *,
    repo_root: Path = ROOT,
    candidate_id: str | None = None,
    source_question_id: str = "rq-evi-002-010",
    goal: str | None = None,
    backlog_id: str | None = None,
    session_id: str = "",
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a read-only preview report for a derived task research capsule."""
    rel = _repo_rel(path, repo_root=repo_root)
    if not rel.is_relative_to(INITIATIVE_BANK_DIR):
        raise PlanningBankValidationError(
            f"{rel}: derived task capsule reports require a bank under {INITIATIVE_BANK_DIR}"
        )

    doc = _load_yaml(path)
    _require_fields(doc, INITIATIVE_REQUIRED_FIELDS, label=str(rel))
    if doc.get("schema_version") != 1 or doc.get("bank_type") != "initiative":
        raise PlanningBankValidationError(f"{rel}: bank must be a schema_version 1 initiative bank")
    initiative_id = _require_string(doc, "initiative_id", label=str(rel))
    if initiative_id != rel.stem:
        raise PlanningBankValidationError(f"{rel}: initiative_id must match filename stem")
    readiness = doc.get("readiness") if isinstance(doc.get("readiness"), dict) else {}
    candidates = (
        doc.get("candidate_slices") if isinstance(doc.get("candidate_slices"), list) else []
    )
    selected_candidate_id = candidate_id or readiness.get("candidate_first_slice")
    candidate = next(
        (
            item
            for item in candidates
            if isinstance(item, dict) and item.get("candidate_id") == selected_candidate_id
        ),
        None,
    )
    candidate_doc = candidate if isinstance(candidate, dict) else {}
    hydration_plan = (
        candidate_doc.get("hydration_plan")
        if isinstance(candidate_doc.get("hydration_plan"), dict)
        else {}
    )
    source_question = _find_research_question(doc, source_question_id)

    candidate_title = (
        _non_empty_string(hydration_plan.get("proposed_title"))
        or _non_empty_string(candidate_doc.get("title"))
        or "Derived task capsule"
    )
    capsule_goal = goal or candidate_title
    capsule_backlog_id = backlog_id or _non_empty_string(candidate_doc.get("proposed_task_id"))
    captured_at = timestamp or _utc_now()
    source_status = _non_empty_string(source_question.get("status")) if source_question else None
    source_fresh_until = (
        _non_empty_string(source_question.get("fresh_until")) if source_question else None
    )
    parsed_fresh_until = (
        research_sufficiency.parse_iso(source_fresh_until) if source_fresh_until else None
    )
    now = research_sufficiency.parse_iso(captured_at) or datetime.now(timezone.utc)
    source_evidence_refs = [
        str(item)
        for item in _list_or_empty(candidate_doc.get("research_evidence_refs"))
        if str(item).strip()
    ]
    excluded_stale_evidence: list[str] = []
    refusal_reasons: list[str] = []

    candidate_status = _non_empty_string(candidate_doc.get("status"))
    if candidate is None:
        refusal_reasons.append("refuse: required candidate or evidence fields are absent")
    elif candidate_status == "complete":
        refusal_reasons.append("refuse: no repeat derivation or hydration action remains")
    elif candidate_status == "hydrated":
        refusal_reasons.append("refuse: task already exists; define delivery boundary only")
    elif candidate_status == "rejected":
        refusal_reasons.append("refuse: candidate is not eligible evidence")
    elif candidate_status != "candidate":
        refusal_reasons.append("refuse: candidate status must be candidate")

    if readiness.get("human_decision") != "approved":
        refusal_reasons.append("refuse: explicit approval is required before derivation output")

    target_layer = str(candidate_doc.get("target_layer") or "").strip().lower()
    if target_layer in PROTECTED_DERIVED_CAPSULE_LAYERS:
        refusal_reasons.append("refuse: protected/kernel/governance outputs require human gate")

    freshness_blocker = _freshness_blocking_reason(readiness.get("freshness_status"))
    if freshness_blocker is not None:
        refusal_reasons.append("refuse: refresh source evidence before derivation")

    if not isinstance(source_question, dict) or not source_evidence_refs:
        refusal_reasons.append("refuse: required candidate or evidence fields are absent")
    if source_status == "conflicting":
        refusal_reasons.append("refuse: resolve or carry conflict through research_sufficiency.py")
        excluded_stale_evidence = source_evidence_refs
    if source_fresh_until is None or parsed_fresh_until is None:
        refusal_reasons.append("refuse: required candidate or evidence fields are absent")
    elif parsed_fresh_until <= now:
        refusal_reasons.append("refuse: refresh source evidence before derivation")
        excluded_stale_evidence = source_evidence_refs

    included_evidence_refs = [] if excluded_stale_evidence else source_evidence_refs
    preview_capsule: dict[str, Any] = {
        "schema_version": 1,
        "source_session_id": session_id or "preview-session",
        "goal": capsule_goal,
        "captured_at": captured_at,
        "volatility": "bounded",
        "limitations": [
            "Preview only; this helper does not emit standalone .azoth/research/*.json capsules."
        ],
        "questions": _derive_task_capsule_questions(
            source_question=source_question,
            goal=capsule_goal,
            backlog_id=capsule_backlog_id or "",
        ),
        "source_initiative_ref": doc.get("initiative_id"),
        "source_bank_ref": rel.as_posix(),
        "candidate_slice_ref": candidate_doc.get("candidate_id") or selected_candidate_id,
        "source_evidence_refs": included_evidence_refs,
        "freshness_window": {
            "fresh_until": source_fresh_until,
            "source_question_id": source_question_id,
        },
        "excluded_stale_evidence": excluded_stale_evidence,
        "decision_context": {
            "approval_scope": readiness.get("approval_scope"),
            "approval_basis": readiness.get("approval_basis"),
            "human_decision": readiness.get("human_decision") or "missing",
            "candidate_status": candidate_status or "missing",
            "source_question_status": source_status or "missing",
        },
    }
    sufficiency = research_sufficiency.evaluate_research_capsule(
        preview_capsule,
        goal=capsule_goal,
        backlog_id=capsule_backlog_id,
        now=now,
    )
    if sufficiency.get("outcome") != "research_sufficient":
        refusal_reasons.append("refuse: research_sufficiency.py must report sufficient")

    return {
        "report_type": "derived_task_capsule_preview",
        "initiative_id": doc.get("initiative_id"),
        "source_bank_ref": rel.as_posix(),
        "candidate_id": candidate_doc.get("candidate_id") or selected_candidate_id or "missing",
        "source_question_id": source_question_id,
        "ready_to_emit": not refusal_reasons,
        "refusal_reasons": list(dict.fromkeys(refusal_reasons)),
        "sufficiency": sufficiency,
        "preview_capsule": preview_capsule,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scaffold_args(command: str) -> list[str]:
    parts = shlex.split(command)
    if not parts:
        raise PlanningBankValidationError("scaffold_command must not be empty")
    if parts[0] in {"python", "python3", sys.executable} and len(parts) >= 2:
        script = parts[1]
        rest = parts[2:]
    else:
        script = parts[0]
        rest = parts[1:]
    if script not in {"scripts/roadmap_scaffold.py", "./scripts/roadmap_scaffold.py"}:
        raise PlanningBankValidationError(
            "scaffold_command must delegate to scripts/roadmap_scaffold.py"
        )
    return [sys.executable, "scripts/roadmap_scaffold.py", *rest]


def _parse_instant(value: Any, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PlanningBankValidationError(f"{label} must be present")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PlanningBankValidationError(f"{label} must be an ISO-8601 instant") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _load_scope_gate(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".azoth" / "scope-gate.json"
    if not path.exists():
        raise PlanningBankValidationError(
            "hydration requires a live approved scope-gate.json with pipeline_command"
        )
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanningBankValidationError("scope-gate.json must be valid JSON") from exc
    if not isinstance(loaded, dict):
        raise PlanningBankValidationError("scope-gate.json root must be a mapping")
    return loaded


def _require_hydration_pipeline_authority(
    repo_root: Path,
    report: dict[str, Any],
    *,
    session_id: str,
) -> None:
    gate = _load_scope_gate(repo_root)
    if gate.get("approved") is not True:
        raise PlanningBankValidationError("hydration requires scope-gate.approved == true")
    if gate.get("closed_at"):
        raise PlanningBankValidationError("hydration requires an open scope gate")
    expires_at = _parse_instant(gate.get("expires_at"), label="scope-gate.expires_at")
    if expires_at <= datetime.now(timezone.utc):
        raise PlanningBankValidationError("hydration requires an unexpired scope gate")

    if not _non_empty_string(session_id):
        raise PlanningBankValidationError(
            "hydration requires --session-id matching the approved scope gate"
        )
    gate_session_id = _non_empty_string(gate.get("session_id"))
    if gate_session_id != session_id:
        raise PlanningBankValidationError("hydration session_id must match the approved scope gate")
    if not _non_empty_string(gate.get("pipeline_command")):
        raise PlanningBankValidationError(
            "hydration requires an approved pipeline_command on scope-gate.json"
        )

    forbidden_outputs = set(_list_or_empty(gate.get("forbidden_outputs")))
    blocked_outputs = {
        "roadmap_hydration",
        "backlog_mutation",
        "roadmap_spec_mutation",
    }
    forbidden_overlap = sorted(forbidden_outputs & blocked_outputs)
    if forbidden_overlap:
        raise PlanningBankValidationError(
            "scope gate explicitly forbids hydration output(s): " + ", ".join(forbidden_overlap)
        )

    approval_scope = _non_empty_string(report.get("approval_scope"))
    if not approval_scope:
        raise PlanningBankValidationError("hydration requires a hydration-specific approval_scope")
    if not approval_scope.startswith("hydration_specific_"):
        raise PlanningBankValidationError("hydration approval_scope must be hydration-specific")
    gate_approval_scope = _non_empty_string(gate.get("approval_scope"))
    if not gate_approval_scope:
        raise PlanningBankValidationError("scope gate approval_scope must be present for hydration")
    if gate_approval_scope != approval_scope:
        raise PlanningBankValidationError(
            "scope gate approval_scope must match the hydration-specific approval scope"
        )

    initiative_id = _non_empty_string(report.get("initiative_id"))
    source_bank_ref = _non_empty_string(report.get("source_bank_ref"))
    source_artifacts = set(str(item) for item in _list_or_empty(gate.get("source_artifacts")))
    if not initiative_id:
        raise PlanningBankValidationError("hydration report must name initiative_id")
    gate_initiative_ref = _non_empty_string(gate.get("source_initiative_ref"))
    if not gate_initiative_ref:
        raise PlanningBankValidationError("scope gate source_initiative_ref must be present")
    if gate_initiative_ref != initiative_id:
        raise PlanningBankValidationError(
            "scope gate source_initiative_ref must match the hydrated initiative"
        )
    if not source_bank_ref:
        raise PlanningBankValidationError("hydration report must name source_bank_ref")
    if not source_artifacts:
        raise PlanningBankValidationError(
            "scope gate source_artifacts must include the hydrated initiative bank"
        )
    if source_bank_ref not in source_artifacts:
        raise PlanningBankValidationError(
            "scope gate source_artifacts must include the hydrated initiative bank"
        )


def hydrate_approved_initiative_candidate(
    path: Path,
    *,
    repo_root: Path = ROOT,
    candidate_id: str | None = None,
    session_id: str = "",
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Hydrate a ready initiative candidate through roadmap_scaffold.py delegation."""
    report = build_initiative_readiness_report(path, repo_root=repo_root, candidate_id=candidate_id)
    if not report.get("ready_to_hydrate"):
        reasons = "; ".join(str(item) for item in report.get("blocking_reasons") or [])
        raise PlanningBankValidationError(f"candidate is not ready to hydrate: {reasons}")

    command = str(report.get("scaffold_command") or "").strip()
    args = _scaffold_args(command)
    _require_hydration_pipeline_authority(repo_root, report, session_id=session_id)
    result = subprocess.run(args, cwd=repo_root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "roadmap_scaffold.py failed").strip()
        raise PlanningBankValidationError(f"roadmap_scaffold.py delegation failed: {detail}")

    output_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    task_ref = output_lines[0] if output_lines else ""
    if not task_ref:
        raise PlanningBankValidationError("roadmap_scaffold.py did not emit a task id")
    spec_ref = f".azoth/roadmap-specs/v0.2.0/{task_ref}.yaml"
    for line in output_lines[1:]:
        marker = ".azoth/roadmap-specs/"
        if marker in line and line.endswith(".yaml"):
            spec_ref = line[line.index(marker) :]
            break

    doc = _load_yaml(path)
    candidates = doc.get("candidate_slices")
    if not isinstance(candidates, list):
        raise PlanningBankValidationError("candidate_slices must be a list")
    selected = str(report.get("candidate_id") or candidate_id or "")
    candidate = next(
        (
            item
            for item in candidates
            if isinstance(item, dict) and str(item.get("candidate_id") or "") == selected
        ),
        None,
    )
    if not isinstance(candidate, dict):
        raise PlanningBankValidationError(f"candidate_slices must include {selected!r}")

    hydrated_at = timestamp or _utc_now()
    candidate["status"] = "hydrated"
    candidate["proposed_task_id"] = task_ref
    hydration_plan = candidate.setdefault("hydration_plan", {})
    if not isinstance(hydration_plan, dict):
        hydration_plan = {}
        candidate["hydration_plan"] = hydration_plan
    hydration_plan["mode"] = "executed"
    hydration_plan["hydrated_task_ref"] = task_ref
    hydration_plan["hydrated_spec_ref"] = spec_ref
    hydration_plan["hydrated_at"] = hydrated_at

    history = doc.setdefault("hydration_history", [])
    if not isinstance(history, list):
        raise PlanningBankValidationError("hydration_history must be a list")
    history.append(
        {
            "hydrated_at": hydrated_at,
            "session_id": session_id or "unknown-session",
            "candidate_slice_ref": selected,
            "task_ref": task_ref,
            "spec_ref": spec_ref,
            "backlog_ref": task_ref,
            "roadmap_ref": task_ref,
            "approval_scope": report.get("approval_scope") or "",
            "approval_basis": report.get("approval_basis") or "",
            "append_policy_ref": CLOSEOUT_HISTORY_POLICY_ID,
            "append_mode": "explicit_hydration_append",
            "merge_key": f"{selected}:{task_ref}:{hydrated_at}",
            "scaffold_command": command,
            "result": (
                f"Created roadmap/backlog/spec artifacts for {task_ref}; "
                "implementation and shipping remain separate."
            ),
        },
    )

    readiness = doc.get("readiness")
    if isinstance(readiness, dict):
        readiness["freshness_status"] = (
            f"current_as_of_{hydrated_at[:10].replace('-', '_')}_hydrated_to_"
            f"{task_ref.lower().replace('-', '_')}"
        )
        readiness["hydration_recommendation"] = (
            f"{selected} has been hydrated as {task_ref}. Do not repeat hydration; "
            "route implementation through a separate delivery child."
        )

    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return {
        "hydrated": True,
        "candidate_id": selected,
        "task_ref": task_ref,
        "spec_ref": spec_ref,
        "source_bank_ref": report.get("source_bank_ref"),
    }


def validate_planning_bank(path: Path, *, repo_root: Path = ROOT) -> None:
    doc = _load_yaml(path)
    bank_type = doc.get("bank_type")
    if bank_type == "design":
        validate_design_bank(path, repo_root=repo_root)
    elif bank_type == "initiative":
        validate_initiative_bank(path, repo_root=repo_root)
    else:
        raise PlanningBankValidationError(
            f"{_repo_rel(path, repo_root=repo_root)}: bank_type must be 'design' or 'initiative'"
        )


def _is_git_tracked(repo_root: Path, rel_path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", rel_path],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def _iter_roadmap_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"proposal_ref", "proposal_refs"}:
                if isinstance(child, str):
                    refs.append(child)
                elif isinstance(child, list):
                    refs.extend(item for item in child if isinstance(item, str))
            else:
                refs.extend(_iter_roadmap_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(_iter_roadmap_refs(child))
    return refs


def validate_roadmap_refs(*, repo_root: Path = ROOT) -> None:
    roadmap_path = repo_root / ".azoth" / "roadmap.yaml"
    roadmap = _load_yaml(roadmap_path)
    for ref in _iter_roadmap_refs(roadmap):
        if ref.startswith(f"{PROPOSAL_DIR.as_posix()}/") and not _is_git_tracked(repo_root, ref):
            raise PlanningBankValidationError(
                f".azoth/roadmap.yaml: authoritative proposal ref points at ignored/untracked file: {ref}"
            )
    for initiative in roadmap.get("initiatives") or []:
        if not isinstance(initiative, dict):
            continue
        initiative_id = str(initiative.get("id") or "").strip()
        bank_ref = str(initiative.get("initiative_bank_ref") or "").strip()
        if not bank_ref:
            continue
        bank_path = repo_root / bank_ref
        if not bank_path.exists():
            raise PlanningBankValidationError(
                f".azoth/roadmap.yaml: initiative_bank_ref for {initiative_id} is missing: {bank_ref}"
            )
        validate_initiative_bank(bank_path, repo_root=repo_root)
        bank = _load_yaml(bank_path)
        if bank.get("initiative_id") != initiative_id:
            raise PlanningBankValidationError(
                f".azoth/roadmap.yaml: initiative_bank_ref for {initiative_id} points at bank for {bank.get('initiative_id')!r}"
            )


def build_planning_bank_coverage_report(repo_root: Path = ROOT) -> dict[str, Any]:
    roadmap = _load_yaml(repo_root / ".azoth" / "roadmap.yaml")
    initiatives: list[dict[str, Any]] = []
    required = covered = missing_required = invalid_required = 0
    not_required = 0

    for initiative in roadmap.get("initiatives") or []:
        if not isinstance(initiative, dict):
            continue
        initiative_id = str(initiative.get("id") or "").strip()
        if not initiative_id:
            continue
        bank_ref = str(initiative.get("initiative_bank_ref") or "").strip()
        coverage_required = bool(bank_ref)
        item: dict[str, Any] = {
            "initiative_id": initiative_id,
            "phase": initiative.get("phase"),
            "initiative_bank_ref": bank_ref or None,
            "coverage_required": coverage_required,
            "covered": False,
            "status": "not_required",
        }

        if not coverage_required:
            not_required += 1
            initiatives.append(item)
            continue

        required += 1
        bank_path = repo_root / bank_ref
        if not bank_path.exists():
            missing_required += 1
            item["status"] = "missing"
            item["error"] = f"{bank_ref} does not exist"
            initiatives.append(item)
            continue

        try:
            validate_initiative_bank(bank_path, repo_root=repo_root)
            bank = _load_yaml(bank_path)
            if bank.get("initiative_id") != initiative_id:
                raise PlanningBankValidationError(
                    f"bank initiative_id {bank.get('initiative_id')!r} does not match {initiative_id!r}"
                )
        except PlanningBankValidationError as exc:
            invalid_required += 1
            item["status"] = "invalid"
            item["error"] = str(exc)
        else:
            covered += 1
            item["covered"] = True
            item["status"] = "covered"
        initiatives.append(item)

    return {
        "summary": {
            "required": required,
            "covered": covered,
            "missing_required": missing_required,
            "invalid_required": invalid_required,
            "not_required": not_required,
        },
        "initiatives": initiatives,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Azoth planning banks.")
    parser.add_argument("paths", nargs="*", type=Path, help="Planning bank YAML paths.")
    parser.add_argument(
        "--readiness-report",
        type=Path,
        metavar="PATH",
        help="Print a read-only initiative-bank readiness report as YAML.",
    )
    parser.add_argument(
        "--candidate-id",
        help=(
            "Select a specific candidate_slices[].candidate_id for --readiness-report, "
            "--hydrate-approved, or --derive-task-capsule."
        ),
    )
    parser.add_argument(
        "--derive-task-capsule",
        type=Path,
        metavar="PATH",
        help="Print a read-only derived task research capsule preview report as YAML.",
    )
    parser.add_argument(
        "--source-question-id",
        default="rq-evi-002-010",
        help="Select the initiative research question for --derive-task-capsule.",
    )
    parser.add_argument(
        "--check-roadmap-refs",
        action="store_true",
        help="Reject authoritative roadmap refs to ignored/untracked proposal files.",
    )
    parser.add_argument(
        "--coverage-report",
        action="store_true",
        help="Print a read-only planning-bank coverage report as YAML.",
    )
    parser.add_argument(
        "--intake-contract",
        type=Path,
        metavar="PATH",
        help="Print a read-only initiative intake contract validation report as YAML.",
    )
    parser.add_argument(
        "--hydrate-approved",
        type=Path,
        metavar="PATH",
        help="Hydrate a ready initiative candidate by delegating to roadmap_scaffold.py.",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help="Session id to record in hydration_history for --hydrate-approved.",
    )
    args = parser.parse_args(argv)
    cli_repo_root = Path.cwd().resolve()

    try:
        for path in args.paths:
            validate_planning_bank(path, repo_root=cli_repo_root)
        if args.check_roadmap_refs:
            validate_roadmap_refs(repo_root=cli_repo_root)
        if args.readiness_report is not None:
            report = build_initiative_readiness_report(
                args.readiness_report,
                repo_root=cli_repo_root,
                candidate_id=args.candidate_id,
            )
            print(yaml.safe_dump({"readiness_reports": [report]}, sort_keys=False), end="")
            return 0
        if args.derive_task_capsule is not None:
            report = build_derived_task_capsule_report(
                args.derive_task_capsule,
                repo_root=cli_repo_root,
                candidate_id=args.candidate_id,
                source_question_id=args.source_question_id,
                session_id=args.session_id,
            )
            print(
                yaml.safe_dump({"derived_task_capsule_reports": [report]}, sort_keys=False),
                end="",
            )
            return 0
        if args.coverage_report:
            report = build_planning_bank_coverage_report(cli_repo_root)
            print(yaml.safe_dump({"planning_bank_coverage": report}, sort_keys=False), end="")
            return 0
        if args.intake_contract is not None:
            import initiative_intake

            report = initiative_intake.validate_intake_contract(_load_yaml(args.intake_contract))
            print(yaml.safe_dump({"initiative_intake_reports": [report]}, sort_keys=False), end="")
            return 0
        if args.hydrate_approved is not None:
            result = hydrate_approved_initiative_candidate(
                args.hydrate_approved,
                repo_root=cli_repo_root,
                candidate_id=args.candidate_id,
                session_id=args.session_id,
            )
            print(yaml.safe_dump({"hydration": result}, sort_keys=False), end="")
            return 0
    except PlanningBankValidationError as exc:
        print(f"planning_bank_validate: {exc}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

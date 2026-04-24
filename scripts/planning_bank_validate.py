#!/usr/bin/env python3
"""Validate Azoth planning banks and roadmap references."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

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
INITIATIVE_READINESS = {"continue_research", "ready_to_hydrate", "defer", "reject"}
INITIATIVE_SLICE_STATUS = {"candidate", "hydrated", "complete", "parked", "rejected"}

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
    initiative_id = doc.get("initiative_id")
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

    human_decision = readiness.get("human_decision")
    readiness_status = readiness.get("readiness_status")
    acceptance_criteria = candidate.get("acceptance_criteria") if isinstance(candidate, dict) else None
    non_goals = candidate.get("known_non_goals") if isinstance(candidate, dict) else None
    open_questions = candidate.get("open_questions") if isinstance(candidate, dict) else None
    candidate_status = candidate.get("status") if isinstance(candidate, dict) else None
    blocking_reasons: list[str] = []
    use_readiness_candidate_status = selected_candidate_id == candidate_first_slice

    if candidate_status == "complete":
        blocking_reasons.append("candidate.status is complete; no hydration action remains")
    if readiness_status != "ready_to_hydrate":
        blocking_reasons.append("readiness.readiness_status must be ready_to_hydrate")
    if human_decision != "approved":
        blocking_reasons.append("readiness.human_decision must be approved")
    if not isinstance(candidate, dict):
        if selected_candidate_id:
            blocking_reasons.append(
                f"candidate_slices must include selected candidate_id {selected_candidate_id!r}"
            )
        else:
            blocking_reasons.append("candidate_slices must include a selected candidate")
    if not isinstance(acceptance_criteria, list) or not acceptance_criteria:
        blocking_reasons.append("candidate.acceptance_criteria must be a non-empty list")
    if not isinstance(non_goals, list) or not non_goals:
        blocking_reasons.append("candidate.known_non_goals must be a non-empty list")
    if isinstance(open_questions, list) and open_questions:
        blocking_reasons.append("candidate.open_questions must be empty")
    elif not isinstance(open_questions, list):
        blocking_reasons.append("candidate.open_questions must be a list")

    ready_to_hydrate = (
        readiness_status == "ready_to_hydrate"
        and human_decision == "approved"
        and isinstance(acceptance_criteria, list)
        and bool(acceptance_criteria)
        and isinstance(non_goals, list)
        and bool(non_goals)
        and isinstance(open_questions, list)
        and not open_questions
        and candidate_status != "complete"
    )
    acceptance_criteria_status = (
        readiness.get("acceptance_criteria_status") if use_readiness_candidate_status else None
    )
    non_goals_status = readiness.get("non_goals_status") if use_readiness_candidate_status else None

    return {
        "initiative_id": doc.get("initiative_id"),
        "readiness_status": readiness_status or "missing",
        "human_decision": human_decision or "missing",
        "candidate_first_slice": candidate_first_slice or (candidate or {}).get("candidate_id"),
        "candidate_id": (candidate or {}).get("candidate_id") or selected_candidate_id or "missing",
        "candidate_task_ref": (candidate or {}).get("proposed_task_id"),
        "candidate_status": candidate_status or "missing",
        "acceptance_criteria_status": acceptance_criteria_status
        or ("present" if acceptance_criteria else "missing"),
        "non_goals_status": non_goals_status or ("present" if non_goals else "missing"),
        "freshness_status": readiness.get("freshness_status") or "missing",
        "hydration_recommendation": readiness.get("hydration_recommendation") or "missing",
        "blocking_reasons": blocking_reasons,
        "ready_to_hydrate": ready_to_hydrate,
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
        help="Select a specific candidate_slices[].candidate_id for --readiness-report.",
    )
    parser.add_argument(
        "--check-roadmap-refs",
        action="store_true",
        help="Reject authoritative roadmap refs to ignored/untracked proposal files.",
    )
    args = parser.parse_args(argv)

    try:
        for path in args.paths:
            validate_planning_bank(path)
        if args.check_roadmap_refs:
            validate_roadmap_refs()
        if args.readiness_report is not None:
            report = build_initiative_readiness_report(
                args.readiness_report,
                candidate_id=args.candidate_id,
            )
            print(yaml.safe_dump({"readiness_reports": [report]}, sort_keys=False), end="")
            return 0
    except PlanningBankValidationError as exc:
        print(f"planning_bank_validate: {exc}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

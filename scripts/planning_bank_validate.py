#!/usr/bin/env python3
"""Validate Azoth planning banks and roadmap references."""

from __future__ import annotations

import argparse
import re
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
DESIGN_BANK_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

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
    if target_layer is None:
        blocking_reasons.append("candidate.target_layer must be a non-empty string")
    if delivery_pipeline is None:
        blocking_reasons.append("candidate.delivery_pipeline must be a non-empty string")
    if proposed_title is None:
        blocking_reasons.append(
            "candidate.hydration_plan.proposed_title must be a non-empty string"
        )
    if isinstance(candidate, dict) and scaffold_command_candidate is None:
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

    return {
        "initiative_id": doc.get("initiative_id"),
        "initiative_ref": initiative_ref,
        "source_bank_ref": rel.as_posix(),
        "readiness_status": readiness_status or "missing",
        "human_decision": human_decision or "missing",
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
        help="Select a specific candidate_slices[].candidate_id for --readiness-report.",
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
        if args.coverage_report:
            report = build_planning_bank_coverage_report()
            print(yaml.safe_dump({"planning_bank_coverage": report}, sort_keys=False), end="")
            return 0
    except PlanningBankValidationError as exc:
        print(f"planning_bank_validate: {exc}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

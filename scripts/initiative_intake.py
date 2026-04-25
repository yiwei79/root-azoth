#!/usr/bin/env python3
"""Validate and render seed-only raw initiative intake for autonomous-auto."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
INITIATIVE_BANK_DIR = Path(".azoth/initiative-banks")

CLASSIFICATION = "planning_discovery_seed"
APPROVAL_SCOPE = "planning_seed_only_no_hydration"

REQUIRED_FIELDS = frozenset(
    {
        "initiative_id",
        "operator_goal",
        "why_now",
        "known_constraints",
        "protected_boundaries",
        "success_signals",
        "initial_uncertainty",
        "approval_scope",
        "approval_basis",
        "allowed_outputs",
        "forbidden_outputs",
    }
)

EXECUTABLE_OUTPUTS = frozenset(
    {
        "scope_gate",
        "run_ledger_entry",
        "backlog_row",
        "roadmap_task",
        "task_spec",
        "hydration_write",
        "implementation_work",
        "hydrate_task",
        "ship_task",
        "protected_expansion",
        "kernel_change",
        "governance_change",
        "destructive_action",
        "network_expansion",
        "credential_access",
        "cross_branch_write",
    }
)

SEED_ONLY_AUTHORIZED_OUTPUTS = frozenset(
    {
        "initiative_bank_seed",
        "validation_report",
        "intake_summary",
    }
)


class InitiativeIntakeValidationError(Exception):
    pass


def _repo_rel(path: Path, *, repo_root: Path) -> Path:
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise InitiativeIntakeValidationError(f"{path}: must live under {repo_root}") from exc


def _normalize_token(value: str) -> str:
    return value.strip().lower()


def _require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InitiativeIntakeValidationError(f"{label}: root must be a mapping")
    missing = sorted(REQUIRED_FIELDS - set(value))
    if missing:
        raise InitiativeIntakeValidationError(f"{label}: missing required field(s): {missing}")
    return value


def _require_string(doc: dict[str, Any], key: str, *, label: str) -> str:
    value = doc.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InitiativeIntakeValidationError(f"{label}: {key} must be a non-empty string")
    return value.strip()


def _require_string_list(doc: dict[str, Any], key: str, *, label: str) -> list[str]:
    value = doc.get(key)
    if not isinstance(value, list) or not value:
        raise InitiativeIntakeValidationError(f"{label}: {key} must be a non-empty list")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise InitiativeIntakeValidationError(
                f"{label}: {key}[{index}] must be a non-empty string"
            )
        normalized.append(item.strip())
    return normalized


def _normalize_raw_intake(value: Any, *, label: str = "raw initiative intake") -> dict[str, Any]:
    doc = _require_mapping(value, label=label)
    initiative_id = _require_string(doc, "initiative_id", label=label)
    operator_goal = _require_string(doc, "operator_goal", label=label)
    why_now = _require_string(doc, "why_now", label=label)
    approval_scope = _require_string(doc, "approval_scope", label=label)
    approval_basis = _require_string(doc, "approval_basis", label=label)
    known_constraints = _require_string_list(doc, "known_constraints", label=label)
    protected_boundaries = _require_string_list(doc, "protected_boundaries", label=label)
    success_signals = _require_string_list(doc, "success_signals", label=label)
    initial_uncertainty = _require_string_list(doc, "initial_uncertainty", label=label)
    allowed_outputs = _require_string_list(doc, "allowed_outputs", label=label)
    forbidden_outputs = _require_string_list(doc, "forbidden_outputs", label=label)

    if approval_scope != APPROVAL_SCOPE:
        raise InitiativeIntakeValidationError(
            f"{label}: approval_scope must be {APPROVAL_SCOPE!r}"
        )

    allowed_tokens = {_normalize_token(item) for item in allowed_outputs}
    forbidden_tokens = {_normalize_token(item) for item in forbidden_outputs}
    executable_allowed = sorted(allowed_tokens & EXECUTABLE_OUTPUTS)
    if executable_allowed:
        raise InitiativeIntakeValidationError(
            f"{label}: allowed_outputs must not include executable output/action(s): "
            f"{executable_allowed}"
        )

    missing_forbidden = sorted(EXECUTABLE_OUTPUTS - forbidden_tokens)
    if missing_forbidden:
        raise InitiativeIntakeValidationError(
            f"{label}: forbidden_outputs must include executable output/action(s): "
            f"{missing_forbidden}"
        )

    return {
        "initiative_id": initiative_id,
        "operator_goal": operator_goal,
        "why_now": why_now,
        "known_constraints": known_constraints,
        "protected_boundaries": protected_boundaries,
        "success_signals": success_signals,
        "initial_uncertainty": initial_uncertainty,
        "approval_scope": approval_scope,
        "approval_basis": approval_basis,
        "allowed_outputs": sorted(allowed_tokens),
        "forbidden_outputs": sorted(forbidden_tokens),
    }


def approval_scope_authorizes(approval_scope: str, output_or_action: str) -> bool:
    if approval_scope != APPROVAL_SCOPE:
        return False
    return _normalize_token(output_or_action) in SEED_ONLY_AUTHORIZED_OUTPUTS


def validate_raw_intake(
    value: Any,
    *,
    label: str = "raw initiative intake",
) -> dict[str, Any]:
    intake = _normalize_raw_intake(value, label=label)
    authorized_outputs = [
        output
        for output in intake["allowed_outputs"]
        if approval_scope_authorizes(intake["approval_scope"], output)
    ]
    return {
        "ok": True,
        "classification": CLASSIFICATION,
        "delivery_authorized": False,
        "approval_scope": intake["approval_scope"],
        "approval_basis": intake["approval_basis"],
        "allowed_outputs": intake["allowed_outputs"],
        "authorized_outputs": sorted(authorized_outputs),
        "blocked_actions": sorted(EXECUTABLE_OUTPUTS),
    }


def validate_intake_contract(
    value: Any,
    *,
    label: str = "raw initiative intake",
) -> dict[str, Any]:
    """Return a read-only report for a raw initiative intake contract."""
    intake = _normalize_raw_intake(value, label=label)
    authorized_outputs = [
        output
        for output in intake["allowed_outputs"]
        if approval_scope_authorizes(intake["approval_scope"], output)
    ]
    return {
        "schema_version": 1,
        "report_type": "initiative_intake_validation",
        "valid": True,
        "classification": CLASSIFICATION,
        "initiative_id": intake["initiative_id"],
        "approval_scope": intake["approval_scope"],
        "approval_basis": intake["approval_basis"],
        "write_allowed": "initiative_bank_seed" in authorized_outputs,
        "delivery_authorized": False,
        "protected_gate_required": False,
        "allowed_outputs": intake["allowed_outputs"],
        "authorized_outputs": sorted(authorized_outputs),
        "forbidden_outputs": intake["forbidden_outputs"],
        "next_safe_actions": ["research_initiative", "refine_proposal"],
        "blocked_actions": sorted(EXECUTABLE_OUTPUTS),
        "errors": [],
        "seed_artifacts": [
            {
                "type": "initiative_bank_seed",
                "path": (INITIATIVE_BANK_DIR / f"{intake['initiative_id']}.yaml").as_posix(),
            }
        ],
    }


def _seed_output_rel(
    output_path: Path,
    *,
    repo_root: Path,
    initiative_id: str,
) -> Path:
    rel = _repo_rel(output_path, repo_root=repo_root)
    if not rel.is_relative_to(INITIATIVE_BANK_DIR):
        raise InitiativeIntakeValidationError(
            f"{rel}: seed output must live under {INITIATIVE_BANK_DIR}"
        )
    if rel.suffix not in {".yaml", ".yml"}:
        raise InitiativeIntakeValidationError(f"{rel}: seed output must be a YAML file")
    if rel.stem != initiative_id:
        raise InitiativeIntakeValidationError(
            f"{rel}: output filename stem must match initiative_id {initiative_id!r}"
        )
    return rel


def render_initiative_seed(
    value: Any,
    *,
    output_path: Path | None = None,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    intake = _normalize_raw_intake(value)
    if output_path is None:
        source_bank_ref = (INITIATIVE_BANK_DIR / f"{intake['initiative_id']}.yaml").as_posix()
    else:
        source_bank_ref = _seed_output_rel(
            output_path,
            repo_root=repo_root,
            initiative_id=intake["initiative_id"],
        ).as_posix()

    blocked_actions = sorted(EXECUTABLE_OUTPUTS)
    allowed_outputs = intake["allowed_outputs"]
    return {
        "schema_version": 1,
        "bank_type": "initiative",
        "initiative_id": intake["initiative_id"],
        "title": f"Raw initiative seed: {intake['initiative_id']}",
        "status": CLASSIFICATION,
        "classification": CLASSIFICATION,
        "delivery_authorized": False,
        "contacts": [],
        "source_proposal_refs": [],
        "research_questions": intake["initial_uncertainty"],
        "research_refs": [],
        "local_findings": [
            {
                "source": "raw_intake.operator_goal",
                "summary": intake["operator_goal"],
            },
            {
                "source": "raw_intake.why_now",
                "summary": intake["why_now"],
            },
        ],
        "external_findings": [],
        "assumptions": [
            {
                "source": "raw_intake.known_constraints",
                "items": intake["known_constraints"],
            }
        ],
        "contradictions": [],
        "challenge_log": [
            {
                "source": "raw_intake.protected_boundaries",
                "items": intake["protected_boundaries"],
            }
        ],
        "candidate_slices": [],
        "readiness": {
            "readiness_status": "continue_research",
            "human_decision": "approved_for_planning_seed_only",
            "classification": CLASSIFICATION,
            "source_bank_ref": source_bank_ref,
            "approval_scope": APPROVAL_SCOPE,
            "approval_basis": intake["approval_basis"],
            "allowed_outputs": allowed_outputs,
            "forbidden_outputs": intake["forbidden_outputs"],
            "blocked_actions": blocked_actions,
            "delivery_authorized": False,
            "hydrate_authorized": False,
            "ship_authorized": False,
            "hydration_recommendation": (
                "No hydration is authorized by planning_seed_only_no_hydration; "
                "complete research/discovery before any hydration slice."
            ),
            "next_readiness_gate": "research_before_hydration",
        },
        "hydration_history": [],
        "raw_intake": intake,
    }


def write_seed(
    value: Any,
    output_path: Path,
    *,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    seed = render_initiative_seed(value, output_path=output_path, repo_root=repo_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(seed, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    return seed


def _load_input(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise InitiativeIntakeValidationError(f"{path}: root must be a mapping")
    return loaded


def _emit_payload(payload: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=False))
    else:
        print(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), end="")


def _cmd_validate(args: argparse.Namespace) -> int:
    doc = _load_input(args.input)
    report = validate_raw_intake(doc, label=str(args.input))
    if args.json:
        _emit_payload(report, as_json=True)
    else:
        print(f"OK: {args.input} -> {CLASSIFICATION}")
    return 0


def _cmd_render_seed(args: argparse.Namespace) -> int:
    doc = _load_input(args.input)
    seed = render_initiative_seed(doc, output_path=args.output)
    _emit_payload(seed, as_json=args.json)
    return 0


def _cmd_write_seed(args: argparse.Namespace) -> int:
    if args.output is None:
        raise InitiativeIntakeValidationError("write-seed requires --output")
    doc = _load_input(args.input)
    seed = write_seed(doc, args.output)
    if args.json:
        _emit_payload(
            {
                "ok": True,
                "output": str(args.output),
                "classification": seed["classification"],
            },
            as_json=True,
        )
    else:
        print(f"OK: wrote {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate raw initiative intake.")
    validate.add_argument("--input", required=True, type=Path)
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=_cmd_validate)

    render = subparsers.add_parser("render-seed", help="Render a seed-only initiative bank.")
    render.add_argument("--input", required=True, type=Path)
    render.add_argument(
        "--output",
        type=Path,
        help="Optional planned seed path used only for source_bank_ref rendering.",
    )
    render.add_argument("--json", action="store_true")
    render.set_defaults(func=_cmd_render_seed)

    write = subparsers.add_parser("write-seed", help="Write a seed-only initiative bank.")
    write.add_argument("--input", required=True, type=Path)
    write.add_argument("--output", type=Path)
    write.add_argument("--json", action="store_true")
    write.set_defaults(func=_cmd_write_seed)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except InitiativeIntakeValidationError as exc:
        if getattr(args, "json", False):
            _emit_payload({"ok": False, "error": str(exc)}, as_json=True)
        else:
            print(f"initiative_intake: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

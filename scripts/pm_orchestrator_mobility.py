#!/usr/bin/env python3
"""Build plan-only PM Orchestrator initiative mobility capsules."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import roadmap_task_id
from planning_bank_validate import build_initiative_readiness_report
from yaml_helpers import safe_load_yaml_path


ROOT = Path(__file__).resolve().parent.parent
CONTRACT = "pm_orchestrator_mobility_plan_v1"
DEFAULT_CAMPAIGN_ID = "pm-orchestrator-initiative-mobility-20260504"
VALIDATION_SET = [
    "python3 scripts/roadmap_dashboard.py",
    "python3 scripts/azoth-deploy.py --check",
    "python3 scripts/run_ledger.py validate",
    "git diff -- .azoth/roadmap.yaml .azoth/backlog.yaml",
]
NON_GOALS = [
    "No roadmap/backlog/spec write without a fresh exact hydration gate",
    "No initiative-bank hydration_history write without a fresh exact hydration gate",
    "No phase advancement",
    "No public release or public checkout mutation",
    "No cockpit/project write",
    "No dependency/network/credential/destructive action",
    "No kernel/governance/M1 mutation",
    "No commit or push",
]
_BACKLOG_DONE_STATUSES = {"complete", "completed", "deferred"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_write_set(repo_root: Path) -> list[str]:
    roadmap_path = repo_root / ".azoth" / "roadmap.yaml"
    if not roadmap_path.is_file():
        raise ValueError("consumer roadmap is required to resolve the hydration write set")
    roadmap = safe_load_yaml_path(roadmap_path)
    if not isinstance(roadmap, dict):
        raise ValueError("consumer roadmap must be a mapping")
    milestone = roadmap_task_id.active_milestone(roadmap)
    return [
        ".azoth/roadmap.yaml",
        ".azoth/backlog.yaml",
        f".azoth/roadmap-specs/{milestone}/",
        ".azoth/initiative-banks/",
    ]


def discover_initiative_banks(repo_root: Path) -> list[Path]:
    bank_dir = repo_root / ".azoth" / "initiative-banks"
    if not bank_dir.exists():
        return []
    return sorted(path for path in bank_dir.glob("*.yaml") if path.is_file())


def _backlog_status_for_task(repo_root: Path, task_ref: str) -> str:
    if not task_ref:
        return ""
    backlog_path = repo_root / ".azoth" / "backlog.yaml"
    if not backlog_path.exists():
        return ""
    backlog = safe_load_yaml_path(backlog_path) or {}
    items = backlog.get("items") if isinstance(backlog, dict) else None
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == task_ref:
            return str(item.get("status") or "").strip()
    return ""


def _route_report(report: dict[str, Any], *, repo_root: Path = ROOT) -> tuple[str, str]:
    candidate_status = str(report.get("candidate_status") or "")
    readiness_status = str(report.get("readiness_status") or "")
    task_status = _backlog_status_for_task(
        repo_root, str(report.get("candidate_task_ref") or "")
    ).casefold()
    if report.get("ready_to_hydrate"):
        return "candidate_ready_for_review", "stop_for_human_gate"
    if task_status in _BACKLOG_DONE_STATUSES:
        return "fulfilled_or_stale", "stop_or_research_fresh_seed"
    if candidate_status == "hydrated":
        return "hydrated_not_delivered", "stop_or_delivery_gate"
    if candidate_status == "complete" or readiness_status == "complete":
        return "fulfilled_or_stale", "stop_or_research_fresh_seed"
    if candidate_status in {"rejected"} or readiness_status in {"reject", "defer"}:
        return "fulfilled_or_stale", "stop_or_research_fresh_seed"
    if readiness_status in {"continue_research", "ready_to_hydrate"}:
        return "discovery_active", "research_initiative_or_refine_proposal"
    return "raw_or_ambiguous", "research_initiative"


def _score_report(report: dict[str, Any], route_state: str) -> dict[str, int]:
    blockers = (
        report.get("blocking_reasons") if isinstance(report.get("blocking_reasons"), list) else []
    )
    ready = bool(report.get("ready_to_hydrate"))
    duplicate_block = route_state in {"fulfilled_or_stale", "hydrated_not_delivered"}
    return {
        "authority": 95 if ready else 80,
        "freshness": 90 if str(report.get("freshness_status") or "") not in {"missing", ""} else 35,
        "readiness": 100 if ready else 0,
        "strategic_fit": 75 if ready else 55,
        "duplication_risk": 100 if duplicate_block else (10 if ready else 40),
        "blast_radius": 95 if not ready else 70,
        "blocking_reason_count": len(blockers),
    }


def _approval_prompt(report: dict[str, Any], *, repo_root: Path) -> str:
    candidate_id = report.get("candidate_id") or "UNKNOWN-CANDIDATE"
    source_bank = report.get("source_bank_ref") or "UNKNOWN-BANK"
    command = report.get("scaffold_command") or "UNKNOWN-SCAFFOLD"
    write_set = _canonical_write_set(repo_root)
    return (
        f"Approve hydrate_task for {candidate_id} from {source_bank} using {command}. "
        f"Allowed writes: {', '.join(write_set)}. "
        f"Validation: {'; '.join(VALIDATION_SET)}. "
        "This approval does not authorize any other candidate, public sync/release, "
        "cockpit/project writes, dependency/network/credential work, destructive actions, "
        "kernel/governance/M1 mutation, broad roadmap/backlog rephasing, commit, or push."
    )


def _candidate_evaluation(report: dict[str, Any], *, repo_root: Path = ROOT) -> dict[str, Any]:
    route_state, selected_route = _route_report(report, repo_root=repo_root)
    evaluation = {
        "initiative_id": report.get("initiative_id"),
        "source_bank_ref": report.get("source_bank_ref"),
        "candidate_id": report.get("candidate_id"),
        "candidate_task_ref": report.get("candidate_task_ref"),
        "readiness_status": report.get("readiness_status"),
        "candidate_status": report.get("candidate_status"),
        "ready_to_hydrate": bool(report.get("ready_to_hydrate")),
        "route_state": route_state,
        "selected_route": selected_route,
        "scorecard": _score_report(report, route_state),
        "refusal_reasons": list(report.get("blocking_reasons") or []),
        "hydration_recommendation": report.get("hydration_recommendation"),
        "scaffold_command": report.get("scaffold_command"),
    }
    if report.get("ready_to_hydrate"):
        evaluation["required_human_approval"] = _approval_prompt(report, repo_root=repo_root)
    return evaluation


def build_mobility_capsule(
    bank_paths: list[Path],
    *,
    repo_root: Path = ROOT,
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    generated_at: str | None = None,
) -> dict[str, Any]:
    reports = [build_initiative_readiness_report(path, repo_root=repo_root) for path in bank_paths]
    evaluations = [_candidate_evaluation(report, repo_root=repo_root) for report in reports]
    ready_candidates = [item for item in evaluations if item.get("ready_to_hydrate") is True]
    selected = ready_candidates[0] if ready_candidates else None
    human_gate_required = selected is not None
    refusal_reasons = []
    if selected is None:
        refusal_reasons = [
            "No evaluated live candidate is safe for hydration.",
            "A fresh human gate must name the exact candidate, scaffold/write path, and validation set before hydrate_task.",
        ]

    return {
        "schema_version": 1,
        "contract": CONTRACT,
        "generated_at": generated_at or _utc_now(),
        "campaign_id": campaign_id,
        "selected_route": "stop_for_human_gate" if human_gate_required else "stop",
        "route_state": (selected.get("route_state") if selected else "no_safe_hydration_candidate"),
        "selected_candidate": selected,
        "source_bank_ref": selected.get("source_bank_ref") if selected else None,
        "readiness_report": {
            "evaluated_banks": [
                str(path.relative_to(repo_root)) if path.is_absolute() else str(path)
                for path in bank_paths
            ],
            "safe_hydration_candidate_count": len(ready_candidates),
        },
        "scorecard": {
            "authority": 100,
            "freshness": 90 if evaluations else 0,
            "readiness": 100 if human_gate_required else 0,
            "strategic_fit": 80 if human_gate_required else 60,
            "duplication_risk": 10 if human_gate_required else 100,
            "blast_radius": 70 if human_gate_required else 95,
        },
        "candidate_evaluations": evaluations,
        "refusal_reasons": refusal_reasons,
        "hydration_recommendation": (
            "Stop for a fresh human hydration gate naming this exact candidate."
            if human_gate_required
            else "Do not hydrate now. Research a fresh distinct seed or ship/refine pre-hydration helper work."
        ),
        "human_gate_required": human_gate_required,
        "required_human_approval": (selected.get("required_human_approval") if selected else None),
        "allowed_write_set_after_gate": (
            _canonical_write_set(repo_root) if human_gate_required else []
        ),
        "scaffold_command_after_gate": selected.get("scaffold_command") if selected else None,
        "validation_set_after_gate": VALIDATION_SET,
        "canonical_boundary": {
            "roadmap": ".azoth/roadmap.yaml",
            "backlog": ".azoth/backlog.yaml",
            "status": "unchanged_by_this_helper",
            "note": "This helper is read-only and plan-only.",
        },
        "non_goals": NON_GOALS,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--generated-at", default=None)
    parser.add_argument(
        "--bank",
        action="append",
        type=Path,
        default=[],
        help="Initiative bank path to evaluate. Defaults to all tracked initiative banks.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = args.repo_root.resolve()
    bank_paths = [
        path if path.is_absolute() else repo_root / path for path in args.bank
    ] or discover_initiative_banks(repo_root)
    capsule = build_mobility_capsule(
        bank_paths,
        repo_root=repo_root,
        campaign_id=args.campaign_id,
        generated_at=args.generated_at,
    )
    output = json.dumps(capsule, indent=2, sort_keys=False)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

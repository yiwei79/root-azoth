#!/usr/bin/env python3
"""Generate and validate planning-only Project Genesis starter packets."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from yaml_helpers import safe_load_yaml_path

DOMAINS: dict[str, dict[str, Any]] = {
    "music_production": {
        "why_now": "I want a place to explore sound, taste, workflow, and unfinished ideas.",
        "desired_help": "Help me notice patterns, choose experiments, and keep creative momentum.",
        "success": [
            "I can name the current sound direction.",
            "I have a small list of next experiments.",
            "Old sketches and references stop feeling scattered.",
        ],
        "artifacts": ["reference tracks", "unfinished sketches", "plugin/tool notes"],
        "questions": [
            "What sound am I circling around?",
            "Which unfinished idea deserves one more session?",
        ],
        "next_action": "Create a context map and choose one 30-60 minute experiment.",
        "prompt": (
            "Help me shape this music-production space without forcing it into "
            "software-task language. Capture my current sound, reference tracks, "
            "tools, unfinished ideas, learning questions, friction, and the next "
            "low-friction experiments."
        ),
    },
    "bachelor_thesis": {
        "why_now": "I need continuity across research, writing, deadlines, and advisor feedback.",
        "desired_help": "Help me recover the thesis state and choose the next focused work block.",
        "success": [
            "The research question is visible.",
            "Sources and evidence gaps are separated.",
            "The next writing/research action is concrete.",
        ],
        "artifacts": ["proposal or abstract", "advisor feedback", "source bibliography"],
        "questions": ["What is the current claim?", "Which source gap blocks writing?"],
        "next_action": "Map thesis state, then pick one reading or writing block.",
        "prompt": (
            "Help me continue my bachelor thesis. Map the research question, advisor "
            "constraints, deadlines, source state, argument structure, writing gaps, "
            "and the next focused work block."
        ),
    },
    "agent_context_project": {
        "why_now": (
            "I want to reconnect a separate agent/context-management idea to Azoth "
            "without forcing a merge."
        ),
        "desired_help": "Help me compare design intent, artifacts, risks, and compatibility.",
        "success": [
            "The project has its own identity.",
            "Compatibility questions with Azoth are explicit.",
            "The next experiment is safe and bounded.",
        ],
        "artifacts": ["architecture notes", "prototype scripts", "memory/context examples"],
        "questions": [
            "Which ideas belong in this project versus root-azoth?",
            "What would prove the context model works?",
        ],
        "next_action": "Create a compatibility map and choose one no-mutation experiment.",
        "prompt": (
            "Help me reconnect this agent/context-management project to Azoth. "
            "Identify its design intent, current artifact or repo state, open risks, "
            "compatibility with Azoth, and safe next experiments."
        ),
    },
}

MUST_NOT_LOAD = {"project source", "project-local memory", "project-local gates"}
CONFIRMS = {
    "no_project_repo_mutation",
    "no_cockpit_mutation",
    "no_public_azoth_mutation",
    "no_kernel_governance_mutation",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text or "project"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_profile(args: argparse.Namespace) -> dict[str, Any]:
    domain = args.domain
    preset = DOMAINS.get(domain, DOMAINS["agent_context_project"])
    project_name = args.project_name or domain.replace("_", " ").title()
    project_id = args.project_id or _slug(project_name)
    project_paths = [args.project_path] if args.project_path else []
    safe_open = (
        f"Open {project_id} as a {domain.replace('_', ' ')} space; "
        "do not load or mutate project files yet."
    )
    return {
        "packet_schema_version": 1,
        "packet_type": "project_genesis_starter",
        "project_id": project_id,
        "project_name": project_name,
        "domain": domain,
        "created_at": _utc_now(),
        "goal": {
            "why_now": args.why_now or preset["why_now"],
            "desired_help": args.desired_help or preset["desired_help"],
            "success_signals": list(preset["success"]),
            "not_success": [
                "A hidden write into project, cockpit, public Azoth, kernel, or governance."
            ],
        },
        "azoth_source_profile": {
            "source": args.azoth_source,
            "version_or_commit": args.version_or_commit or "",
            "upgrade_path": args.upgrade_path
            or "Record installed/public Azoth version before mutation.",
            "boundaries": [
                "Root-azoth owns toolkit development.",
                "Personal cockpit owns pointer-only routing.",
                "The project owns project-local context and write authority.",
            ],
        },
        "local_context": {
            "project_paths": project_paths,
            "important_artifacts": list(preset["artifacts"]),
            "people_or_roles": [],
            "current_state": "",
            "recent_history": "",
            "open_questions": list(preset["questions"]),
        },
        "starter_prompt": {
            "intent": f"Open a planning-only {domain.replace('_', ' ')} exploration.",
            "prompt": args.prompt or preset["prompt"],
            "expected_outputs": ["context map", "open questions", "next low-friction actions"],
            "forbidden_outputs": [
                "project code mutation",
                "cockpit write",
                "root roadmap/backlog/spec hydration",
                "kernel or governance edit",
            ],
        },
        "readiness": {
            "status": "discovery_active",
            "next_safe_action": preset["next_action"],
            "evidence_needed": [],
            "hydration_blockers": [
                "No project-local approval yet.",
                "No cockpit route approval yet.",
                "No root roadmap/backlog/spec hydration approval yet.",
            ],
        },
        "cockpit_route": {
            "desired_route_id": project_id,
            "route_label": project_name,
            "pointer_only": True,
            "safe_open_prompt": safe_open,
            "must_not_load": sorted(MUST_NOT_LOAD),
        },
        "validation_receipt": {
            "checked_at": "",
            "commands_or_checks": [],
            "changed_files": [],
            "confirms": {key: True for key in sorted(CONFIRMS)},
            "residual_risks": [],
        },
    }


def validate_packet(doc: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["root must be a mapping"]
    if doc.get("packet_schema_version") != 1:
        errors.append("packet_schema_version must be 1")
    if doc.get("packet_type") != "project_genesis_starter":
        errors.append("packet_type must be project_genesis_starter")
    for key in ("project_id", "project_name", "domain", "created_at"):
        if not isinstance(doc.get(key), str) or not doc.get(key).strip():
            errors.append(f"{key} must be a non-empty string")
    for key in (
        "goal",
        "azoth_source_profile",
        "local_context",
        "starter_prompt",
        "readiness",
        "cockpit_route",
        "validation_receipt",
    ):
        if not isinstance(doc.get(key), dict):
            errors.append(f"{key} must be a mapping")

    cockpit = doc.get("cockpit_route") if isinstance(doc.get("cockpit_route"), dict) else {}
    if cockpit.get("pointer_only") is not True:
        errors.append("cockpit_route.pointer_only must be true")
    missing_load = sorted(
        MUST_NOT_LOAD - set(str(item) for item in _list(cockpit.get("must_not_load")))
    )
    if missing_load:
        errors.append("cockpit_route.must_not_load missing: " + ", ".join(missing_load))

    confirms = {}
    receipt = doc.get("validation_receipt")
    if isinstance(receipt, dict) and isinstance(receipt.get("confirms"), dict):
        confirms = receipt["confirms"]
    for key in sorted(CONFIRMS):
        if confirms.get(key) is not True:
            errors.append(f"validation_receipt.confirms.{key} must be true")

    blockers = _list(
        (doc.get("readiness") or {}).get("hydration_blockers")
        if isinstance(doc.get("readiness"), dict)
        else None
    )
    if not blockers:
        errors.append("readiness.hydration_blockers must be a non-empty list")
    return errors


def _dump(doc: dict[str, Any]) -> str:
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def cmd_profile(args: argparse.Namespace) -> int:
    sys.stdout.write(_dump(build_profile(args)))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    doc = safe_load_yaml_path(args.path)
    errors = validate_packet(doc)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {args.path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    profile = sub.add_parser("profile", help="Print a starter packet YAML profile to stdout.")
    profile.add_argument("domain", choices=sorted(DOMAINS))
    profile.add_argument("--project-id", default="")
    profile.add_argument("--project-name", default="")
    profile.add_argument("--project-path", default="")
    profile.add_argument(
        "--azoth-source",
        default="public_install",
        choices=["public_install", "root_azoth", "personal_cockpit", "mixed"],
    )
    profile.add_argument("--version-or-commit", default="")
    profile.add_argument("--upgrade-path", default="")
    profile.add_argument("--why-now", default="")
    profile.add_argument("--desired-help", default="")
    profile.add_argument("--prompt", default="")
    profile.set_defaults(func=cmd_profile)
    validate = sub.add_parser("validate", help="Validate a starter packet YAML file.")
    validate.add_argument("path", type=Path)
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

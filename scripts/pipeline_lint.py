#!/usr/bin/env python3
"""
Pipeline Composition Linter (P1-003)

Validates Azoth pipeline definition files (`pipelines/*.pipeline.yaml`) against
the core pipeline schema constraints. Ensures syntactic correctness and
structural validity without requiring jsonschema dependencies.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

VALID_PRESETS = {"full", "deliver", "hotfix", "docs", "research", "review", "refactor", "auto"}
VALID_GATE_TYPES = {"human", "agent"}
VALID_AGENT_NAMES = {
    "architect",
    "planner",
    "builder",
    "reviewer",
    "researcher",
    "research-orchestrator",
    "evaluator",
    "prompt-engineer",
    "agent-crafter",
    "context-architect",
}
VALID_TOOLS = {"explore", "research", "research-orchestrator"}
VALID_SCOPE = {"kernel", "skills", "agents", "pipelines", "docs", "mixed"}
VALID_RISK = {"governance-change", "breaking-change", "additive", "cosmetic"}
VALID_COMPLEXITY = {"simple", "medium", "complex"}
VALID_KNOWLEDGE = {"known-pattern", "needs-research", "novel", "instruction-refinement"}


class ValidationError(Exception):
    pass


def validate_gate(gate: Any, stage_name: str) -> None:
    if not isinstance(gate, dict):
        raise ValidationError(f"stage '{stage_name}': gate must be a mapping")
    for field in ("type", "action"):
        if field not in gate:
            raise ValidationError(f"stage '{stage_name}': gate missing required field '{field}'")
    if gate["type"] not in VALID_GATE_TYPES:
        raise ValidationError(
            f"stage '{stage_name}': gate.type '{gate['type']}' not in {VALID_GATE_TYPES}"
        )
    if gate["type"] == "agent" and "agent" not in gate:
        raise ValidationError(f"stage '{stage_name}': gate.type=agent requires gate.agent")
    if gate["type"] == "human" and "agent" in gate:
        raise ValidationError(f"stage '{stage_name}': gate.type=human must not have gate.agent")
    if "agent" in gate and gate["agent"] not in VALID_AGENT_NAMES:
        raise ValidationError(
            f"stage '{stage_name}': gate.agent '{gate['agent']}' not in valid agent names"
        )


def validate_stage(stage: Any) -> None:
    if not isinstance(stage, dict):
        raise ValidationError("stage must be a mapping")
    for field in ("name", "agent", "gate"):
        if field not in stage:
            raise ValidationError(f"stage missing required field '{field}'")
    name = stage["name"]
    if stage["agent"] not in VALID_AGENT_NAMES:
        raise ValidationError(f"stage '{name}': agent '{stage['agent']}' not in valid agent names")
    if "tools" in stage:
        invalid = set(stage["tools"]) - VALID_TOOLS
        if invalid:
            raise ValidationError(f"stage '{name}': invalid tools {invalid}")
    validate_gate(stage["gate"], name)


def validate_composition_rules(rules: Any) -> None:
    if not isinstance(rules, dict):
        raise ValidationError("composition_rules must be a mapping")
    if "classification" not in rules:
        raise ValidationError("composition_rules missing 'classification'")
    if "rules" not in rules:
        raise ValidationError("composition_rules missing 'rules'")
    clf = rules["classification"]
    for field, valid in (
        ("scope", VALID_SCOPE),
        ("risk", VALID_RISK),
        ("complexity", VALID_COMPLEXITY),
        ("knowledge", VALID_KNOWLEDGE),
    ):
        if field not in clf:
            raise ValidationError(f"composition_rules.classification missing '{field}'")
        if clf[field] not in valid:
            raise ValidationError(
                f"composition_rules.classification.{field} '{clf[field]}' not in {valid}"
            )
    if not isinstance(rules["rules"], list) or len(rules["rules"]) == 0:
        raise ValidationError("composition_rules.rules must be a non-empty list")
    for i, rule in enumerate(rules["rules"]):
        if "condition" not in rule:
            raise ValidationError(f"composition_rules.rules[{i}] missing 'condition'")
        if "pipeline" not in rule:
            raise ValidationError(f"composition_rules.rules[{i}] missing 'pipeline'")


def validate_pipeline(data: Any) -> None:
    """Validate a parsed pipeline YAML structure against the schema constraints."""
    if not isinstance(data, dict):
        raise ValidationError("pipeline must be a YAML mapping")
    for field in ("name", "description", "preset", "stages"):
        if field not in data:
            raise ValidationError(f"pipeline missing required field '{field}'")
    if data["preset"] not in VALID_PRESETS:
        raise ValidationError(f"preset '{data['preset']}' not in {VALID_PRESETS}")
    if not isinstance(data["stages"], list) or len(data["stages"]) == 0:
        raise ValidationError("stages must be a non-empty list")
    for stage in data["stages"]:
        validate_stage(stage)
    if "composition_rules" in data:
        if data["preset"] != "auto":
            raise ValidationError("composition_rules is only valid when preset=auto")
        validate_composition_rules(data["composition_rules"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Azoth pipeline YAML files.")
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Specific pipeline files to lint. If absent, finds all in pipelines/ directory.",
    )
    args = parser.parse_args()

    # Determine files to check
    repo_root = Path(__file__).resolve().parent.parent
    pipelines_dir = repo_root / "pipelines"

    if args.files:
        files_to_check = args.files
    else:
        files_to_check = list(pipelines_dir.glob("*.pipeline.yaml"))
        # Also check the template file
        template_file = pipelines_dir / "pipeline.template.yaml"
        if template_file.exists():
            files_to_check.append(template_file)

    if not files_to_check:
        print("No pipeline YAML files found to lint.", file=sys.stderr)
        return 1

    errors_found = False

    for file_path in files_to_check:
        try:
            content = yaml.safe_load(file_path.read_text())
            if content is None:
                print(f"FAILED: {file_path.name} is empty.", file=sys.stderr)
                errors_found = True
                continue
            validate_pipeline(content)
            print(f"OK: {file_path.name}")
        except FileNotFoundError:
            print(f"FAILED: {file_path.name} not found.", file=sys.stderr)
            errors_found = True
        except yaml.YAMLError as exc:
            print(f"FAILED: {file_path.name} is invalid YAML: {exc}", file=sys.stderr)
            errors_found = True
        except ValidationError as exc:
            print(f"FAILED: {file_path.name} schema constraint violation: {exc}", file=sys.stderr)
            errors_found = True

    if errors_found:
        return 1

    print("Pipeline validation matched successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Pipeline schema validation tests for Azoth Phase 3 (P3-002).

Validates:
- pipeline.schema.yaml is well-formed with all required top-level keys
- pipeline.template.yaml is valid YAML and passes structural validation
- Valid pipeline structures pass the validator
- Invalid structures are rejected (missing required fields, bad enums, constraint violations)
- Gate type constraints (D24): agent gates require gate.agent; human gates must not have gate.agent
- Auto composition rules use the shared stage-family contract
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINES_DIR = REPO_ROOT / "pipelines"

SCHEMA_FILE = PIPELINES_DIR / "pipeline.schema.yaml"
TEMPLATE_FILE = PIPELINES_DIR / "pipeline.template.yaml"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from pipeline_lint import (  # noqa: E402
    VALID_AGENT_NAMES,
    VALID_DISCOVERY_POLICY,
    VALID_DISCOVERY_TRIGGERS,
    VALID_PRESETS,
    VALID_REFERENCE_PRESETS,
    VALID_SHARED_STAGE_FAMILIES,
    ValidationError,
    validate_pipeline,
)


MINIMAL_PIPELINE = {
    "name": "hotfix",
    "description": "Urgent fix — planner then builder then review.",
    "preset": "hotfix",
    "stages": [
        {
            "name": "planning",
            "agent": "planner",
            "gate": {"type": "agent", "agent": "architect", "action": "architect-review"},
        },
        {
            "name": "implementation",
            "agent": "builder",
            "gate": {"type": "agent", "agent": "evaluator", "action": "auto-test"},
        },
        {
            "name": "architect-review",
            "agent": "architect",
            "role": "post-delivery-review",
            "gate": {"type": "human", "action": "final-approval"},
        },
    ],
}

FULL_PIPELINE = {
    "name": "full",
    "description": "Full governance pipeline for kernel and breaking changes.",
    "preset": "full",
    "stages": [
        {
            "name": "goal-clarification",
            "agent": "architect",
            "gate": {"type": "human", "action": "approve-pipeline"},
        },
        {
            "name": "architect-design",
            "agent": "architect",
            "tools": ["explore", "research"],
            "outputs": ["architecture-brief"],
            "gate": {"type": "human", "action": "approve-design"},
        },
        {
            "name": "governance-review",
            "agent": "reviewer",
            "gate": {"type": "agent", "agent": "architect", "action": "architect-disposition"},
        },
        {
            "name": "planning",
            "agent": "planner",
            "inputs": ["architecture-brief"],
            "outputs": ["task-plan", "test-strategy"],
            "gate": {"type": "agent", "agent": "architect", "action": "architect-review"},
        },
        {
            "name": "test-design",
            "agent": "evaluator",
            "inputs": ["task-plan"],
            "outputs": ["test-specs", "acceptance-criteria"],
            "gate": {"type": "agent", "agent": "architect", "action": "architect-review"},
        },
        {
            "name": "implementation",
            "agent": "builder",
            "inputs": ["task-plan", "test-specs"],
            "gate": {"type": "agent", "agent": "evaluator", "action": "auto-test"},
        },
        {
            "name": "architect-review",
            "agent": "architect",
            "role": "post-delivery-review",
            "gate": {"type": "human", "action": "final-approval"},
        },
    ],
    "output": "alignment-summary",
}

AUTO_PIPELINE = {
    "name": "auto",
    "description": "Dynamically composed by the Architect based on goal classification (D23).",
    "preset": "auto",
    "stages": [
        {
            "name": "goal-clarification",
            "agent": "architect",
            "gate": {"type": "human", "action": "approve-pipeline"},
        },
    ],
    "composition_rules": {
        "classification": {
            "scope": "mixed",
            "risk": "additive",
            "complexity": "medium",
            "knowledge": "known-pattern",
        },
        "shared_stage_families": [
            "context-recall",
            "discovery-evidence-research",
            "architect-design",
            "review",
            "plan",
            "execute",
            "quality-gate",
            "closeout",
        ],
        "discovery_triggers": [
            "low-solution-confidence",
            "conflicting-memory-or-pattern-evidence",
            "cross-surface-drift",
            "latest-context-dependency",
            "gate-finding-evidence-insufficient",
        ],
        "rules": [
            {
                "condition": "risk == governance-change",
                "reference_preset": "full",
                "stage_families": [
                    "architect-design",
                    "review",
                    "plan",
                    "execute",
                    "quality-gate",
                    "closeout",
                ],
                "discovery_policy": "conditional",
            },
            {
                "condition": "default",
                "reference_preset": "deliver",
                "stage_families": ["plan", "execute", "quality-gate", "closeout"],
                "discovery_policy": "conditional",
            },
        ],
    },
}


class TestSchemaFile:
    def test_schema_file_exists(self) -> None:
        assert SCHEMA_FILE.exists(), f"Schema file not found: {SCHEMA_FILE}"

    def test_schema_is_valid_yaml(self) -> None:
        assert yaml.safe_load(SCHEMA_FILE.read_text()) is not None

    def test_schema_has_required_top_level_keys(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        for key in ("$schema", "$id", "title", "type", "required", "properties", "$defs"):
            assert key in data

    def test_schema_defs_cover_auto_contract(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        defs = data["$defs"]
        for key in (
            "gate",
            "stage",
            "agent_name",
            "reference_preset_name",
            "stage_family_name",
            "discovery_trigger_name",
            "discovery_policy_name",
            "composition_rules",
        ):
            assert key in defs

    def test_schema_enums_match_known_values(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        assert set(data["$defs"]["agent_name"]["enum"]) == VALID_AGENT_NAMES
        assert set(data["properties"]["preset"]["enum"]) == VALID_PRESETS
        assert set(data["$defs"]["reference_preset_name"]["enum"]) == VALID_REFERENCE_PRESETS
        assert set(data["$defs"]["stage_family_name"]["enum"]) == VALID_SHARED_STAGE_FAMILIES
        assert set(data["$defs"]["discovery_trigger_name"]["enum"]) == VALID_DISCOVERY_TRIGGERS
        assert set(data["$defs"]["discovery_policy_name"]["enum"]) == VALID_DISCOVERY_POLICY


class TestTemplateFile:
    def test_template_file_exists(self) -> None:
        assert TEMPLATE_FILE.exists(), f"Template file not found: {TEMPLATE_FILE}"

    def test_template_is_valid_yaml(self) -> None:
        assert yaml.safe_load(TEMPLATE_FILE.read_text()) is not None

    def test_template_has_required_fields(self) -> None:
        data = yaml.safe_load(TEMPLATE_FILE.read_text())
        for field in ("name", "description", "preset", "stages"):
            assert field in data

    def test_template_passes_validation(self) -> None:
        validate_pipeline(yaml.safe_load(TEMPLATE_FILE.read_text()))


class TestValidPipelines:
    def test_minimal_hotfix_pipeline(self) -> None:
        validate_pipeline(MINIMAL_PIPELINE)

    def test_full_7_stage_pipeline(self) -> None:
        validate_pipeline(FULL_PIPELINE)

    def test_auto_pipeline_with_shared_stage_family_rules(self) -> None:
        validate_pipeline(AUTO_PIPELINE)

    def test_all_agent_names_accepted(self) -> None:
        for agent in VALID_AGENT_NAMES:
            pipeline = copy.deepcopy(MINIMAL_PIPELINE)
            pipeline["stages"][0]["agent"] = agent
            validate_pipeline(pipeline)

    def test_all_presets_accepted(self) -> None:
        for preset in VALID_PRESETS - {"auto"}:
            pipeline = copy.deepcopy(MINIMAL_PIPELINE)
            pipeline["preset"] = preset
            pipeline["name"] = preset
            validate_pipeline(pipeline)

    def test_stage_with_all_optional_fields(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][0].update(
            {
                "role": "lead-planner",
                "tools": ["explore"],
                "inputs": ["prior-artifact"],
                "outputs": ["task-plan"],
            }
        )
        validate_pipeline(pipeline)

    def test_human_gate_without_agent_field(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][-1]["gate"] = {"type": "human", "action": "final-approval"}
        validate_pipeline(pipeline)


class TestInvalidPipelines:
    def test_missing_name(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["name"]
        with pytest.raises(ValidationError, match="missing required field 'name'"):
            validate_pipeline(pipeline)

    def test_invalid_preset(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["preset"] = "turbo"
        with pytest.raises(ValidationError, match="preset"):
            validate_pipeline(pipeline)

    def test_invalid_stage_tool(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][0]["tools"] = ["drill"]
        with pytest.raises(ValidationError, match="invalid tools"):
            validate_pipeline(pipeline)

    def test_agent_gate_without_gate_agent(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["stages"][0]["gate"]["agent"]
        with pytest.raises(ValidationError, match="gate.type=agent requires gate.agent"):
            validate_pipeline(pipeline)

    def test_human_gate_with_gate_agent(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][-1]["gate"]["agent"] = "architect"
        with pytest.raises(ValidationError, match="gate.type=human must not have gate.agent"):
            validate_pipeline(pipeline)

    def test_composition_rules_on_non_auto_preset(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["composition_rules"] = AUTO_PIPELINE["composition_rules"]
        with pytest.raises(ValidationError, match="only valid when preset=auto"):
            validate_pipeline(pipeline)

    def test_auto_preset_requires_composition_rules(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        del pipeline["composition_rules"]
        with pytest.raises(ValidationError, match="requires composition_rules"):
            validate_pipeline(pipeline)

    def test_composition_rules_missing_shared_stage_families(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        del pipeline["composition_rules"]["shared_stage_families"]
        with pytest.raises(ValidationError, match="missing 'shared_stage_families'"):
            validate_pipeline(pipeline)

    def test_composition_rules_missing_discovery_triggers(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        del pipeline["composition_rules"]["discovery_triggers"]
        with pytest.raises(ValidationError, match="missing 'discovery_triggers'"):
            validate_pipeline(pipeline)

    def test_invalid_reference_preset(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        pipeline["composition_rules"]["rules"][0]["reference_preset"] = "auto"
        with pytest.raises(ValidationError, match="reference_preset"):
            validate_pipeline(pipeline)

    def test_invalid_discovery_policy(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        pipeline["composition_rules"]["rules"][0]["discovery_policy"] = "maybe"
        with pytest.raises(ValidationError, match="discovery_policy"):
            validate_pipeline(pipeline)

    def test_rule_stage_family_outside_shared_vocabulary(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        pipeline["composition_rules"]["rules"][0]["stage_families"] = ["imaginary-phase"]
        with pytest.raises(ValidationError, match="stage_families entry 'imaginary-phase'"):
            validate_pipeline(pipeline)

    def test_rule_stage_family_must_be_subset_of_shared_stage_families(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        pipeline["composition_rules"]["shared_stage_families"].remove("review")
        with pytest.raises(
            ValidationError, match="must be declared in composition_rules.shared_stage_families"
        ):
            validate_pipeline(pipeline)

    def test_legacy_pipeline_key_rejected(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        pipeline["composition_rules"]["rules"][0]["pipeline"] = ["architect"]
        with pytest.raises(ValidationError, match="legacy key 'pipeline'"):
            validate_pipeline(pipeline)

    def test_legacy_inject_key_rejected(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        pipeline["composition_rules"]["rules"][0]["inject"] = "research-phase into architect"
        with pytest.raises(ValidationError, match="legacy key 'inject'"):
            validate_pipeline(pipeline)

    def test_instruction_refinement_knowledge_valid(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        pipeline["composition_rules"]["classification"]["knowledge"] = "instruction-refinement"
        validate_pipeline(pipeline)

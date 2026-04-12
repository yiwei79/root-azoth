"""
Pipeline schema validation tests for Azoth Phase 3 (P3-002).

Validates:
- pipeline.schema.yaml is well-formed with all required top-level keys
- pipeline.template.yaml is valid YAML and passes structural validation
- Valid pipeline structures pass the validator
- Invalid structures are rejected (missing required fields, bad enums, constraint violations)
- Gate type constraints (D24): agent gates require gate.agent; human gates must not have gate.agent
- Enum constraints: preset, gate.type, agent name, stage tool names
- composition_rules only valid when preset=auto
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

# Import logic from scripts/pipeline_lint.py
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from pipeline_lint import (  # noqa: E402
    VALID_AGENT_NAMES,
    VALID_PRESETS,
    ValidationError,
    validate_pipeline,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

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
        "rules": [
            {
                "condition": "risk == governance-change",
                "pipeline": ["architect", "planner", "builder", "evaluator", "architect"],
            },
            {
                "condition": "default",
                "pipeline": ["planner", "builder", "architect"],
            },
        ],
    },
}


# ── Schema file tests ─────────────────────────────────────────────────────────


class TestSchemaFile:
    def test_schema_file_exists(self) -> None:
        assert SCHEMA_FILE.exists(), f"Schema file not found: {SCHEMA_FILE}"

    def test_schema_is_valid_yaml(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        assert data is not None

    def test_schema_has_required_top_level_keys(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        for key in ("$schema", "$id", "title", "type", "required", "properties", "$defs"):
            assert key in data, f"Schema missing top-level key '{key}'"

    def test_schema_properties_cover_all_top_level_fields(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        required = set(data["required"])
        props = set(data["properties"].keys())
        assert required <= props, f"Required fields not in properties: {required - props}"

    def test_schema_defs_cover_gate_stage_agent_name(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        defs = data["$defs"]
        for key in ("gate", "stage", "agent_name", "composition_rules"):
            assert key in defs, f"$defs missing '{key}'"

    def test_schema_agent_enum_matches_known_agents(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        schema_agents = set(data["$defs"]["agent_name"]["enum"])
        assert schema_agents == VALID_AGENT_NAMES, (
            f"Schema agent enum mismatch.\n"
            f"  Extra in schema: {schema_agents - VALID_AGENT_NAMES}\n"
            f"  Missing from schema: {VALID_AGENT_NAMES - schema_agents}"
        )

    def test_schema_preset_enum_matches_known_presets(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        schema_presets = set(data["properties"]["preset"]["enum"])
        assert schema_presets == VALID_PRESETS


# ── Template file tests ───────────────────────────────────────────────────────


class TestTemplateFile:
    def test_template_file_exists(self) -> None:
        assert TEMPLATE_FILE.exists(), f"Template file not found: {TEMPLATE_FILE}"

    def test_template_is_valid_yaml(self) -> None:
        data = yaml.safe_load(TEMPLATE_FILE.read_text())
        assert data is not None

    def test_template_has_required_fields(self) -> None:
        data = yaml.safe_load(TEMPLATE_FILE.read_text())
        for field in ("name", "description", "preset", "stages"):
            assert field in data, f"Template missing required field '{field}'"

    def test_template_passes_validation(self) -> None:
        data = yaml.safe_load(TEMPLATE_FILE.read_text())
        validate_pipeline(data)


# ── Valid pipeline tests ──────────────────────────────────────────────────────


class TestValidPipelines:
    def test_minimal_hotfix_pipeline(self) -> None:
        validate_pipeline(MINIMAL_PIPELINE)

    def test_full_7_stage_pipeline(self) -> None:
        validate_pipeline(FULL_PIPELINE)

    def test_auto_pipeline_with_composition_rules(self) -> None:
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

    def test_pipeline_with_output_field(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["output"] = "alignment-summary"
        validate_pipeline(pipeline)

    def test_human_gate_without_agent_field(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][-1]["gate"] = {"type": "human", "action": "final-approval"}
        validate_pipeline(pipeline)

    def test_gate_with_rubric(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][-1]["gate"]["rubric"] = {
            "min_depth": 3,
            "criteria": ["constraints", "interaction-patterns"],
        }
        validate_pipeline(pipeline)


# ── Invalid pipeline tests ────────────────────────────────────────────────────


class TestInvalidPipelines:
    def test_missing_name(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["name"]
        with pytest.raises(ValidationError, match="missing required field 'name'"):
            validate_pipeline(pipeline)

    def test_missing_description(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["description"]
        with pytest.raises(ValidationError, match="missing required field 'description'"):
            validate_pipeline(pipeline)

    def test_missing_preset(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["preset"]
        with pytest.raises(ValidationError, match="missing required field 'preset'"):
            validate_pipeline(pipeline)

    def test_missing_stages(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["stages"]
        with pytest.raises(ValidationError, match="missing required field 'stages'"):
            validate_pipeline(pipeline)

    def test_empty_stages(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"] = []
        with pytest.raises(ValidationError, match="non-empty"):
            validate_pipeline(pipeline)

    def test_invalid_preset(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["preset"] = "turbo"
        with pytest.raises(ValidationError, match="preset"):
            validate_pipeline(pipeline)

    def test_invalid_agent_name(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][0]["agent"] = "wizard"
        with pytest.raises(ValidationError, match="agent"):
            validate_pipeline(pipeline)

    def test_stage_missing_name(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["stages"][0]["name"]
        with pytest.raises(ValidationError, match="missing required field 'name'"):
            validate_pipeline(pipeline)

    def test_stage_missing_agent(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["stages"][0]["agent"]
        with pytest.raises(ValidationError, match="missing required field 'agent'"):
            validate_pipeline(pipeline)

    def test_stage_missing_gate(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["stages"][0]["gate"]
        with pytest.raises(ValidationError, match="missing required field 'gate'"):
            validate_pipeline(pipeline)

    def test_gate_missing_type(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["stages"][0]["gate"]["type"]
        with pytest.raises(ValidationError, match="missing required field 'type'"):
            validate_pipeline(pipeline)

    def test_gate_missing_action(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        del pipeline["stages"][0]["gate"]["action"]
        with pytest.raises(ValidationError, match="missing required field 'action'"):
            validate_pipeline(pipeline)

    def test_invalid_gate_type(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][0]["gate"]["type"] = "maybe"
        with pytest.raises(ValidationError, match="gate.type"):
            validate_pipeline(pipeline)

    def test_agent_gate_without_gate_agent(self) -> None:
        """D24: agent-type gates require gate.agent."""
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        gate = pipeline["stages"][0]["gate"]
        del gate["agent"]  # agent gate missing gate.agent
        with pytest.raises(ValidationError, match="gate.type=agent requires gate.agent"):
            validate_pipeline(pipeline)

    def test_human_gate_with_gate_agent(self) -> None:
        """D24: human-type gates must not carry gate.agent."""
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][-1]["gate"]["agent"] = "architect"  # human gate, should fail
        with pytest.raises(ValidationError, match="gate.type=human must not have gate.agent"):
            validate_pipeline(pipeline)

    def test_invalid_gate_agent_name(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][0]["gate"]["agent"] = "unknown-bot"
        with pytest.raises(ValidationError, match="gate.agent"):
            validate_pipeline(pipeline)

    def test_invalid_stage_tool(self) -> None:
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["stages"][0]["tools"] = ["drill"]
        with pytest.raises(ValidationError, match="invalid tools"):
            validate_pipeline(pipeline)

    def test_composition_rules_on_non_auto_preset(self) -> None:
        """composition_rules must not appear on non-auto presets."""
        pipeline = copy.deepcopy(MINIMAL_PIPELINE)
        pipeline["composition_rules"] = AUTO_PIPELINE["composition_rules"]
        with pytest.raises(ValidationError, match="only valid when preset=auto"):
            validate_pipeline(pipeline)

    def test_composition_rules_missing_classification(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        del pipeline["composition_rules"]["classification"]
        with pytest.raises(ValidationError, match="missing 'classification'"):
            validate_pipeline(pipeline)

    def test_composition_rules_missing_rules(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        del pipeline["composition_rules"]["rules"]
        with pytest.raises(ValidationError, match="missing 'rules'"):
            validate_pipeline(pipeline)

    def test_composition_rules_invalid_scope(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        pipeline["composition_rules"]["classification"]["scope"] = "galaxy"
        with pytest.raises(ValidationError, match="scope"):
            validate_pipeline(pipeline)

    def test_composition_rules_rule_missing_condition(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        del pipeline["composition_rules"]["rules"][0]["condition"]
        with pytest.raises(ValidationError, match="missing 'condition'"):
            validate_pipeline(pipeline)

    def test_composition_rules_rule_missing_pipeline(self) -> None:
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        del pipeline["composition_rules"]["rules"][0]["pipeline"]
        with pytest.raises(ValidationError, match="missing 'pipeline'"):
            validate_pipeline(pipeline)


class TestInstructionRefinementKnowledge:
    """P1-008: instruction-refinement must be a valid knowledge enum value."""

    def test_instruction_refinement_knowledge_valid(self) -> None:
        """A pipeline with knowledge=instruction-refinement must pass validation."""
        pipeline = copy.deepcopy(AUTO_PIPELINE)
        pipeline["composition_rules"]["classification"]["knowledge"] = "instruction-refinement"
        validate_pipeline(pipeline)

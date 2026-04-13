"""
Swarm/eval-wave schema validation tests for Azoth Phase 1 (P1-002).

Validates:
- swarm-eval-wave.schema.yaml is well-formed with all required top-level keys
- swarm-eval-wave.example.yaml is valid YAML and passes structural validation
- Valid wave structures pass the validator
- Invalid structures are rejected (missing required fields, bad enums, constraint violations)
- Evaluator threshold conditional (F5): agent=evaluator requires threshold field
- agent=builder (Wave D) passes without threshold (F5b)
- schema_version is integer const:1 and is required (F4)
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINES_DIR = REPO_ROOT / "pipelines"

SCHEMA_FILE = PIPELINES_DIR / "swarm-eval-wave.schema.yaml"
EXAMPLE_FILE = PIPELINES_DIR / "swarm-eval-wave.example.yaml"

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
VALID_WAVES = {"A", "B", "C", "D"}


# ── Validator ────────────────────────────────────────────────────────────────


class ValidationError(Exception):
    pass


def validate_constants(data: Any) -> None:
    """Validate the constants block: eval_threshold (float 0–1), max_iteration_rounds (int ≥ 1)."""
    if not isinstance(data, dict):
        raise ValidationError("constants must be a mapping")
    if "eval_threshold" not in data:
        raise ValidationError("constants missing required field 'eval_threshold'")
    if "max_iteration_rounds" not in data:
        raise ValidationError("constants missing required field 'max_iteration_rounds'")
    threshold = data["eval_threshold"]
    if not isinstance(threshold, (int, float)):
        raise ValidationError(
            f"constants.eval_threshold must be a number, got {type(threshold).__name__}"
        )
    if not (0.0 <= float(threshold) <= 1.0):
        raise ValidationError(
            f"constants.eval_threshold {threshold} out of range [0.0, 1.0]"
        )
    rounds = data["max_iteration_rounds"]
    if not isinstance(rounds, int):
        raise ValidationError(
            f"constants.max_iteration_rounds must be an integer, got {type(rounds).__name__}"
        )
    if rounds < 1:
        raise ValidationError(
            f"constants.max_iteration_rounds {rounds} must be >= 1"
        )


def validate_wave_def(wave: Any) -> None:
    """Validate a single wave definition.

    Enforces:
    - Required fields: stage_id, wave, agent, max_parallel
    - agent must be in VALID_AGENT_NAMES
    - wave must be in VALID_WAVES
    - max_parallel must be an integer in [1, 7]
    - agent=evaluator requires threshold (F5a)
    - agent != evaluator passes without threshold (F5b)
    """
    if not isinstance(wave, dict):
        raise ValidationError("wave definition must be a mapping")
    for field in ("stage_id", "wave", "agent", "max_parallel"):
        if field not in wave:
            raise ValidationError(f"wave missing required field '{field}'")
    agent = wave["agent"]
    if agent not in VALID_AGENT_NAMES:
        raise ValidationError(f"wave agent '{agent}' not in {VALID_AGENT_NAMES}")
    wave_label = wave["wave"]
    if wave_label not in VALID_WAVES:
        raise ValidationError(f"wave label '{wave_label}' not in {VALID_WAVES}")
    max_parallel = wave["max_parallel"]
    if not isinstance(max_parallel, int):
        raise ValidationError(
            f"wave max_parallel must be an integer, got {type(max_parallel).__name__}"
        )
    if not (1 <= max_parallel <= 7):
        raise ValidationError(
            f"wave max_parallel {max_parallel} out of bounds [1, 7]"
        )
    # F5a: evaluator agent requires threshold
    if agent == "evaluator" and "threshold" not in wave:
        raise ValidationError(
            f"wave stage_id='{wave['stage_id']}': agent=evaluator requires threshold field"
        )


def validate_swarm_wave(data: Any) -> None:
    """Validate a parsed swarm-eval-wave YAML structure against schema constraints."""
    if not isinstance(data, dict):
        raise ValidationError("swarm-eval-wave document must be a YAML mapping")
    # F4: schema_version is required and must equal 1
    if "schema_version" not in data:
        raise ValidationError("swarm-eval-wave missing required field 'schema_version'")
    if data["schema_version"] != 1:
        raise ValidationError(
            f"schema_version must be 1, got {data['schema_version']!r}"
        )
    if "description" not in data:
        raise ValidationError("swarm-eval-wave missing required field 'description'")
    if "constants" not in data:
        raise ValidationError("swarm-eval-wave missing required field 'constants'")
    if "waves" not in data:
        raise ValidationError("swarm-eval-wave missing required field 'waves'")
    validate_constants(data["constants"])
    waves = data["waves"]
    if not isinstance(waves, list) or len(waves) == 0:
        raise ValidationError("waves must be a non-empty list")
    for wave in waves:
        validate_wave_def(wave)


# ── Fixtures ─────────────────────────────────────────────────────────────────

MINIMAL_WAVE_BUILDER = {
    "stage_id": "build-wave",
    "wave": "D",
    "agent": "builder",
    "max_parallel": 3,
}

MINIMAL_WAVE_EVALUATOR = {
    "stage_id": "eval-wave",
    "wave": "C",
    "agent": "evaluator",
    "max_parallel": 2,
    "threshold": 0.9,
}

MINIMAL_SWARM_WAVE = {
    "schema_version": 1,
    "description": "Minimal swarm-eval-wave for unit tests.",
    "constants": {
        "eval_threshold": 0.9,
        "max_iteration_rounds": 3,
    },
    "waves": [
        MINIMAL_WAVE_BUILDER,
        MINIMAL_WAVE_EVALUATOR,
    ],
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

    def test_schema_id_is_correct(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        assert data["$id"] == "azoth:swarm-wave:v1", (
            f"Schema $id expected 'azoth:swarm-wave:v1', got '{data['$id']}'"
        )

    def test_schema_has_schema_version_field(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        assert "schema_version" in data["properties"], (
            "Schema properties missing 'schema_version'"
        )

    def test_schema_version_is_const_1(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        schema_version_def = data["properties"]["schema_version"]
        assert schema_version_def.get("const") == 1, (
            f"schema_version must have const:1, got: {schema_version_def}"
        )

    def test_schema_version_in_required(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        assert "schema_version" in data["required"], (
            "schema_version must be in top-level required list"
        )

    def test_schema_defs_contain_wave_def(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        assert "wave_def" in data["$defs"], "$defs missing 'wave_def'"

    def test_schema_defs_contain_agent_name(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        assert "agent_name" in data["$defs"], "$defs missing 'agent_name'"

    def test_schema_defs_contain_constants(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        assert "constants" in data["$defs"], "$defs missing 'constants'"

    def test_schema_agent_enum_matches_known_agents(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        schema_agents = set(data["$defs"]["agent_name"]["enum"])
        assert schema_agents == VALID_AGENT_NAMES, (
            f"Schema agent enum mismatch.\n"
            f"  Extra in schema: {schema_agents - VALID_AGENT_NAMES}\n"
            f"  Missing from schema: {VALID_AGENT_NAMES - schema_agents}"
        )

    def test_schema_wave_enum_matches_known_waves(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        wave_def = data["$defs"]["wave_def"]
        schema_waves = set(wave_def["properties"]["wave"]["enum"])
        assert schema_waves == VALID_WAVES, (
            f"Schema wave enum mismatch.\n"
            f"  Extra in schema: {schema_waves - VALID_WAVES}\n"
            f"  Missing from schema: {VALID_WAVES - schema_waves}"
        )

    def test_schema_wave_def_required_fields(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        wave_def = data["$defs"]["wave_def"]
        required_set = set(wave_def.get("required", []))
        expected = {"stage_id", "wave", "agent", "max_parallel"}
        assert expected <= required_set, (
            f"wave_def required missing fields: {expected - required_set}"
        )

    def test_schema_max_parallel_bounded_1_to_7(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        wave_def = data["$defs"]["wave_def"]
        max_parallel_def = wave_def["properties"]["max_parallel"]
        assert max_parallel_def.get("maximum") == 7, (
            f"max_parallel maximum must be 7, got {max_parallel_def.get('maximum')}"
        )
        assert max_parallel_def.get("minimum") == 1, (
            f"max_parallel minimum must be 1, got {max_parallel_def.get('minimum')}"
        )

    def test_schema_threshold_conditional_exists(self) -> None:
        data = yaml.safe_load(SCHEMA_FILE.read_text())
        wave_def = data["$defs"]["wave_def"]
        assert "if" in wave_def, "wave_def must have an 'if' conditional for threshold"
        assert "then" in wave_def, "wave_def must have a 'then' clause for threshold"


# ── Example file tests ────────────────────────────────────────────────────────


class TestExampleFile:
    def test_example_file_exists(self) -> None:
        assert EXAMPLE_FILE.exists(), f"Example file not found: {EXAMPLE_FILE}"

    def test_example_is_valid_yaml(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        assert data is not None

    def test_example_has_required_top_level_keys(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        for key in ("schema_version", "description", "constants", "waves"):
            assert key in data, f"Example missing required field '{key}'"

    def test_example_schema_version_is_1(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        assert data["schema_version"] == 1, (
            f"Example schema_version must be 1, got {data['schema_version']!r}"
        )

    def test_example_passes_full_validation(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        validate_swarm_wave(data)

    def test_example_has_four_waves(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        assert len(data["waves"]) == 4, (
            f"Example must have 4 waves, got {len(data['waves'])}"
        )

    def test_example_wave_ids_are_unique(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        ids = [w["stage_id"] for w in data["waves"]]
        assert len(ids) == len(set(ids)), f"Duplicate wave stage_ids: {ids}"

    def test_example_wave_labels_are_a_b_c_d(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        labels = {w["wave"] for w in data["waves"]}
        assert labels == {"A", "B", "C", "D"}, (
            f"Example wave labels must be {{A,B,C,D}}, got {labels}"
        )

    def test_example_wave_c_has_threshold(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        wave_c = next((w for w in data["waves"] if w["wave"] == "C"), None)
        assert wave_c is not None, "Example has no Wave C"
        assert "threshold" in wave_c, "Wave C must have 'threshold' field"
        assert wave_c["threshold"] == 0.9, (
            f"Wave C threshold must be 0.9, got {wave_c['threshold']}"
        )

    def test_example_wave_d_agent_is_builder(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        wave_d = next((w for w in data["waves"] if w["wave"] == "D"), None)
        assert wave_d is not None, "Example has no Wave D"
        assert wave_d["agent"] == "builder", (
            f"Wave D agent must be 'builder', got '{wave_d['agent']}'"
        )

    def test_example_constants_eval_threshold(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        assert data["constants"]["eval_threshold"] == 0.9, (
            f"Example constants.eval_threshold must be 0.9, got {data['constants']['eval_threshold']}"
        )

    def test_example_constants_max_iteration_rounds(self) -> None:
        data = yaml.safe_load(EXAMPLE_FILE.read_text())
        assert data["constants"]["max_iteration_rounds"] == 3, (
            f"Example constants.max_iteration_rounds must be 3, "
            f"got {data['constants']['max_iteration_rounds']}"
        )


# ── Valid wave tests ──────────────────────────────────────────────────────────


class TestValidWaves:
    def test_minimal_wave_non_evaluator(self) -> None:
        """builder with no threshold — must pass (F5b)."""
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        validate_wave_def(wave)

    def test_evaluator_wave_with_threshold(self) -> None:
        """evaluator with threshold=0.9 — must pass (F5a happy path)."""
        wave = copy.deepcopy(MINIMAL_WAVE_EVALUATOR)
        validate_wave_def(wave)

    def test_all_agent_names_accepted(self) -> None:
        """All non-evaluator agent names must pass without threshold."""
        for agent in VALID_AGENT_NAMES - {"evaluator"}:
            wave = {
                "stage_id": f"wave-{agent}",
                "wave": "A",
                "agent": agent,
                "max_parallel": 2,
            }
            validate_wave_def(wave)

    def test_all_wave_labels_accepted(self) -> None:
        """All four wave labels A–D must be accepted."""
        for label in VALID_WAVES:
            wave = {
                "stage_id": f"stage-{label}",
                "wave": label,
                "agent": "builder",
                "max_parallel": 1,
            }
            validate_wave_def(wave)

    def test_max_parallel_at_bounds(self) -> None:
        """max_parallel=1 and max_parallel=7 are both valid."""
        for bound in (1, 7):
            wave = {
                "stage_id": "bound-test",
                "wave": "B",
                "agent": "planner",
                "max_parallel": bound,
            }
            validate_wave_def(wave)

    def test_optional_field_accepted(self) -> None:
        """threshold is accepted as an optional field on non-evaluator agents."""
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        wave["threshold"] = 0.85
        validate_wave_def(wave)

    def test_description_field_accepted(self) -> None:
        """description is accepted as an optional field on a wave."""
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        wave["description"] = "Research and gather context."
        validate_wave_def(wave)


# ── Invalid wave tests ────────────────────────────────────────────────────────


class TestInvalidWaves:
    def test_missing_stage_id(self) -> None:
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        del wave["stage_id"]
        with pytest.raises(ValidationError, match="missing required field 'stage_id'"):
            validate_wave_def(wave)

    def test_missing_wave(self) -> None:
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        del wave["wave"]
        with pytest.raises(ValidationError, match="missing required field 'wave'"):
            validate_wave_def(wave)

    def test_missing_agent(self) -> None:
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        del wave["agent"]
        with pytest.raises(ValidationError, match="missing required field 'agent'"):
            validate_wave_def(wave)

    def test_missing_max_parallel(self) -> None:
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        del wave["max_parallel"]
        with pytest.raises(ValidationError, match="missing required field 'max_parallel'"):
            validate_wave_def(wave)

    def test_invalid_agent_name(self) -> None:
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        wave["agent"] = "wizard"
        with pytest.raises(ValidationError, match="agent"):
            validate_wave_def(wave)

    def test_invalid_wave_label(self) -> None:
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        wave["wave"] = "Z"
        with pytest.raises(ValidationError, match="wave label"):
            validate_wave_def(wave)

    def test_max_parallel_zero(self) -> None:
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        wave["max_parallel"] = 0
        with pytest.raises(ValidationError, match="out of bounds"):
            validate_wave_def(wave)

    def test_max_parallel_eight(self) -> None:
        wave = copy.deepcopy(MINIMAL_WAVE_BUILDER)
        wave["max_parallel"] = 8
        with pytest.raises(ValidationError, match="out of bounds"):
            validate_wave_def(wave)

    def test_evaluator_without_threshold_fails(self) -> None:
        """F5a: agent=evaluator without threshold must raise ValidationError."""
        wave = {
            "stage_id": "eval-no-threshold",
            "wave": "C",
            "agent": "evaluator",
            "max_parallel": 2,
        }
        with pytest.raises(ValidationError, match="agent=evaluator requires threshold"):
            validate_wave_def(wave)

    def test_non_evaluator_without_threshold_passes(self) -> None:
        """F5b: agent=builder without threshold must NOT raise ValidationError."""
        wave = {
            "stage_id": "build-no-threshold",
            "wave": "D",
            "agent": "builder",
            "max_parallel": 3,
        }
        validate_wave_def(wave)  # must not raise


# ── Invalid swarm-wave document tests ────────────────────────────────────────


class TestInvalidSwarmWave:
    def test_missing_schema_version(self) -> None:
        doc = copy.deepcopy(MINIMAL_SWARM_WAVE)
        del doc["schema_version"]
        with pytest.raises(ValidationError, match="missing required field 'schema_version'"):
            validate_swarm_wave(doc)

    def test_missing_description(self) -> None:
        doc = copy.deepcopy(MINIMAL_SWARM_WAVE)
        del doc["description"]
        with pytest.raises(ValidationError, match="missing required field 'description'"):
            validate_swarm_wave(doc)

    def test_missing_constants(self) -> None:
        doc = copy.deepcopy(MINIMAL_SWARM_WAVE)
        del doc["constants"]
        with pytest.raises(ValidationError, match="missing required field 'constants'"):
            validate_swarm_wave(doc)

    def test_missing_waves(self) -> None:
        doc = copy.deepcopy(MINIMAL_SWARM_WAVE)
        del doc["waves"]
        with pytest.raises(ValidationError, match="missing required field 'waves'"):
            validate_swarm_wave(doc)

    def test_wrong_schema_version(self) -> None:
        doc = copy.deepcopy(MINIMAL_SWARM_WAVE)
        doc["schema_version"] = 2
        with pytest.raises(ValidationError, match="schema_version must be 1"):
            validate_swarm_wave(doc)

    def test_empty_waves_list(self) -> None:
        doc = copy.deepcopy(MINIMAL_SWARM_WAVE)
        doc["waves"] = []
        with pytest.raises(ValidationError, match="non-empty"):
            validate_swarm_wave(doc)

    def test_missing_eval_threshold(self) -> None:
        doc = copy.deepcopy(MINIMAL_SWARM_WAVE)
        del doc["constants"]["eval_threshold"]
        with pytest.raises(ValidationError, match="missing required field 'eval_threshold'"):
            validate_swarm_wave(doc)

    def test_missing_max_iteration_rounds(self) -> None:
        doc = copy.deepcopy(MINIMAL_SWARM_WAVE)
        del doc["constants"]["max_iteration_rounds"]
        with pytest.raises(ValidationError, match="missing required field 'max_iteration_rounds'"):
            validate_swarm_wave(doc)

    def test_eval_threshold_out_of_range(self) -> None:
        doc = copy.deepcopy(MINIMAL_SWARM_WAVE)
        doc["constants"]["eval_threshold"] = 1.5
        with pytest.raises(ValidationError, match="out of range"):
            validate_swarm_wave(doc)


# ── Build-review example file tests (BL-034) ─────────────────────────────────

BUILD_REVIEW_EXAMPLE_FILE = PIPELINES_DIR / "swarm-build-review.example.yaml"


class TestBuildReviewExample:
    def test_build_review_example_exists(self) -> None:
        assert BUILD_REVIEW_EXAMPLE_FILE.exists(), (
            f"Build-review example not found: {BUILD_REVIEW_EXAMPLE_FILE}"
        )

    def test_build_review_example_passes_full_validation(self) -> None:
        """swarm-build-review.example.yaml validates against swarm-eval-wave schema rules."""
        data = yaml.safe_load(BUILD_REVIEW_EXAMPLE_FILE.read_text())
        validate_swarm_wave(data)  # must not raise

    def test_build_review_example_has_exactly_two_waves(self) -> None:
        data = yaml.safe_load(BUILD_REVIEW_EXAMPLE_FILE.read_text())
        assert len(data["waves"]) == 2, (
            f"Build-review example must have 2 waves, got {len(data['waves'])}"
        )

    def test_build_review_example_wave_labels_are_a_and_b(self) -> None:
        data = yaml.safe_load(BUILD_REVIEW_EXAMPLE_FILE.read_text())
        labels = {w["wave"] for w in data["waves"]}
        assert labels == {"A", "B"}, (
            f"Build-review example wave labels must be {{A, B}}, got {labels}"
        )

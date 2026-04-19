"""
Pipeline preset validation tests for Azoth Phase 3 (P3-003).

Validates:
- All 8 preset files exist in pipelines/
- Each file is valid YAML and passes structural schema validation
- Each preset's name field matches its filename stem
- Each preset uses the correct preset enum value
- Stage agent sequences match D28 architectural spec
- Human gates present at required positions (D24)
- Full pipeline has exactly 7 stages (D21)
- Auto pipeline uses the shared stage-family router contract
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINES_DIR = REPO_ROOT / "pipelines"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from pipeline_lint import VALID_SHARED_STAGE_FAMILIES, validate_pipeline  # noqa: E402

EXPECTED_PRESETS = {"full", "deliver", "hotfix", "docs", "research", "review", "refactor", "auto"}


def load_preset(name: str) -> dict[str, Any]:
    path = PIPELINES_DIR / f"{name}.pipeline.yaml"
    return yaml.safe_load(path.read_text())


def stage_agents(pipeline: dict[str, Any]) -> list[str]:
    return [s["agent"] for s in pipeline["stages"]]


def human_gate_actions(pipeline: dict[str, Any]) -> list[str]:
    return [s["gate"]["action"] for s in pipeline["stages"] if s["gate"]["type"] == "human"]


class TestPresetFiles:
    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_file_exists(self, preset: str) -> None:
        assert (PIPELINES_DIR / f"{preset}.pipeline.yaml").exists()

    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_is_valid_yaml(self, preset: str) -> None:
        assert yaml.safe_load((PIPELINES_DIR / f"{preset}.pipeline.yaml").read_text()) is not None

    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_passes_schema_validation(self, preset: str) -> None:
        validate_pipeline(load_preset(preset))

    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_name_matches_filename(self, preset: str) -> None:
        assert load_preset(preset)["name"] == preset

    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_field_matches_filename(self, preset: str) -> None:
        assert load_preset(preset)["preset"] == preset


class TestPresetComposition:
    def test_full_has_7_stages(self) -> None:
        assert len(load_preset("full")["stages"]) == 7

    def test_full_stage_agent_sequence(self) -> None:
        assert stage_agents(load_preset("full")) == [
            "architect",
            "architect",
            "reviewer",
            "planner",
            "evaluator",
            "builder",
            "architect",
        ]

    def test_deliver_stage_agent_sequence(self) -> None:
        assert stage_agents(load_preset("deliver")) == ["planner", "evaluator", "builder", "architect"]

    def test_hotfix_stage_agent_sequence(self) -> None:
        assert stage_agents(load_preset("hotfix")) == ["planner", "builder", "architect"]

    def test_docs_stage_agent_sequence(self) -> None:
        assert stage_agents(load_preset("docs")) == ["architect", "builder", "architect"]

    def test_research_stage_agent_sequence(self) -> None:
        assert stage_agents(load_preset("research")) == ["architect", "architect"]

    def test_review_stage_agent_sequence(self) -> None:
        assert stage_agents(load_preset("review")) == ["architect", "reviewer", "architect"]

    def test_refactor_stage_agent_sequence(self) -> None:
        assert stage_agents(load_preset("refactor")) == ["architect", "planner", "evaluator", "builder", "architect"]

    def test_auto_has_shared_stage_family_contract(self) -> None:
        data = load_preset("auto")
        rules = data["composition_rules"]
        assert "shared_stage_families" in rules
        assert "discovery_triggers" in rules

    def test_auto_composition_rules_has_all_classification_dims(self) -> None:
        clf = load_preset("auto")["composition_rules"]["classification"]
        for dim in ("scope", "risk", "complexity", "knowledge"):
            assert dim in clf

    def test_auto_has_default_rule(self) -> None:
        conditions = [r["condition"] for r in load_preset("auto")["composition_rules"]["rules"]]
        assert "default" in conditions

    def test_auto_governance_and_kernel_rules_present(self) -> None:
        rules = load_preset("auto")["composition_rules"]["rules"]
        assert any("governance-change" in rule["condition"] for rule in rules)
        assert any("kernel" in rule["condition"] for rule in rules)

    def test_auto_needs_research_rule_requires_discovery(self) -> None:
        rules = load_preset("auto")["composition_rules"]["rules"]
        needs_research = next(rule for rule in rules if rule["condition"] == "knowledge == needs-research")
        assert needs_research["discovery_policy"] == "required"
        assert needs_research["stage_families"][0] == "discovery-evidence-research"

    def test_auto_rule_stage_families_are_valid_shared_members(self) -> None:
        data = load_preset("auto")
        shared = set(data["composition_rules"]["shared_stage_families"])
        assert shared <= VALID_SHARED_STAGE_FAMILIES
        for rule in data["composition_rules"]["rules"]:
            assert set(rule["stage_families"]) <= shared

    def test_auto_rules_do_not_use_legacy_pipeline_or_inject_keys(self) -> None:
        for rule in load_preset("auto")["composition_rules"]["rules"]:
            assert "pipeline" not in rule
            assert "inject" not in rule


class TestGateConstraints:
    def test_full_has_human_gates_at_design_and_final(self) -> None:
        actions = human_gate_actions(load_preset("full"))
        assert "approve-pipeline" in actions
        assert "approve-design" in actions
        assert "final-approval" in actions

    def test_all_presets_end_with_human_final_approval(self) -> None:
        for preset in EXPECTED_PRESETS - {"auto"}:
            last_gate = load_preset(preset)["stages"][-1]["gate"]
            assert last_gate["type"] == "human"
            assert last_gate["action"] == "final-approval"

    def test_full_governance_stage_has_agent_gate(self) -> None:
        gov_stage = next(s for s in load_preset("full")["stages"] if s["name"] == "governance-review")
        assert gov_stage["gate"]["type"] == "agent"
        assert gov_stage["gate"]["action"] == "architect-disposition"

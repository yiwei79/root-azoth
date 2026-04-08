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
- Auto pipeline has composition_rules with all required dimensions
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINES_DIR = REPO_ROOT / "pipelines"

# Import validator from schema tests — single source of truth
sys.path.insert(0, str(REPO_ROOT / "tests"))
from test_pipeline_schema import validate_pipeline  # noqa: E402

EXPECTED_PRESETS = {"full", "deliver", "hotfix", "docs", "research", "review", "refactor", "auto"}


def load_preset(name: str) -> dict[str, Any]:
    path = PIPELINES_DIR / f"{name}.pipeline.yaml"
    return yaml.safe_load(path.read_text())


def stage_agents(pipeline: dict[str, Any]) -> list[str]:
    return [s["agent"] for s in pipeline["stages"]]


def human_gate_actions(pipeline: dict[str, Any]) -> list[str]:
    return [s["gate"]["action"] for s in pipeline["stages"] if s["gate"]["type"] == "human"]


# ── Existence and validity ────────────────────────────────────────────────────


class TestPresetFiles:
    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_file_exists(self, preset: str) -> None:
        path = PIPELINES_DIR / f"{preset}.pipeline.yaml"
        assert path.exists(), f"Missing preset file: {path}"

    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_is_valid_yaml(self, preset: str) -> None:
        path = PIPELINES_DIR / f"{preset}.pipeline.yaml"
        data = yaml.safe_load(path.read_text())
        assert data is not None

    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_passes_schema_validation(self, preset: str) -> None:
        data = load_preset(preset)
        validate_pipeline(data)

    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_name_matches_filename(self, preset: str) -> None:
        data = load_preset(preset)
        assert data["name"] == preset, (
            f"name field '{data['name']}' does not match filename stem '{preset}'"
        )

    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_field_matches_filename(self, preset: str) -> None:
        data = load_preset(preset)
        assert data["preset"] == preset, (
            f"preset field '{data['preset']}' does not match filename stem '{preset}'"
        )

    @pytest.mark.parametrize("preset", sorted(EXPECTED_PRESETS))
    def test_preset_has_description(self, preset: str) -> None:
        data = load_preset(preset)
        assert data.get("description", "").strip(), f"preset '{preset}' has empty description"


# ── Stage count and composition (D21, D28) ────────────────────────────────────


class TestPresetComposition:
    def test_full_has_7_stages(self) -> None:
        """D21: full pipeline has exactly 7 stages."""
        data = load_preset("full")
        assert len(data["stages"]) == 7, (
            f"full pipeline has {len(data['stages'])} stages, expected 7 (D21)"
        )

    def test_full_stage_agent_sequence(self) -> None:
        """D28: full = Goal→Architect→Governance→Planner→TestBuilder→SWE→ArchReview"""
        agents = stage_agents(load_preset("full"))
        assert agents == [
            "architect",  # goal-clarification
            "architect",  # architect-design
            "reviewer",  # governance-review
            "planner",  # planning
            "evaluator",  # test-design
            "builder",  # implementation
            "architect",  # architect-review
        ]

    def test_deliver_stage_agent_sequence(self) -> None:
        """D28: deliver = Planner→TestBuilder→SWE→ArchReview"""
        agents = stage_agents(load_preset("deliver"))
        assert agents == ["planner", "evaluator", "builder", "architect"]

    def test_hotfix_stage_agent_sequence(self) -> None:
        """D28: hotfix = Planner→SWE→ArchReview"""
        agents = stage_agents(load_preset("hotfix"))
        assert agents == ["planner", "builder", "architect"]

    def test_docs_stage_agent_sequence(self) -> None:
        """D28: docs = Architect→Builder→ArchReview"""
        agents = stage_agents(load_preset("docs"))
        assert agents == ["architect", "builder", "architect"]

    def test_research_stage_agent_sequence(self) -> None:
        """D28: research = Architect(+research-swarm)→ArchReview"""
        agents = stage_agents(load_preset("research"))
        assert agents == ["architect", "architect"]

    def test_research_architect_uses_research_tools(self) -> None:
        """Research stage must invoke research sub-agents (D27)."""
        data = load_preset("research")
        first_stage = data["stages"][0]
        tools = set(first_stage.get("tools", []))
        assert tools & {"research", "research-orchestrator"}, (
            "research pipeline's architect stage must have research or research-orchestrator in tools"
        )

    def test_review_stage_agent_sequence(self) -> None:
        """D28: review = Architect→Governance→ArchReview"""
        agents = stage_agents(load_preset("review"))
        assert agents == ["architect", "reviewer", "architect"]

    def test_refactor_stage_agent_sequence(self) -> None:
        """D28: refactor = Architect(+explore)→Planner→TestBuilder→SWE→ArchReview"""
        agents = stage_agents(load_preset("refactor"))
        assert agents == ["architect", "planner", "evaluator", "builder", "architect"]

    def test_refactor_architect_uses_explore(self) -> None:
        """Refactor architect stage must use explore tool (D27)."""
        data = load_preset("refactor")
        first_stage = data["stages"][0]
        assert "explore" in first_stage.get("tools", []), (
            "refactor pipeline's architect stage must include explore tool"
        )

    def test_auto_has_composition_rules(self) -> None:
        """D23: auto preset must have composition_rules."""
        data = load_preset("auto")
        assert "composition_rules" in data

    def test_auto_composition_rules_has_all_classification_dims(self) -> None:
        """D23: classification must cover all 4 dimensions."""
        data = load_preset("auto")
        clf = data["composition_rules"]["classification"]
        for dim in ("scope", "risk", "complexity", "knowledge"):
            assert dim in clf, f"auto preset classification missing dimension '{dim}'"

    def test_auto_has_default_rule(self) -> None:
        """D23: composition_rules must include a catch-all default rule."""
        data = load_preset("auto")
        conditions = [r["condition"] for r in data["composition_rules"]["rules"]]
        assert "default" in conditions, (
            "auto preset composition_rules must include a 'default' catch-all rule"
        )

    def test_auto_governance_rule_present(self) -> None:
        """D23: governance-change must always route to full pipeline."""
        data = load_preset("auto")
        rules = data["composition_rules"]["rules"]
        governance_rules = [r for r in rules if "governance-change" in r["condition"]]
        assert governance_rules, "auto preset must have a rule for risk == governance-change (D23)"

    def test_auto_kernel_rule_present(self) -> None:
        """D23: kernel scope must always route to full pipeline."""
        data = load_preset("auto")
        rules = data["composition_rules"]["rules"]
        kernel_rules = [r for r in rules if "kernel" in r["condition"]]
        assert kernel_rules, "auto preset must have a rule for scope == kernel (D23)"


# ── Gate typing (D24) ─────────────────────────────────────────────────────────


class TestGateConstraints:
    def test_full_has_human_gates_at_design_and_final(self) -> None:
        """D24: full pipeline must have human gates at design approval and final delivery."""
        actions = human_gate_actions(load_preset("full"))
        assert "approve-pipeline" in actions
        assert "approve-design" in actions
        assert "final-approval" in actions

    def test_all_presets_end_with_human_final_approval(self) -> None:
        """D24: every preset's last stage must be a human final-approval gate."""
        for preset in EXPECTED_PRESETS - {"auto"}:
            data = load_preset(preset)
            last_gate = data["stages"][-1]["gate"]
            assert last_gate["type"] == "human", (
                f"preset '{preset}': last stage gate must be type=human (D24)"
            )
            assert last_gate["action"] == "final-approval", (
                f"preset '{preset}': last stage gate action must be final-approval"
            )

    def test_agent_gates_have_gate_agent(self) -> None:
        """D24: all agent-type gates must specify the validating agent."""
        for preset in EXPECTED_PRESETS:
            data = load_preset(preset)
            for stage in data["stages"]:
                gate = stage["gate"]
                if gate["type"] == "agent":
                    assert "agent" in gate, (
                        f"preset '{preset}', stage '{stage['name']}': agent gate missing gate.agent"
                    )

    def test_human_gates_have_no_gate_agent(self) -> None:
        """D24: human-type gates must not carry a gate.agent field."""
        for preset in EXPECTED_PRESETS:
            data = load_preset(preset)
            for stage in data["stages"]:
                gate = stage["gate"]
                if gate["type"] == "human":
                    assert "agent" not in gate, (
                        f"preset '{preset}', stage '{stage['name']}': "
                        f"human gate must not have gate.agent"
                    )

    def test_full_governance_stage_has_agent_gate(self) -> None:
        """D21: governance-review stage uses agent gate (architect-disposition)."""
        data = load_preset("full")
        gov_stage = next(s for s in data["stages"] if s["name"] == "governance-review")
        assert gov_stage["gate"]["type"] == "agent"
        assert gov_stage["gate"]["action"] == "architect-disposition"

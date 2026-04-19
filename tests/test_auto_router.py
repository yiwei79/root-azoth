"""Tests for skills/auto-router/SKILL.md — P3-004 (Auto-Pipeline Router)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "skills" / "auto-router" / "SKILL.md"
PIPELINE_PATH = REPO_ROOT / "pipelines" / "auto.pipeline.yaml"
SKILL_INDEX_PATH = REPO_ROOT / "skills" / "index.yaml"

CANONICAL_CONDITIONS: list[str] = [
    "risk == governance-change",
    "scope == kernel",
    "knowledge == needs-research",
    "knowledge == instruction-refinement AND complexity == simple AND risk == additive",
    "knowledge == instruction-refinement",
    "scope == docs",
    "complexity == simple AND risk == cosmetic",
    "complexity == simple AND risk == additive",
    "complexity == medium AND risk == additive AND knowledge == known-pattern",
    "complexity == medium AND risk == additive",
    "default",
]

EXPECTED_RULES: dict[str, dict[str, object]] = {
    "risk == governance-change": {
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
    "scope == kernel": {
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
    "knowledge == needs-research": {
        "reference_preset": "research",
        "stage_families": [
            "discovery-evidence-research",
            "architect-design",
            "plan",
            "execute",
            "quality-gate",
            "closeout",
        ],
        "discovery_policy": "required",
    },
    "knowledge == instruction-refinement AND complexity == simple AND risk == additive": {
        "reference_preset": "refactor",
        "stage_families": [
            "context-recall",
            "architect-design",
            "plan",
            "execute",
            "quality-gate",
            "closeout",
        ],
        "discovery_policy": "conditional",
    },
    "knowledge == instruction-refinement": {
        "reference_preset": "full",
        "stage_families": [
            "context-recall",
            "architect-design",
            "review",
            "plan",
            "execute",
            "quality-gate",
            "closeout",
        ],
        "discovery_policy": "conditional",
    },
    "scope == docs": {
        "reference_preset": "docs",
        "stage_families": ["architect-design", "execute", "closeout"],
        "discovery_policy": "conditional",
    },
    "complexity == simple AND risk == cosmetic": {
        "reference_preset": "hotfix",
        "stage_families": ["plan", "execute", "closeout"],
        "discovery_policy": "conditional",
    },
    "complexity == simple AND risk == additive": {
        "reference_preset": "deliver",
        "stage_families": ["plan", "execute", "quality-gate", "closeout"],
        "discovery_policy": "conditional",
    },
    "complexity == medium AND risk == additive AND knowledge == known-pattern": {
        "reference_preset": "deliver",
        "stage_families": ["plan", "execute", "quality-gate", "closeout"],
        "discovery_policy": "conditional",
    },
    "complexity == medium AND risk == additive": {
        "reference_preset": "refactor",
        "stage_families": [
            "architect-design",
            "plan",
            "execute",
            "quality-gate",
            "closeout",
        ],
        "discovery_policy": "conditional",
    },
    "default": {
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
}


def _parse_frontmatter(content: str) -> dict:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end_index = lines.index("---", 1)
    except ValueError:
        return {}
    return yaml.safe_load("\n".join(lines[1:end_index])) or {}


def _load_pipeline_rules() -> list[dict]:
    data = yaml.safe_load(PIPELINE_PATH.read_text(encoding="utf-8"))
    return data.get("composition_rules", {}).get("rules", [])


def _rule_matches(condition: str, classification: dict[str, str]) -> bool:
    if condition == "default":
        return True
    for clause in condition.split(" AND "):
        key, expected = [part.strip() for part in clause.split("==", 1)]
        expected = expected.strip('"').strip("'")
        if classification.get(key) != expected:
            return False
    return True


def _select_rule_for_classification(classification: dict[str, str]) -> dict:
    for rule in _load_pipeline_rules():
        if _rule_matches(rule["condition"], classification):
            return rule
    raise AssertionError("auto.pipeline.yaml must include a default routing rule")


def test_auto_router_skill_structure() -> None:
    assert SKILL_PATH.is_file(), f"Skill file not found: {SKILL_PATH}"
    content = SKILL_PATH.read_text(encoding="utf-8")

    frontmatter = _parse_frontmatter(content)
    assert frontmatter.get("name") == "auto-router"
    description = (frontmatter.get("description") or "").strip()
    assert len(description) >= 35
    assert "/auto" in description or "D23" in description

    for section in (
        "## Overview",
        "## When to Use",
        "## Shared Stage Families",
        "## Routing Rules",
        "## Bounded Replay",
    ):
        assert section in content, f"Required section '{section}' is missing"

    index = yaml.safe_load(SKILL_INDEX_PATH.read_text(encoding="utf-8")) or {}
    entries = {entry["name"]: entry for entry in index.get("skills", [])}
    assert entries["auto-router"].get("depends_on") == ["subagent-router"]
    assert len(content.splitlines()) >= 50


def test_auto_router_rule_ordering() -> None:
    content = SKILL_PATH.read_text(encoding="utf-8")
    positions: list[int] = []
    for condition in CANONICAL_CONDITIONS:
        assert condition in content
        delimited = f"`{condition}`"
        pos = content.find(delimited)
        if pos == -1:
            pos = content.index(condition)
        positions.append(pos)
    for i in range(len(positions) - 1):
        assert positions[i] < positions[i + 1]


def test_pipeline_rule_contract_matches_expected_metadata() -> None:
    rules = _load_pipeline_rules()
    by_condition = {rule["condition"]: rule for rule in rules}
    assert set(by_condition) == set(EXPECTED_RULES)
    for condition, expected in EXPECTED_RULES.items():
        rule = by_condition[condition]
        assert rule["reference_preset"] == expected["reference_preset"]
        assert rule["stage_families"] == expected["stage_families"]
        assert rule["discovery_policy"] == expected["discovery_policy"]


def test_instruction_refinement_routing_behavior() -> None:
    lightweight = _select_rule_for_classification(
        {
            "scope": "pipelines",
            "risk": "additive",
            "complexity": "simple",
            "knowledge": "instruction-refinement",
        }
    )
    assert (
        lightweight["condition"]
        == "knowledge == instruction-refinement AND complexity == simple AND risk == additive"
    )
    assert "context-recall" in lightweight["stage_families"]

    for classification in (
        {
            "scope": "pipelines",
            "risk": "additive",
            "complexity": "medium",
            "knowledge": "instruction-refinement",
        },
        {
            "scope": "pipelines",
            "risk": "cosmetic",
            "complexity": "simple",
            "knowledge": "instruction-refinement",
        },
        {
            "scope": "pipelines",
            "risk": "governance-change",
            "complexity": "simple",
            "knowledge": "instruction-refinement",
        },
        {
            "scope": "kernel",
            "risk": "additive",
            "complexity": "simple",
            "knowledge": "instruction-refinement",
        },
    ):
        selected = _select_rule_for_classification(classification)
        assert selected["condition"] != (
            "knowledge == instruction-refinement AND complexity == simple AND risk == additive"
        )
        assert selected["reference_preset"] == "full"


def test_needs_research_rule_requires_discovery() -> None:
    selected = _select_rule_for_classification(
        {
            "scope": "skills",
            "risk": "additive",
            "complexity": "medium",
            "knowledge": "needs-research",
        }
    )
    assert selected["condition"] == "knowledge == needs-research"
    assert selected["discovery_policy"] == "required"
    assert selected["stage_families"][0] == "discovery-evidence-research"


def test_auto_router_cross_file_consistency() -> None:
    skill_content = SKILL_PATH.read_text(encoding="utf-8")
    pipeline_content = PIPELINE_PATH.read_text(encoding="utf-8")

    for condition, expected in EXPECTED_RULES.items():
        assert condition in skill_content
        assert condition in pipeline_content
        marker = f"`{condition}`"
        row = next(line for line in skill_content.splitlines() if marker in line and "|" in line)
        assert expected["reference_preset"] in row
        assert expected["discovery_policy"] in row
        for family in expected["stage_families"]:
            assert family in row


def test_pipeline_uses_shared_stage_family_contract_not_legacy_keys() -> None:
    rules = _load_pipeline_rules()
    for rule in rules:
        assert "pipeline" not in rule
        assert "inject" not in rule


def test_instruction_refinement_rules_include_context_recall() -> None:
    rules = {rule["condition"]: rule for rule in _load_pipeline_rules()}
    for condition in (
        "knowledge == instruction-refinement AND complexity == simple AND risk == additive",
        "knowledge == instruction-refinement",
    ):
        rule = rules[condition]
        assert rule["discovery_policy"] == "conditional"
        assert "context-recall" in rule["stage_families"]


def test_skill_l2_evidence_review_phase_defined() -> None:
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert "l2-evidence-review" in content
    assert "M3" in content or "episodes" in content.lower()
    assert "M2" in content or "pattern" in content.lower()
    assert "before the `architect-design` stage" in content or "before architect" in content

"""Tests for skills/auto-router/SKILL.md — P3-004 (Auto-Pipeline Router).

Governance anchor: D23 — dynamic pipeline composition by the Architect.
Failure mode: if the routing skill is absent or its rules diverge from
auto.pipeline.yaml, the Architect has no canonical decision table, causing
ad-hoc pipeline selection that bypasses the governed composition_rules.

Tests use lazy reads inside each function (not module-level) so this file
can be imported before the skill is created; tests will fail until the
builder delivers the skill.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "skills" / "auto-router" / "SKILL.md"
PIPELINE_PATH = REPO_ROOT / "pipelines" / "auto.pipeline.yaml"
SKILL_INDEX_PATH = REPO_ROOT / "skills" / "index.yaml"

# Canonical condition strings in required top-to-bottom order.
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


# ── Helper ────────────────────────────────────────────────────────────────────


def _parse_frontmatter(content: str) -> dict:
    """Extract and parse YAML frontmatter between the first two '---' fences."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end_index = lines.index("---", 1)
    except ValueError:
        return {}
    frontmatter_text = "\n".join(lines[1:end_index])
    return yaml.safe_load(frontmatter_text) or {}


def _load_pipeline_rules() -> list[dict]:
    data = yaml.safe_load(PIPELINE_PATH.read_text(encoding="utf-8"))
    return data.get("composition_rules", {}).get("rules", [])


def _rule_matches(condition: str, classification: dict[str, str]) -> bool:
    """Evaluate the small D23 condition language used in auto.pipeline.yaml."""
    if condition == "default":
        return True

    for clause in condition.split(" AND "):
        key, expected = [part.strip() for part in clause.split("==", 1)]
        expected = expected.strip('"').strip("'")
        if classification.get(key) != expected:
            return False
    return True


def _select_pipeline_for_classification(classification: dict[str, str]) -> list[str]:
    """Apply first-match-wins routing semantics to auto.pipeline.yaml rules."""
    for rule in _load_pipeline_rules():
        if _rule_matches(rule["condition"], classification):
            return rule["pipeline"]
    raise AssertionError("auto.pipeline.yaml must include a default routing rule")


# ── Structure ─────────────────────────────────────────────────────────────────


def test_auto_router_skill_structure() -> None:
    """skills/auto-router/SKILL.md must exist and satisfy structural requirements."""
    assert SKILL_PATH.is_file(), (
        f"Skill file not found: {SKILL_PATH}. "
        "Builder must create skills/auto-router/SKILL.md before this test passes."
    )

    content = SKILL_PATH.read_text(encoding="utf-8")

    # Frontmatter
    frontmatter = _parse_frontmatter(content)
    assert frontmatter.get("name") == "auto-router", (
        f"Expected frontmatter name 'auto-router', got {frontmatter.get('name')!r}"
    )

    description = (frontmatter.get("description") or "").strip()
    assert len(description) >= 35, "auto-router description must be substantive (BL-015)"
    lowered = description.lower()
    assert "use this skill when" in lowered or "/auto" in lowered or "d23" in lowered, (
        "auto-router description must cite /auto or D23 (routing hook per BL-015). "
        f"Got: {description!r}"
    )

    # Required sections
    for section in ("## Overview", "## When to Use"):
        assert section in content, (
            f"Required section '{section}' is missing from skills/auto-router/SKILL.md"
        )

    index = yaml.safe_load(SKILL_INDEX_PATH.read_text(encoding="utf-8")) or {}
    entries = {entry["name"]: entry for entry in index.get("skills", [])}
    assert "auto-router" in entries, "skills/index.yaml must include auto-router"
    assert entries["auto-router"].get("depends_on") == ["subagent-router"], (
        "skills/index.yaml must record auto-router's dependency on subagent-router"
    )

    # Minimum content length
    line_count = len(content.splitlines())
    assert line_count >= 50, (
        f"skills/auto-router/SKILL.md must have at least 50 lines; found {line_count}"
    )


# ── Rule ordering ─────────────────────────────────────────────────────────────


def test_auto_router_rule_ordering() -> None:
    """All 7 canonical condition strings must appear in SKILL.md in canonical order."""
    assert SKILL_PATH.is_file(), (
        f"Skill file not found: {SKILL_PATH}. "
        "Builder must create skills/auto-router/SKILL.md before this test passes."
    )

    content = SKILL_PATH.read_text(encoding="utf-8")

    # Verify all conditions are present
    for condition in CANONICAL_CONDITIONS:
        assert condition in content, (
            f"Canonical condition {condition!r} is missing from skills/auto-router/SKILL.md"
        )

    # Verify canonical order: position of condition[i] < position of condition[i+1]
    # Use backtick-delimited form to avoid substring matching (e.g., "medium AND additive"
    # matching inside "medium AND additive AND known-pattern")
    positions = []
    for cond in CANONICAL_CONDITIONS:
        delimited = f"`{cond}`"
        pos = content.find(delimited)
        if pos == -1:
            # Fall back to undelimited (for "default" which may not be backtick-wrapped)
            pos = content.index(cond)
        positions.append(pos)
    for i in range(len(positions) - 1):
        assert positions[i] < positions[i + 1], (
            f"Rule ordering violation: "
            f"{CANONICAL_CONDITIONS[i]!r} (pos {positions[i]}) "
            f"must appear before "
            f"{CANONICAL_CONDITIONS[i + 1]!r} (pos {positions[i + 1]})"
        )


# ── Cross-file consistency ────────────────────────────────────────────────────


def test_skill_instruction_refinement_rules() -> None:
    """SKILL.md must define both lightweight and fallback instruction-refinement rules."""
    assert SKILL_PATH.is_file(), (
        f"Skill file not found: {SKILL_PATH}. "
        "Builder must create skills/auto-router/SKILL.md before this test passes."
    )

    content = SKILL_PATH.read_text(encoding="utf-8")

    lightweight_condition = (
        "knowledge == instruction-refinement AND complexity == simple AND risk == additive"
    )
    fallback_condition = "knowledge == instruction-refinement"

    assert lightweight_condition in content, (
        f"Routing table must contain lightweight condition {lightweight_condition!r}"
    )
    assert fallback_condition in content, (
        f"Routing table must contain fallback condition {fallback_condition!r}"
    )

    pos_needs_research = content.index("knowledge == needs-research")
    pos_lightweight = content.index(lightweight_condition)
    pos_fallback = content.index(fallback_condition, pos_lightweight + 1)
    pos_scope_docs = content.index("scope == docs")
    assert pos_needs_research < pos_lightweight < pos_fallback < pos_scope_docs, (
        "instruction-refinement lightweight and fallback rules must appear after "
        "needs-research and before scope == docs in that order"
    )

    lightweight_row = None
    fallback_row = None
    for line in content.splitlines():
        if lightweight_condition in line and "|" in line:
            lightweight_row = line
        elif fallback_condition in line and "|" in line:
            fallback_row = line

    assert lightweight_row is not None, "Could not find lightweight instruction-refinement row"
    assert fallback_row is not None, "Could not find fallback instruction-refinement row"
    assert "architect, planner, evaluator, builder, architect" in lightweight_row, (
        "lightweight instruction-refinement rule must use "
        "[architect, planner, evaluator, builder, architect]"
    )
    assert "architect, reviewer, planner, evaluator, builder, architect" in fallback_row, (
        "fallback instruction-refinement rule must use full pipeline "
        "[architect, reviewer, planner, evaluator, builder, architect]"
    )


def test_pipeline_instruction_refinement_rules() -> None:
    """auto.pipeline.yaml must contain both lightweight and fallback instruction-refinement rules."""
    assert PIPELINE_PATH.is_file(), f"Pipeline file not found: {PIPELINE_PATH}"

    rules = _load_pipeline_rules()
    by_condition = {rule["condition"]: rule for rule in rules}
    lightweight_condition = (
        "knowledge == instruction-refinement AND complexity == simple AND risk == additive"
    )
    fallback_condition = "knowledge == instruction-refinement"

    assert lightweight_condition in by_condition, (
        f"Missing lightweight instruction-refinement rule {lightweight_condition!r}"
    )
    assert fallback_condition in by_condition, (
        f"Missing fallback instruction-refinement rule {fallback_condition!r}"
    )

    assert by_condition[lightweight_condition]["pipeline"] == [
        "architect",
        "planner",
        "evaluator",
        "builder",
        "architect",
    ], "lightweight instruction-refinement rule pipeline mismatch"
    assert by_condition[fallback_condition]["pipeline"] == [
        "architect",
        "reviewer",
        "planner",
        "evaluator",
        "builder",
        "architect",
    ], "fallback instruction-refinement rule pipeline mismatch"


def test_instruction_refinement_routing_behavior() -> None:
    """D23 first-match semantics must prefer the lightweight lane only for the qualifying case."""
    lightweight_pipeline = ["architect", "planner", "evaluator", "builder", "architect"]
    full_pipeline = ["architect", "reviewer", "planner", "evaluator", "builder", "architect"]

    assert _select_pipeline_for_classification(
        {
            "scope": "pipelines",
            "risk": "additive",
            "complexity": "simple",
            "knowledge": "instruction-refinement",
        }
    ) == lightweight_pipeline

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
        assert _select_pipeline_for_classification(classification) == full_pipeline, (
            "non-qualifying instruction-refinement work must fall through to the "
            "existing full path or a higher-priority full rule"
        )


def test_auto_router_cross_file_consistency() -> None:
    """Every canonical condition string must appear in both SKILL.md and auto.pipeline.yaml."""
    assert SKILL_PATH.is_file(), (
        f"Skill file not found: {SKILL_PATH}. "
        "Builder must create skills/auto-router/SKILL.md before this test passes."
    )
    assert PIPELINE_PATH.is_file(), f"Pipeline file not found: {PIPELINE_PATH}"

    skill_content = SKILL_PATH.read_text(encoding="utf-8")
    pipeline_content = PIPELINE_PATH.read_text(encoding="utf-8")

    for condition in CANONICAL_CONDITIONS:
        assert condition in skill_content, (
            f"Condition {condition!r} missing from "
            f"skills/auto-router/SKILL.md — skill and pipeline are out of sync"
        )
        assert condition in pipeline_content, (
            f"Condition {condition!r} missing from "
            f"pipelines/auto.pipeline.yaml — skill and pipeline are out of sync"
        )


# ── P1-008: inject field and l2-evidence-review phase ────────────────────────


def test_pipeline_instruction_refinement_inject_fields() -> None:
    """Both instruction-refinement rules must keep the l2-evidence-review inject."""
    assert PIPELINE_PATH.is_file(), f"Pipeline file not found: {PIPELINE_PATH}"

    rules = _load_pipeline_rules()
    expected_conditions = [
        "knowledge == instruction-refinement AND complexity == simple AND risk == additive",
        "knowledge == instruction-refinement",
    ]

    for condition in expected_conditions:
        matching_rules = [r for r in rules if r.get("condition") == condition]
        assert len(matching_rules) == 1, (
            f"Expected exactly one rule with condition {condition!r}; "
            f"found {len(matching_rules)}"
        )
        inject_value = matching_rules[0].get("inject")
        assert inject_value is not None, (
            f"instruction-refinement rule {condition!r} is missing 'inject' field"
        )
        assert "l2-evidence-review" in inject_value, (
            f"inject value must reference 'l2-evidence-review'; got: {inject_value!r}"
        )
        assert "architect" in inject_value, (
            f"inject value must reference 'architect' (the target stage); got: {inject_value!r}"
        )


def test_skill_l2_evidence_review_phase_defined() -> None:
    """SKILL.md Rule 4 rationale must provide an actionable definition of l2-evidence-review.

    The definition must specify:
    - What it reads: M3 episodes (tagged instruction-refinement) from memory
    - What it loads: M2 patterns
    - Its trigger point: before planning (runs before architect produces a brief)
    """
    assert SKILL_PATH.is_file(), f"Skill file not found: {SKILL_PATH}"

    content = SKILL_PATH.read_text(encoding="utf-8")

    assert "l2-evidence-review" in content, (
        "SKILL.md must contain 'l2-evidence-review' in Rule 4 rationale"
    )
    assert "M3" in content or "episodes" in content.lower(), (
        "Rule 4 rationale must reference M3 episodes as the source of L2 evidence"
    )
    assert "M2" in content or "pattern" in content.lower(), (
        "Rule 4 rationale must reference M2 patterns"
    )
    assert (
        "before planning" in content
        or "before the architect" in content
        or "before architect" in content
    ), "Rule 4 rationale must state l2-evidence-review runs before planning begins"

    rule4_start = content.find("**Rule 4")
    rule5_start = content.find("**Rule 5")
    if rule4_start != -1 and rule5_start != -1:
        rule4_block = content[rule4_start:rule5_start]
        sentence_count = rule4_block.count(". ") + rule4_block.count(".\n")
        assert sentence_count >= 3, (
            f"Rule 4 rationale block must have at least 3 sentences (it defines a phase); "
            f"found {sentence_count}. Expand the definition."
        )


def test_pipeline_inject_field_consistency() -> None:
    """Both inject-bearing rules in auto.pipeline.yaml must have consistent inject fields.

    Verifies:
    - 'knowledge == needs-research' rule has inject referencing 'research-phase' and 'architect'
    - 'knowledge == instruction-refinement' rule has inject referencing 'l2-evidence-review'
      and 'architect'
    - The two inject values are distinct
    - Both target the 'architect' stage (architectural consistency)
    """
    assert PIPELINE_PATH.is_file(), f"Pipeline file not found: {PIPELINE_PATH}"

    data = yaml.safe_load(PIPELINE_PATH.read_text(encoding="utf-8"))
    rules = data.get("composition_rules", {}).get("rules", [])

    by_condition = {r["condition"]: r for r in rules}

    nr_rule = by_condition.get("knowledge == needs-research", {})
    assert "inject" in nr_rule, (
        "'knowledge == needs-research' rule must have inject field (regression guard)"
    )
    assert "research-phase" in nr_rule["inject"], (
        f"needs-research inject must reference 'research-phase'; got {nr_rule['inject']!r}"
    )

    lightweight_ir_rule = by_condition.get(
        "knowledge == instruction-refinement AND complexity == simple AND risk == additive", {}
    )
    fallback_ir_rule = by_condition.get("knowledge == instruction-refinement", {})

    for condition, rule in (
        (
            "knowledge == instruction-refinement AND complexity == simple AND risk == additive",
            lightweight_ir_rule,
        ),
        ("knowledge == instruction-refinement", fallback_ir_rule),
    ):
        assert "inject" in rule, f"{condition!r} rule must have inject field"
        assert "l2-evidence-review" in rule["inject"], (
            f"{condition!r} inject must reference 'l2-evidence-review'; "
            f"got {rule['inject']!r}"
        )

    assert nr_rule["inject"] != lightweight_ir_rule["inject"], (
        "needs-research and lightweight instruction-refinement inject values must be distinct"
    )
    assert nr_rule["inject"] != fallback_ir_rule["inject"], (
        "needs-research and fallback instruction-refinement inject values must be distinct"
    )
    assert (
        "architect" in nr_rule["inject"]
        and "architect" in lightweight_ir_rule["inject"]
        and "architect" in fallback_ir_rule["inject"]
    ), "All inject directives must target the 'architect' stage"

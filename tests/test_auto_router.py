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
    "knowledge == instruction-refinement AND complexity == simple AND risk == cosmetic",
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
    """Load composition rules from the auto pipeline."""
    data = yaml.safe_load(PIPELINE_PATH.read_text(encoding="utf-8"))
    return data.get("composition_rules", {}).get("rules", [])


def _rule_matches(condition: str, classification: dict[str, str]) -> bool:
    """Evaluate the limited rule syntax used by the auto router."""
    if condition == "default":
        return True

    clauses = [clause.strip() for clause in condition.split("AND")]
    for clause in clauses:
        field, expected = [part.strip() for part in clause.split("==", maxsplit=1)]
        if classification.get(field) != expected:
            return False
    return True


def _first_matching_rule(classification: dict[str, str]) -> dict:
    """Return the first composition rule that matches the given classification."""
    for rule in _load_pipeline_rules():
        if _rule_matches(rule["condition"], classification):
            return rule
    raise AssertionError(f"No matching rule found for classification: {classification!r}")


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
    """SKILL.md must document both instruction-refinement rules in order.

    Verifies:
    - A lightweight row exists for the exact low-risk qualifier
    - A fallback row exists for generic instruction-refinement
    - The lightweight row appears AFTER needs-research and BEFORE the fallback row
    - The fallback row appears BEFORE scope == docs
    """
    assert SKILL_PATH.is_file(), (
        f"Skill file not found: {SKILL_PATH}. "
        "Builder must create skills/auto-router/SKILL.md before this test passes."
    )

    content = SKILL_PATH.read_text(encoding="utf-8")

    lightweight_condition = (
        "knowledge == instruction-refinement AND complexity == simple AND risk == cosmetic"
    )
    fallback_condition = "knowledge == instruction-refinement"
    assert lightweight_condition in content, (
        f"Routing table must contain condition {lightweight_condition!r}"
    )
    assert fallback_condition in content, (
        f"Routing table must contain condition {fallback_condition!r}"
    )

    pos_needs_research = content.index("knowledge == needs-research")
    pos_lightweight = content.index(lightweight_condition)
    pos_instruction_refinement = content.index(fallback_condition, pos_lightweight + 1)
    pos_scope_docs = content.index("scope == docs")
    assert pos_needs_research < pos_lightweight < pos_instruction_refinement < pos_scope_docs, (
        "instruction-refinement rules must appear AFTER needs-research, with the lightweight "
        "rule immediately before the fallback rule and both before scope == docs"
    )

    lightweight_seen = False
    fallback_seen = False
    for line in content.splitlines():
        if lightweight_condition in line and "|" in line:
            lightweight_seen = True
            assert "planner, builder, architect" in line, (
                "Lightweight instruction-refinement rule must use pipeline "
                "[planner, builder, architect]"
            )
        if fallback_condition in line and lightweight_condition not in line and "|" in line:
            fallback_seen = True
            assert "architect, reviewer, planner, evaluator, builder, architect" in line, (
                "Fallback instruction-refinement rule must use full pipeline "
                "[architect, reviewer, planner, evaluator, builder, architect]"
            )
    assert lightweight_seen, "Could not find lightweight instruction-refinement row in SKILL.md"
    assert fallback_seen, "Could not find fallback instruction-refinement row in SKILL.md"


def test_pipeline_instruction_refinement_rules() -> None:
    """auto.pipeline.yaml must contain both instruction-refinement routing rules.

    Verifies:
    - A lightweight exact-match rule exists
    - A generic fallback rule exists
    - The lightweight rule precedes the fallback rule
    """
    assert PIPELINE_PATH.is_file(), f"Pipeline file not found: {PIPELINE_PATH}"

    rules = _load_pipeline_rules()

    lightweight_condition = (
        "knowledge == instruction-refinement AND complexity == simple AND risk == cosmetic"
    )
    fallback_condition = "knowledge == instruction-refinement"
    by_condition = {rule["condition"]: rule for rule in rules}

    assert lightweight_condition in by_condition, (
        "Expected a lightweight instruction-refinement composition rule"
    )
    assert fallback_condition in by_condition, (
        "Expected a fallback instruction-refinement composition rule"
    )

    lightweight_pipeline = ["planner", "builder", "architect"]
    assert by_condition[lightweight_condition]["pipeline"] == lightweight_pipeline, (
        f"Lightweight instruction-refinement rule pipeline mismatch.\n"
        f"  Expected: {lightweight_pipeline}\n"
        f"  Got:      {by_condition[lightweight_condition]['pipeline']}"
    )

    expected_pipeline = ["architect", "reviewer", "planner", "evaluator", "builder", "architect"]
    assert by_condition[fallback_condition]["pipeline"] == expected_pipeline, (
        f"Fallback instruction-refinement rule pipeline mismatch.\n"
        f"  Expected: {expected_pipeline}\n"
        f"  Got:      {by_condition[fallback_condition]['pipeline']}"
    )

    positions = {rule["condition"]: index for index, rule in enumerate(rules)}
    assert positions[lightweight_condition] < positions[fallback_condition], (
        "The lightweight instruction-refinement rule must be evaluated before the fallback rule"
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


def test_pipeline_instruction_refinement_fallback_inject_field() -> None:
    """The fallback instruction-refinement rule must retain its inject field.

    Verifies:
    - The fallback rule with condition 'knowledge == instruction-refinement' has an 'inject' key
    - The inject value references 'l2-evidence-review' and 'architect'
    """
    assert PIPELINE_PATH.is_file(), f"Pipeline file not found: {PIPELINE_PATH}"

    rules = _load_pipeline_rules()
    matching_rules = [
        r for r in rules if r.get("condition") == "knowledge == instruction-refinement"
    ]
    assert len(matching_rules) == 1, "Expected exactly one fallback instruction-refinement rule"
    rule = matching_rules[0]

    assert "inject" in rule, (
        "instruction-refinement rule is missing 'inject' field in auto.pipeline.yaml. "
        'Add: inject: "l2-evidence-review into architect"'
    )
    inject_value = rule["inject"]
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

    by_condition = {r["condition"]: r for r in _load_pipeline_rules()}

    nr_rule = by_condition.get("knowledge == needs-research", {})
    assert "inject" in nr_rule, (
        "'knowledge == needs-research' rule must have inject field (regression guard)"
    )
    assert "research-phase" in nr_rule["inject"], (
        f"needs-research inject must reference 'research-phase'; got {nr_rule['inject']!r}"
    )

    ir_rule = by_condition.get("knowledge == instruction-refinement", {})
    assert "inject" in ir_rule, "'knowledge == instruction-refinement' rule must have inject field"
    assert "l2-evidence-review" in ir_rule["inject"], (
        f"instruction-refinement inject must reference 'l2-evidence-review'; "
        f"got {ir_rule['inject']!r}"
    )

    assert nr_rule["inject"] != ir_rule["inject"], (
        "inject values for needs-research and instruction-refinement must be distinct"
    )
    assert "architect" in nr_rule["inject"] and "architect" in ir_rule["inject"], (
        "Both inject directives must target the 'architect' stage"
    )


def test_first_match_routes_lightweight_instruction_refinement() -> None:
    """Qualifying low-risk instruction refinement should take the lightweight lane."""
    rule = _first_matching_rule(
        {
            "scope": "skills",
            "risk": "cosmetic",
            "complexity": "simple",
            "knowledge": "instruction-refinement",
        }
    )
    assert (
        rule["condition"]
        == "knowledge == instruction-refinement AND complexity == simple AND risk == cosmetic"
    )
    assert rule["pipeline"] == ["planner", "builder", "architect"]


def test_first_match_falls_back_for_nonqualifying_instruction_refinement() -> None:
    """Instruction refinement outside the exact low-risk qualifier should use the full lane."""
    rule = _first_matching_rule(
        {
            "scope": "skills",
            "risk": "additive",
            "complexity": "simple",
            "knowledge": "instruction-refinement",
        }
    )
    assert rule["condition"] == "knowledge == instruction-refinement"
    assert rule["pipeline"] == ["architect", "reviewer", "planner", "evaluator", "builder", "architect"]


def test_governance_precedence_over_instruction_refinement() -> None:
    """Governance risk must win before any instruction-refinement routing rule."""
    rule = _first_matching_rule(
        {
            "scope": "skills",
            "risk": "governance-change",
            "complexity": "simple",
            "knowledge": "instruction-refinement",
        }
    )
    assert rule["condition"] == "risk == governance-change"
    assert rule["pipeline"] == ["architect", "reviewer", "planner", "evaluator", "builder", "architect"]


def test_kernel_precedence_over_instruction_refinement() -> None:
    """Kernel scope must win before any instruction-refinement routing rule."""
    rule = _first_matching_rule(
        {
            "scope": "kernel",
            "risk": "cosmetic",
            "complexity": "simple",
            "knowledge": "instruction-refinement",
        }
    )
    assert rule["condition"] == "scope == kernel"
    assert rule["pipeline"] == ["architect", "reviewer", "planner", "evaluator", "builder", "architect"]

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


def test_skill_instruction_refinement_rule() -> None:
    """SKILL.md must contain an instruction-refinement routing row at priority 4.

    Verifies:
    - A row with condition `knowledge == instruction-refinement` exists
    - It appears AFTER `knowledge == needs-research` and BEFORE `scope == docs`
    - Its pipeline is the full pipeline: [architect, reviewer, planner, evaluator, builder, architect]
    """
    assert SKILL_PATH.is_file(), (
        f"Skill file not found: {SKILL_PATH}. "
        "Builder must create skills/auto-router/SKILL.md before this test passes."
    )

    content = SKILL_PATH.read_text(encoding="utf-8")

    # Condition must be present
    condition = "knowledge == instruction-refinement"
    assert condition in content, (
        f"Routing table must contain condition {condition!r}"
    )

    # Ordering: after needs-research, before scope == docs
    pos_needs_research = content.index("knowledge == needs-research")
    pos_instruction_refinement = content.index("knowledge == instruction-refinement")
    pos_scope_docs = content.index("scope == docs")
    assert pos_needs_research < pos_instruction_refinement < pos_scope_docs, (
        "instruction-refinement rule must appear AFTER needs-research and BEFORE scope == docs"
    )

    # Pipeline for this rule must be full pipeline
    # Find the table row containing the condition and verify the pipeline
    for line in content.splitlines():
        if "knowledge == instruction-refinement" in line and "|" in line:
            assert "architect, reviewer, planner, evaluator, builder, architect" in line, (
                "instruction-refinement rule must use full pipeline "
                "[architect, reviewer, planner, evaluator, builder, architect]"
            )
            break
    else:
        raise AssertionError(
            "Could not find instruction-refinement as a table row in SKILL.md"
        )


def test_pipeline_instruction_refinement_rule() -> None:
    """auto.pipeline.yaml must contain a composition rule for instruction-refinement.

    Verifies:
    - A rule with condition 'knowledge == instruction-refinement' exists
    - Its pipeline list equals [architect, reviewer, planner, evaluator, builder, architect]
    """
    assert PIPELINE_PATH.is_file(), f"Pipeline file not found: {PIPELINE_PATH}"

    data = yaml.safe_load(PIPELINE_PATH.read_text(encoding="utf-8"))
    rules = data.get("composition_rules", {}).get("rules", [])

    matching_rules = [
        r for r in rules if r.get("condition") == "knowledge == instruction-refinement"
    ]
    assert len(matching_rules) == 1, (
        "Expected exactly one composition rule with condition "
        "'knowledge == instruction-refinement', "
        f"found {len(matching_rules)}"
    )

    expected_pipeline = ["architect", "reviewer", "planner", "evaluator", "builder", "architect"]
    assert matching_rules[0]["pipeline"] == expected_pipeline, (
        f"instruction-refinement rule pipeline mismatch.\n"
        f"  Expected: {expected_pipeline}\n"
        f"  Got:      {matching_rules[0]['pipeline']}"
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


def test_pipeline_instruction_refinement_inject_field() -> None:
    """auto.pipeline.yaml instruction-refinement rule must have an inject field.

    Verifies:
    - The rule with condition 'knowledge == instruction-refinement' has an 'inject' key
    - The inject value references 'l2-evidence-review' and 'architect'
    """
    assert PIPELINE_PATH.is_file(), f"Pipeline file not found: {PIPELINE_PATH}"

    data = yaml.safe_load(PIPELINE_PATH.read_text(encoding="utf-8"))
    rules = data.get("composition_rules", {}).get("rules", [])

    matching_rules = [
        r for r in rules if r.get("condition") == "knowledge == instruction-refinement"
    ]
    assert len(matching_rules) == 1, (
        "Expected exactly one rule with condition 'knowledge == instruction-refinement'"
    )
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
    ), (
        "Rule 4 rationale must state l2-evidence-review runs before planning begins"
    )

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

    ir_rule = by_condition.get("knowledge == instruction-refinement", {})
    assert "inject" in ir_rule, (
        "'knowledge == instruction-refinement' rule must have inject field"
    )
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

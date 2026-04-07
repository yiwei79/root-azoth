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

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "skills" / "auto-router" / "SKILL.md"
PIPELINE_PATH = REPO_ROOT / "pipelines" / "auto.pipeline.yaml"

# Canonical condition strings in required top-to-bottom order.
CANONICAL_CONDITIONS: list[str] = [
    "risk == governance-change",
    "scope == kernel",
    "knowledge == needs-research",
    "scope == docs",
    "complexity == simple AND risk == cosmetic",
    "complexity == simple AND risk == additive",
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

    content = SKILL_PATH.read_text()

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
    for section in ("## Overview", "## When to Use", "## Integration"):
        assert section in content, (
            f"Required section '{section}' is missing from skills/auto-router/SKILL.md"
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

    content = SKILL_PATH.read_text()

    # Verify all conditions are present
    for condition in CANONICAL_CONDITIONS:
        assert condition in content, (
            f"Canonical condition {condition!r} is missing from "
            "skills/auto-router/SKILL.md"
        )

    # Verify canonical order: position of condition[i] < position of condition[i+1]
    positions = [content.index(cond) for cond in CANONICAL_CONDITIONS]
    for i in range(len(positions) - 1):
        assert positions[i] < positions[i + 1], (
            f"Rule ordering violation: "
            f"{CANONICAL_CONDITIONS[i]!r} (pos {positions[i]}) "
            f"must appear before "
            f"{CANONICAL_CONDITIONS[i + 1]!r} (pos {positions[i + 1]})"
        )


# ── Cross-file consistency ────────────────────────────────────────────────────


def test_auto_router_cross_file_consistency() -> None:
    """Every canonical condition string must appear in both SKILL.md and auto.pipeline.yaml."""
    assert SKILL_PATH.is_file(), (
        f"Skill file not found: {SKILL_PATH}. "
        "Builder must create skills/auto-router/SKILL.md before this test passes."
    )
    assert PIPELINE_PATH.is_file(), (
        f"Pipeline file not found: {PIPELINE_PATH}"
    )

    skill_content = SKILL_PATH.read_text()
    pipeline_content = PIPELINE_PATH.read_text()

    for condition in CANONICAL_CONDITIONS:
        assert condition in skill_content, (
            f"Condition {condition!r} missing from "
            f"skills/auto-router/SKILL.md — skill and pipeline are out of sync"
        )
        assert condition in pipeline_content, (
            f"Condition {condition!r} missing from "
            f"pipelines/auto.pipeline.yaml — skill and pipeline are out of sync"
        )

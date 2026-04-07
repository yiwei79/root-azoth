"""
P3-005 / P3-006 content tests.

Validates:
- skills/stage6-rubric/SKILL.md — D44 quality rubric for structured content
- skills/context-recall/SKILL.md — D45 memory read interface
- skills/remember/SKILL.md — soft-dep note pointing to context-recall
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from a file that starts with ---."""
    if not content.startswith("---"):
        return {}
    end = content.index("---", 3)
    return yaml.safe_load(content[3:end])


class TestStage6RubricContent:
    """Verify skills/stage6-rubric/SKILL.md meets content requirements (D44)."""

    SKILL_FILE = REPO_ROOT / "skills" / "stage6-rubric" / "SKILL.md"

    def _content(self) -> str:
        return self.SKILL_FILE.read_text(encoding="utf-8")

    def test_has_governance_anchor_d44(self) -> None:
        data = parse_frontmatter(self._content())
        assert data.get("governance_anchor") == "D44", (
            "stage6-rubric frontmatter must have governance_anchor: D44"
        )

    def test_has_axis1_section(self) -> None:
        assert "Axis 1" in self._content(), "stage6-rubric must contain an 'Axis 1' section"

    def test_has_axis2_section(self) -> None:
        assert "Axis 2" in self._content(), "stage6-rubric must contain an 'Axis 2' section"

    def test_has_axis3_section(self) -> None:
        assert "Axis 3" in self._content(), "stage6-rubric must contain an 'Axis 3' section"

    def test_has_fail_conditions_section(self) -> None:
        assert "Fail Conditions" in self._content(), (
            "stage6-rubric must contain a 'Fail Conditions' section"
        )

    def test_fail_conditions_lists_five_items(self) -> None:
        content = self._content()
        # Isolate text after the Fail Conditions heading
        idx = content.index("Fail Conditions")
        section = content[idx:]
        count = sum(
            f"\n{n}." in section for n in range(1, 6)
        )
        assert count == 5, (
            f"Fail Conditions section must list exactly 5 numbered items, found {count}"
        )

    def test_axis1_requires_three_items(self) -> None:
        content = self._content()
        assert (
            "3 substantive" in content
            or "\u2265 3" in content
            or "three" in content.lower()
        ), "Axis 1 must reference a minimum of 3 substantive items"

    def test_axis2_references_decisions_index(self) -> None:
        assert "DECISIONS_INDEX" in self._content(), (
            "stage6-rubric Axis 2 must reference DECISIONS_INDEX"
        )

    def test_axis2_requires_gate_type(self) -> None:
        content = self._content()
        assert "gate type" in content.lower(), (
            "stage6-rubric must reference gate type (case-insensitive)"
        )

    def test_fail_condition_5_generic_trigger(self) -> None:
        assert "generic" in self._content(), (
            "Fail condition 5 must reference 'generic' triggers"
        )

    def test_integration_references_deliver_full(self) -> None:
        assert "deliver-full" in self._content(), (
            "stage6-rubric Integration section must reference deliver-full"
        )


class TestContextRecallContent:
    """Verify skills/context-recall/SKILL.md meets content requirements (D45)."""

    SKILL_FILE = REPO_ROOT / "skills" / "context-recall" / "SKILL.md"

    def _content(self) -> str:
        return self.SKILL_FILE.read_text(encoding="utf-8")

    def test_has_governance_anchor_d45(self) -> None:
        data = parse_frontmatter(self._content())
        assert data.get("governance_anchor") == "D45", (
            "context-recall frontmatter must have governance_anchor: D45"
        )

    def test_has_scoring_algorithm_section(self) -> None:
        assert "Scoring" in self._content(), (
            "context-recall must contain a Scoring section"
        )

    def test_scoring_formula_tag_overlap(self) -> None:
        assert "tag_overlap_count * 2" in self._content(), (
            "context-recall scoring formula must include 'tag_overlap_count * 2'"
        )

    def test_scoring_formula_recency_floor(self) -> None:
        assert "max(days_since_timestamp, 0.5)" in self._content(), (
            "context-recall scoring formula must include 'max(days_since_timestamp, 0.5)'"
        )

    def test_scoring_formula_reinforcement(self) -> None:
        assert "reinforcement_count * 0.5" in self._content(), (
            "context-recall scoring formula must include 'reinforcement_count * 0.5'"
        )

    def test_scoring_surfaces_top_candidates(self) -> None:
        content = self._content()
        assert "top 1-3" in content or "top 1\u20133" in content, (
            "context-recall must state it surfaces 'top 1-3' (or 1–3) candidates"
        )

    def test_has_output_format_section(self) -> None:
        assert "Output Format" in self._content(), (
            "context-recall must contain an 'Output Format' section"
        )

    def test_output_format_context_recall_heading(self) -> None:
        assert "## Context Recall" in self._content(), (
            "context-recall Output Format must include a '## Context Recall' heading"
        )

    def test_m2_read_authorization_note(self) -> None:
        content = self._content()
        assert "human-approved" in content and "patterns.yaml" in content, (
            "context-recall must note that M2 patterns.yaml is human-approved"
        )

    def test_m2_graceful_absence(self) -> None:
        content = self._content()
        assert "gracefully" in content or "skip" in content, (
            "context-recall must describe graceful handling when M2 file is absent"
        )

    def test_integration_references_remember(self) -> None:
        assert "remember" in self._content(), (
            "context-recall Integration section must reference the remember skill (write path)"
        )

    def test_when_to_use_survey_phase(self) -> None:
        assert "SURVEY" in self._content(), (
            "context-recall When to Use must reference the SURVEY phase"
        )

    def test_when_to_use_stage2(self) -> None:
        assert "Stage 2" in self._content(), (
            "context-recall When to Use must reference Stage 2"
        )


class TestRememberSoftDependency:
    """Verify the context-recall soft-dep note exists in skills/remember/SKILL.md."""

    REMEMBER_FILE = REPO_ROOT / "skills" / "remember" / "SKILL.md"

    def _content(self) -> str:
        return self.REMEMBER_FILE.read_text(encoding="utf-8")

    def test_remember_has_context_recall_soft_dep(self) -> None:
        assert "context-recall skill is the canonical read path" in self._content(), (
            "remember/SKILL.md must contain soft-dep note: "
            "'context-recall skill is the canonical read path'"
        )

    def test_remember_episode_surfacing_section_intact(self) -> None:
        assert "## Episode Surfacing" in self._content(), (
            "remember/SKILL.md must retain the '## Episode Surfacing' section"
        )

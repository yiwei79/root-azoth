"""
Skill drift detection tests for Azoth Phase 2.

Validates:
- All expected skills exist with SKILL.md files
- SKILL.md files have valid YAML frontmatter
- Frontmatter contains required fields (name, description)
- Skill names are consistent between directory and frontmatter
- Description contains a routing signal (legacy "Use this skill when:" or BL-015 cue)
- No unexpected skills (drift detection)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
SKILL_INDEX = SKILLS_DIR / "index.yaml"

EXPECTED_SKILLS = [
    "context-map",
    "structured-autonomy-plan",
    "agentic-eval",
    "remember",
    "prompt-engineer",
    "entropy-guard",
    "alignment-sync",
    "self-improve",
    "subagent-router",
    "auto-router",
    "stage6-rubric",
    "context-recall",
    "cursor-review-insights",
    "dynamic-full-auto",
    "orientation",
]

EXTRACTED_SKILLS = [
    "context-map",
    "structured-autonomy-plan",
    "agentic-eval",
    "remember",
    "prompt-engineer",
]

NEW_SKILLS = [
    "entropy-guard",
    "alignment-sync",
    "self-improve",
    "subagent-router",
    "auto-router",
    "stage6-rubric",
    "context-recall",
    "cursor-review-insights",
    "dynamic-full-auto",
    "orientation",
]


class TestSkillStructure:
    """Verify all expected skills exist with proper structure."""

    def test_skills_directory_exists(self) -> None:
        assert SKILLS_DIR.is_dir(), "skills/ directory must exist"

    def test_skill_index_exists(self) -> None:
        assert SKILL_INDEX.is_file(), "skills/index.yaml must exist"

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_skill_directory_exists(self, skill_name: str) -> None:
        skill_dir = SKILLS_DIR / skill_name
        assert skill_dir.is_dir(), f"skills/{skill_name}/ directory must exist"

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_skill_md_exists(self, skill_name: str) -> None:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        assert skill_md.is_file(), f"skills/{skill_name}/SKILL.md must exist"

    def test_no_unexpected_skills(self) -> None:
        """Drift detection: no skills should exist that aren't in the expected list."""
        actual_skills = sorted(
            d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")
        )
        unexpected = set(actual_skills) - set(EXPECTED_SKILLS)
        assert not unexpected, f"Unexpected skills found (drift): {unexpected}"

    def test_skill_count(self) -> None:
        actual = [d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
        assert len(actual) == len(EXPECTED_SKILLS), (
            f"Expected {len(EXPECTED_SKILLS)} skills, found {len(actual)}"
        )


class TestSkillFrontmatter:
    """Verify SKILL.md files have valid YAML frontmatter."""

    @staticmethod
    def _parse_frontmatter(skill_name: str) -> dict:
        """Extract YAML frontmatter from SKILL.md."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")

        assert content.startswith("---"), (
            f"skills/{skill_name}/SKILL.md must start with YAML frontmatter (---)"
        )

        end_idx = content.index("---", 3)
        frontmatter_str = content[3:end_idx].strip()
        return yaml.safe_load(frontmatter_str)

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_has_valid_yaml_frontmatter(self, skill_name: str) -> None:
        fm = self._parse_frontmatter(skill_name)
        assert isinstance(fm, dict), f"Frontmatter must be a YAML mapping for {skill_name}"

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_frontmatter_has_name(self, skill_name: str) -> None:
        fm = self._parse_frontmatter(skill_name)
        assert "name" in fm, f"Frontmatter missing 'name' field for {skill_name}"

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_frontmatter_has_description(self, skill_name: str) -> None:
        fm = self._parse_frontmatter(skill_name)
        assert "description" in fm, f"Frontmatter missing 'description' field for {skill_name}"

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_name_matches_directory(self, skill_name: str) -> None:
        fm = self._parse_frontmatter(skill_name)
        assert fm["name"] == skill_name, (
            f"Frontmatter name '{fm['name']}' doesn't match directory '{skill_name}'"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_description_has_routing_signal(self, skill_name: str) -> None:
        """BL-015: 1–2 sentence descriptions replace bullet 'Use this skill when:' lists."""
        fm = self._parse_frontmatter(skill_name)
        desc = (fm.get("description") or "").strip()
        assert len(desc) >= 35, f"Description for {skill_name} is too short to be substantive"
        lowered = desc.lower()
        legacy = "use this skill when" in lowered
        cue_tokens = (
            "`",
            "/",
            ".yaml",
            ".md",
            "m3",
            "m2",
            "m1",
            "pipeline",
            "stage",
            "slash",
            "entropy",
            "subagent",
            "trust contract",
            "episodes",
            "governance",
            "roadmap",
            "backlog",
            "reviewer",
            "evaluator",
            "deliver",
            "router",
            "bl-",
            "memory",
            "d23",
            "d44",
            "d45",
            "d21",
            "survey",
            "phone",
            "reflexion",
            "rubric",
            "optimizer",
            "blast",
        )
        has_cue = any(tok in lowered for tok in cue_tokens)
        assert legacy or has_cue, (
            f"Description for {skill_name} must include a concrete routing hook (BL-015)"
        )


class TestSkillContent:
    """Verify SKILL.md content quality."""

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_has_overview_section(self, skill_name: str) -> None:
        content = (SKILLS_DIR / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "## Overview" in content or "## overview" in content.lower(), (
            f"{skill_name} SKILL.md should have an Overview section"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_has_when_to_use_section(self, skill_name: str) -> None:
        content = (SKILLS_DIR / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "## When to Use" in content or "## when to use" in content.lower(), (
            f"{skill_name} SKILL.md should have a When to Use section"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
    def test_minimum_content_length(self, skill_name: str) -> None:
        content = (SKILLS_DIR / skill_name / "SKILL.md").read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) >= 50, (
            f"{skill_name} SKILL.md has {len(lines)} lines — minimum 50 expected"
        )


class TestSkillConsistency:
    """Verify skills are consistent with architecture and each other."""

    @staticmethod
    def _load_skill_index() -> dict:
        return yaml.safe_load(SKILL_INDEX.read_text(encoding="utf-8")) or {}

    def test_extracted_vs_new_count(self) -> None:
        assert len(EXTRACTED_SKILLS) == 5, "Should have 5 extracted skills"
        assert len(NEW_SKILLS) == 10, "Should have 10 new skills"
        assert len(EXTRACTED_SKILLS) + len(NEW_SKILLS) == len(EXPECTED_SKILLS)

    def test_skill_index_lists_all_expected_skills(self) -> None:
        index = self._load_skill_index()
        listed = [entry["name"] for entry in index.get("skills", [])]
        assert sorted(listed) == sorted(EXPECTED_SKILLS), (
            "skills/index.yaml must list every canonical skill exactly once"
        )

    def test_skill_index_dependencies_reference_known_skills(self) -> None:
        index = self._load_skill_index()
        known = set(EXPECTED_SKILLS)
        for entry in index.get("skills", []):
            for dependency in entry.get("depends_on", []):
                assert dependency in known, (
                    f"skills/index.yaml dependency {dependency!r} for {entry['name']!r} "
                    "must reference a known skill"
                )

    def test_architecture_references_all_skills(self) -> None:
        """CLAUDE.md should reference every skill slug (BL-013 progressive disclosure)."""
        claude_md = (REPO_ROOT / "CLAUDE.md").read_text()
        for slug in EXPECTED_SKILLS:
            assert slug in claude_md, f"CLAUDE.md must reference skill slug {slug!r}"

    def test_azoth_yaml_skill_count(self) -> None:
        """azoth.yaml should reflect correct skill count."""
        azoth_yaml = yaml.safe_load((REPO_ROOT / "azoth.yaml").read_text())
        skill_count = azoth_yaml["layers"]["mineral"]["skills"]
        assert skill_count == len(EXPECTED_SKILLS), (
            f"azoth.yaml reports {skill_count} skills, expected {len(EXPECTED_SKILLS)}"
        )

    def test_entropy_guard_references_trust_contract(self) -> None:
        """Entropy guard should reference the Trust Contract it enforces."""
        content = (SKILLS_DIR / "entropy-guard" / "SKILL.md").read_text()
        assert "Trust Contract" in content

    def test_remember_references_memory_layers(self) -> None:
        """Remember skill should reference all 3 memory layers."""
        content = (SKILLS_DIR / "remember" / "SKILL.md").read_text()
        assert "M3" in content or "episodic" in content.lower()
        assert "M2" in content or "semantic" in content.lower()
        assert "M1" in content or "procedural" in content.lower()

    def test_self_improve_references_maturity_levels(self) -> None:
        """Self-improve should reference L1/L2/L3 maturity ladder."""
        content = (SKILLS_DIR / "self-improve" / "SKILL.md").read_text()
        assert "L1" in content
        assert "L2" in content
        assert "L3" in content

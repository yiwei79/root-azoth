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
    "karpathy-principles",
]

INJECTABLE_ONLY_SKILLS = {
    "karpathy-principles",
}

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
    "karpathy-principles",
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

    def test_structured_autonomy_plan_derives_success_criteria_before_tasks(self) -> None:
        content = (SKILLS_DIR / "structured-autonomy-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        goal_idx = content.index("### 1. Goal Restatement")
        criteria_idx = content.index("### 2. Success Criteria")
        checkpoint_idx = content.index("#### Non-Goals and Deferrals Checkpoint")
        decomposition_idx = content.index("### 3. Task Decomposition")

        assert goal_idx < criteria_idx < checkpoint_idx < decomposition_idx, (
            "structured-autonomy-plan must derive falsifiable success criteria before "
            "task decomposition"
        )
        assert "falsifiable" in content[criteria_idx:decomposition_idx].lower()

    def test_structured_autonomy_plan_maps_each_success_criterion_to_validation(self) -> None:
        content = (SKILLS_DIR / "structured-autonomy-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        mapping_needles = (
            "Each success criterion MUST map to exactly one validation disposition:",
            "automated_test",
            "manual_validation",
            "human_review",
            "deferred",
            "criteria_id",
            "validation_disposition",
            "validation_ref",
        )
        for needle in mapping_needles:
            assert needle in content, f"structured-autonomy-plan missing {needle!r}"

    def test_structured_autonomy_plan_requires_non_goals_before_builder_handoff(self) -> None:
        content = (SKILLS_DIR / "structured-autonomy-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        checkpoint_idx = content.index("#### Non-Goals and Deferrals Checkpoint")
        decomposition_idx = content.index("### 3. Task Decomposition")
        handoff_idx = content.index("consumed by the test-builder and builder stages")

        assert checkpoint_idx < decomposition_idx < handoff_idx
        for needle in (
            "Before builder handoff",
            "non_goals:",
            "deferrals:",
            "linked_success_criteria",
            "The checkpoint MUST appear before task decomposition",
        ):
            assert needle in content, f"structured-autonomy-plan missing {needle!r}"

    def test_structured_autonomy_plan_template_places_non_goals_before_tasks(self) -> None:
        content = (SKILLS_DIR / "structured-autonomy-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        template = content[content.index("## Plan Template") :]

        success_criteria_idx = template.index("### Success Criteria")
        non_goals_idx = template.index("### Non-Goals and Deferrals")
        tasks_idx = template.index("### Tasks")

        assert success_criteria_idx < non_goals_idx < tasks_idx, (
            "Plan Template must put Non-Goals and Deferrals before Tasks"
        )

    def test_structured_autonomy_plan_declares_krp_and_replay_boundaries(self) -> None:
        content = (SKILLS_DIR / "structured-autonomy-plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        for needle in (
            "T-KRP-A root behavior",
            "T-KRP-B injectable skill",
            "T-KRP-C Builder posture",
            "T-KRP-D Orchestrator assumption surfacing",
            "T-KRP-E structured success criteria",
            "T-006 stable criteria for replay routing",
            "lowest legitimate corrective stage",
        ):
            assert needle in content, f"structured-autonomy-plan missing {needle!r}"


class TestSkillConsistency:
    """Verify skills are consistent with architecture and each other."""

    @staticmethod
    def _load_skill_index() -> dict:
        return yaml.safe_load(SKILL_INDEX.read_text(encoding="utf-8")) or {}

    def test_extracted_vs_new_count(self) -> None:
        assert len(EXTRACTED_SKILLS) == 5, "Should have 5 extracted skills"
        assert len(NEW_SKILLS) == 11, "Should have 11 new skills"
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
        """CLAUDE.md should reference non-injectable skill slugs (BL-013)."""
        claude_md = (REPO_ROOT / "CLAUDE.md").read_text()
        for slug in sorted(set(EXPECTED_SKILLS) - INJECTABLE_ONLY_SKILLS):
            assert slug in claude_md, f"CLAUDE.md must reference skill slug {slug!r}"

    def test_injectable_only_skills_are_not_added_to_root_architecture(self) -> None:
        """Injectable-only skills stay opt-in instead of expanding the root instruction surface."""
        claude_md = (REPO_ROOT / "CLAUDE.md").read_text()
        for slug in sorted(INJECTABLE_ONLY_SKILLS):
            assert slug not in claude_md, (
                f"Injectable-only skill {slug!r} must not be added to CLAUDE.md"
            )

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

    def test_karpathy_principles_content_contract(self) -> None:
        """T-KRP-B: injectable discipline skill must carry the scoped Karpathy contract."""
        skill_md = SKILLS_DIR / "karpathy-principles" / "SKILL.md"
        assert skill_md.is_file(), "T-KRP-B requires skills/karpathy-principles/SKILL.md"

        content = skill_md.read_text(encoding="utf-8")
        lowered = content.lower()
        fm = TestSkillFrontmatter._parse_frontmatter("karpathy-principles")

        assert fm.get("name") == "karpathy-principles"
        assert "governance_anchor" in fm, (
            "karpathy-principles frontmatter must include a governance_anchor"
        )
        for section in (
            "## Overview",
            "## When to Use",
            "## Integration",
        ):
            assert section.lower() in lowered, (
                f"karpathy-principles SKILL.md missing required section: {section}"
            )
        for principle in (
            "Think Before Coding",
            "Simplicity First",
            "Surgical Changes",
            "Goal-Driven Execution",
        ):
            assert principle.lower() in lowered, (
                f"karpathy-principles SKILL.md missing principle: {principle}"
            )
        for phrase in (
            "stage6-rubric",
            "usage pattern",
            "T-KRP-C",
            "T-KRP-D",
            "T-KRP-E",
        ):
            assert phrase.lower() in lowered, (
                f"karpathy-principles SKILL.md missing T-KRP-B contract phrase: {phrase}"
            )


class TestP1007RecallGovernance:
    """Guard the planned recall-governance doc updates for P1-007."""

    ROADMAP_SPEC = REPO_ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "P1-007.yaml"
    EXPECTED_SCOPE = [
        "skills/context-recall/SKILL.md",
        "skills/remember/SKILL.md",
        ".azoth/roadmap-specs/v0.2.0/P1-007.yaml",
        "tests/test_skills.py",
    ]

    @staticmethod
    def _read_skill(skill_name: str) -> str:
        return (SKILLS_DIR / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()

    @classmethod
    def _load_spec(cls) -> dict:
        spec = yaml.safe_load(cls.ROADMAP_SPEC.read_text(encoding="utf-8"))
        assert isinstance(spec, dict), "P1-007 roadmap spec must remain a YAML mapping"
        return spec

    @classmethod
    def _load_acceptance(cls) -> str:
        spec = cls._load_spec()
        acceptance = spec.get("acceptance", [])
        assert isinstance(acceptance, list), "P1-007 acceptance criteria must remain a YAML list"
        normalized: list[str] = []
        for item in acceptance:
            if isinstance(item, str):
                normalized.append(item)
                continue
            assert isinstance(item, dict), "P1-007 acceptance items must be strings or mappings"
            normalized.extend(
                f"{key} {value}" if value is not None else str(key) for key, value in item.items()
            )
        return " ".join(normalized).lower()

    def test_p1007_scope_matches_approved_four_file_slice(self) -> None:
        spec = self._load_spec()
        assert spec.get("scope") == self.EXPECTED_SCOPE, (
            "P1-007 scope must stay aligned to the approved four-file slice"
        )

    def test_p1007_delivery_uses_governed_m1_metadata(self) -> None:
        delivery = self._load_spec().get("delivery")
        assert isinstance(delivery, dict), "P1-007 delivery metadata must remain a YAML mapping"
        assert delivery == {
            "target_layer": "M1",
            "delivery_pipeline": "governed",
            "suggested_command": "/deliver-full",
        }, "P1-007 delivery metadata must use governed M1 /deliver-full"

    def test_context_recall_documents_tag_guidance_and_episode_conflicts(self) -> None:
        content = self._read_skill("context-recall")
        assert "tag vocabulary" in content, (
            "P1-007 requires context-recall to document tag vocabulary guidance"
        )
        assert "contradiction" in content, (
            "P1-007 requires context-recall to explain contradiction handling"
        )
        assert "stale" in content, "P1-007 requires context-recall to address stale episodes"
        assert "archive" in content and "supersede" in content, (
            "P1-007 requires an explicit archive-vs-supersede policy for recalled episodes"
        )

    def test_remember_documents_when_not_to_add_a_pattern(self) -> None:
        content = self._read_skill("remember")
        assert "when not to add a pattern" in content, (
            "P1-007 requires remember to document when not to add a pattern"
        )

    def test_remember_documents_append_only_supersession_rules(self) -> None:
        content = self._read_skill("remember")
        assert "append-only" in content, (
            "P1-007 requires remember to keep append-only episode guidance explicit"
        )
        assert "new episode linked to the older one" in content, (
            "P1-007 requires contradictions to create a new episode linked to the older one"
        )
        for phrase in ("stale", "superseded", "contradicted"):
            assert phrase in content, (
                f"P1-007 requires remember to define the {phrase!r} status-tag guidance"
            )

    def test_p1007_acceptance_language_is_reflected_in_skill_docs(self) -> None:
        acceptance = self._load_acceptance()
        assert "tag vocabulary guidance" in acceptance
        assert "when not to add a pattern" in acceptance
        assert "archive vs supersede tags" in acceptance
        assert "append-only supersession guidance" in acceptance
        assert "new episode linked to the older one" in acceptance
        assert "stale" in acceptance and "superseded" in acceptance and "contradicted" in acceptance

        combined = "\n".join([self._read_skill("context-recall"), self._read_skill("remember")])
        for phrase in (
            "tag vocabulary",
            "when not to add a pattern",
            "append-only",
            "new episode linked to the older one",
            "contradiction",
            "stale",
            "archive",
            "supersede",
            "superseded",
            "contradicted",
        ):
            assert phrase in combined, f"P1-007 doc set is missing acceptance phrase: {phrase}"

"""
Agent archetype drift detection tests for Azoth Phase 3.

Validates:
- All expected agents exist with .agent.md files
- .agent.md files have valid YAML frontmatter
- Frontmatter contains required fields (name, tier, role, skills, posture, pipeline_stages)
- Agent names are consistent between directory and frontmatter
- Tier directories follow tier{N}-{name} convention
- Posture field contains all three sub-keys (always_do, ask_first, never_auto)
- No unexpected agents (drift detection)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "agents"

TIER_DIRS = {
    "tier1-core": 1,
    "tier2-research": 2,
    "tier3-meta": 3,
    "tier4-utility": 4,
}

EXPECTED_AGENTS: dict[str, str] = {
    # agent_name -> tier_dir
    "architect": "tier1-core",
    "planner": "tier1-core",
    "builder": "tier1-core",
    "reviewer": "tier1-core",
    "researcher": "tier2-research",
    "research-orchestrator": "tier2-research",
    "prompt-engineer": "tier3-meta",
    "evaluator": "tier3-meta",
    "agent-crafter": "tier3-meta",
    "orchestrator": "tier1-core",
    "context-architect": "tier4-utility",
}

REQUIRED_FRONTMATTER_FIELDS = [
    "name",
    "tier",
    "tier_name",
    "role",
    "skills",
    "tools",
    "posture",
    "pipeline_stages",
    "trust_level",
]

POSTURE_SUBKEYS = ["always_do", "ask_first", "never_auto"]

REQUIRED_SECTIONS = [
    "## Constraints",
]

BUILDER_POSTURE_MARKERS = [
    "State the approved goal, owned surfaces, expected changed files, and out-of-scope surfaces before editing.",
    "Prefer existing repo helpers, patterns, and generated-source flows before adding new abstractions.",
    "Avoid drive-by cleanup; preserve unrelated dirty state; keep every changed line traceable to the approved scope.",
    "Choose the narrowest meaningful verification first, then run the relevant tests or parity checks.",
    "Final reports must name changed paths, goal mapping, validation commands and outcomes, residual risk, and deferred adjacent work.",
]


def _agent_path(agent_name: str) -> Path:
    """Return the path to an agent's .agent.md file."""
    tier_dir = EXPECTED_AGENTS[agent_name]
    return AGENTS_DIR / tier_dir / f"{agent_name}.agent.md"


def _parse_frontmatter(agent_name: str) -> dict:
    """Extract YAML frontmatter from .agent.md."""
    path = _agent_path(agent_name)
    content = path.read_text(encoding="utf-8")

    assert content.startswith("---"), (
        f"agents/{EXPECTED_AGENTS[agent_name]}/{agent_name}.agent.md "
        f"must start with YAML frontmatter (---)"
    )

    end_idx = content.index("---", 3)
    frontmatter_str = content[3:end_idx].strip()
    return yaml.safe_load(frontmatter_str)


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------


class TestAgentStructure:
    """Verify all expected agents exist with proper directory structure."""

    def test_agents_directory_exists(self) -> None:
        assert AGENTS_DIR.is_dir(), "agents/ directory must exist"

    @pytest.mark.parametrize("tier_dir", TIER_DIRS.keys())
    def test_tier_directory_exists(self, tier_dir: str) -> None:
        assert (AGENTS_DIR / tier_dir).is_dir(), f"agents/{tier_dir}/ directory must exist"

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_agent_md_exists(self, agent_name: str) -> None:
        path = _agent_path(agent_name)
        assert path.is_file(), (
            f"agents/{EXPECTED_AGENTS[agent_name]}/{agent_name}.agent.md must exist"
        )

    def test_no_unexpected_agents(self) -> None:
        """Drift detection: no agents should exist that aren't in the expected list."""
        actual_agents: list[str] = []
        for tier_dir in TIER_DIRS:
            tier_path = AGENTS_DIR / tier_dir
            if tier_path.is_dir():
                actual_agents.extend(
                    f.name.removesuffix(".agent.md")
                    for f in tier_path.iterdir()
                    if f.is_file() and f.name.endswith(".agent.md")
                )
        unexpected = set(actual_agents) - set(EXPECTED_AGENTS.keys())
        assert not unexpected, f"Unexpected agents found (drift): {unexpected}"

    def test_no_unexpected_tier_dirs(self) -> None:
        """Drift detection: no tier directories should exist that aren't expected."""
        actual_dirs = sorted(
            d.name for d in AGENTS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")
        )
        unexpected = set(actual_dirs) - set(TIER_DIRS.keys())
        assert not unexpected, f"Unexpected tier directories found (drift): {unexpected}"

    def test_agent_count(self) -> None:
        count = 0
        for tier_dir in TIER_DIRS:
            tier_path = AGENTS_DIR / tier_dir
            if tier_path.is_dir():
                count += sum(1 for f in tier_path.iterdir() if f.name.endswith(".agent.md"))
        assert count == len(EXPECTED_AGENTS), (
            f"Expected {len(EXPECTED_AGENTS)} agents, found {count}"
        )

    def test_tier_agent_counts(self) -> None:
        """Each tier should have the expected number of agents."""
        expected_per_tier = {
            "tier1-core": 5,
            "tier2-research": 2,
            "tier3-meta": 3,
            "tier4-utility": 1,
        }
        for tier_dir, expected_count in expected_per_tier.items():
            tier_path = AGENTS_DIR / tier_dir
            actual = sum(1 for f in tier_path.iterdir() if f.name.endswith(".agent.md"))
            assert actual == expected_count, (
                f"{tier_dir} should have {expected_count} agents, found {actual}"
            )


# ---------------------------------------------------------------------------
# Frontmatter tests
# ---------------------------------------------------------------------------


class TestAgentFrontmatter:
    """Verify .agent.md files have valid YAML frontmatter with required fields."""

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_has_valid_yaml_frontmatter(self, agent_name: str) -> None:
        fm = _parse_frontmatter(agent_name)
        assert isinstance(fm, dict), f"Frontmatter must be a YAML mapping for {agent_name}"

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_frontmatter_has_required_fields(self, agent_name: str) -> None:
        fm = _parse_frontmatter(agent_name)
        for field in REQUIRED_FRONTMATTER_FIELDS:
            assert field in fm, f"Frontmatter missing '{field}' field for {agent_name}"

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_name_matches_filename(self, agent_name: str) -> None:
        fm = _parse_frontmatter(agent_name)
        assert fm["name"] == agent_name, (
            f"Frontmatter name '{fm['name']}' doesn't match filename '{agent_name}'"
        )

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_tier_matches_directory(self, agent_name: str) -> None:
        fm = _parse_frontmatter(agent_name)
        tier_dir = EXPECTED_AGENTS[agent_name]
        expected_tier = TIER_DIRS[tier_dir]
        assert fm["tier"] == expected_tier, (
            f"Agent {agent_name} has tier {fm['tier']} but lives in {tier_dir} (expected {expected_tier})"
        )

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_tier_name_matches_directory(self, agent_name: str) -> None:
        fm = _parse_frontmatter(agent_name)
        tier_dir = EXPECTED_AGENTS[agent_name]
        expected_name = tier_dir.split("-", 1)[1]  # "tier1-core" -> "core"
        assert fm["tier_name"] == expected_name, (
            f"Agent {agent_name} has tier_name '{fm['tier_name']}' but expected '{expected_name}'"
        )

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_posture_has_required_subkeys(self, agent_name: str) -> None:
        fm = _parse_frontmatter(agent_name)
        posture = fm.get("posture", {})
        assert isinstance(posture, dict), f"posture must be a mapping for {agent_name}"
        for key in POSTURE_SUBKEYS:
            assert key in posture, f"posture missing '{key}' for {agent_name}"

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_skills_is_list(self, agent_name: str) -> None:
        fm = _parse_frontmatter(agent_name)
        assert isinstance(fm["skills"], list), f"skills must be a list for {agent_name}"

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_trust_level_is_valid(self, agent_name: str) -> None:
        fm = _parse_frontmatter(agent_name)
        assert fm["trust_level"] in ("high", "medium", "low"), (
            f"trust_level must be high/medium/low for {agent_name}, got '{fm['trust_level']}'"
        )


# ---------------------------------------------------------------------------
# Content tests
# ---------------------------------------------------------------------------


class TestAgentContent:
    """Verify .agent.md content has required sections."""

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_has_required_sections(self, agent_name: str) -> None:
        content = _agent_path(agent_name).read_text(encoding="utf-8")
        for section in REQUIRED_SECTIONS:
            assert section in content, f"{agent_name}.agent.md missing '{section}' section"

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_has_sufficient_sections(self, agent_name: str) -> None:
        """Enriched agents must have at least 3 h2 sections in the body."""
        content = _agent_path(agent_name).read_text(encoding="utf-8")
        # Count ## headings after frontmatter
        end_idx = content.index("---", 3)
        body = content[end_idx + 3 :]
        h2_count = sum(1 for line in body.split("\n") if line.startswith("## "))
        assert h2_count >= 3, (
            f"{agent_name}.agent.md has {h2_count} h2 sections — minimum 3 expected"
        )

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS.keys())
    def test_minimum_content_length(self, agent_name: str) -> None:
        content = _agent_path(agent_name).read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) >= 60, (
            f"{agent_name}.agent.md has {len(lines)} lines — minimum 60 expected for enriched agents"
        )

    def test_builder_enforces_surgical_simplicity_posture(self) -> None:
        content = _agent_path("builder").read_text(encoding="utf-8")
        for marker in BUILDER_POSTURE_MARKERS:
            assert marker in content, f"builder.agent.md missing posture marker: {marker}"


# ---------------------------------------------------------------------------
# Cross-reference tests
# ---------------------------------------------------------------------------


class TestAgentConsistency:
    """Verify agents are consistent with architecture and skills."""

    def test_all_skill_references_are_valid(self) -> None:
        """Every skill referenced by an agent must exist in skills/."""
        skills_dir = REPO_ROOT / "skills"
        existing_skills = {
            d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        }
        for agent_name in EXPECTED_AGENTS:
            fm = _parse_frontmatter(agent_name)
            for skill in fm["skills"]:
                assert skill in existing_skills, (
                    f"Agent {agent_name} references skill '{skill}' which doesn't exist in skills/"
                )

    def test_core_agents_reference_pipeline_stages(self) -> None:
        """T1 core agents should reference at least one pipeline stage."""
        for agent_name in ["architect", "planner", "builder", "reviewer"]:
            fm = _parse_frontmatter(agent_name)
            assert len(fm["pipeline_stages"]) > 0, (
                f"Core agent {agent_name} must reference at least one pipeline stage"
            )


# ---------------------------------------------------------------------------
# Agent Crafter (P6-001) — meta-loop contract markers
# ---------------------------------------------------------------------------


class TestAgentCrafterMetaLoop:
    """P6-001: governed meta-recursive loop is documented and machine-checkable."""

    def test_agent_crafter_pipeline_stages_non_empty(self) -> None:
        fm = _parse_frontmatter("agent-crafter")
        ps = fm["pipeline_stages"]
        assert isinstance(ps, list) and len(ps) >= 1, (
            "agent-crafter must list at least one pipeline_stages slug"
        )
        assert all(isinstance(s, str) and s.strip() for s in ps), (
            "pipeline_stages must be non-empty strings"
        )

    def test_agent_crafter_meta_loop_markers(self) -> None:
        content = _agent_path("agent-crafter").read_text(encoding="utf-8")
        end_idx = content.index("---", 3)
        body = content[end_idx + 3 :]
        markers = [
            "prior_stage_summaries",
            "evaluator",
            "prompt-engineer",
            "reviewer",
            "governed",
            "waiver",
            "Human",
            "Task",
        ]
        missing = [m for m in markers if m not in body]
        assert not missing, f"agent-crafter body missing required meta-loop markers: {missing}"

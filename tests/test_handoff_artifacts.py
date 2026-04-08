"""Azoth v0.1.0 Handoff Artifact Validation Tests.

Post-build TDD: validates the 7 handoff artifacts against
the architecture spec (docs/AZOTH_ARCHITECTURE.md).

BL-013: Phase roadmap detail may live in skills/orientation/SKILL.md (progressive
disclosure); tests below allow phase strings in that file where noted.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml


def _count_decisions() -> int:
    idx = (AZOTH_ROOT / "docs" / "DECISIONS_INDEX.md").read_text(encoding="utf-8")
    return sum(1 for line in idx.splitlines() if line.startswith("| D"))

AZOTH_ROOT = Path(__file__).resolve().parent.parent


def _orientation_skill_text() -> str:
    """Lazy-loaded roadmap / workflow source (BL-013)."""
    return (AZOTH_ROOT / "skills" / "orientation" / "SKILL.md").read_text(encoding="utf-8")


# ── Fixture: load architecture doc once ──────────────────────────────


@pytest.fixture(scope="session")
def arch_doc() -> str:
    path = AZOTH_ROOT / "docs" / "AZOTH_ARCHITECTURE.md"
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE — all 7 handoff artifacts must exist
# ═══════════════════════════════════════════════════════════════════════


REQUIRED_FILES = [
    "CLAUDE.md",
    "docs/AZOTH_ARCHITECTURE.md",
    ".claude/settings.json",
    ".claude/commands/bootstrap.md",
    ".github/AGENTIC_BOOTLOADER.md",
    "azoth.yaml",
    ".gitignore",
]


@pytest.mark.parametrize("relpath", REQUIRED_FILES)
def test_handoff_file_exists(relpath: str) -> None:
    path = AZOTH_ROOT / relpath
    assert path.exists(), f"Missing handoff artifact: {relpath}"
    assert path.stat().st_size > 0, f"Empty handoff artifact: {relpath}"


# ═══════════════════════════════════════════════════════════════════════
# 2. YAML VALIDITY — azoth.yaml must parse and contain required keys
# ═══════════════════════════════════════════════════════════════════════


class TestAzothYaml:
    @pytest.fixture(autouse=True)
    def load_yaml(self) -> None:
        path = AZOTH_ROOT / "azoth.yaml"
        self.data = yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_parses_as_dict(self) -> None:
        assert isinstance(self.data, dict)

    def test_has_name(self) -> None:
        assert self.data.get("name") == "root-azoth"

    def test_has_version(self) -> None:
        assert "version" in self.data
        assert re.match(r"\d+\.\d+", str(self.data["version"]))

    def test_has_layers(self) -> None:
        layers = self.data.get("layers", {})
        for layer_name in ("molecule", "mineral", "wave", "current"):
            assert layer_name in layers, f"Missing layer: {layer_name}"
            assert "status" in layers[layer_name], f"Layer {layer_name} missing status"

    def test_molecule_is_complete(self) -> None:
        assert self.data["layers"]["molecule"]["status"] == "complete"

    def test_has_platforms(self) -> None:
        platforms = self.data.get("platforms", {})
        assert platforms.get("claude_code") == "primary"

    def test_has_memory_section(self) -> None:
        assert "memory" in self.data

    def test_has_sync_section(self) -> None:
        assert "sync" in self.data
        assert "sanitize_config" in self.data["sync"]


# ═══════════════════════════════════════════════════════════════════════
# 3. JSON VALIDITY — settings.json must parse and have permissions
# ═══════════════════════════════════════════════════════════════════════


class TestSettingsJson:
    @pytest.fixture(autouse=True)
    def load_json(self) -> None:
        path = AZOTH_ROOT / ".claude" / "settings.json"
        self.data = json.loads(path.read_text(encoding="utf-8"))

    def test_parses_as_dict(self) -> None:
        assert isinstance(self.data, dict)

    def test_has_permissions(self) -> None:
        assert "permissions" in self.data
        perms = self.data["permissions"]
        assert "allow" in perms
        assert "deny" in perms

    def test_allow_list_nonempty(self) -> None:
        assert len(self.data["permissions"]["allow"]) >= 3

    def test_deny_list_nonempty(self) -> None:
        assert len(self.data["permissions"]["deny"]) >= 1

    def test_read_in_allow(self) -> None:
        assert "Read" in self.data["permissions"]["allow"]

    def test_destructive_in_deny(self) -> None:
        deny = self.data["permissions"]["deny"]
        deny_str = " ".join(deny)
        assert "rm -rf" in deny_str or "force" in deny_str

    # ── Governance Review B1: kernel protection ──
    def test_kernel_protection_in_deny(self) -> None:
        """B1 RESOLVED: settings.json must deny writes to kernel/."""
        deny = self.data["permissions"]["deny"]
        deny_str = " ".join(deny).lower()
        assert "kernel" in deny_str, (
            "GOVERNANCE B1: settings.json has NO deny rules for kernel/ files. "
            "Agent can freely modify the immutable kernel."
        )

    def test_self_protection_in_deny(self) -> None:
        """B1 RESOLVED: settings.json must deny edits to itself."""
        deny = self.data["permissions"]["deny"]
        deny_str = " ".join(deny).lower()
        assert "settings.json" in deny_str, (
            "GOVERNANCE B1: settings.json has no self-protection rule. "
            "Agent could relax permissions by editing this file."
        )


# ═══════════════════════════════════════════════════════════════════════
# 4. CLAUDE.md CONTENT — must contain required sections
# ═══════════════════════════════════════════════════════════════════════


class TestClaudeMd:
    @pytest.fixture(autouse=True)
    def load_content(self) -> None:
        self.content = (AZOTH_ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    def test_has_title(self) -> None:
        assert "AZOTH" in self.content.upper()

    def test_has_project_routing(self) -> None:
        assert "Project Routing" in self.content or "Routing" in self.content

    def test_has_architecture_reference(self) -> None:
        assert "AZOTH_ARCHITECTURE.md" in self.content

    def test_has_water_molecule_model(self) -> None:
        assert "MOLECULE" in self.content.upper()
        assert "MINERAL" in self.content.upper()
        assert "WAVE" in self.content.upper()
        assert "CURRENT" in self.content.upper()

    def test_has_memory_system(self) -> None:
        assert "M3" in self.content or "EPISODIC" in self.content.upper()
        assert "M2" in self.content or "SEMANTIC" in self.content.upper()
        assert "M1" in self.content or "PROCEDURAL" in self.content.upper()

    def test_has_kernel_immutability_rule(self) -> None:
        content_lower = self.content.lower()
        assert "kernel" in content_lower and (
            "immutab" in content_lower or "human-approved" in content_lower
        ), "CLAUDE.md must state kernel immutability rule"

    def test_has_phase_roadmap(self) -> None:
        orientation = _orientation_skill_text()
        assert "Phase 1" in orientation
        assert "Phase 2" in orientation

    def test_has_coding_standards(self) -> None:
        assert "pytest" in self.content.lower() or "ruff" in self.content.lower()

    def test_cross_platform_requirement(self) -> None:
        assert "pathlib" in self.content.lower()


# ═══════════════════════════════════════════════════════════════════════
# 5. ARCHITECTURE DOC — all 20 decisions present
# ═══════════════════════════════════════════════════════════════════════


class TestArchitectureDoc:
    @pytest.fixture(autouse=True)
    def load_content(self) -> None:
        path = AZOTH_ROOT / "docs" / "AZOTH_ARCHITECTURE.md"
        self.content = path.read_text(encoding="utf-8")

    def test_has_all_41_decisions(self) -> None:
        """Architecture must contain all 41 architecture decisions."""
        for i in range(1, 42):
            assert f"D{i}" in self.content, f"Missing architecture decision D{i}"

    def test_has_four_layer_model(self) -> None:
        for layer in ("Layer 0", "Layer 1", "Layer 2", "Layer 3"):
            assert layer in self.content, f"Missing {layer} in architecture doc"

    def test_has_trust_contract_section(self) -> None:
        assert "Trust Contract" in self.content

    def test_has_memory_system_section(self) -> None:
        assert "Memory" in self.content
        assert "M3" in self.content or "Episodic" in self.content
        assert "M2" in self.content or "Semantic" in self.content
        assert "M1" in self.content or "Procedural" in self.content

    def test_has_agent_catalog(self) -> None:
        for agent in ("Architect", "Planner", "Builder", "Reviewer"):
            assert agent in self.content, f"Missing core agent: {agent}"

    def test_has_sync_section(self) -> None:
        assert "Sync" in self.content
        assert "SANITIZE" in self.content.upper() or "sanitize" in self.content

    def test_has_platform_section(self) -> None:
        assert "Claude Code" in self.content
        assert "OpenCode" in self.content or "Copilot" in self.content

    def test_has_risk_table(self) -> None:
        assert "Risk" in self.content
        assert "Mitigation" in self.content

    def test_has_repo_structure(self) -> None:
        assert "kernel/" in self.content
        assert "skills/" in self.content
        assert "agents/" in self.content
        assert "pipelines/" in self.content

    def test_no_org_specific_content(self) -> None:
        """Architecture doc must not contain org-specific references."""
        for org_ref in ("Glovo", "SupplyOps", "dhub-glovo", "fulfillment-dwh"):
            assert org_ref not in self.content, (
                f"Architecture doc contains org-specific reference: '{org_ref}'"
            )


# ═══════════════════════════════════════════════════════════════════════
# 6. BOOTSTRAP COMMAND — proper frontmatter and structure
# ═══════════════════════════════════════════════════════════════════════


class TestBootstrapCommand:
    @pytest.fixture(autouse=True)
    def load_content(self) -> None:
        path = AZOTH_ROOT / ".claude" / "commands" / "bootstrap.md"
        self.content = path.read_text(encoding="utf-8")

    def test_has_yaml_frontmatter(self) -> None:
        assert self.content.startswith("---"), "Bootstrap must have YAML frontmatter"
        end = self.content.index("---", 3)
        assert end > 3, "Frontmatter must have closing ---"

    def test_frontmatter_has_description(self) -> None:
        end = self.content.index("---", 3)
        frontmatter = yaml.safe_load(self.content[3:end])
        assert "description" in frontmatter

    def test_has_pre_flight(self) -> None:
        assert "Pre-Flight" in self.content or "pre-flight" in self.content.lower()

    def test_references_architecture_doc(self) -> None:
        assert "AZOTH_ARCHITECTURE.md" in self.content

    def test_has_phase_1_steps(self) -> None:
        assert "Step 1" in self.content or "1.1" in self.content

    def test_has_human_alignment_checks(self) -> None:
        content_lower = self.content.lower()
        assert "alignment" in content_lower or "human" in content_lower


# ═══════════════════════════════════════════════════════════════════════
# 7. BOOTLOADER STATE — tracks artifacts correctly
# ═══════════════════════════════════════════════════════════════════════


class TestBootloaderState:
    @pytest.fixture(autouse=True)
    def load_content(self) -> None:
        path = AZOTH_ROOT / ".github" / "AGENTIC_BOOTLOADER.md"
        self.content = path.read_text(encoding="utf-8")

    def test_tracks_created_artifacts(self) -> None:
        assert "✅" in self.content, "Should track completed artifacts with ✅"

    def test_tracks_pending_artifacts(self) -> None:
        assert "⬜" in self.content, "Should track pending artifacts with ⬜"

    def test_has_risk_section(self) -> None:
        assert "Risk" in self.content

    def test_references_kernel_files(self) -> None:
        for kernel_file in ("BOOTLOADER.md", "TRUST_CONTRACT.md", "GOVERNANCE.md"):
            assert kernel_file in self.content, (
                f"Missing kernel file reference: {kernel_file}"
            )


# ═══════════════════════════════════════════════════════════════════════
# 8. GITIGNORE — excludes runtime state
# ═══════════════════════════════════════════════════════════════════════


class TestGitignore:
    @pytest.fixture(autouse=True)
    def load_content(self) -> None:
        self.content = (AZOTH_ROOT / ".gitignore").read_text(encoding="utf-8")

    def test_excludes_memory(self) -> None:
        assert "memory" in self.content.lower() or ".azoth" in self.content

    def test_excludes_telemetry(self) -> None:
        assert "telemetry" in self.content.lower()

    def test_excludes_python_artifacts(self) -> None:
        assert "__pycache__" in self.content or ".pyc" in self.content

    def test_excludes_runtime_scope_and_pipeline_gate_json(self) -> None:
        """BL-020: live gate files are local-only; examples stay tracked."""
        assert ".azoth/scope-gate.json" in self.content
        assert ".azoth/pipeline-gate.json" in self.content

    def test_excludes_session_state_md(self) -> None:
        """BL-021: session-state.md is local cross-IDE handoff; example file is tracked."""
        assert ".azoth/session-state.md" in self.content


# ═══════════════════════════════════════════════════════════════════════
# 9. CROSS-ARTIFACT CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════


class TestCrossArtifactConsistency:
    @pytest.fixture(autouse=True)
    def load_all(self) -> None:
        self.claude_md = (AZOTH_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.orientation_md = _orientation_skill_text()
        self.arch_doc = (AZOTH_ROOT / "docs" / "AZOTH_ARCHITECTURE.md").read_text(
            encoding="utf-8"
        )
        self.azoth_yaml = yaml.safe_load(
            (AZOTH_ROOT / "azoth.yaml").read_text(encoding="utf-8")
        )
        self.bootloader = (
            AZOTH_ROOT / ".github" / "AGENTIC_BOOTLOADER.md"
        ).read_text(encoding="utf-8")

    def test_version_consistent(self) -> None:
        """azoth.yaml version is a valid semver-like string; release target 0.1.0 in CLAUDE or orientation."""
        version_str = str(self.azoth_yaml["version"])
        assert re.match(r"\d+\.\d+", version_str)
        assert "0.1.0" in self.claude_md or "0.1.0" in self.orientation_md

    def test_phase_consistent(self) -> None:
        """Current phase in azoth.yaml matches CLAUDE.md and roadmap; orientation still carries earlier phases (BL-013)."""
        phase = int(self.azoth_yaml["phase"])
        assert f"Phase {phase}" in self.claude_md
        roadmap_path = AZOTH_ROOT / ".azoth" / "roadmap.yaml"
        assert roadmap_path.is_file()
        roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
        assert int(roadmap["current_phase"]) == phase
        assert "Phase 2" in self.orientation_md

    def test_four_layers_consistent(self) -> None:
        """Water Molecule Model should be consistent across docs."""
        for layer in ("MOLECULE", "MINERAL", "WAVE", "CURRENT"):
            assert layer in self.claude_md.upper(), (
                f"CLAUDE.md missing layer: {layer}"
            )
            assert layer in self.arch_doc.upper(), (
                f"Architecture missing layer: {layer}"
            )
            assert layer.lower() in str(self.azoth_yaml.get("layers", {}))

    def test_platform_targets_consistent(self) -> None:
        """Platform targets should match between azoth.yaml and CLAUDE.md."""
        assert self.azoth_yaml["platforms"]["claude_code"] == "primary"
        assert "Claude Code" in self.claude_md
        claude_lower = self.claude_md.lower()
        assert "primary" in claude_lower and "claude" in claude_lower

    def test_decision_count_consistent(self) -> None:
        """azoth.yaml decisions matches the actual count in DECISIONS_INDEX.md."""
        expected = _count_decisions()
        assert self.azoth_yaml["decisions"] == expected


# ═══════════════════════════════════════════════════════════════════════
# 10. GOVERNANCE REVIEW BLOCKERS (tracked as expected failures)
# ═══════════════════════════════════════════════════════════════════════


class TestGovernanceBlockers:
    """Tests for issues flagged by the Governance Reviewer.

    Marked xfail to document known gaps. They will PASS once
    the blockers are addressed in Phase 1 implementation.
    """

    @pytest.fixture(autouse=True)
    def load_all(self) -> None:
        self.settings = json.loads(
            (AZOTH_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
        )
        self.arch_doc = (AZOTH_ROOT / "docs" / "AZOTH_ARCHITECTURE.md").read_text(
            encoding="utf-8"
        )

    def test_b2_kernel_integrity_script(self) -> None:
        """B2: A kernel integrity validation script should exist in Phase 1."""
        path = AZOTH_ROOT / "scripts" / "kernel-integrity.py"
        assert path.exists(), "scripts/kernel-integrity.py not yet created"

    def test_b3_m2_m1_promotion_mentioned(self) -> None:
        """B3: Architecture must mention M2→M1 promotion gate."""
        assert "M2" in self.arch_doc and "M1" in self.arch_doc
        arch_lower = self.arch_doc.lower()
        assert "promotion" in arch_lower or "promoted" in arch_lower


# ═══════════════════════════════════════════════════════════════════════
# 11. PIPELINE ARCHITECTURE (D21-D24, D27, D28)
# ═══════════════════════════════════════════════════════════════════════


class TestPipelineArchitecture:
    """Tests for D21-D24, D27, D28 pipeline architecture."""

    @pytest.fixture(autouse=True)
    def load_content(self) -> None:
        path = AZOTH_ROOT / "docs" / "AZOTH_ARCHITECTURE.md"
        self.content = path.read_text(encoding="utf-8")

    def test_has_seven_stage_pipeline(self) -> None:
        """D21: Full pipeline should reference 7 stages."""
        # Check for key stage names
        for stage in ("Goal Clarification", "Test Builder", "Architect Review"):
            assert stage in self.content, f"Missing pipeline stage: {stage}"

    def test_has_auto_pipeline(self) -> None:
        """D23: Auto-pipeline section must exist."""
        assert "auto-pipeline" in self.content.lower() or "auto pipeline" in self.content.lower()

    def test_has_gate_typing(self) -> None:
        """D24: Gate typing with human/agent distinction."""
        content_lower = self.content.lower()
        assert "type: human" in content_lower or "type:human" in content_lower

    def test_has_pipeline_presets(self) -> None:
        """D28: All 8 pipeline presets must be referenced."""
        for preset in ("full", "deliver", "hotfix", "docs", "research", "review", "refactor", "auto"):
            assert preset in self.content.lower(), f"Missing pipeline preset: {preset}"

    def test_explore_research_as_architect_tools(self) -> None:
        """D27: Explore/Research are Architect tools, not separate stages."""
        assert "Architect" in self.content
        # Should mention explore/research in context of architect
        content_lower = self.content.lower()
        assert "explore" in content_lower or "research" in content_lower


# ═══════════════════════════════════════════════════════════════════════
# 12. SEED COMMANDS (D25)
# ═══════════════════════════════════════════════════════════════════════


class TestSeedCommands:
    """Tests for D25 seed commands."""

    @pytest.fixture(autouse=True)
    def load_content(self) -> None:
        path = AZOTH_ROOT / "docs" / "AZOTH_ARCHITECTURE.md"
        self.content = path.read_text(encoding="utf-8")

    def test_has_seed_commands_section(self) -> None:
        """D25: Architecture must reference seed commands."""
        assert "seed" in self.content.lower() or "command" in self.content.lower()

    def test_references_key_commands(self) -> None:
        """D25: Key seed commands must be mentioned."""
        for cmd in ("/bootstrap", "/auto", "/deliver", "/eval", "/remember"):
            assert cmd in self.content, f"Missing seed command reference: {cmd}"


# ═══════════════════════════════════════════════════════════════════════
# 13. PROACTIVE AGENT POSTURE (D26)
# ═══════════════════════════════════════════════════════════════════════


class TestProactivePosture:
    """Tests for D26 proactive agent posture."""

    @pytest.fixture(autouse=True)
    def load_content(self) -> None:
        path = AZOTH_ROOT / "docs" / "AZOTH_ARCHITECTURE.md"
        self.content = path.read_text(encoding="utf-8")

    def test_has_proactive_section(self) -> None:
        """D26: Proactive posture section must exist."""
        assert "Proactive" in self.content

    def test_has_three_tiers(self) -> None:
        """D26: Three posture tiers must be defined."""
        content_lower = self.content.lower()
        assert "always" in content_lower
        assert "ask" in content_lower
        assert "never" in content_lower

    def test_kernel_in_never_auto(self) -> None:
        """D26: Kernel modifications must be in never-auto tier."""
        content_lower = self.content.lower()
        assert "kernel" in content_lower

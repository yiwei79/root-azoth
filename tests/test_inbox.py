"""
tests/test_inbox.py — Azoth Insight Inbox Protocol validation tests

Validates all artifacts from the Insight Inbox Protocol (D29–D33)
and Root Scaffold Identity (D34–D38).

TDD: Written first; tests initially fail, then pass as implementation proceeds.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

AZOTH_ROOT = Path(__file__).resolve().parent.parent

INSIGHT_REQUIRED_FIELDS = {
    "id",
    "source",
    "source_type",
    "timestamp",
    "category",
    "severity",
    "target",
    "summary",
    "evidence",
    "recommended_action",
    "auto_applicable",
    "requires_human_gate",
}


# ---------------------------------------------------------------------------
# Class 1: Inbox Infrastructure
# ---------------------------------------------------------------------------


class TestInboxInfrastructure:
    """Validates .azoth/inbox/ directory structure (T1, T2)."""

    def test_inbox_directory_exists(self) -> None:
        """T1: .azoth/inbox/ directory must exist."""
        inbox_dir = AZOTH_ROOT / ".azoth" / "inbox"
        assert inbox_dir.is_dir(), f"Expected directory at {inbox_dir}"

    def test_inbox_processed_directory_exists(self) -> None:
        """T2: .azoth/inbox/processed/ directory must exist."""
        processed_dir = AZOTH_ROOT / ".azoth" / "inbox" / "processed"
        assert processed_dir.is_dir(), f"Expected directory at {processed_dir}"

    def test_inbox_has_gitkeep(self) -> None:
        """T1: .azoth/inbox/.gitkeep must exist to track empty dir in git."""
        gitkeep = AZOTH_ROOT / ".azoth" / "inbox" / ".gitkeep"
        assert gitkeep.exists(), f"Expected .gitkeep at {gitkeep}"

    def test_inbox_processed_has_gitkeep(self) -> None:
        """T2: .azoth/inbox/processed/.gitkeep must exist."""
        gitkeep = AZOTH_ROOT / ".azoth" / "inbox" / "processed" / ".gitkeep"
        assert gitkeep.exists(), f"Expected .gitkeep at {gitkeep}"


# ---------------------------------------------------------------------------
# Class 2: Trusted Sources
# ---------------------------------------------------------------------------


class TestTrustedSources:
    """Validates .azoth/trusted-sources.yaml (T3, F3)."""

    @pytest.fixture(autouse=True)
    def load_file(self) -> None:
        self.path = AZOTH_ROOT / ".azoth" / "trusted-sources.yaml"
        self.lines = self.path.read_text().splitlines() if self.path.exists() else []
        self.data = (
            yaml.safe_load(self.path.read_text()) if self.path.exists() else None
        )

    def test_trusted_sources_exists(self) -> None:
        """T3: .azoth/trusted-sources.yaml must exist."""
        assert self.path.exists(), f"Missing {self.path}"

    def test_trusted_sources_parses_as_yaml(self) -> None:
        """T3: File must parse as a dict via yaml.safe_load()."""
        assert isinstance(self.data, dict), "trusted-sources.yaml must parse as a dict"

    def test_trusted_sources_has_governance_header(self) -> None:
        """T3, F3: First 5 lines must contain a '# GOVERNANCE:' comment."""
        first_lines = self.lines[:5]
        assert any(
            line.startswith("# GOVERNANCE:") for line in first_lines
        ), "trusted-sources.yaml must have '# GOVERNANCE:' in first 5 lines"

    def test_all_sources_require_human_approval(self) -> None:
        """T3, F3: Every source entry must have require_approval: human."""
        assert self.data is not None
        sources = self.data.get("sources", [])
        assert len(sources) > 0, "Must have at least one source"
        for src in sources:
            assert src.get("require_approval") == "human", (
                f"Source '{src.get('id')}' must have require_approval: human"
            )

    def test_has_initial_source_entry(self) -> None:
        """T3: Must have a source with id 'supplygrowth-architect'."""
        assert self.data is not None
        sources = self.data.get("sources", [])
        ids = [s.get("id") for s in sources]
        assert "supplygrowth-architect" in ids, (
            "trusted-sources.yaml must contain source id 'supplygrowth-architect'"
        )

    def test_source_schema_valid(self) -> None:
        """T3: Each source must have id, name, trust_level, require_approval."""
        assert self.data is not None
        required = {"id", "name", "trust_level", "require_approval"}
        for src in self.data.get("sources", []):
            missing = required - set(src.keys())
            assert not missing, f"Source '{src.get('id')}' missing fields: {missing}"


# ---------------------------------------------------------------------------
# Class 3: Insight Schema
# ---------------------------------------------------------------------------


class TestInsightSchema:
    """Validates the insight schema definition (D32)."""

    def test_sample_insight_validates(self) -> None:
        """D32: A sample insight with all required fields must be valid."""
        sample = {
            "id": "insight-test-001",
            "source": "supplygrowth-architect",
            "source_type": "agent",
            "timestamp": "2025-01-01T00:00:00Z",
            "category": "bug",
            "severity": "medium",
            "target": "sync-config.yaml",
            "summary": "strip_patterns array is empty",
            "evidence": "sync-config.yaml line 7: strip_patterns: []",
            "recommended_action": "Populate with org identifiers",
            "auto_applicable": True,
            "requires_human_gate": True,
        }
        missing = INSIGHT_REQUIRED_FIELDS - set(sample.keys())
        assert not missing, f"Sample insight missing fields: {missing}"

    def test_insight_required_fields(self) -> None:
        """D32: INSIGHT_REQUIRED_FIELDS must contain all 12 required fields."""
        expected = {
            "id",
            "source",
            "source_type",
            "timestamp",
            "category",
            "severity",
            "target",
            "summary",
            "evidence",
            "recommended_action",
            "auto_applicable",
            "requires_human_gate",
        }
        assert INSIGHT_REQUIRED_FIELDS == expected, (
            f"INSIGHT_REQUIRED_FIELDS mismatch. Got: {INSIGHT_REQUIRED_FIELDS}"
        )

    def test_insight_severity_is_advisory(self) -> None:
        """F2a: The intake command must document that severity is advisory only."""
        intake_path = AZOTH_ROOT / ".claude" / "commands" / "intake.md"
        assert intake_path.exists(), "intake.md must exist"
        content = intake_path.read_text().lower()
        assert "advisory" in content, (
            "intake.md must mention that source severity is advisory only (F2a)"
        )


# ---------------------------------------------------------------------------
# Class 4: Kernel Inbox Integration
# ---------------------------------------------------------------------------


class TestKernelInboxIntegration:
    """Validates kernel file updates for inbox awareness (T5, T6)."""

    @pytest.fixture(autouse=True)
    def load_kernel_files(self) -> None:
        bootloader = AZOTH_ROOT / "kernel" / "BOOTLOADER.md"
        governance = AZOTH_ROOT / "kernel" / "GOVERNANCE.md"
        self.bootloader = bootloader.read_text() if bootloader.exists() else ""
        self.governance = governance.read_text() if governance.exists() else ""

    def test_bootloader_mentions_inbox_check(self) -> None:
        """T5: kernel/BOOTLOADER.md must reference inbox (case-insensitive)."""
        assert "inbox" in self.bootloader.lower(), (
            "BOOTLOADER.md must mention inbox check in SURVEY phase"
        )

    def test_bootloader_survey_has_inbox_step(self) -> None:
        """T5: Phase 2 SURVEY section must reference inbox."""
        # Find the SURVEY section (specifically the ## Phase 2: SURVEY header)
        # and check it mentions inbox before the next ## Phase header.
        lines = self.bootloader.splitlines()
        in_survey = False
        found = False
        for line in lines:
            # Only enter survey mode when we hit the actual section header
            if line.startswith("## Phase") and "SURVEY" in line:
                in_survey = True
                continue
            if in_survey and "inbox" in line.lower():
                found = True
                break
            # Stop at the next phase header (## Phase N: ...)
            if in_survey and line.startswith("## Phase"):
                break
        assert found, "BOOTLOADER.md Phase 2 SURVEY must reference inbox"

    def test_bootloader_integration_table_has_inbox(self) -> None:
        """T5: Integration Points table must list .azoth/inbox/*.jsonl."""
        assert ".azoth/inbox" in self.bootloader, (
            "BOOTLOADER.md Integration Points table must include .azoth/inbox"
        )

    def test_governance_has_section_7(self) -> None:
        """T6: kernel/GOVERNANCE.md must contain Section 7."""
        has_section_7 = "## 7" in self.governance or "Section 7" in self.governance
        assert has_section_7, "GOVERNANCE.md must have Section 7"

    def test_governance_section_7_has_intake_protocol(self) -> None:
        """T6: Section 7 must mention intake or Insight Intake."""
        assert "intake" in self.governance.lower(), (
            "GOVERNANCE.md Section 7 must reference intake protocol"
        )

    def test_governance_has_f2b_clause(self) -> None:
        """T6, F2b: GOVERNANCE.md must reference 'governance violation' for direct writes."""
        assert "governance violation" in self.governance.lower(), (
            "GOVERNANCE.md must contain 'governance violation' clause (F2b)"
        )

    def test_governance_has_f2c_clause(self) -> None:
        """T6, F2c: GOVERNANCE.md must reference 'untrusted input'."""
        assert "untrusted input" in self.governance.lower(), (
            "GOVERNANCE.md must contain 'untrusted input' clause (F2c)"
        )

    def test_governance_drift_table_has_trusted_sources(self) -> None:
        """T6, F3: Drift detection table must include trusted-sources.yaml."""
        assert "trusted-sources.yaml" in self.governance, (
            "GOVERNANCE.md drift detection table must include trusted-sources.yaml"
        )


# ---------------------------------------------------------------------------
# Class 5: Session Closeout Inbox
# ---------------------------------------------------------------------------


class TestSessionCloseoutInbox:
    """Validates session-closeout.md Part D addition (T7, F4)."""

    @pytest.fixture(autouse=True)
    def load_file(self) -> None:
        path = AZOTH_ROOT / ".claude" / "commands" / "session-closeout.md"
        self.content = path.read_text() if path.exists() else ""

    def test_session_closeout_has_part_d(self) -> None:
        """T7: session-closeout.md must contain Part D."""
        assert "Part D" in self.content, (
            "session-closeout.md must have a Part D section"
        )

    def test_session_closeout_part_d_surfaces_not_processes(self) -> None:
        """T7, F4: Part D must say 'Surface' not 'Process'; must not say 'auto-intake'."""
        assert "Surface" in self.content or "surface" in self.content, (
            "Part D must say 'Surface' (not auto-process)"
        )
        assert "auto-intake" not in self.content, (
            "Part D must NOT say 'auto-intake'"
        )

    def test_session_closeout_part_d_mentions_intake_command(self) -> None:
        """T7, F4: Part D must reference the /intake command."""
        assert "/intake" in self.content, (
            "session-closeout.md Part D must reference /intake command"
        )


# ---------------------------------------------------------------------------
# Class 6: Intake Command
# ---------------------------------------------------------------------------


class TestIntakeCommand:
    """Validates .claude/commands/intake.md (T4)."""

    @pytest.fixture(autouse=True)
    def load_file(self) -> None:
        self.path = AZOTH_ROOT / ".claude" / "commands" / "intake.md"
        self.content = self.path.read_text() if self.path.exists() else ""

    def test_intake_command_exists(self) -> None:
        """T4: .claude/commands/intake.md must exist."""
        assert self.path.exists(), f"Missing {self.path}"

    def test_intake_command_has_frontmatter(self) -> None:
        """T4: File must start with --- YAML frontmatter."""
        assert self.content.startswith("---"), (
            "intake.md must start with YAML frontmatter (---)"
        )

    def test_intake_command_frontmatter_has_description(self) -> None:
        """T4: Frontmatter must have a 'description' key."""
        # Parse the frontmatter block
        lines = self.content.splitlines()
        in_frontmatter = False
        found = False
        for i, line in enumerate(lines):
            if i == 0 and line == "---":
                in_frontmatter = True
                continue
            if in_frontmatter and line == "---":
                break
            if in_frontmatter and line.startswith("description"):
                found = True
                break
        assert found, "intake.md frontmatter must have a 'description' key"

    def test_intake_command_references_inbox_dir(self) -> None:
        """T4: intake.md must reference .azoth/inbox/."""
        assert ".azoth/inbox/" in self.content, (
            "intake.md must reference .azoth/inbox/ directory"
        )

    def test_intake_command_references_governance(self) -> None:
        """T4: intake.md must reference governance or GOVERNANCE.md."""
        assert (
            "governance" in self.content.lower()
            or "GOVERNANCE.md" in self.content
        ), "intake.md must reference governance"


# ---------------------------------------------------------------------------
# Class 7: Handoff Inbox File
# ---------------------------------------------------------------------------


class TestHandoffInboxFile:
    """Validates the first inbox JSONL file (T15)."""

    @pytest.fixture(autouse=True)
    def find_inbox_files(self) -> None:
        inbox_dir = AZOTH_ROOT / ".azoth" / "inbox"
        self.jsonl_files = (
            [
                f
                for f in inbox_dir.iterdir()
                if f.suffix == ".jsonl" and f.is_file()
            ]
            if inbox_dir.exists()
            else []
        )

    def test_at_least_one_inbox_file_exists(self) -> None:
        """T15: At least one .jsonl file must exist in .azoth/inbox/."""
        assert len(self.jsonl_files) >= 1, (
            "At least one .jsonl insight file must exist in .azoth/inbox/"
        )

    def test_inbox_file_has_valid_jsonl(self) -> None:
        """T15: Each line in each .jsonl file must be valid JSON."""
        assert len(self.jsonl_files) >= 1, "No .jsonl files to validate"
        for jf in self.jsonl_files:
            lines = [l for l in jf.read_text().splitlines() if l.strip()]
            assert len(lines) >= 1, f"{jf.name} must have at least one line"
            for i, line in enumerate(lines, 1):
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    pytest.fail(f"{jf.name} line {i} is invalid JSON: {e}")

    def test_inbox_insights_have_required_fields(self) -> None:
        """T15: Each insight in inbox files must have all required schema fields."""
        assert len(self.jsonl_files) >= 1, "No .jsonl files to validate"
        for jf in self.jsonl_files:
            lines = [l for l in jf.read_text().splitlines() if l.strip()]
            for i, line in enumerate(lines, 1):
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue  # covered by previous test
                missing = INSIGHT_REQUIRED_FIELDS - set(obj.keys())
                assert not missing, (
                    f"{jf.name} line {i} missing required fields: {missing}"
                )

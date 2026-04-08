"""P6-003: /arch-proposal command body + cross-platform deploy targets."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CLAUDE_CMD = REPO / ".claude" / "commands" / "arch-proposal.md"


def test_arch_proposal_command_exists() -> None:
    assert CLAUDE_CMD.is_file(), "create .claude/commands/arch-proposal.md"


def test_arch_proposal_command_contract_strings() -> None:
    text = CLAUDE_CMD.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "YAML frontmatter required"
    assert "azoth_effect: mixed" in text
    assert "approved_for_docs" in text
    assert "docs/AZOTH_ARCHITECTURE.md" in text
    assert "docs/adrs/" in text or "docs/adrs" in text
    assert "docs/DECISIONS_INDEX.md" in text
    assert ".azoth/proposals/" in text
    assert "architecture_proposal_validate" in text
    assert "PreToolUse" in text or "pre-tool" in text.lower() or "parity" in text.lower()
    assert "Task" in text
    assert "prior_stage_summaries" in text


@pytest.mark.parametrize(
    "rel",
    [
        ".opencode/commands/arch-proposal.md",
        ".github/prompts/arch-proposal.prompt.md",
    ],
)
def test_deployed_command_copy_when_present(rel: str) -> None:
    path = REPO / rel
    if not path.is_file():
        pytest.skip(f"{rel} missing — run: python3 scripts/azoth-deploy.py")
    assert "approved_for_docs" in path.read_text(encoding="utf-8")

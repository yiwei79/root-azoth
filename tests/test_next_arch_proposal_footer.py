"""Regression: /next step 8b architecture proposal footer instructions."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CLAUDE_NEXT = REPO / ".claude" / "commands" / "next.md"

_REQUIRED_SUBSTRINGS = (
    "8b",
    ".azoth/proposals/",
    "draft",
    "submitted",
    "informational only",
    "read-only",
    "exactly one",
    "approved",
    "expires_at",
    "yaml.safe_load",
)


def test_next_command_arch_proposal_footer_contract() -> None:
    text = CLAUDE_NEXT.read_text(encoding="utf-8")
    missing = [s for s in _REQUIRED_SUBSTRINGS if s not in text]
    assert not missing, f"missing substrings in next.md: {missing}"


@pytest.mark.parametrize(
    "rel",
    [
        ".opencode/commands/next.md",
        ".github/prompts/next.prompt.md",
    ],
)
def test_deployed_next_copy_when_present(rel: str) -> None:
    path = REPO / rel
    if not path.is_file():
        pytest.skip(f"{rel} missing — run: python3 scripts/azoth-deploy.py")
    text = path.read_text(encoding="utf-8")
    missing = [s for s in _REQUIRED_SUBSTRINGS if s not in text]
    assert not missing, f"{rel} missing substrings: {missing}"

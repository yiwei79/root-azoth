"""Drift: every .claude/commands/*.md declares azoth_effect (kernel/GOVERNANCE.md)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
COMMANDS = REPO / ".claude" / "commands"
ALLOWED = frozenset({"read", "write", "mixed"})


def _frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    return text[4:end]


@pytest.mark.parametrize(
    "path",
    sorted(COMMANDS.glob("*.md")),
    ids=lambda p: p.name,
)
def test_command_declares_azoth_effect(path: Path) -> None:
    body = path.read_text(encoding="utf-8")
    fm = _frontmatter(body)
    assert fm is not None, f"{path.name}: missing YAML frontmatter"
    m = re.search(r"^azoth_effect:\s*(\S+)\s*$", fm, re.MULTILINE)
    assert m is not None, f"{path.name}: frontmatter must include azoth_effect: read|write|mixed"
    assert m.group(1) in ALLOWED, f"{path.name}: invalid azoth_effect {m.group(1)!r}"


def test_all_commands_covered() -> None:
    md_files = list(COMMANDS.glob("*.md"))
    assert len(md_files) >= 15, "expected full slash-command set"

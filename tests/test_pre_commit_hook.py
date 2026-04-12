"""
Tests for .githooks/pre-commit hook detection logic.

Covers:
- Staged files outside source patterns → skip check
- Staged source file → triggers check
- All SOURCE_PATTERNS match representative paths
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

# Load the hook module (no .py extension → specify loader explicitly)
_HOOK = Path(__file__).resolve().parent.parent / ".githooks" / "pre-commit"
_loader = importlib.machinery.SourceFileLoader("pre_commit_hook", str(_HOOK))
_spec = importlib.util.spec_from_file_location("pre_commit_hook", str(_HOOK), loader=_loader)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

SOURCE_PATTERNS = _mod.SOURCE_PATTERNS


def _matches(path: str) -> bool:
    """Return True if *path* matches any SOURCE_PATTERN."""
    return any(path.startswith(p) for p in SOURCE_PATTERNS)


# ── Pattern matching tests ────────────────────────────────────────────────────


def test_no_source_files_skips_check() -> None:
    """Non-source paths like README.md should NOT trigger the check."""
    assert not _matches("README.md")
    assert not _matches("scripts/azoth-deploy.py")
    assert not _matches("tests/test_azoth_deploy.py")
    assert not _matches(".github/prompts/auto.prompt.md")


def test_source_file_triggers_check() -> None:
    """A staged file under agents/ should trigger the check."""
    assert _matches("agents/tier1-core/builder.agent.md")
    assert _matches("agents/foo.agent.md")


def test_all_patterns_match() -> None:
    """Each SOURCE_PATTERN must match at least one representative path."""
    representatives = {
        "agents/": "agents/tier1-core/architect.agent.md",
        ".claude/commands/": ".claude/commands/auto.md",
        "skills/": "skills/deep-research/SKILL.md",
        "kernel/templates/platform-adapters/": "kernel/templates/platform-adapters/cursor/rule.mdc.template",
    }
    for pattern in SOURCE_PATTERNS:
        path = representatives[pattern]
        assert _matches(path), f"Pattern {pattern!r} should match {path!r}"

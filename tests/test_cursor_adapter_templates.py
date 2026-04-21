"""Drift guard: Cursor platform adapter templates stay present and marked alwaysApply."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CURSOR_DIR = REPO / "kernel" / "templates" / "platform-adapters" / "cursor"


@pytest.mark.parametrize(
    "name",
    [
        "azoth-memory.mdc.template",
        "claude-code-parity.mdc.template",
        "code-review-insights.mdc.template",
    ],
)
def test_cursor_template_exists_and_always_apply(name: str) -> None:
    path = CURSOR_DIR / name
    assert path.is_file(), f"missing {path}"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{name} must have YAML frontmatter"
    assert "alwaysApply: true" in text, f"{name} must set alwaysApply: true"


def test_live_cursor_rules_mirror_templates() -> None:
    """Deployed .cursor/rules/*.mdc must match kernel templates (run azoth-deploy)."""
    rules = REPO / ".cursor" / "rules"
    adapter = REPO / "kernel" / "templates" / "platform-adapters" / "cursor"
    assert (rules / "azoth-memory.mdc").is_file()
    assert (rules / "claude-code-parity.mdc").is_file()
    for template in sorted(adapter.glob("*.mdc.template")):
        out_name = template.name.removesuffix(".template")
        deployed = rules / out_name
        assert deployed.is_file(), (
            f"missing deployed {deployed} — run: python3 scripts/azoth-deploy.py --platforms cursor"
        )
        assert deployed.read_text(encoding="utf-8") == template.read_text(encoding="utf-8"), (
            f"{out_name} drift — run: python3 scripts/azoth-deploy.py --platforms cursor"
        )


def test_cursor_memory_template_documents_memory_operation_parity() -> None:
    text = (CURSOR_DIR / "azoth-memory.mdc.template").read_text(encoding="utf-8")
    for token in (
        "context-recall",
        "/remember",
        "/promote",
        ".azoth/memory/episodes.jsonl",
        ".azoth/memory/patterns.yaml",
        "~/.claude/projects/<project-key>/memory/",
    ):
        assert token in text, f"cursor memory template must mention {token}"

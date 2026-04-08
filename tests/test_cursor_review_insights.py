"""cursor-review-insights skill, trusted source, and Cursor rule template."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


def test_skill_exists() -> None:
    p = REPO / "skills" / "cursor-review-insights" / "SKILL.md"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "cursor-review" in text
    assert "D32" in text


def test_trusted_source_cursor_review() -> None:
    raw = (REPO / ".azoth" / "trusted-sources.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    ids = {s["id"] for s in data.get("sources", [])}
    assert "cursor-review" in ids


def test_kernel_cursor_template_exists() -> None:
    t = (
        REPO
        / "kernel"
        / "templates"
        / "platform-adapters"
        / "cursor"
        / "code-review-insights.mdc.template"
    )
    assert t.is_file()
    assert "cursor-review-insights" in t.read_text(encoding="utf-8")


def test_review_insights_command_exists() -> None:
    p = REPO / ".claude" / "commands" / "review-insights.md"
    assert p.is_file()
    body = p.read_text(encoding="utf-8")
    assert "azoth_effect:" in body
    assert "cursor-review" in body

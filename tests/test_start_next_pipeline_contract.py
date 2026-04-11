"""Drift guard: scope approval must still route through pipeline selection."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "rel",
    [
        ".claude/commands/start.md",
        ".github/prompts/start.prompt.md",
        ".opencode/commands/start.md",
    ],
)
def test_start_resume_requires_pipeline_or_auto(rel: str) -> None:
    text = _read(rel)
    assert "selected delivery pipeline" in text, f"{rel}: missing pipeline-resume guidance"
    assert "/auto" in text, f"{rel}: missing /auto default guidance"
    assert "Stage 0" in text, f"{rel}: missing Stage 0 guidance"
    assert "do not jump straight to implementation" in text, (
        f"{rel}: missing direct-implementation prohibition"
    )


@pytest.mark.parametrize(
    "rel",
    [
        ".claude/commands/next.md",
        ".github/prompts/next.prompt.md",
        ".opencode/commands/next.md",
    ],
)
def test_next_scope_approval_requires_pipeline_selection(rel: str) -> None:
    text = _read(rel)
    for needle in (
        "Pipeline selection after scope approval (all scopes)",
        "does **not** authorize direct implementation",
        "/auto` is the default (D23)",
        "Stage 0 goal clarification",
        "For standard scopes, Stage 0 / pipeline selection still applies",
    ):
        assert needle in text, f"{rel}: missing {needle!r}"

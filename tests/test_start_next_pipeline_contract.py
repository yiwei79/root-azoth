"""Drift guards for resume, scope approval, and pipeline selection contracts."""

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
    assert "/resume" in text, f"{rel}: missing /resume guidance"
    assert "/auto" in text, f"{rel}: missing /auto default guidance"
    assert "Stage 0" in text, f"{rel}: missing Stage 0 guidance"
    assert (
        "without a second scope-approval wall" in text
        or "do not jump straight to implementation" in text
    ), f"{rel}: missing resume continuity guidance"


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


@pytest.mark.parametrize(
    "rel",
    [
        ".claude/commands/next.md",
        ".github/prompts/next.prompt.md",
        ".opencode/commands/next.md",
    ],
)
def test_next_refuses_to_overwrite_live_scope(rel: str) -> None:
    text = _read(rel)
    assert "route to `/resume`, `/park`, or `/session-closeout` instead" in text, (
        f"{rel}: missing active-scope hard stop guidance"
    )


@pytest.mark.parametrize(
    "rel",
    [
        "commands/next/body.md",
        ".claude/commands/next.md",
        ".github/prompts/next.prompt.md",
        ".opencode/commands/next.md",
    ],
)
def test_next_surfaces_planning_bank_seeds_before_roadmap_preview(rel: str) -> None:
    text = _read(rel)
    for needle in (
        "Planning-bank fallback when no candidate tasks exist",
        ".azoth/design-banks/*.yaml",
        ".azoth/initiative-banks/*.yaml",
        "Planning banks are seeds, not scopes",
        "Do **not** read `.azoth/proposals/` as a candidate source",
    ):
        assert needle in text, f"{rel}: missing {needle!r}"

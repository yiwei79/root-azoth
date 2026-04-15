"""P1-006: session-closeout W2 names session-state handoff path."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLOSEOUT = REPO / ".claude" / "commands" / "session-closeout.md"
ARCHITECTURE = REPO / "docs" / "AZOTH_ARCHITECTURE.md"


def test_w2_mentions_session_state_path() -> None:
    text = CLOSEOUT.read_text(encoding="utf-8")
    assert ".azoth/session-state.md" in text


def test_closeout_mentions_governed_final_delivery_approval_dependency() -> None:
    text = CLOSEOUT.read_text(encoding="utf-8")
    assert ".azoth/final-delivery-approvals.jsonl" in text
    assert "human final-delivery approval" in text


def test_architecture_matches_always_fire_version_bump_rule() -> None:
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert "final step always calls `version-bump.py --patch`" in text
    assert "after\n  confirming at least one artifact was written this session" not in text

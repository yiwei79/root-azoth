"""P8-006: session-closeout W2 names session-state handoff path."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLOSEOUT = REPO / ".claude" / "commands" / "session-closeout.md"


def test_w2_mentions_session_state_path() -> None:
    text = CLOSEOUT.read_text(encoding="utf-8")
    assert ".azoth/session-state.md" in text

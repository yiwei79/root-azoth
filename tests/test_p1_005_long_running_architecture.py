"""P1-005: architecture anchors long-running session playbook."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARCH = REPO / "docs" / "AZOTH_ARCHITECTURE.md"
NEXT = REPO / ".claude" / "commands" / "next.md"
CLOSEOUT = REPO / ".claude" / "commands" / "session-closeout.md"


def test_architecture_has_long_running_p1_005_heading() -> None:
    text = ARCH.read_text(encoding="utf-8")
    assert "### Long-running sessions (P1-005)" in text
    assert "SWARM_RESEARCH_DIGEST.yaml" in text
    assert "scope-gate" in text.lower() or "scope gate" in text.lower()


def test_next_resume_contract_preserves_human_approval_gate() -> None:
    text = NEXT.read_text(encoding="utf-8")
    assert "resume <session_id>" in text
    assert "Wait for human signal" in text
    assert "approved" in text
    assert "Never auto-resume by rewriting scope" in text


def test_session_closeout_contract_preserves_bootloader_and_session_mirror() -> None:
    text = CLOSEOUT.read_text(encoding="utf-8")
    assert "bootloader-state.md" in text
    assert "active\n  scope `session_id` as the default selected session" in text
    assert ".azoth/session-state.md" in text
    assert "same `session_id`" in text

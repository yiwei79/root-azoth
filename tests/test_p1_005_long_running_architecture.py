"""P1-005: architecture anchors long-running session playbook."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARCH = REPO / "docs" / "AZOTH_ARCHITECTURE.md"
RESUME = REPO / ".claude" / "commands" / "resume.md"
CLOSEOUT = REPO / ".claude" / "commands" / "session-closeout.md"


def test_architecture_has_long_running_p1_005_heading() -> None:
    text = ARCH.read_text(encoding="utf-8")
    assert "### Long-running sessions (P1-005)" in text
    assert "SWARM_RESEARCH_DIGEST.yaml" in text
    assert "scope-gate" in text.lower() or "scope gate" in text.lower()


def test_resume_contract_is_stage_aware_and_direct() -> None:
    text = RESUME.read_text(encoding="utf-8")
    assert "/resume [<session_id>]" in text
    assert "Explicit resume intent is already the approval" in text
    assert "saved run checkpoint" in text
    assert "saved stage" in text


def test_session_closeout_contract_preserves_bootloader_and_session_mirror() -> None:
    text = CLOSEOUT.read_text(encoding="utf-8")
    assert "bootloader-state.md" in text
    assert "active\n  scope `session_id` as the default selected session" in text
    assert ".azoth/session-state.md" in text
    assert "same `session_id`" in text

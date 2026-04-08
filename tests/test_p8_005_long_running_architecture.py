"""P8-005: architecture anchors long-running session playbook."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARCH = REPO / "docs" / "AZOTH_ARCHITECTURE.md"


def test_architecture_has_long_running_p8_005_heading() -> None:
    text = ARCH.read_text(encoding="utf-8")
    assert "### Long-running sessions (P8-005)" in text
    assert "SWARM_RESEARCH_DIGEST.yaml" in text
    assert "scope-gate" in text.lower() or "scope gate" in text.lower()

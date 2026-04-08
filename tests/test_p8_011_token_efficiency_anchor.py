"""P8-011: architecture anchors context & token budget section."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARCH = REPO / "docs" / "AZOTH_ARCHITECTURE.md"


def test_architecture_has_p8_011_context_token_heading() -> None:
    text = ARCH.read_text(encoding="utf-8")
    assert "### Context & token budget (P8-011)" in text
    assert "BL-012" in text
    assert "RP-E" in text

"""
BL-026: install.sh Step 7 uses GOVERNANCE §4 five-file lexicographic order, not glob.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_INSTALL = _REPO / "install.sh"

_EXPECTED_PATHS = (
    ".azoth/kernel/BOOTLOADER.md",
    ".azoth/kernel/GOVERNANCE.md",
    ".azoth/kernel/PROMOTION_RUBRIC.md",
    ".azoth/kernel/TRUST_CONTRACT.md",
    ".azoth/kernel/TRUST_HOSTS.md",
)


def test_install_sh_step7_explicit_paths_not_glob() -> None:
    text = _INSTALL.read_text(encoding="utf-8")
    assert ".azoth/kernel/*.md" not in text, "Step 7 must not use glob (ordering not §4-stable)"
    for p in _EXPECTED_PATHS:
        assert p in text, f"Missing explicit path {p}"
    # Lexicographic basename order B < G < P < TRUST_CONTRACT < TRUST_HOSTS
    b = text.index(_EXPECTED_PATHS[0])
    g = text.index(_EXPECTED_PATHS[1])
    p = text.index(_EXPECTED_PATHS[2])
    t = text.index(_EXPECTED_PATHS[3])
    h = text.index(_EXPECTED_PATHS[4])
    assert b < g < p < t < h, "§4 paths must appear in lexicographic order in install.sh"

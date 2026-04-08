"""P6-003: install scripts and root .gitignore mention `.azoth/proposals/`."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_root_gitignore_excludes_proposals_dir() -> None:
    gi = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert ".azoth/proposals/" in gi


def test_install_sh_appends_proposals_gitignore_rule() -> None:
    sh = (REPO / "install.sh").read_text(encoding="utf-8")
    assert ".azoth/proposals/" in sh
    assert 'grep -qF ".azoth/proposals/"' in sh


def test_install_ps1_appends_proposals_gitignore_rule() -> None:
    ps1 = (REPO / "install.ps1").read_text(encoding="utf-8")
    assert ".azoth/proposals/" in ps1
    assert "proposals" in ps1.lower()

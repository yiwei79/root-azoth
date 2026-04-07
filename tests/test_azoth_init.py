"""Tests for scripts/azoth_init.py (no full install run)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "azoth_init.py"


def test_help_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "project" in r.stdout.lower()


def test_y_without_mode_errors() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "-y"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 2


def test_scaffold_non_interactive() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--scaffold", "-y"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    out = r.stdout.lower()
    assert "workshop" in out or "root-azoth" in out

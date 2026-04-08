"""Ruff gate aligned with `.github/workflows/ci.yml` (P4-003: repo-wide drift lint)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_ruff_check_repo_wide() -> None:
    """`python -m ruff check .` must pass (same as CI) when ruff is installed."""
    r = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 and "No module named ruff" in (r.stderr or ""):
        pytest.skip("ruff not installed (pip install -r requirements-dev.txt)")
    assert r.returncode == 0, r.stdout + r.stderr

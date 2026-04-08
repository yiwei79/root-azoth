"""Optional ruff gate when `ruff` is on PATH (dev/CI with dev-deps)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
RUFF_TARGETS = [
    "scripts/architecture_proposal_validate.py",
    "scripts/kernel-integrity.py",
    "tests/test_architecture_proposal_schema.py",
    "tests/test_kernel_integrity.py",
    "tests/test_next_arch_proposal_footer.py",
]


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not on PATH")
def test_ruff_check_architecture_proposal_stack() -> None:
    r = subprocess.run(
        ["ruff", "check", *RUFF_TARGETS],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr

"""Tests for the repeatable T-036 product release smoke script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "product_release_smoke.py"


def test_product_release_smoke_checks_extract_without_install(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--out",
            str(tmp_path / "product"),
            "--skip-install",
            "--skip-ruff",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "product_release_smoke: OK" in result.stdout
    assert (tmp_path / "product" / "README.md").is_file()
    assert (tmp_path / "product" / ".github" / "workflows" / "ci.yml").is_file()
    assert not (tmp_path / "product" / ".azoth").exists()
    assert not (tmp_path / "product" / ".venv").exists()

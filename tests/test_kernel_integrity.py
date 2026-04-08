"""BL-017 / GOV-B2 — scripts/kernel-integrity.py smoke tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "kernel-integrity.py"
CHECKSUM = REPO / ".azoth" / "kernel-checksums.sha256"


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_kernel_integrity_default_exits_zero() -> None:
    r = _run_script()
    assert r.returncode == 0, r.stderr + r.stdout


def test_kernel_integrity_verify_checksums_exits_zero_when_manifest_present() -> None:
    assert CHECKSUM.is_file(), (
        "golden .azoth/kernel-checksums.sha256 must be committed for §4 verify"
    )
    r = _run_script("--verify-checksums")
    assert r.returncode == 0, r.stderr + r.stdout

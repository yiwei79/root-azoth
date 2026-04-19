"""BL-017 / GOV-B2 — scripts/kernel-integrity.py smoke tests."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "kernel-integrity.py"
CHECKSUM = REPO / ".azoth" / "kernel-checksums.sha256"


def _load_module():
    spec = importlib.util.spec_from_file_location("kernel_integrity", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


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


def test_parse_checksum_lines_rejects_empty_path() -> None:
    """BL-039: malformed line '<64-hex> *' should not insert an empty key."""
    mod = _load_module()
    digest = "a" * 64
    malformed = f"{digest} *\n"
    result = mod._parse_checksum_lines(malformed)
    assert "" not in result, "empty-string key should be rejected"
    assert len(result) == 0

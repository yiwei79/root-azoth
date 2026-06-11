from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from hermes_manifest_check import run_check  # noqa: E402


def _payload_for(repo_root: Path) -> dict[str, object]:
    return run_check(repo_root)


def test_check_runs_and_reports_json() -> None:
    payload = _payload_for(REPO_ROOT)
    assert "checks" in payload
    assert "kernel_checksum_ok" in payload
    assert "agents_md_parity_ok" in payload
    assert "tests_directory_present" in payload
    assert "trust_hosts_md_present" in payload


def test_kernel_files_checked_are_four() -> None:
    payload = _payload_for(REPO_ROOT)
    kernel_checks = [c for c in payload["checks"] if c.get("kind") == "kernel_file"]
    assert len(kernel_checks) == 4, (
        "Manifest check must cover all 4 kernel files (BOOTLOADER, TRUST_CONTRACT, GOVERNANCE, PROMOTION_RUBRIC)"
    )


def test_check_detects_missing_kernel_file(tmp_path: Path) -> None:
    """A repo without kernel/BOOTLOADER.md must report failure."""
    fake_root = tmp_path / "fake_repo"
    fake_root.mkdir()
    payload = _payload_for(fake_root)
    assert not payload["ok"]
    missing_files = [c for c in payload["checks"] if c.get("kind") == "kernel_file" and not c.get("present")]
    assert len(missing_files) == 4
    assert payload["trust_hosts_md_present"] is False
    assert payload["tests_directory_present"] is False
    assert payload["agents_md_parity_ok"] is False


def test_check_passes_on_real_repo_after_trust_green_fix() -> None:
    """On the real workshop repo with the trust-green fix applied, the check should pass."""
    payload = _payload_for(REPO_ROOT)
    assert payload["trust_hosts_md_present"], "TRUST_HOSTS.md must be detected as present"
    assert payload["tests_directory_present"], "tests/ directory must be detected as present"
    assert payload["agents_md_parity_ok"], "AGENTS.md must use scope-gated wording"

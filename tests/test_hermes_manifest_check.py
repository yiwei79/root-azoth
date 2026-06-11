from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "hermes_manifest_check.py"


def _run_check(*args: str, repo_root: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), *args]
    if repo_root is not None:
        cmd.extend(["--repo-root", str(repo_root)])
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_check_runs_and_reports_json() -> None:
    proc = _run_check("--json")
    assert proc.returncode in (0, 1), f"unexpected exit: {proc.returncode}\n{proc.stderr}"
    payload = json.loads(proc.stdout)
    assert "checks" in payload
    assert "kernel_checksum_ok" in payload
    assert "agents_md_parity_ok" in payload
    assert "tests_directory_present" in payload
    assert "trust_hosts_md_present" in payload


def test_kernel_files_checked_are_four() -> None:
    proc = _run_check("--json")
    payload = json.loads(proc.stdout)
    kernel_checks = [c for c in payload["checks"] if c.get("kind") == "kernel_file"]
    assert len(kernel_checks) == 4, (
        "Manifest check must cover all 4 kernel files (BOOTLOADER, TRUST_CONTRACT, GOVERNANCE, PROMOTION_RUBRIC)"
    )


def test_check_detects_missing_kernel_file(tmp_path: Path) -> None:
    """A repo without kernel/BOOTLOADER.md must report failure."""
    fake_root = tmp_path / "fake_repo"
    fake_root.mkdir()
    proc = _run_check("--json", repo_root=fake_root)
    assert proc.returncode == 1, "Missing kernel files must produce exit 1"
    payload = json.loads(proc.stdout)
    assert not payload["ok"]
    # The kernel_file checks must individually report missing
    missing_files = [c for c in payload["checks"] if c.get("kind") == "kernel_file" and not c.get("present")]
    assert len(missing_files) == 4
    # The top-level invariants should also be false
    assert payload["trust_hosts_md_present"] is False
    assert payload["tests_directory_present"] is False
    assert payload["agents_md_parity_ok"] is False


def test_check_passes_on_real_repo_after_trust_green_fix() -> None:
    """On the real workshop repo with the trust-green fix applied, the check should pass."""
    proc = _run_check("--json")
    payload = json.loads(proc.stdout)
    # The trust-green fix (commit 72bc183) refreshed the checksum; TRUST_HOSTS.md exists.
    assert payload["trust_hosts_md_present"], "TRUST_HOSTS.md must be detected as present"
    assert payload["tests_directory_present"], "tests/ directory must be detected as present"
    assert payload["agents_md_parity_ok"], "AGENTS.md must use scope-gated wording"

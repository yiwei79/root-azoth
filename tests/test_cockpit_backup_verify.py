from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cockpit_backup_verify import verify_backup  # noqa: E402
from test_cockpit_bootstrap_verify import _write_cockpit_bootstrap_fixture  # noqa: E402
from test_personal_knowledge_validate import _write_empty_skeleton  # noqa: E402


def _run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def _init_git_repo(path: Path) -> str:
    assert _run(["git", "init", "-b", "main"], cwd=path).returncode == 0
    assert _run(["git", "config", "user.email", "test@example.com"], cwd=path).returncode == 0
    assert _run(["git", "config", "user.name", "Test User"], cwd=path).returncode == 0
    assert _run(["git", "add", "."], cwd=path).returncode == 0
    assert _run(["git", "commit", "-m", "fixture"], cwd=path).returncode == 0
    result = _run(["git", "rev-parse", "HEAD"], cwd=path)
    assert result.returncode == 0
    return result.stdout.strip()


def test_verify_backup_clones_and_runs_restore_checks(tmp_path: Path) -> None:
    cockpit = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_empty_skeleton(cockpit)
    head = _init_git_repo(cockpit)

    result = verify_backup(
        remote_url=str(cockpit),
        temp_parent=tmp_path,
        keep_restore=True,
    )

    assert result.status == "passed"
    assert result.remote_head == head
    assert result.restored_head == head
    assert (result.restore_path / ".git").is_dir()
    assert {step.name for step in result.steps} >= {
        "remote_head",
        "remote_clone",
        "personal_knowledge_validate",
        "cockpit_bootstrap_restore_drill",
        "cockpit_menu_check",
        "cockpit_project_handoff",
    }


def test_verify_backup_fails_when_branch_is_missing(tmp_path: Path) -> None:
    cockpit = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_empty_skeleton(cockpit)
    _init_git_repo(cockpit)

    result = verify_backup(
        remote_url=str(cockpit),
        branch="missing",
        temp_parent=tmp_path,
    )

    assert result.status == "failed"
    assert any(step.name == "remote_head" and step.status == "failed" for step in result.steps)

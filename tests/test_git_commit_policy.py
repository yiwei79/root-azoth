"""Tests for scripts/git_commit_policy.py (P5-001)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import git_commit_policy  # noqa: E402

CommitPolicyError = git_commit_policy.CommitPolicyError
validate_commit_message = git_commit_policy.validate_commit_message


@pytest.mark.parametrize(
    ("body", "id"),
    [
        ("Co-Authored-By: Alice <a@b.com>\n", "canonical"),
        ("co-authored-by: Bob <b@c.com>\n", "lower"),
        ("CO-AUTHORED-BY: x <y@z.com>\n", "upper"),
        ("  Co-Authored-By: trailing space before colon \n", "spaced"),
        ("Subject\n\nCo-Authored-By: Eve <e@f.com>\n", "after_blank"),
        ("\ufeffCo-Authored-By: Lead <l@m.com>\n", "bom_prefix"),
    ],
)
def test_rejects_co_authored_trailer(body: str, id: str) -> None:
    with pytest.raises(CommitPolicyError, match="Co-Authored-By"):
        validate_commit_message(body)


@pytest.mark.parametrize(
    "body",
    [
        "fix: thing\n",
        "fix: thing\n\nBody without trailer.\n",
        "fix: mention co authored by in prose only\n",
        "fix: Co-Authored-By without colon is not a trailer line\n",
    ],
)
def test_accepts_clean_messages(body: str) -> None:
    validate_commit_message(body)


def test_cli_rejects_violation(tmp_path: Path) -> None:
    p = tmp_path / "msg.txt"
    p.write_text("Co-Authored-By: X <x@y.com>\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/git_commit_policy.py"), "check", "--path", str(p)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
    assert "Co-Authored-By" in r.stderr


def test_cli_accepts_clean(tmp_path: Path) -> None:
    p = tmp_path / "msg.txt"
    p.write_text("fix: ok\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/git_commit_policy.py"), "check", "--path", str(p)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert r.stderr == ""


def test_install_git_hooks_idempotent(tmp_path: Path) -> None:
    """Minimal repo: install script sets core.hooksPath and commit-msg blocks bad commits."""
    import shutil

    init = subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    if init.returncode != 0:
        pytest.skip(f"git init unavailable in this environment: {init.stderr.decode()}")
    subprocess.run(
        ["git", "config", "user.email", "t@e.st"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
    )
    scripts = tmp_path / "scripts" / "git-hooks"
    scripts.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "scripts" / "git-hooks" / "commit-msg", scripts / "commit-msg")
    shutil.copy(REPO_ROOT / "scripts" / "git_commit_policy.py", tmp_path / "scripts" / "git_commit_policy.py")

    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/azoth_install_git_hooks.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    p = subprocess.run(
        ["git", "config", "core.hooksPath"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert p.stdout.strip() == "scripts/git-hooks"

    bad = subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "x\n\nCo-Authored-By: A <a@b.com>\n"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert bad.returncode != 0

    good = subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "fix: no trailer"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert good.returncode == 0

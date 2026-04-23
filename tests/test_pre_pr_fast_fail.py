"""Fast-fail pre-PR runner for parity-sensitive work."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent
_SCRIPT = REPO / "scripts" / "pre_pr_fast_fail.py"
_SPEC = importlib.util.spec_from_file_location("pre_pr_fast_fail", _SCRIPT)
pre_pr_fast_fail = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(pre_pr_fast_fail)


def _completed(
    cmd: list[str], returncode: int = 0, stdout: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")


def test_parity_sensitive_change_triggers_deploy_refresh_before_check(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        pre_pr_fast_fail,
        "changed_files_since_head",
        lambda repo_root: ["agents/tier1-core/builder.agent.md"],
    )

    def fake_run(cmd: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return _completed(cmd)

    rc = pre_pr_fast_fail.main(repo_root=tmp_path, run=fake_run)

    assert rc == 0
    assert calls[0] == [pre_pr_fast_fail.PYTHON, "scripts/azoth-deploy.py"]
    assert calls[1] == [pre_pr_fast_fail.PYTHON, "scripts/azoth-deploy.py", "--check"]


def test_non_parity_change_skips_refresh_but_keeps_required_checks(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        pre_pr_fast_fail,
        "changed_files_since_head",
        lambda repo_root: ["README.md"],
    )

    def fake_run(cmd: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return _completed(cmd)

    rc = pre_pr_fast_fail.main(repo_root=tmp_path, run=fake_run)

    assert rc == 0
    assert [pre_pr_fast_fail.PYTHON, "scripts/azoth-deploy.py"] not in calls
    assert calls == [
        [pre_pr_fast_fail.PYTHON, "scripts/azoth-deploy.py", "--check"],
        [pre_pr_fast_fail.PYTHON, "-m", "ruff", "format", "--check", "."],
        [pre_pr_fast_fail.PYTHON, "-m", "ruff", "check", "."],
        [
            pre_pr_fast_fail.PYTHON,
            "-m",
            "pytest",
            "-q",
            "tests/test_install_proposals_gitignore.py",
            "tests/test_v020_roadmap_spec_decision_ref_parity.py",
        ],
    ]


def test_generated_mirror_change_is_parity_sensitive() -> None:
    assert pre_pr_fast_fail.is_parity_sensitive(".agents/skills/subagent-router/SKILL.md")
    assert pre_pr_fast_fail.is_parity_sensitive(".github/prompts/auto.prompt.md")
    assert pre_pr_fast_fail.is_parity_sensitive("AGENTS.md")
    assert not pre_pr_fast_fail.is_parity_sensitive("README.md")


def test_fast_fail_stops_at_first_failed_command(monkeypatch: Any, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        pre_pr_fast_fail,
        "changed_files_since_head",
        lambda repo_root: ["skills/context-map/SKILL.md"],
    )

    def fake_run(cmd: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return _completed(cmd, returncode=7)

    rc = pre_pr_fast_fail.main(repo_root=tmp_path, run=fake_run)

    assert rc == 7
    assert calls == [[pre_pr_fast_fail.PYTHON, "scripts/azoth-deploy.py"]]


def test_changed_files_includes_tracked_and_untracked(monkeypatch: Any, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_subprocess_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[:3] == ["git", "diff", "--name-only"]:
            return _completed(cmd, stdout="README.md\n.github/pull_request_template.md\n")
        if cmd[:3] == ["git", "ls-files", "--others"]:
            return _completed(cmd, stdout="scripts/pre_pr_fast_fail.py\n")
        raise AssertionError(f"unexpected command: {cmd!r}")

    monkeypatch.setattr(pre_pr_fast_fail.subprocess, "run", fake_subprocess_run)

    assert pre_pr_fast_fail.changed_files_since_head(tmp_path) == [
        "README.md",
        ".github/pull_request_template.md",
        "scripts/pre_pr_fast_fail.py",
    ]
    assert calls == [
        ["git", "diff", "--name-only", "HEAD", "--"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]


def test_pr_template_names_pre_pr_fast_fail_command() -> None:
    text = (REPO / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert "python3 scripts/pre_pr_fast_fail.py" in text


def test_readme_documents_pre_pr_fast_fail_command() -> None:
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "python3 scripts/pre_pr_fast_fail.py" in text

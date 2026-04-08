"""P5-005: mechanical git checkpoints (scripts/azoth_checkpoint.py) and RED entropy hint."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "azoth_checkpoint.py"
_HOOKS = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from entropy_check import ZONE_RED_MIN, evaluate_entropy  # noqa: E402


def _run_checkpoint(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _init_repo(path: Path) -> None:
    init = subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    if init.returncode != 0:
        legacy = subprocess.run(
            ["git", "init"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        if legacy.returncode != 0:
            pytest.skip(
                "git init failed (install git or relax sandbox for checkpoint tests): "
                f"{legacy.stderr.strip() or legacy.stdout.strip()}"
            )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    (path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def test_checkpoint_tag_creates_lightweight_ref(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    r = _run_checkpoint(tmp_path, "tag")
    assert r.returncode == 0, r.stderr
    lr = subprocess.run(
        ["git", "-C", str(tmp_path), "tag", "-l", "azoth/checkpoint/*"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert re.search(r"azoth/checkpoint/\d+", lr.stdout)


def test_checkpoint_list_shows_azoth_stash_and_tag(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    assert _run_checkpoint(tmp_path, "create").returncode == 0
    assert _run_checkpoint(tmp_path, "tag").returncode == 0
    r = _run_checkpoint(tmp_path, "list")
    assert r.returncode == 0
    out = r.stdout
    assert "azoth-checkpoint-" in out
    assert re.search(r"azoth/checkpoint/\d+", out)
    assert "--- stash (azoth) ---" in out
    assert "--- tags (azoth/checkpoint/*) ---" in out


def test_checkpoint_list_no_azoth_stashes(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    r = _run_checkpoint(tmp_path, "list")
    assert r.returncode == 0
    assert r.stdout.count("(none)") >= 1


def test_checkpoint_create_stash_message(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "tracked.txt").write_text("v2\n", encoding="utf-8")
    r = _run_checkpoint(tmp_path, "create")
    assert r.returncode == 0, r.stderr
    lr = subprocess.run(
        ["git", "-C", str(tmp_path), "stash", "list"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert re.search(r"azoth-checkpoint-\d+", lr.stdout)


def test_checkpoint_help_documents_apply_vs_pop() -> None:
    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "git stash apply" in r.stdout
    assert "git stash pop" in r.stdout


def test_checkpoint_tag_help_says_lightweight() -> None:
    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "tag", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "lightweight" in r.stdout.lower()


def test_checkpoint_non_git_fails(tmp_path: Path) -> None:
    d = tmp_path / "nogit"
    d.mkdir()
    r = _run_checkpoint(d, "create")
    assert r.returncode == 1


def test_evaluate_entropy_red_reason_includes_checkpoint_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    est = tmp_path / "entropy-state.json"
    monkeypatch.setenv("AZOTH_ENTROPY_STATE_PATH", str(est))
    (tmp_path / ".azoth").mkdir(parents=True)
    est.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": "sess-red",
                "cumulative_entropy": 8.99,
                "modified_paths": [],
                "created_paths": [],
                "lines_total": 0,
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "new_file_red.txt"
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target), "content": "a\n"},
    }
    scope_data = {"session_id": "sess-red"}
    r = evaluate_entropy(payload, scope_data, repo_root=tmp_path)
    assert r.allowed is False
    assert r.cumulative_entropy is not None
    assert r.cumulative_entropy >= ZONE_RED_MIN
    reason = r.reason or ""
    assert "scripts/azoth_checkpoint.py" in reason
    assert "TRUST_CONTRACT" in reason and "§4" in reason

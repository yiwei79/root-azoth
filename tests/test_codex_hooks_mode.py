from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "codex_hooks_mode.py"


def _prepare_repo(root: Path) -> None:
    adapter = root / "kernel" / "templates" / "platform-adapters" / "codex"
    adapter.mkdir(parents=True)
    (adapter / "hooks.json.template").write_text(
        '{"hooks": {"UserPromptSubmit": []}}\n', encoding="utf-8"
    )
    (adapter / "hooks.verbose.json.template").write_text(
        '{"hooks": {"SessionStart": [], "UserPromptSubmit": []}}\n',
        encoding="utf-8",
    )
    (root / ".codex").mkdir(parents=True)


def test_codex_hooks_mode_set_verbose_and_restore_calm(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)

    verbose = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "set", "verbose"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert verbose.returncode == 0
    assert (tmp_path / ".codex" / "hooks.mode.local").read_text(
        encoding="utf-8"
    ).strip() == "verbose"
    assert (tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8") == (
        tmp_path
        / "kernel"
        / "templates"
        / "platform-adapters"
        / "codex"
        / "hooks.verbose.json.template"
    ).read_text(encoding="utf-8")

    calm = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "set", "calm"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert calm.returncode == 0
    assert not (tmp_path / ".codex" / "hooks.mode.local").exists()
    assert (tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8") == (
        tmp_path / "kernel" / "templates" / "platform-adapters" / "codex" / "hooks.json.template"
    ).read_text(encoding="utf-8")


def test_codex_hooks_mode_accepts_verbo_alias(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "set", "verbo"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0
    assert "Codex hooks mode: verbose" in proc.stdout
    assert (tmp_path / ".codex" / "hooks.mode.local").read_text(
        encoding="utf-8"
    ).strip() == "verbose"


def test_codex_hooks_mode_status_reports_unsynced_file(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    (tmp_path / ".codex" / "hooks.json").write_text(
        '{"hooks": {"Unexpected": []}}\n', encoding="utf-8"
    )

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "status"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1
    assert "Hooks in sync: no" in proc.stdout
    assert "Codex hooks mode: calm" in proc.stdout

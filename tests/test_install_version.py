"""T-035: installers must not advertise stale release versions."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent

FULL_INSTALL_REQUIRED_PATHS = (
    "commands/start/command.yaml",
    "commands/roadmap/command.yaml",
    "pipelines/full.pipeline.yaml",
    "scripts/codex_control_plane.py",
    "scripts/roadmap_dashboard.py",
    "scripts/autonomous_loop.py",
    ".agents/skills/azoth-start/SKILL.md",
    ".agents/skills/azoth-roadmap/SKILL.md",
    ".agents/skills/azoth-autonomous-auto/SKILL.md",
    ".azoth/roadmap.yaml",
    ".azoth/backlog.yaml",
    ".azoth/roadmap-specs/v0.1.0/README.md",
    ".azoth/initiative-banks/.gitkeep",
    ".azoth/design-banks/.gitkeep",
    ".azoth/autonomous-loop-state.local.yaml.example",
)

PRIVATE_RUNTIME_STATE = (
    ".azoth/scope-gate.json",
    ".azoth/pipeline-gate.json",
    ".azoth/run-ledger.local.yaml",
    ".azoth/autonomous-loop-state.local.yaml",
    ".azoth/final-delivery-approvals.jsonl",
)


def _manifest_version(path: Path = REPO / "azoth.yaml") -> str:
    data = cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))
    return str(data["version"])


def test_installers_read_version_from_source_manifest() -> None:
    shell_installer = (REPO / "install.sh").read_text(encoding="utf-8")
    powershell_installer = (REPO / "install.ps1").read_text(encoding="utf-8")

    assert "0.1.0-dev" not in shell_installer
    assert "0.1.0-dev" not in powershell_installer
    assert "read_azoth_version" in shell_installer
    assert 'manifest="$SCRIPT_DIR/azoth.yaml"' in shell_installer
    assert "Get-AzothVersion" in powershell_installer
    assert 'Join-Path $SCRIPT_DIR "azoth.yaml"' in powershell_installer
    assert "AZOTH_PLATFORMS" in shell_installer
    assert "AZOTH_PLATFORMS" in powershell_installer
    assert "Defaulting to Claude Code + GitHub Copilot" in shell_installer
    assert "Defaulting to Claude Code + GitHub Copilot" in powershell_installer
    assert ".github/prompts" in shell_installer
    assert ".github\\prompts" in powershell_installer


def test_install_sh_generates_manifest_with_source_version(tmp_path: Path) -> None:
    if not shutil.which("bash"):
        pytest.skip("bash not available on this platform")

    subprocess.run(
        ["bash", str(REPO / "install.sh")],
        env={**os.environ, "AZOTH_PLATFORMS": "copilot"},
        input="1\n",
        text=True,
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    generated = _manifest_version(tmp_path / "azoth.yaml")
    assert generated == _manifest_version()

    generated_manifest = yaml.safe_load((tmp_path / "azoth.yaml").read_text(encoding="utf-8"))
    platforms = generated_manifest["platforms"]
    assert isinstance(platforms, list)
    assert platforms == ["copilot"]
    assert all(isinstance(platform, str) and " " not in platform for platform in platforms)
    assert (tmp_path / ".github" / "copilot-instructions.md").is_file()
    assert (tmp_path / ".github" / "prompts" / "auto.prompt.md").is_file()
    assert (tmp_path / ".github" / "agents" / "orchestrator.agent.md").is_file()
    assert "tools:" in (tmp_path / ".github" / "agents" / "builder.agent.md").read_text(
        encoding="utf-8"
    )


def test_install_sh_full_setup_materializes_runtime_bundle_and_consumer_safe_seeds(
    tmp_path: Path,
) -> None:
    if not shutil.which("bash"):
        pytest.skip("bash not available on this platform")

    subprocess.run(
        ["bash", str(REPO / "install.sh")],
        env={**os.environ, "AZOTH_PLATFORMS": "codex copilot"},
        input="3\n",
        text=True,
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    for required_path in FULL_INSTALL_REQUIRED_PATHS:
        assert (tmp_path / required_path).exists(), required_path

    for private_path in PRIVATE_RUNTIME_STATE:
        assert not (tmp_path / private_path).exists(), private_path

    gitignore_lines = {
        line.strip()
        for line in (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for private_path in PRIVATE_RUNTIME_STATE:
        assert private_path in gitignore_lines
    assert "!.azoth/autonomous-loop-state.local.yaml.example" in gitignore_lines

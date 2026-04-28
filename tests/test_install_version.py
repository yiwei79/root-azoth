"""T-035: installers must not advertise stale release versions."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, cast

import yaml

REPO = Path(__file__).resolve().parent.parent


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


def test_install_sh_generates_manifest_with_source_version(tmp_path: Path) -> None:
    subprocess.run(
        ["bash", str(REPO / "install.sh")],
        input="1\n",
        text=True,
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    generated = _manifest_version(tmp_path / "azoth.yaml")
    assert generated == _manifest_version()

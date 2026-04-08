"""BL-018: `.claude/settings.json` env must match `azoth.yaml` manifest (version, phase)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

AZOTH_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = AZOTH_ROOT / ".claude" / "settings.json"
AZOTH_YAML_PATH = AZOTH_ROOT / "azoth.yaml"


def _load_settings() -> dict[str, Any]:
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def _load_manifest() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        yaml.safe_load(AZOTH_YAML_PATH.read_text(encoding="utf-8")),
    )


def test_settings_env_matches_azoth_manifest() -> None:
    settings = _load_settings()
    manifest = _load_manifest()
    env = settings["env"]
    assert env["AZOTH_VERSION"] == manifest["version"]
    assert env["AZOTH_PHASE"] == str(manifest["phase"])

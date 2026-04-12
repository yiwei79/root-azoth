"""Drift guard: Codex platform adapter templates stay present and match deployed files."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CODEX_DIR = REPO / "kernel" / "templates" / "platform-adapters" / "codex"


@pytest.mark.parametrize(
    "name",
    [
        "config.toml.template",
        "hooks.json.template",
        "user_prompt_submit_router.py.template",
    ],
)
def test_codex_template_exists(name: str) -> None:
    path = CODEX_DIR / name
    assert path.is_file(), f"missing {path}"


def test_live_codex_adapter_mirrors_templates() -> None:
    mapping = {
        "config.toml.template": REPO / ".codex" / "config.toml",
        "hooks.json.template": REPO / ".codex" / "hooks.json",
        "user_prompt_submit_router.py.template": REPO / ".codex" / "hooks" / "user_prompt_submit_router.py",
    }
    for template_name, deployed in mapping.items():
        template = CODEX_DIR / template_name
        assert deployed.is_file(), (
            f"missing deployed {deployed.relative_to(REPO)} — run: python3 scripts/azoth-deploy.py --platforms codex"
        )
        assert deployed.read_text(encoding="utf-8") == template.read_text(encoding="utf-8"), (
            f"{deployed.relative_to(REPO)} drift — run: python3 scripts/azoth-deploy.py --platforms codex"
        )


def test_codex_router_adds_context_for_auto_token() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    proc = subprocess.run(
        [sys.executable, str(router)],
        input=json.dumps({"prompt": "/auto investigate drift"}),
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "/auto" in ctx
    assert ".claude/commands/auto.md" in ctx

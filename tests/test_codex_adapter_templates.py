"""Drift guard: Codex platform adapter templates stay present and match deployed files."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CODEX_DIR = REPO / "kernel" / "templates" / "platform-adapters" / "codex"


def _run_router(router: Path, prompt: str, *, cwd: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(router)],
        input=json.dumps({"prompt": prompt}),
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
    )
    assert proc.returncode == 0
    return proc.stdout


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
        "user_prompt_submit_router.py.template": REPO
        / ".codex"
        / "hooks"
        / "user_prompt_submit_router.py",
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
    payload = json.loads(_run_router(router, "/auto investigate drift", cwd=REPO))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "/auto" in ctx
    assert ".claude/commands/auto.md" in ctx


def test_codex_router_adds_context_for_any_existing_command_token() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = json.loads(_run_router(router, "/remember capture this lesson", cwd=REPO))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "/remember" in ctx
    assert ".claude/commands/remember.md" in ctx


def test_codex_router_adds_context_from_non_root_cwd() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = json.loads(_run_router(router, "/auto investigate drift", cwd=REPO / "tests"))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "/auto" in ctx
    assert ".claude/commands/auto.md" in ctx


def test_codex_router_ignores_mention_only_command_tokens() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    assert _run_router(router, "Explain the difference between /auto and /deliver in Azoth.", cwd=REPO).strip() == ""


def _copy_router_fixture(tmp_path: Path) -> Path:
    (tmp_path / ".codex" / "hooks").mkdir(parents=True)
    (tmp_path / ".claude" / "commands").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / ".azoth").mkdir(parents=True)

    (tmp_path / ".codex" / "hooks" / "user_prompt_submit_router.py").write_text(
        (REPO / ".codex" / "hooks" / "user_prompt_submit_router.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / ".claude" / "commands" / "auto.md").write_text(
        (REPO / ".claude" / "commands" / "auto.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "scripts" / "session_continuity.py").write_text(
        (REPO / "scripts" / "session_continuity.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return tmp_path / ".codex" / "hooks" / "user_prompt_submit_router.py"


def test_codex_router_adds_resume_guidance_and_write_disclaimer(tmp_path: Path) -> None:
    router = _copy_router_fixture(tmp_path)
    (tmp_path / ".azoth" / "scope-gate.json").write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": "2099-04-16T19:17:45+00:00",
                "goal": "BL-123: Active scope",
                "session_id": "sess-active",
                "approved_by": "human",
                "backlog_id": "BL-123",
                "governance_mode": "standard",
                "pipeline_command": "auto",
                "target_layer": "application",
            }
        ),
        encoding="utf-8",
    )

    payload = json.loads(_run_router(router, "/auto BL-123: Active scope", cwd=tmp_path))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "resume/continue decision" in ctx
    assert "does not authorize writes" in ctx

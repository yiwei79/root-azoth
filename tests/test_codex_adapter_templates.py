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
        "hooks.verbose.json.template",
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


def test_codex_hook_template_keeps_only_user_prompt_submit() -> None:
    hooks = json.loads((CODEX_DIR / "hooks.json.template").read_text(encoding="utf-8"))["hooks"]
    assert set(hooks.keys()) == {"UserPromptSubmit"}


def test_codex_verbose_hook_template_restores_extended_hook_set() -> None:
    hooks = json.loads((CODEX_DIR / "hooks.verbose.json.template").read_text(encoding="utf-8"))[
        "hooks"
    ]
    assert set(hooks.keys()) == {
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "Stop",
    }


def test_codex_router_adds_context_for_auto_token() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = json.loads(_run_router(router, "/auto investigate drift", cwd=REPO))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "/auto" in ctx
    assert "commands/start/command.yaml" in ctx
    assert "pipeline_command=auto" in ctx
    assert (
        payload["hookSpecificOutput"]["updatedInput"]
        == "$azoth-start pipeline_command=auto investigate drift"
    )


def test_codex_router_adds_context_for_any_existing_command_token() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = json.loads(_run_router(router, "/remember capture this lesson", cwd=REPO))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "/remember" in ctx
    assert "commands/remember/command.yaml" in ctx


def test_codex_router_adds_context_for_hookmode_token() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = json.loads(_run_router(router, "/hookmode verbo", cwd=REPO))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "/hookmode" in ctx
    assert "commands/hookmode/command.yaml" in ctx


def test_codex_router_adds_context_from_non_root_cwd() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = json.loads(_run_router(router, "/auto investigate drift", cwd=REPO / "tests"))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "/auto" in ctx
    assert "commands/start/command.yaml" in ctx
    assert (
        payload["hookSpecificOutput"]["updatedInput"]
        == "$azoth-start pipeline_command=auto investigate drift"
    )


def test_codex_router_ignores_mention_only_command_tokens() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    assert (
        _run_router(
            router, "Explain the difference between /auto and /deliver in Azoth.", cwd=REPO
        ).strip()
        == ""
    )


def test_codex_router_redirects_deliver_full_token_to_start_centered_route() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = json.loads(_run_router(router, "/deliver-full harden codex adapter", cwd=REPO))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "/deliver-full" in ctx
    assert "commands/start/command.yaml" in ctx
    assert "commands/deliver-full/command.yaml" in ctx
    assert ".agents/skills/azoth-start/SKILL.md" in ctx
    assert (
        payload["hookSpecificOutput"]["updatedInput"]
        == "$azoth-start pipeline_command=deliver-full harden codex adapter"
    )


def test_codex_router_warns_pipeline_tokens_need_staged_delegation_not_inline_fallback() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = json.loads(_run_router(router, "/deliver-full harden codex adapter", cwd=REPO))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "staged pipeline execution" in ctx
    assert "not permission to improvise the work inline" in ctx
    assert "STOP after the Declaration and ask the human" in ctx


def _copy_router_fixture(tmp_path: Path) -> Path:
    (tmp_path / ".codex" / "hooks").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / ".azoth").mkdir(parents=True)

    (tmp_path / ".codex" / "hooks" / "user_prompt_submit_router.py").write_text(
        (REPO / ".codex" / "hooks" / "user_prompt_submit_router.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "scripts" / "codex_control_plane.py").write_text(
        (REPO / "scripts" / "codex_control_plane.py").read_text(encoding="utf-8"),
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
    assert (
        payload["hookSpecificOutput"]["updatedInput"]
        == "$azoth-start pipeline_command=auto BL-123: Active scope"
    )


def test_codex_router_canonical_start_fails_closed_when_staged_delegation_is_unavailable(
    tmp_path: Path,
) -> None:
    router = _copy_router_fixture(tmp_path)
    payload = json.loads(
        _run_router(
            router,
            "/start pipeline_command=deliver-full harden codex adapter",
            cwd=tmp_path,
        )
    )
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "pipeline_command=deliver-full" in ctx
    assert "Staged delegation is unavailable in this runtime" in ctx
    assert "STOP after the Declaration and ask the human" in ctx
    assert (
        payload["hookSpecificOutput"]["updatedInput"]
        == "$azoth-start pipeline_command=deliver-full harden codex adapter"
    )


def test_codex_config_fails_closed_when_staged_delegation_is_unavailable() -> None:
    config = REPO / ".codex" / "config.toml"
    assert config.is_file(), "missing deployed Codex config"
    text = config.read_text(encoding="utf-8")
    assert "staged pipeline execution and staged delegation" in text
    assert "STOP after the Declaration and ask the human" in text
    assert "Never silently continue inline as a fallback" in text


def test_codex_config_declares_bounded_swarm_budget_defaults() -> None:
    text = (CODEX_DIR / "config.toml.template").read_text(encoding="utf-8")
    assert "max_threads = 10" in text
    assert "max_depth = 2" in text
    assert "Nested delegation is bounded" in text
    assert "`research-orchestrator`, and `architect` may spend depth > 1" in text

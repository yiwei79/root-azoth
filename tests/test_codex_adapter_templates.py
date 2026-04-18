"""Drift guard: Codex platform adapter templates stay present and match deployed files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_journey_harness import copy_codex_router_fixture, run_router, write_json  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CODEX_DIR = REPO / "kernel" / "templates" / "platform-adapters" / "codex"


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
    payload = run_router(router, "/auto investigate drift", cwd=REPO)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]
    assert hook["updatedInput"] == "$azoth-start pipeline_command=auto investigate drift"
    assert ".claude/commands/auto.md" in ctx
    assert "pipeline_command=auto" in ctx
    assert "staged pipeline execution" in ctx
    assert "does not count as stage execution" in ctx


def test_codex_router_adds_context_for_any_existing_command_token() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = run_router(router, "/remember capture this lesson", cwd=REPO)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]
    assert hook["updatedInput"] == "$azoth-remember capture this lesson"
    assert ".claude/commands/remember.md" in ctx


def test_codex_router_adds_context_for_hookmode_token() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = run_router(router, "/hookmode verbo", cwd=REPO)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]
    assert hook["updatedInput"] == "$azoth-hookmode verbo"
    assert ".claude/commands/hookmode.md" in ctx


def test_codex_router_adds_context_from_non_root_cwd() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = run_router(router, "/auto investigate drift", cwd=REPO / "tests")
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]
    assert hook["updatedInput"] == "$azoth-start pipeline_command=auto investigate drift"
    assert ".claude/commands/auto.md" in ctx


def test_codex_router_ignores_mention_only_command_tokens() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    assert not run_router(
        router,
        "Explain the difference between /auto and /deliver in Azoth.",
        cwd=REPO,
    )


def test_codex_router_redirects_deliver_full_token_to_staged_skill_entry() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = run_router(router, "/deliver-full harden codex adapter", cwd=REPO)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]
    assert hook["updatedInput"] == "$azoth-start pipeline_command=deliver-full harden codex adapter"
    assert ".claude/commands/deliver-full.md" in ctx
    assert "canonical calm-flow skill path" in ctx
    assert "pipeline_command=deliver-full" in ctx


def test_codex_router_warns_pipeline_tokens_need_staged_delegation_not_inline_fallback() -> None:
    router = REPO / ".codex" / "hooks" / "user_prompt_submit_router.py"
    assert router.is_file(), "missing deployed Codex user prompt router"
    payload = run_router(router, "/deliver-full harden codex adapter", cwd=REPO)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "staged pipeline execution" in ctx
    assert "not permission to improvise the work inline" in ctx
    assert "STOP after the Declaration and ask the human" in ctx
    assert "does not count as stage execution" in ctx


def test_codex_router_adds_resume_guidance_and_write_disclaimer(tmp_path: Path) -> None:
    router = copy_codex_router_fixture(tmp_path, "auto")
    write_json(
        tmp_path / ".azoth" / "scope-gate.json",
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
        },
    )

    payload = run_router(router, "/auto BL-123: Active scope", cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    ctx = hook["additionalContext"]
    assert hook["updatedInput"] == "$azoth-start pipeline_command=auto BL-123: Active scope"
    assert "resume/continue decision" in ctx
    assert "does not authorize writes" in ctx


def test_codex_router_blocks_when_skill_wrapper_is_missing(tmp_path: Path) -> None:
    router = copy_codex_router_fixture(tmp_path, "auto", include_skills=False)

    payload = run_router(router, "/auto investigate drift", cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    assert hook["decision"] == "block"
    assert "azoth-start/SKILL.md" in hook["additionalContext"]
    assert "azoth-deploy.py --platforms codex" in hook["additionalContext"]


def test_codex_router_blocks_pipeline_when_staged_delegation_is_unavailable(tmp_path: Path) -> None:
    router = copy_codex_router_fixture(tmp_path, "deliver-full", multi_agent=False)

    payload = run_router(router, "$azoth-deliver-full harden codex adapter", cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    assert hook["decision"] == "block"
    assert "staged delegation is not ready" in hook["additionalContext"]
    assert "$azoth-start pipeline_command=deliver-full harden codex adapter" in hook["additionalContext"]


def test_codex_router_blocks_start_centered_pipeline_when_staged_delegation_is_unavailable(
    tmp_path: Path,
) -> None:
    router = copy_codex_router_fixture(tmp_path, "start", multi_agent=False)

    payload = run_router(
        router,
        "$azoth-start pipeline_command=deliver-full harden codex adapter",
        cwd=tmp_path,
    )
    hook = payload["hookSpecificOutput"]
    assert hook["decision"] == "block"
    assert "staged delegation is not ready" in hook["additionalContext"]
    assert "$azoth-start pipeline_command=deliver-full harden codex adapter" in hook["additionalContext"]


def test_codex_router_start_intake_stays_orientation_only(tmp_path: Path) -> None:
    router = copy_codex_router_fixture(tmp_path, "start")
    write_json(
        tmp_path / ".azoth" / "scope-gate.json",
        {
            "approved": True,
            "expires_at": "2099-04-16T19:17:45+00:00",
            "goal": "BL-123: Active scope",
            "session_id": "sess-active",
        },
    )

    payload = run_router(router, "/start intake", cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    assert hook["updatedInput"] == "$azoth-start intake"
    assert "replace decision" not in hook["additionalContext"]


def test_codex_router_start_next_keeps_replace_guidance(tmp_path: Path) -> None:
    router = copy_codex_router_fixture(tmp_path, "start")
    write_json(
        tmp_path / ".azoth" / "scope-gate.json",
        {
            "approved": True,
            "expires_at": "2099-04-16T19:17:45+00:00",
            "goal": "BL-123: Active scope",
            "session_id": "sess-active",
        },
    )

    payload = run_router(router, "/start next", cwd=tmp_path)
    hook = payload["hookSpecificOutput"]
    assert hook["updatedInput"] == "$azoth-start next"
    assert "replace decision" in hook["additionalContext"]


def test_codex_config_fails_closed_when_staged_delegation_is_unavailable() -> None:
    config = REPO / ".codex" / "config.toml"
    assert config.is_file(), "missing deployed Codex config"
    text = config.read_text(encoding="utf-8")
    assert "$azoth-start" in text
    assert "canonical Codex wrapper is missing" in text
    assert "staged pipeline execution and staged delegation" in text
    assert "STOP after the Declaration and ask the human" in text
    assert "does not count as stage execution" in text


def test_codex_config_declares_bounded_swarm_budget_defaults() -> None:
    text = (CODEX_DIR / "config.toml.template").read_text(encoding="utf-8")
    assert "max_threads = 10" in text
    assert "max_depth = 2" in text
    assert "Nested delegation is bounded" in text
    assert "`research-orchestrator`, and `architect` may spend depth > 1" in text

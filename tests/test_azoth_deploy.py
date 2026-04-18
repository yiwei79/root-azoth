"""
Unit tests for scripts/azoth-deploy.py.

Covers:
- parse_frontmatter: valid, missing, unclosed, "---" inside YAML value (regression)
- posture_to_permissions: tier baseline, keyword narrowing, word-boundary regression
- transform_agent_claude: correct fields, Azoth fields stripped
- transform_agent_copilot: name/description required, tools/model optional
- transform_agent_codex: TOML custom-agent output
- transform_agent_opencode: no name field, mode from tier, permission object
- transform_command_copilot: mode:agent added
- transform_command_opencode: description preserved, body unchanged
- deployed command parity: .github/prompts + .opencode/commands match transforms (D46, BL-023)
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import uuid
from pathlib import Path

import pytest
import yaml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 test env
    import tomli as tomllib

# Load the script as a module without executing main()
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "azoth-deploy.py"
_spec = importlib.util.spec_from_file_location("azoth_deploy", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

parse_frontmatter = _mod.parse_frontmatter
render_frontmatter = _mod.render_frontmatter
posture_to_permissions = _mod.posture_to_permissions
merge_never_auto = _mod.merge_never_auto
effective_posture_for_permissions = _mod.effective_posture_for_permissions
UNIVERSAL_NEVER_AUTO = _mod.UNIVERSAL_NEVER_AUTO
transform_agent_claude = _mod.transform_agent_claude
transform_agent_copilot = _mod.transform_agent_copilot
transform_agent_codex = _mod.transform_agent_codex
transform_agent_opencode = _mod.transform_agent_opencode
transform_command_claude = _mod.transform_command_claude
transform_command_copilot = _mod.transform_command_copilot
transform_command_codex_skill = _mod.transform_command_codex_skill
transform_command_gemini = _mod.transform_command_gemini
transform_command_opencode = _mod.transform_command_opencode
iter_codex_adapter_deployments = _mod.iter_codex_adapter_deployments
deploy_codex_adapter = _mod.deploy_codex_adapter
lint_codex_hooks = _mod.lint_codex_hooks
iter_cursor_rule_deployments = _mod.iter_cursor_rule_deployments
deploy_cursor_rules = _mod.deploy_cursor_rules
load_agents = _mod.load_agents
load_commands = _mod.load_commands
load_skills = _mod.load_skills
gemini_command_name = _mod.gemini_command_name
shared_skill_name = _mod.shared_skill_name
transform_shared_skill = _mod.transform_shared_skill
write_file = _mod.write_file
main = _mod.main


# ── parse_frontmatter ────────────────────────────────────────────────────────


def test_parse_frontmatter_valid() -> None:
    text = "---\nname: foo\ndescription: bar\n---\n\n# Body\nContent here.\n"
    meta, body = parse_frontmatter(text)
    assert meta == {"name": "foo", "description": "bar"}
    assert body.startswith("# Body")


def test_parse_frontmatter_no_frontmatter() -> None:
    text = "# Just a body\nNo frontmatter here."
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_parse_frontmatter_unclosed() -> None:
    text = "---\nname: foo\n# No closing delimiter"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_parse_frontmatter_dashes_inside_yaml_value() -> None:
    # Regression: "---" inside a YAML string value must not be treated as closing delimiter.
    # Line-anchored search (\n---) prevents this.
    text = '---\ndescription: "a --- b"\n---\n\n# Body\n'
    meta, body = parse_frontmatter(text)
    assert meta["description"] == "a --- b"
    assert body.startswith("# Body")


def test_parse_frontmatter_empty_body() -> None:
    text = "---\nname: x\n---\n"
    meta, body = parse_frontmatter(text)
    assert meta == {"name": "x"}
    assert body == ""


# ── posture_to_permissions ───────────────────────────────────────────────────


def test_tier1_baseline() -> None:
    # Tier 1 with empty posture: edit=allow, bash=ask, webfetch=allow, task=allow
    perms = posture_to_permissions(1, {})
    assert perms == {"edit": "allow", "bash": "ask", "webfetch": "allow", "task": "allow"}


def test_tier3_baseline_bash_deny() -> None:
    # Tier 3 meta agents have bash:deny from baseline
    perms = posture_to_permissions(3, {})
    assert perms["bash"] == "deny"


def test_keyword_narrows_allow_to_ask() -> None:
    # "Kernel modifications" matches "kernel" in edit keywords: allow → ask
    posture = {"never_auto": ["Kernel modifications", "Governance changes"]}
    perms = posture_to_permissions(1, posture)
    assert perms["edit"] == "ask"


def test_keyword_does_not_relax_deny() -> None:
    # Tier 3 baseline has bash:deny; no keyword scan should relax it to ask or allow
    posture = {"ask_first": ["Run a script to check something"]}
    perms = posture_to_permissions(3, posture)
    assert perms["bash"] == "deny"


def test_no_false_positive_research_vs_search() -> None:
    # Regression: "research" must NOT match the "search" webfetch keyword.
    # Before word-boundary fix, researcher/research-orchestrator got webfetch:ask
    # instead of the tier-2 baseline webfetch:allow.
    posture = {
        "never_auto": ["Kernel modifications", "Governance changes"],
        "ask_first": ["Expanding research scope beyond original question"],
    }
    perms = posture_to_permissions(2, posture)
    assert perms["webfetch"] == "allow", (
        '"research" should not match the "search" keyword — word-boundary regression'
    )


def test_pipeline_self_matches_task() -> None:
    # "Pipeline self-modification" should match "pipeline self" in task keywords
    posture = {"never_auto": ["Pipeline self-modification"]}
    perms = posture_to_permissions(1, posture)
    assert perms["task"] == "ask"


def test_unknown_tier_uses_default() -> None:
    perms = posture_to_permissions(99, {})
    assert set(perms.keys()) == {"edit", "bash", "webfetch", "task"}


def test_merge_never_auto_empty_is_universal_only() -> None:
    assert merge_never_auto([]) == list(UNIVERSAL_NEVER_AUTO)
    assert merge_never_auto(None) == list(UNIVERSAL_NEVER_AUTO)


def test_merge_never_auto_skips_duplicate_universal_lines() -> None:
    merged = merge_never_auto(["Kernel modifications", "Governance changes"])
    assert merged == list(UNIVERSAL_NEVER_AUTO)


def test_merge_never_auto_appends_agent_only_line() -> None:
    extra = "Approving kernel or governance PRs"
    merged = merge_never_auto([extra])
    assert merged[: len(UNIVERSAL_NEVER_AUTO)] == list(UNIVERSAL_NEVER_AUTO)
    assert merged[-1] == extra


def test_effective_posture_for_permissions_preserves_always_do() -> None:
    eff = effective_posture_for_permissions(
        {
            "always_do": ["Do the thing"],
            "ask_first": [],
            "never_auto": [],
        }
    )
    assert eff["always_do"] == ["Do the thing"]
    assert eff["never_auto"] == list(UNIVERSAL_NEVER_AUTO)


# ── transform_agent_claude ───────────────────────────────────────────────────

_ARCHITECT = {
    "meta": {
        "name": "architect",
        "tier": 1,
        "tier_name": "core",
        "role": "Design, constraints, alignment",
        "skills": ["context-map"],
        "tools": ["explore", "research"],
        "posture": {"never_auto": ["Kernel modifications"], "ask_first": []},
        "trust_level": "high",
    },
    "body": "# Architect\n\nYou are the Architect.\n",
}


def test_claude_agent_required_fields() -> None:
    out = transform_agent_claude(_ARCHITECT)
    meta, body = parse_frontmatter(out)
    assert meta["name"] == "architect"
    assert meta["description"] == "Design, constraints, alignment"


def test_claude_agent_strips_azoth_fields() -> None:
    out = transform_agent_claude(_ARCHITECT)
    meta, _ = parse_frontmatter(out)
    for field in ("tier", "tier_name", "role", "skills", "posture", "trust_level"):
        assert field not in meta, f"Azoth field '{field}' should be stripped from Claude output"


def test_claude_agent_model_optional() -> None:
    out_no_model = transform_agent_claude(_ARCHITECT)
    meta_no_model, _ = parse_frontmatter(out_no_model)
    assert "model" not in meta_no_model

    agent_with_model = {**_ARCHITECT, "meta": {**_ARCHITECT["meta"], "model": "claude-opus-4-5"}}
    out_with_model = transform_agent_claude(agent_with_model)
    meta_with_model, _ = parse_frontmatter(out_with_model)
    assert meta_with_model["model"] == "claude-opus-4-5"


def test_claude_agent_body_preserved() -> None:
    out = transform_agent_claude(_ARCHITECT)
    assert "You are the Architect." in out


# ── transform_agent_copilot ──────────────────────────────────────────────────


def test_copilot_agent_required_fields() -> None:
    out = transform_agent_copilot(_ARCHITECT)
    meta, _ = parse_frontmatter(out)
    assert "name" in meta
    assert "description" in meta


def test_copilot_agent_tools_included() -> None:
    out = transform_agent_copilot(_ARCHITECT)
    meta, _ = parse_frontmatter(out)
    assert meta.get("tools") == ["explore", "research"]


def test_copilot_agent_no_tools_omitted() -> None:
    agent = {**_ARCHITECT, "meta": {**_ARCHITECT["meta"], "tools": []}}
    out = transform_agent_copilot(agent)
    meta, _ = parse_frontmatter(out)
    assert "tools" not in meta


# ── transform_agent_codex ─────────────────────────────────────────────────────


def test_codex_agent_required_fields() -> None:
    out = transform_agent_codex(_ARCHITECT)
    data = tomllib.loads(out)
    assert data["name"] == "architect"
    assert data["description"] == "Design, constraints, alignment"
    assert "developer_instructions" in data


def test_codex_agent_body_preserved() -> None:
    out = transform_agent_codex(_ARCHITECT)
    data = tomllib.loads(out)
    assert "You are the Architect." in data["developer_instructions"]


def test_codex_agent_model_optional() -> None:
    out_no_model = transform_agent_codex(_ARCHITECT)
    data_no_model = tomllib.loads(out_no_model)
    assert "model" not in data_no_model

    agent_with_model = {**_ARCHITECT, "meta": {**_ARCHITECT["meta"], "model": "gpt-5.4"}}
    out_with_model = transform_agent_codex(agent_with_model)
    data_with_model = tomllib.loads(out_with_model)
    assert data_with_model["model"] == "gpt-5.4"


# ── transform_agent_opencode ─────────────────────────────────────────────────


def test_opencode_agent_no_name_field() -> None:
    # OpenCode derives identity from filename — name must NOT be in frontmatter
    out = transform_agent_opencode(_ARCHITECT)
    meta, _ = parse_frontmatter(out)
    assert "name" not in meta


def test_opencode_agent_has_description() -> None:
    out = transform_agent_opencode(_ARCHITECT)
    meta, _ = parse_frontmatter(out)
    assert meta["description"] == "Design, constraints, alignment"


def test_opencode_agent_mode_tier1_is_all() -> None:
    out = transform_agent_opencode(_ARCHITECT)
    meta, _ = parse_frontmatter(out)
    assert meta["mode"] == "all"


def test_opencode_agent_mode_tier3_is_subagent() -> None:
    agent = {**_ARCHITECT, "meta": {**_ARCHITECT["meta"], "tier": 3}}
    out = transform_agent_opencode(agent)
    meta, _ = parse_frontmatter(out)
    assert meta["mode"] == "subagent"


def test_opencode_agent_has_permission_object() -> None:
    out = transform_agent_opencode(_ARCHITECT)
    meta, _ = parse_frontmatter(out)
    perms = meta.get("permission", {})
    assert set(perms.keys()) == {"edit", "bash", "webfetch", "task"}
    assert all(v in ("allow", "ask", "deny") for v in perms.values())


def test_opencode_merge_universal_never_auto_when_agent_lists_empty() -> None:
    """BL-015: empty per-agent never_auto still tightens OpenCode perms via universal merge."""
    agent = {
        "meta": {
            **{k: v for k, v in _ARCHITECT["meta"].items() if k != "posture"},
            "posture": {"never_auto": [], "ask_first": [], "always_do": []},
        },
        "body": _ARCHITECT["body"],
    }
    out = transform_agent_opencode(agent)
    meta, _ = parse_frontmatter(out)
    perms = meta.get("permission", {})
    assert perms["edit"] == "ask"


# ── transform_command_copilot ────────────────────────────────────────────────

_REMEMBER_CMD = {
    "name": "remember",
    "meta": {"description": "Capture a cross-session learning"},
    "body": "# /remember $ARGUMENTS\n\nCapture a durable lesson.\n",
}


def test_copilot_prompt_mode_agent() -> None:
    out = transform_command_copilot(_REMEMBER_CMD)
    meta, _ = parse_frontmatter(out)
    assert meta["mode"] == "agent"


def test_copilot_prompt_description_preserved() -> None:
    out = transform_command_copilot(_REMEMBER_CMD)
    meta, _ = parse_frontmatter(out)
    assert meta["description"] == "Capture a cross-session learning"


def test_copilot_prompt_preserves_agent_binding() -> None:
    out = transform_command_copilot(
        {
            **_REMEMBER_CMD,
            "meta": {**_REMEMBER_CMD["meta"], "agent": "architect"},
        }
    )
    meta, _ = parse_frontmatter(out)
    assert meta["agent"] == "architect"


def test_copilot_prompt_body_preserved() -> None:
    out = transform_command_copilot(_REMEMBER_CMD)
    assert "Capture a durable lesson." in out


# ── transform_command_opencode ───────────────────────────────────────────────


def test_opencode_command_description_preserved() -> None:
    out = transform_command_opencode(_REMEMBER_CMD)
    meta, _ = parse_frontmatter(out)
    assert meta.get("description") == "Capture a cross-session learning"


def test_opencode_command_body_preserved() -> None:
    out = transform_command_opencode(_REMEMBER_CMD)
    assert "$ARGUMENTS" in out


def test_opencode_command_preserves_agent_binding() -> None:
    out = transform_command_opencode(
        {
            **_REMEMBER_CMD,
            "meta": {**_REMEMBER_CMD["meta"], "agent": "architect"},
        }
    )
    meta, _ = parse_frontmatter(out)
    assert meta["agent"] == "architect"


def test_opencode_command_no_description_no_frontmatter() -> None:
    cmd = {"name": "bare", "meta": {}, "body": "# bare\nDo the thing.\n"}
    out = transform_command_opencode(cmd)
    assert not out.startswith("---")
    assert "Do the thing." in out


def _write_minimal_agent(root: Path) -> None:
    path = root / "agents" / "tier1-core" / "architect.agent.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "name: architect\n"
        "description: Design authority\n"
        "role: Design authority\n"
        "tier: 1\n"
        "---\n\n"
        "# Architect\n",
        encoding="utf-8",
    )


def _write_minimal_command(root: Path) -> None:
    path = root / ".claude" / "commands" / "auto.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\ndescription: Auto pipeline\n---\n\n# /auto $ARGUMENTS\n",
        encoding="utf-8",
    )


def _write_contract_command(root: Path) -> None:
    legacy_path = root / ".claude" / "commands" / "next.md"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(
        "---\n"
        'description: "Legacy next description"\n'
        "agent: orchestrator\n"
        "azoth_effect: mixed\n"
        "---\n\n"
        "# /next\n\nUse the legacy body.\n",
        encoding="utf-8",
    )

    contract_path = root / "commands" / "next" / "command.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        "schema_version: 1\n"
        "name: next\n"
        "display_name: /next\n"
        "description: Canonical next description\n"
        "agent: orchestrator\n"
        "azoth_effect: mixed\n"
        "body:\n"
        "  mode: legacy_claude_markdown\n"
        "  source_path: .claude/commands/next.md\n"
        "projection:\n"
        "  claude:\n"
        "    output_path: .claude/commands/next.md\n",
        encoding="utf-8",
    )


def _write_minimal_skill(root: Path) -> None:
    path = root / "skills" / "context-map" / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\nname: context-map\ndescription: Map context.\n---\n\nUse this skill.\n",
        encoding="utf-8",
    )


def _write_codex_templates(root: Path) -> None:
    adapter = root / "kernel" / "templates" / "platform-adapters" / "codex"
    adapter.mkdir(parents=True, exist_ok=True)
    (adapter / "config.toml.template").write_text(
        'approval_policy = "on-request"\n',
        encoding="utf-8",
    )
    (adapter / "hooks.json.template").write_text('{"hooks": {}}\n', encoding="utf-8")
    (adapter / "user_prompt_submit_router.py.template").write_text(
        "#!/usr/bin/env python3\n",
        encoding="utf-8",
    )


def test_main_copilot_default_agent_location_is_claude(tmp_path: Path) -> None:
    _write_minimal_agent(tmp_path)
    _write_minimal_command(tmp_path)

    rc = main(
        [
            "--root",
            str(tmp_path),
            "--platforms",
            "copilot",
        ]
    )

    assert rc == 0
    assert (tmp_path / ".claude" / "agents" / "architect.md").is_file()
    assert not (tmp_path / ".github" / "agents" / "architect.agent.md").exists()
    assert (tmp_path / ".github" / "prompts" / "auto.prompt.md").is_file()


def test_main_copilot_agent_location_claude_preserves_prompts(tmp_path: Path) -> None:
    _write_minimal_agent(tmp_path)
    _write_minimal_command(tmp_path)

    rc = main(
        [
            "--root",
            str(tmp_path),
            "--platforms",
            "copilot",
            "--copilot-agent-location",
            "claude",
        ]
    )

    assert rc == 0
    assert (tmp_path / ".claude" / "agents" / "architect.md").is_file()
    assert not (tmp_path / ".github" / "agents" / "architect.agent.md").exists()
    assert (tmp_path / ".github" / "prompts" / "auto.prompt.md").is_file()


def test_main_copilot_agent_location_both_writes_both_agent_formats(tmp_path: Path) -> None:
    _write_minimal_agent(tmp_path)
    _write_minimal_command(tmp_path)

    rc = main(
        [
            "--root",
            str(tmp_path),
            "--platforms",
            "copilot",
            "--copilot-agent-location",
            "both",
        ]
    )

    assert rc == 0
    assert (tmp_path / ".claude" / "agents" / "architect.md").is_file()
    assert (tmp_path / ".github" / "agents" / "architect.agent.md").is_file()


def test_main_codex_writes_agents_skills_and_adapter(tmp_path: Path) -> None:
    _write_minimal_agent(tmp_path)
    _write_minimal_skill(tmp_path)
    _write_codex_templates(tmp_path)

    rc = main(["--root", str(tmp_path), "--platforms", "codex"])

    assert rc == 0
    assert (tmp_path / ".codex" / "agents" / "architect.toml").is_file()
    assert (tmp_path / ".agents" / "skills" / "context-map" / "SKILL.md").is_file()
    assert (tmp_path / ".codex" / "config.toml").is_file()
    assert (tmp_path / ".codex" / "hooks.json").is_file()
    assert (tmp_path / ".codex" / "hooks" / "user_prompt_submit_router.py").is_file()


# ── Cursor rule deployment ────────────────────────────────────────────────────


def test_iter_codex_adapter_deployments_maps_templates() -> None:
    repo = Path(__file__).resolve().parent.parent
    root = repo / "tests" / "_tmp_deploy" / uuid.uuid4().hex
    adapter = root / "kernel" / "templates" / "platform-adapters" / "codex"
    adapter.mkdir(parents=True)
    try:
        (adapter / "config.toml.template").write_text(
            'approval_policy = "on-request"\n', encoding="utf-8"
        )
        (adapter / "hooks.json.template").write_text('{"hooks": {}}\n', encoding="utf-8")
        (adapter / "hooks.verbose.json.template").write_text(
            '{"hooks": {"SessionStart": []}}\n', encoding="utf-8"
        )
        (adapter / "user_prompt_submit_router.py.template").write_text(
            "#!/usr/bin/env python3\n", encoding="utf-8"
        )
        pairs = iter_codex_adapter_deployments(root)
        assert len(pairs) == 3
        dests = {p[1].as_posix() for p in pairs}
        assert root.joinpath(".codex", "config.toml").as_posix() in dests
        assert root.joinpath(".codex", "hooks.json").as_posix() in dests
        assert root.joinpath(".codex", "hooks", "user_prompt_submit_router.py").as_posix() in dests
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_deploy_codex_adapter_writes_matching_content() -> None:
    repo = Path(__file__).resolve().parent.parent
    root = repo / "tests" / "_tmp_deploy" / uuid.uuid4().hex
    adapter = root / "kernel" / "templates" / "platform-adapters" / "codex"
    adapter.mkdir(parents=True)
    try:
        config = 'approval_policy = "on-request"\n'
        hooks = '{"hooks": {}}\n'
        verbose_hooks = '{"hooks": {"SessionStart": []}}\n'
        router = "#!/usr/bin/env python3\n"
        (adapter / "config.toml.template").write_text(config, encoding="utf-8")
        (adapter / "hooks.json.template").write_text(hooks, encoding="utf-8")
        (adapter / "hooks.verbose.json.template").write_text(verbose_hooks, encoding="utf-8")
        (adapter / "user_prompt_submit_router.py.template").write_text(router, encoding="utf-8")
        n, _ = deploy_codex_adapter(root, dry_run=False)
        assert n == 3
        assert (root / ".codex" / "config.toml").read_text(encoding="utf-8") == config
        assert (root / ".codex" / "hooks.json").read_text(encoding="utf-8") == hooks
        assert (root / ".codex" / "hooks" / "user_prompt_submit_router.py").read_text(
            encoding="utf-8"
        ) == router
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_deploy_codex_adapter_uses_verbose_template_when_local_marker_is_set() -> None:
    repo = Path(__file__).resolve().parent.parent
    root = repo / "tests" / "_tmp_deploy" / uuid.uuid4().hex
    adapter = root / "kernel" / "templates" / "platform-adapters" / "codex"
    adapter.mkdir(parents=True)
    try:
        config = 'approval_policy = "on-request"\n'
        hooks = '{"hooks": {}}\n'
        verbose_hooks = '{"hooks": {"SessionStart": []}}\n'
        router = "#!/usr/bin/env python3\n"
        (adapter / "config.toml.template").write_text(config, encoding="utf-8")
        (adapter / "hooks.json.template").write_text(hooks, encoding="utf-8")
        (adapter / "hooks.verbose.json.template").write_text(verbose_hooks, encoding="utf-8")
        (adapter / "user_prompt_submit_router.py.template").write_text(router, encoding="utf-8")
        (root / ".codex").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks.mode.local").write_text("verbose\n", encoding="utf-8")

        n, _ = deploy_codex_adapter(root, dry_run=False)

        assert n == 3
        assert (root / ".codex" / "hooks.json").read_text(encoding="utf-8") == verbose_hooks
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_lint_codex_hooks_allows_bash_pretooluse_permission_decision_script(tmp_path: Path) -> None:
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "hooks" / "pip-install-guard.py").write_text(
        "print('permissionDecision')\n",
        encoding="utf-8",
    )
    hooks_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'python3 "$(git rev-parse --show-toplevel)/.claude/hooks/pip-install-guard.py"',
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    assert lint_codex_hooks(tmp_path) == []


def test_lint_codex_hooks_warns_for_unsupported_pretooluse_surface(tmp_path: Path) -> None:
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    hooks_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Edit|Write",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 .claude/hooks/edit_pretooluse_orchestrator.py",
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    warnings = lint_codex_hooks(tmp_path)
    assert any("unsupported non-Bash or Write/Edit interception" in warning for warning in warnings)
    assert any("only emits Bash" in warning for warning in warnings)


def test_iter_cursor_rule_deployments_maps_templates() -> None:
    repo = Path(__file__).resolve().parent.parent
    root = repo / "tests" / "_tmp_deploy" / uuid.uuid4().hex
    adapter = root / "kernel" / "templates" / "platform-adapters" / "cursor"
    adapter.mkdir(parents=True)
    try:
        (adapter / "azoth-memory.mdc.template").write_text(
            "---\nx: 1\n---\nbody\n", encoding="utf-8"
        )
        (adapter / "claude-code-parity.mdc.template").write_text(
            "---\ny: 2\n---\n", encoding="utf-8"
        )
        pairs = iter_cursor_rule_deployments(root)
        assert len(pairs) == 2
        dests = {p[1].name for p in pairs}
        assert dests == {"azoth-memory.mdc", "claude-code-parity.mdc"}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_deploy_cursor_rules_writes_matching_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deploy to a non-.cursor path — some sandboxes block mkdir `.cursor/`."""
    repo = Path(__file__).resolve().parent.parent
    root = repo / "tests" / "_tmp_deploy" / uuid.uuid4().hex
    rules_out = root / "rules_out"
    adapter = root / "kernel" / "templates" / "platform-adapters" / "cursor"
    adapter.mkdir(parents=True)
    try:
        src = "---\nalwaysApply: true\n---\n\n# Rule\n"
        (adapter / "test-rule.mdc.template").write_text(src, encoding="utf-8")
        monkeypatch.setenv("AZOTH_CURSOR_RULES_DIR", str(rules_out))
        n, _ = deploy_cursor_rules(root, dry_run=False)
        assert n == 1
        out = rules_out / "test-rule.mdc"
        assert out.read_text(encoding="utf-8") == src
    finally:
        monkeypatch.delenv("AZOTH_CURSOR_RULES_DIR", raising=False)
        shutil.rmtree(root, ignore_errors=True)


# ── Deployed command parity (D46 / BL-023) ────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parent.parent
BL051_SPEC_PATH = _REPO_ROOT / ".azoth" / "roadmap-specs" / "v0.2.0" / "BL-051.yaml"
BL051_CLAUDE_MD_PATH = _REPO_ROOT / "CLAUDE.md"
BL051_ORCHESTRATOR_ARCHETYPE_PATH = _REPO_ROOT / "agents" / "tier1-core" / "orchestrator.agent.md"
BL051_REQUIRED_RUBRIC_LINES = (
    "Default to paragraph-led, information-dense explanations for human-facing non-operational responses; use bullets only when the content is inherently list-shaped.",
    "Use contrastive reasoning to make tradeoffs explicit instead of presenting disconnected facts in human-facing explanations.",
    "Preserve terse operational modes for status updates, approvals, gates, and explicit short-output requests.",
    "Keep agent-to-agent artifacts optimized for determinism and parseability, including BL-011 spawn payloads, BL-012 stage summaries, evaluator scorecards, planner task tables, reviewer findings blocks, and schema-bound YAML/JSON/TOML outputs.",
)


def _copy_repo_fixture_entry(relative_path: str, root: Path) -> None:
    source = _REPO_ROOT / relative_path
    destination = root / relative_path
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _stage_bl051_deploy_fixture(root: Path) -> None:
    for relative_path in (
        "agents/tier1-core/orchestrator.agent.md",
        "kernel/templates/platform-adapters/codex",
        "kernel/templates/platform-adapters/gemini",
    ):
        _copy_repo_fixture_entry(relative_path, root)


def test_bl051_spec_file_exists_and_has_required_shape() -> None:
    assert BL051_SPEC_PATH.is_file(), f"missing {BL051_SPEC_PATH.relative_to(_REPO_ROOT)}"

    data = yaml.safe_load(BL051_SPEC_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "BL-051 spec must be a YAML mapping"
    assert data.get("id") == "BL-051"
    assert isinstance(data.get("title"), str) and data["title"].strip(), (
        "BL-051 spec must define a non-empty title"
    )
    deploy_assertions = data.get("deploy_assertions")
    assert isinstance(deploy_assertions, list), "BL-051 spec must define deploy_assertions"
    for line in BL051_REQUIRED_RUBRIC_LINES:
        assert line in deploy_assertions, f"BL-051 spec missing deploy_assertion: {line!r}"


def test_bl051_claude_md_contains_required_rubric_lines() -> None:
    content = BL051_CLAUDE_MD_PATH.read_text(encoding="utf-8")
    for line in BL051_REQUIRED_RUBRIC_LINES:
        assert line in content, f"CLAUDE.md missing BL-051 rubric line: {line!r}"


def test_bl051_orchestrator_archetype_contains_required_rubric_lines() -> None:
    content = BL051_ORCHESTRATOR_ARCHETYPE_PATH.read_text(encoding="utf-8")
    for line in BL051_REQUIRED_RUBRIC_LINES:
        assert line in content, f"orchestrator.agent.md missing BL-051 rubric line: {line!r}"


def test_bl051_style_rubric_lines_propagate_to_deployed_orchestrator_outputs(
    tmp_path: Path,
) -> None:
    _stage_bl051_deploy_fixture(tmp_path)

    rc = main(
        [
            "--root",
            str(tmp_path),
            "--platforms",
            "claude",
            "copilot",
            "opencode",
            "codex",
            "gemini",
            "--copilot-agent-location",
            "both",
        ]
    )

    assert rc == 0

    for output_path in (
        tmp_path / ".claude" / "agents" / "orchestrator.md",
        tmp_path / ".github" / "agents" / "orchestrator.agent.md",
        tmp_path / ".opencode" / "agents" / "orchestrator.md",
        tmp_path / ".codex" / "agents" / "orchestrator.toml",
        tmp_path / ".gemini" / "agents" / "orchestrator.md",
    ):
        assert output_path.is_file(), f"missing deployed orchestrator output: {output_path}"
        content = output_path.read_text(encoding="utf-8")
        for line in BL051_REQUIRED_RUBRIC_LINES:
            assert line in content, f"{output_path.name} missing BL-051 rubric line: {line!r}"


def test_deployed_copilot_prompts_match_transform() -> None:
    """`.github/prompts/*.prompt.md` must match `transform_command_copilot` output."""
    commands = load_commands(_REPO_ROOT)
    assert commands, "expected .claude/commands/*.md"
    for cmd in commands:
        expected = transform_command_copilot(cmd)
        dest = _REPO_ROOT / ".github" / "prompts" / f"{cmd['name']}.prompt.md"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        actual = dest.read_text(encoding="utf-8")
        assert actual == expected, (
            f"Copilot prompt drift for {cmd['name']}: run python3 scripts/azoth-deploy.py"
        )


def test_deployed_claude_contract_commands_match_transform() -> None:
    """Contract-backed `.claude/commands/*.md` outputs must match the Claude transform."""
    commands = [cmd for cmd in load_commands(_REPO_ROOT) if "contract" in cmd]
    assert commands, "expected at least one contract-backed command"
    for cmd in commands:
        contract = cmd["contract"]
        claude_projection = contract.get("projection", {}).get("claude", {})
        dest = _REPO_ROOT / str(claude_projection["output_path"])
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        actual = dest.read_text(encoding="utf-8")
        expected = transform_command_claude(cmd)
        if actual == expected:
            continue
        if cmd["contract"]["body"]["mode"] == "legacy_claude_markdown":
            actual_meta, actual_body = parse_frontmatter(actual)
            expected_meta, expected_body = parse_frontmatter(expected)
            assert actual_meta == expected_meta and actual_body == expected_body, (
                f"Claude command semantic drift for {cmd['name']}: run python3 scripts/azoth-deploy.py"
            )
            continue
        assert actual == expected, (
            f"Claude command drift for {cmd['name']}: run python3 scripts/azoth-deploy.py"
        )


def test_deployed_opencode_commands_match_transform() -> None:
    """`.opencode/commands/*.md` must match `transform_command_opencode` output."""
    commands = load_commands(_REPO_ROOT)
    assert commands, "expected .claude/commands/*.md"
    for cmd in commands:
        expected = transform_command_opencode(cmd)
        dest = _REPO_ROOT / ".opencode" / "commands" / f"{cmd['name']}.md"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        actual = dest.read_text(encoding="utf-8")
        assert actual == expected, (
            f"OpenCode command drift for {cmd['name']}: run python3 scripts/azoth-deploy.py"
        )


def test_deployed_codex_command_wrappers_match_transform() -> None:
    """Codex command wrapper skills must match `transform_command_codex_skill` output."""
    commands = load_commands(_REPO_ROOT)
    assert commands, "expected command sources"
    for cmd in commands:
        dest = _REPO_ROOT / ".agents" / "skills" / f"azoth-{cmd['name']}" / "SKILL.md"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        actual = dest.read_text(encoding="utf-8")
        assert actual == transform_command_codex_skill(cmd), (
            f"Codex command skill drift for {cmd['name']}: run python3 scripts/azoth-deploy.py"
        )


def test_deployed_gemini_commands_match_transform() -> None:
    """`.gemini/commands/*.toml` must match the Gemini transform with stable names."""
    commands = load_commands(_REPO_ROOT)
    assert commands, "expected .claude/commands/*.md"
    for cmd in commands:
        expected = transform_command_gemini(cmd)
        deployed_name = gemini_command_name(cmd["name"])
        dest = _REPO_ROOT / ".gemini" / "commands" / f"{deployed_name}.toml"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        actual = dest.read_text(encoding="utf-8")
        assert actual == expected, (
            f"Gemini command drift for {cmd['name']}: run python3 scripts/azoth-deploy.py"
        )


def test_deployed_gemini_removes_legacy_conflicting_command_names() -> None:
    """Gemini command remaps must retire the old conflicting filenames."""
    commands = load_commands(_REPO_ROOT)
    assert commands, "expected .claude/commands/*.md"
    for cmd in commands:
        deployed_name = gemini_command_name(cmd["name"])
        if deployed_name == cmd["name"]:
            continue
        legacy_dest = _REPO_ROOT / ".gemini" / "commands" / f"{cmd['name']}.toml"
        assert not legacy_dest.exists(), (
            f"legacy Gemini command still present at {legacy_dest.relative_to(_REPO_ROOT)}"
        )


def test_deployed_codex_agents_match_transform() -> None:
    """`.codex/agents/*.toml` must match `transform_agent_codex` output."""
    agents = load_agents(_REPO_ROOT)
    assert agents, "expected agents/**/*.agent.md"
    for agent in agents:
        expected = transform_agent_codex(agent)
        dest = _REPO_ROOT / ".codex" / "agents" / f"{agent['meta']['name']}.toml"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        actual = dest.read_text(encoding="utf-8")
        assert actual == expected, (
            f"Codex agent drift for {agent['meta']['name']}: run python3 scripts/azoth-deploy.py"
        )


def test_deployed_codex_skill_mirror_matches_canonical() -> None:
    """`.agents/skills/` must mirror the shared-surface transform used by Codex/Gemini/Antigravity."""
    skills = load_skills(_REPO_ROOT)
    assert skills, "expected skills/**/SKILL.md"
    for skill in skills:
        dest = _REPO_ROOT / ".agents" / "skills" / shared_skill_name(skill["name"]) / "SKILL.md"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        assert dest.read_text(encoding="utf-8") == transform_shared_skill(skill), (
            f"Shared skill drift for {skill['name']}: run python3 scripts/azoth-deploy.py"
        )


def test_deployed_gemini_uses_shared_agents_skill_surface() -> None:
    """Gemini CLI must use the shared `.agents/skills/` mirror and retire `.gemini/skills/`."""
    skills = load_skills(_REPO_ROOT)
    assert skills, "expected skills/**/SKILL.md"
    for skill in skills:
        shared_dest = (
            _REPO_ROOT / ".agents" / "skills" / shared_skill_name(skill["name"]) / "SKILL.md"
        )
        assert shared_dest.is_file(), (
            f"missing {shared_dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        assert shared_dest.read_text(encoding="utf-8") == transform_shared_skill(skill), (
            f"Gemini shared skill drift for {skill['name']}: run python3 scripts/azoth-deploy.py"
        )
        legacy_dest = _REPO_ROOT / ".gemini" / "skills" / skill["name"] / "SKILL.md"
        assert not legacy_dest.exists(), (
            f"legacy Gemini skill mirror still present at {legacy_dest.relative_to(_REPO_ROOT)}"
        )


def test_deployed_agents_skill_surface_has_no_stale_non_azoth_entries() -> None:
    """`.agents/skills/` must be an Azoth-managed mirror, not an append-only cache."""
    expected = {shared_skill_name(skill["name"]) for skill in load_skills(_REPO_ROOT)}
    skill_root = _REPO_ROOT / ".agents" / "skills"
    assert skill_root.is_dir(), "missing .agents/skills — run: python3 scripts/azoth-deploy.py"
    unexpected = sorted(
        path.name
        for path in skill_root.iterdir()
        if path.is_dir() and path.name not in expected and not path.name.startswith("azoth-")
    )
    assert unexpected == [], (
        ".agents/skills contains stale non-Azoth entries: "
        + ", ".join(unexpected)
        + " — run python3 scripts/azoth-deploy.py"
    )


# ── P1-013: Orchestrator binding tests ──────────────────────────────────────

_PIPELINE_CMD_NAMES = ("auto", "dynamic-full-auto", "deliver", "deliver-full")

_SESSION_ENTRY_CMD_NAMES = ("start", "next", "resume")

_REQUIRED_ORCHESTRATOR_SECTIONS = (
    "## Inline vs Orchestrate",
    "## Goal Clarification",
    "## Declaration Ownership",
    "## Pipeline Composition",
    "## Mid-Pipeline Adaptation",
    "## Model Tiering",
    "## Token Budget",
    "## Session Lifecycle",
    "## Memory Integration",
    "## Gate Handling",
    "## Architect as Spawned Role",
    "## Error Recovery",
    "## Platform Parity",
)


def test_transform_command_copilot_preserves_orchestrator_agent_field() -> None:
    """T1: transform_command_copilot passes through agent: orchestrator — GREEN immediately."""
    cmd = {
        "name": "auto",
        "meta": {"description": "Auto pipeline", "agent": "orchestrator"},
        "body": "# /auto $ARGUMENTS\n\nClassify and execute.\n",
    }
    out = transform_command_copilot(cmd)
    meta, _ = parse_frontmatter(out)
    assert meta.get("agent") == "orchestrator", (
        "transform_command_copilot must preserve agent: orchestrator field"
    )


def test_copilot_pipeline_prompts_have_orchestrator_agent_binding() -> None:
    """T2: deployed pipeline prompts must have agent: orchestrator."""
    for name in _PIPELINE_CMD_NAMES:
        dest = _REPO_ROOT / ".github" / "prompts" / f"{name}.prompt.md"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        meta, _ = parse_frontmatter(dest.read_text(encoding="utf-8"))
        assert meta.get("agent") == "orchestrator", (
            f"{dest.name}: expected agent: orchestrator, got {meta.get('agent')!r}"
        )


def test_opencode_pipeline_commands_have_orchestrator_agent_binding() -> None:
    """T3: deployed pipeline commands must have agent: orchestrator."""
    for name in _PIPELINE_CMD_NAMES:
        dest = _REPO_ROOT / ".opencode" / "commands" / f"{name}.md"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        meta, _ = parse_frontmatter(dest.read_text(encoding="utf-8"))
        assert meta.get("agent") == "orchestrator", (
            f"{dest.name}: expected agent: orchestrator, got {meta.get('agent')!r}"
        )


def test_orchestrator_claude_agent_deployed_with_required_body_sections() -> None:
    """T4: .claude/agents/orchestrator.md must exist with all 7 required body sections."""
    dest = _REPO_ROOT / ".claude" / "agents" / "orchestrator.md"
    assert dest.is_file(), (
        "missing .claude/agents/orchestrator.md — run: python3 scripts/azoth-deploy.py"
    )
    content = dest.read_text(encoding="utf-8")
    for section in _REQUIRED_ORCHESTRATOR_SECTIONS:
        assert section in content, f"orchestrator.md missing required section: {section!r}"


def test_deployed_copilot_prompts_match_transform_with_orchestrator() -> None:
    """T5: pipeline prompt parity — .github/prompts/ matches transform output including agent: orchestrator."""
    commands = load_commands(_REPO_ROOT)
    pipeline_cmds = [c for c in commands if c["name"] in _PIPELINE_CMD_NAMES]
    assert len(pipeline_cmds) == len(_PIPELINE_CMD_NAMES), (
        f"expected all {len(_PIPELINE_CMD_NAMES)} pipeline commands, found {[c['name'] for c in pipeline_cmds]}"
    )
    for cmd in pipeline_cmds:
        expected = transform_command_copilot(cmd)
        dest = _REPO_ROOT / ".github" / "prompts" / f"{cmd['name']}.prompt.md"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        actual = dest.read_text(encoding="utf-8")
        assert actual == expected, (
            f"Pipeline prompt drift for {cmd['name']}: run python3 scripts/azoth-deploy.py"
        )


def test_source_session_entry_commands_have_orchestrator_agent_field() -> None:
    """T6: source session-entry commands must have agent: orchestrator."""
    for name in _SESSION_ENTRY_CMD_NAMES:
        src = _REPO_ROOT / ".claude" / "commands" / f"{name}.md"
        assert src.is_file(), f"missing source command {name}.md"
        meta, _ = parse_frontmatter(src.read_text(encoding="utf-8"))
        assert meta.get("agent") == "orchestrator", (
            f"{name}.md: expected agent: orchestrator, got {meta.get('agent')!r}"
        )


def test_copilot_session_entry_prompts_have_orchestrator_agent_binding() -> None:
    """T7: deployed session-entry prompts must have agent: orchestrator."""
    for name in _SESSION_ENTRY_CMD_NAMES:
        dest = _REPO_ROOT / ".github" / "prompts" / f"{name}.prompt.md"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        meta, _ = parse_frontmatter(dest.read_text(encoding="utf-8"))
        assert meta.get("agent") == "orchestrator", (
            f"{dest.name}: expected agent: orchestrator, got {meta.get('agent')!r}"
        )


def test_opencode_session_entry_commands_have_orchestrator_agent_binding() -> None:
    """T8: deployed session-entry commands must have agent: orchestrator."""
    for name in _SESSION_ENTRY_CMD_NAMES:
        dest = _REPO_ROOT / ".opencode" / "commands" / f"{name}.md"
        assert dest.is_file(), (
            f"missing {dest.relative_to(_REPO_ROOT)} — run: python3 scripts/azoth-deploy.py"
        )
        meta, _ = parse_frontmatter(dest.read_text(encoding="utf-8"))
        assert meta.get("agent") == "orchestrator", (
            f"{dest.name}: expected agent: orchestrator, got {meta.get('agent')!r}"
        )


def test_orchestrator_archetype_has_intelligence_sections() -> None:
    """T9: orchestrator archetype must contain all required intelligence sections."""
    src = _REPO_ROOT / "agents" / "tier1-core" / "orchestrator.agent.md"
    assert src.is_file(), "missing agents/tier1-core/orchestrator.agent.md"
    content = src.read_text(encoding="utf-8")
    for section in _REQUIRED_ORCHESTRATOR_SECTIONS:
        assert section in content, f"orchestrator.agent.md missing required section: {section!r}"


def test_orchestrator_archetype_line_count_ceiling() -> None:
    """T10: orchestrator archetype must be ≤ 400 lines."""
    src = _REPO_ROOT / "agents" / "tier1-core" / "orchestrator.agent.md"
    assert src.is_file(), "missing agents/tier1-core/orchestrator.agent.md"
    lines = src.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 400, (
        f"orchestrator.agent.md is {len(lines)} lines, exceeds 400-line ceiling"
    )


def test_orchestrator_requires_official_source_research_for_current_external_facts() -> None:
    content = (_REPO_ROOT / "agents" / "tier1-core" / "orchestrator.agent.md").read_text(
        encoding="utf-8"
    )
    assert "official-source research pass before analysis, routing, or edits" in content
    assert "latest/current external facts are material" in content


def test_dynamic_full_auto_requires_wave_a_for_latest_external_facts() -> None:
    content = (_REPO_ROOT / "skills" / "dynamic-full-auto" / "SKILL.md").read_text(encoding="utf-8")
    assert "Wave A is mandatory" in content
    assert "official sources before Checkpoint" in content
    assert "max_threads: 10, max_depth: 2" in content


def test_subagent_router_defines_execution_budget_for_bounded_nesting() -> None:
    content = (_REPO_ROOT / "skills" / "subagent-router" / "SKILL.md").read_text(encoding="utf-8")
    for needle in (
        "execution_budget",
        "child_fanout_cap",
        "depth_remaining",
        "leaf-only",
        "`research-orchestrator`",
        "`architect`",
    ):
        assert needle in content, f"skills/subagent-router/SKILL.md missing {needle!r}"


def test_adaptive_swarm_sources_drop_fixed_fanout_numbers() -> None:
    for rel in (
        "agents/tier1-core/orchestrator.agent.md",
        "skills/dynamic-full-auto/SKILL.md",
        ".claude/workflows/enterprise/e2e-swarm-eval-loop.md",
    ):
        content = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "active platform execution budget" in content, f"{rel} missing budget-driven wording"
        assert "≤7" not in content, f"{rel} still contains stale fixed fan-out wording"
    dynamic = (_REPO_ROOT / "skills" / "dynamic-full-auto" / "SKILL.md").read_text(encoding="utf-8")
    assert "4–7" not in dynamic
    assert "4-7" not in dynamic


def test_all_source_commands_have_orchestrator_agent_binding() -> None:
    """T11: every .claude/commands/*.md must have agent: orchestrator to prevent
    Copilot agent reset when invoking any Azoth command."""
    cmd_dir = _REPO_ROOT / ".claude" / "commands"
    assert cmd_dir.is_dir(), "missing .claude/commands/"
    missing = []
    for path in sorted(cmd_dir.glob("*.md")):
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("agent") != "orchestrator":
            missing.append(path.name)
    assert not missing, f"source commands missing agent: orchestrator: {missing}"


def test_all_copilot_prompts_have_orchestrator_agent_binding() -> None:
    """T12: every .github/prompts/*.prompt.md must have agent: orchestrator."""
    prompt_dir = _REPO_ROOT / ".github" / "prompts"
    assert prompt_dir.is_dir(), "missing .github/prompts/"
    missing = []
    for path in sorted(prompt_dir.glob("*.prompt.md")):
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("agent") != "orchestrator":
            missing.append(path.name)
    assert not missing, f"Copilot prompts missing agent: orchestrator: {missing}"


# ── --check mode ──────────────────────────────────────────────────────────────


def test_check_mode_clean_returns_zero(tmp_path: Path) -> None:
    """Deploy then --check → exit 0 (everything in sync)."""
    _write_minimal_agent(tmp_path)
    _write_minimal_command(tmp_path)

    rc = main(["--root", str(tmp_path), "--platforms", "copilot"])
    assert rc == 0

    rc = main(["--root", str(tmp_path), "--platforms", "copilot", "--check"])
    assert rc == 0


def test_load_commands_prefers_canonical_contract_and_resolves_body(tmp_path: Path) -> None:
    _write_contract_command(tmp_path)
    commands = load_commands(tmp_path)
    assert len(commands) == 1
    cmd = commands[0]
    assert cmd["name"] == "next"
    assert cmd["meta"]["description"] == "Canonical next description"
    assert cmd["contract_path"] == "commands/next/command.yaml"
    assert cmd["body_source_path"] == ".claude/commands/next.md"
    assert cmd["body"].startswith("# /next")
    assert "Legacy next description" not in cmd["body"]


def test_transform_command_codex_skill_uses_contract_path_when_present(tmp_path: Path) -> None:
    _write_contract_command(tmp_path)
    cmd = load_commands(tmp_path)[0]
    rendered = transform_command_codex_skill(cmd)
    assert "commands/next/command.yaml" in rendered
    assert ".claude/commands/next.md" in rendered


def test_load_commands_resolves_canonical_markdown_body(tmp_path: Path) -> None:
    command_path = tmp_path / "commands" / "start" / "command.yaml"
    command_path.parent.mkdir(parents=True, exist_ok=True)
    command_path.write_text(
        "schema_version: 1\n"
        "name: start\n"
        "display_name: /start\n"
        "description: Canonical start description\n"
        "agent: orchestrator\n"
        "azoth_effect: read\n"
        "body:\n"
        "  mode: canonical_markdown\n"
        "  source_path: commands/start/body.md\n",
        encoding="utf-8",
    )
    body_path = tmp_path / "commands" / "start" / "body.md"
    body_path.write_text("# /start\n\nUse the canonical body.\n", encoding="utf-8")

    commands = load_commands(tmp_path)
    assert len(commands) == 1
    cmd = commands[0]
    assert cmd["name"] == "start"
    assert cmd["contract_path"] == "commands/start/command.yaml"
    assert cmd["body_source_path"] == "commands/start/body.md"
    assert cmd["body"].startswith("# /start")
    assert "canonical body" in cmd["body"]


@pytest.mark.parametrize(
    ("command_name", "body_source_path"),
    [
        ("deliver", ".claude/commands/deliver.md"),
        ("deliver-full", ".claude/commands/deliver-full.md"),
        ("auto", ".claude/commands/auto.md"),
        ("plan", ".claude/commands/plan.md"),
        ("test", ".claude/commands/test.md"),
        ("eval", ".claude/commands/eval.md"),
        ("eval-swarm", ".claude/commands/eval-swarm.md"),
        ("hookmode", ".claude/commands/hookmode.md"),
        ("session-closeout", "commands/session-closeout/body.md"),
        ("remember", ".claude/commands/remember.md"),
        ("sync", ".claude/commands/sync.md"),
        ("roadmap", ".claude/commands/roadmap.md"),
    ],
)
def test_migrated_commands_load_from_canonical_contracts(
    command_name: str, body_source_path: str
) -> None:
    commands = {cmd["name"]: cmd for cmd in load_commands(_REPO_ROOT)}
    cmd = commands[command_name]
    assert cmd["contract_path"] == f"commands/{command_name}/command.yaml"
    assert cmd["body_source_path"] == body_source_path
    assert cmd["body"].startswith(f"# /{command_name}")


def test_ini_plt_006_exit_commands_are_canonicalized() -> None:
    commands = {cmd["name"]: cmd for cmd in load_commands(_REPO_ROOT)}
    for command_name in ("session-closeout", "remember", "sync", "roadmap", "hookmode"):
        assert "contract" in commands[command_name], (
            f"INI-PLT-006 exit evidence missing canonical contract for {command_name}"
        )


def test_t003_delivery_orchestration_family_is_canonicalized() -> None:
    commands = {cmd["name"]: cmd for cmd in load_commands(_REPO_ROOT)}
    for command_name in (
        "deliver",
        "plan",
        "test",
        "auto",
        "deliver-full",
        "eval",
        "eval-swarm",
    ):
        assert "contract" in commands[command_name], (
            f"T-003 migration incomplete: expected canonical contract for {command_name}"
        )


@pytest.mark.parametrize(
    ("command_name", "azoth_effect", "gemini_output_path"),
    [
        ("plan", "read", ".gemini/commands/workspace.plan.toml"),
        ("test", "write", ".gemini/commands/test.toml"),
        ("eval-swarm", "mixed", ".gemini/commands/eval-swarm.toml"),
    ],
)
def test_bl057_residual_bundle_contract_metadata_is_complete_and_consistent(
    command_name: str, azoth_effect: str, gemini_output_path: str
) -> None:
    commands = {cmd["name"]: cmd for cmd in load_commands(_REPO_ROOT)}
    cmd = commands[command_name]
    contract = cmd["contract"]

    assert contract["schema_version"] == 1
    assert contract["name"] == command_name
    assert contract["display_name"] == f"/{command_name}"
    assert contract["agent"] == "orchestrator"
    assert contract["azoth_effect"] == azoth_effect

    assert contract["body"] == {
        "mode": "legacy_claude_markdown",
        "source_path": f".claude/commands/{command_name}.md",
    }
    assert cmd["contract_path"] == f"commands/{command_name}/command.yaml"
    assert cmd["body_source_path"] == f".claude/commands/{command_name}.md"

    assert contract["migration"]["phase"] == "canonical_body_batch_2_residual_bundle"
    assert contract["migration"]["runtime_source_of_truth"] == cmd["contract_path"]
    assert any("BL-057" in note for note in contract["migration"]["notes"])
    assert any(cmd["body_source_path"] in note for note in contract["migration"]["notes"])

    assert contract["references"] == [
        ".azoth/roadmap-specs/v0.2.0/T-003.yaml",
        "docs/CANONICAL_COMMAND_CONTRACT.md",
    ]

    assert contract["projection"] == {
        "claude": {
            "kind": "native_command_markdown",
            "output_path": f".claude/commands/{command_name}.md",
        },
        "cursor": {
            "kind": "claude_command_toggle_surface",
            "output_path": f".claude/commands/{command_name}.md",
        },
        "copilot": {
            "kind": "prompt_markdown",
            "output_path": f".github/prompts/{command_name}.prompt.md",
        },
        "opencode": {
            "kind": "native_command_markdown",
            "output_path": f".opencode/commands/{command_name}.md",
        },
        "codex": {
            "kind": "skill_wrapper",
            "output_path": f".agents/skills/azoth-{command_name}/SKILL.md",
            "metadata_path": f".agents/skills/azoth-{command_name}/agents/openai.yaml",
        },
        "gemini": {
            "kind": "native_command_toml",
            "output_path": gemini_output_path,
        },
        "antigravity": {
            "kind": "workflow_markdown",
            "output_path": f".agents/workflows/{command_name}.md",
        },
    }


def test_check_mode_stale_returns_one(tmp_path: Path) -> None:
    """Deploy, mutate a mirror file, then --check → exit 1."""
    _write_minimal_agent(tmp_path)
    _write_minimal_command(tmp_path)

    rc = main(["--root", str(tmp_path), "--platforms", "copilot"])
    assert rc == 0

    # Corrupt a deployed file
    agent_mirror = tmp_path / ".claude" / "agents" / "architect.md"
    assert agent_mirror.is_file()
    agent_mirror.write_text("corrupted content", encoding="utf-8")

    rc = main(["--root", str(tmp_path), "--platforms", "copilot", "--check"])
    assert rc == 1


def test_check_mode_missing_returns_one(tmp_path: Path) -> None:
    """Deploy, delete a mirror file, then --check → exit 1."""
    _write_minimal_agent(tmp_path)
    _write_minimal_command(tmp_path)

    rc = main(["--root", str(tmp_path), "--platforms", "copilot"])
    assert rc == 0

    # Remove a deployed file
    agent_mirror = tmp_path / ".claude" / "agents" / "architect.md"
    assert agent_mirror.is_file()
    agent_mirror.unlink()

    rc = main(["--root", str(tmp_path), "--platforms", "copilot", "--check"])
    assert rc == 1


def test_check_and_dry_run_mutually_exclusive() -> None:
    """--check and --dry-run together → SystemExit(2) from argparse."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--check", "--dry-run"])
    assert exc_info.value.code == 2


def test_check_mode_does_not_write(tmp_path: Path) -> None:
    """Running --check on a missing file must NOT create it."""
    _write_minimal_agent(tmp_path)
    _write_minimal_command(tmp_path)

    # Run check without prior deploy — files should be missing
    agent_mirror = tmp_path / ".claude" / "agents" / "architect.md"
    assert not agent_mirror.exists()

    rc = main(["--root", str(tmp_path), "--platforms", "copilot", "--check"])
    assert rc == 1

    # The file must still not exist
    assert not agent_mirror.exists()

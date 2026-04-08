"""
Unit tests for scripts/azoth-deploy.py.

Covers:
- parse_frontmatter: valid, missing, unclosed, "---" inside YAML value (regression)
- posture_to_permissions: tier baseline, keyword narrowing, word-boundary regression
- transform_agent_claude: correct fields, Azoth fields stripped
- transform_agent_copilot: name/description required, tools/model optional
- transform_agent_opencode: no name field, mode from tier, permission object
- transform_command_copilot: mode:agent added
- transform_command_opencode: description preserved, body unchanged
- deployed command parity: .github/prompts + .opencode/commands match transforms (D46, BL-023)
"""

from __future__ import annotations

import importlib.util
import shutil
import uuid
from pathlib import Path

import pytest

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
transform_agent_opencode = _mod.transform_agent_opencode
transform_command_copilot = _mod.transform_command_copilot
transform_command_opencode = _mod.transform_command_opencode
iter_cursor_rule_deployments = _mod.iter_cursor_rule_deployments
deploy_cursor_rules = _mod.deploy_cursor_rules
load_commands = _mod.load_commands


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


def test_opencode_command_no_description_no_frontmatter() -> None:
    cmd = {"name": "bare", "meta": {}, "body": "# bare\nDo the thing.\n"}
    out = transform_command_opencode(cmd)
    assert not out.startswith("---")
    assert "Do the thing." in out


# ── Cursor rule deployment ────────────────────────────────────────────────────


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
        n = deploy_cursor_rules(root, dry_run=False)
        assert n == 1
        out = rules_out / "test-rule.mdc"
        assert out.read_text(encoding="utf-8") == src
    finally:
        monkeypatch.delenv("AZOTH_CURSOR_RULES_DIR", raising=False)
        shutil.rmtree(root, ignore_errors=True)


# ── Deployed command parity (D46 / BL-023) ────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parent.parent


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

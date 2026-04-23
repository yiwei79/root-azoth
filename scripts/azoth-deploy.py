#!/usr/bin/env python3
"""
azoth-deploy.py — Translate canonical Azoth sources into platform-specific deployed files.

Transforms:
  agents/**/*.agent.md  →  .claude/agents/<name>.md            (Claude Code)
                                                →  .github/agents/<name>.agent.md      (GitHub Copilot compatibility mirror)
                        →  .opencode/agents/<name>.md          (OpenCode)
                        →  .codex/agents/<name>.toml           (Codex custom agents)
  commands/<name>/command.yaml
                        →  .claude/commands/<name>.md          (Claude Code, when contract-backed)
                        →  .github/prompts/<name>.prompt.md    (Copilot)
                        →  .opencode/commands/<name>.md        (OpenCode)
                        →  .agents/skills/azoth-<name>/...     (Codex explicit command-wrapper skills)
  .claude/commands/*.md →  same deploy targets as legacy fallback when no canonical contract exists
    skills/**/SKILL.md    →  .opencode/skills/<name>/SKILL.md   (OpenCode per-subdirectory)
                                                →  .agents/skills/<name>/SKILL.md     (Codex / Gemini / Antigravity shared skill path)
  kernel/templates/platform-adapters/cursor/*.mdc.template
                        →  .cursor/rules/<name>.mdc            (Cursor IDE always-on rules)
  kernel/templates/platform-adapters/codex/*.template
                        →  .codex/*                            (Codex project adapter files)
  (synthesized)         →  AGENTS.md                          (AAIF cross-platform broadcast)

Usage:
  python scripts/azoth-deploy.py
  python scripts/azoth-deploy.py --dry-run
  python scripts/azoth-deploy.py --platforms claude copilot
    python scripts/azoth-deploy.py --platforms copilot --copilot-agent-location claude
  python scripts/azoth-deploy.py --platforms cursor
  python scripts/azoth-deploy.py --platforms codex
  python scripts/azoth-deploy.py --root /path/to/project

Environment:
  AZOTH_CURSOR_RULES_DIR  If set, deploy Cursor *.mdc templates to this directory instead
                          of <root>/.cursor/rules (tests; sandboxes that block .cursor/).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml
from yaml_helpers import safe_load_yaml

CODEX_HOOKS_DEFAULT_TEMPLATE = "hooks.json.template"
CODEX_HOOKS_VERBOSE_TEMPLATE = "hooks.verbose.json.template"
CODEX_CONFIG_DEFAULT_TEMPLATE = "config.toml.template"
CODEX_CONFIG_SEAMLESS_TEMPLATE = "config.seamless.toml.template"
CODEX_RULES_TEMPLATE = "azoth-seamless.star.template"


# ── Frontmatter helpers ──────────────────────────────────────────────────────


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from body text. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    # Anchor to line start to avoid matching "---" inside YAML string values.
    try:
        end = text.index("\n---", 3)
    except ValueError:
        return {}, text
    meta = safe_load_yaml(text[3:end]) or {}
    body = text[end + 4 :].lstrip("\n")
    return meta, body


def render_frontmatter(data: dict[str, Any]) -> str:
    """Render a dict as a YAML frontmatter block."""
    return (
        "---\n"
        + yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        + "---\n\n"
    )


def render_yaml_document(data: dict[str, Any]) -> str:
    """Render a plain YAML document with stable formatting."""
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


# ── Posture → OpenCode permission mapping ────────────────────────────────────

# Tier-based baseline permissions (permissive for orchestrators, restricted for meta agents).
# Rationale: Tier 1 orchestrators need broad tool access; Tier 3 meta agents should
# not run bash by default (they inspect and evaluate, not execute).
_TIER_BASE_PERMS: dict[int, dict[str, str]] = {
    1: {"edit": "allow", "bash": "ask", "webfetch": "allow", "task": "allow"},
    2: {"edit": "ask", "bash": "ask", "webfetch": "allow", "task": "allow"},
    3: {"edit": "ask", "bash": "deny", "webfetch": "allow", "task": "ask"},
    4: {"edit": "allow", "bash": "ask", "webfetch": "ask", "task": "ask"},
}

_DEFAULT_PERMS: dict[str, str] = {"edit": "ask", "bash": "ask", "webfetch": "allow", "task": "ask"}

# Keywords to match posture item text against OpenCode tool names.
# Used to tighten tier baseline based on ask_first / never_auto content.
_TOOL_KEYWORDS: dict[str, set[str]] = {
    "edit": {"kernel", "governance", "file", "write", "modify", "create", "delete", "edit"},
    "bash": {"execute", "script", "command", "run", "shell", "bash", "hook"},
    "webfetch": {"web", "search", "fetch", "online", "internet", "lookup"},
    "task": {"agent", "subagent", "invoke", "spawn", "delegate", "orchestrat", "pipeline self"},
}

# Canonical Never-Auto lines — kernel/GOVERNANCE.md §5 Default Posture (D26). Merged with
# per-agent `never_auto` when computing OpenCode permissions so empty YAML lists stay
# fail-closed vs keyword tightening (BL-015).
UNIVERSAL_NEVER_AUTO: tuple[str, ...] = (
    "Kernel modifications",
    "Governance changes",
    "Dependency additions",
    "Pipeline self-modification",
    "Memory M2 → M1 promotion",
    "File deletion",
)


def _normalize_posture_line(s: str) -> str:
    return s.strip().lower()


def merge_never_auto(agent_never_auto: list[str] | None) -> list[str]:
    """
    Union universal Never-Auto with per-agent lines; dedupe; universal order first,
    then agent-only lines in first-seen order.
    """
    uni_norm = {_normalize_posture_line(x) for x in UNIVERSAL_NEVER_AUTO}
    out: list[str] = list(UNIVERSAL_NEVER_AUTO)
    seen: set[str] = set(uni_norm)
    for raw in agent_never_auto or []:
        n = _normalize_posture_line(raw)
        if n in uni_norm:
            continue
        if n in seen:
            continue
        out.append(raw)
        seen.add(n)
    return out


def effective_posture_for_permissions(posture: dict[str, list[str]]) -> dict[str, list[str]]:
    """Shallow copy of posture with `never_auto` merged for permission mapping."""
    eff: dict[str, list[str]] = {}
    for k, v in posture.items():
        if isinstance(v, list):
            eff[k] = list(v)
        else:
            eff[k] = v  # type: ignore[assignment]
    na = eff.get("never_auto")
    if not isinstance(na, list):
        na = []
    eff["never_auto"] = merge_never_auto(na)
    return eff


def posture_to_permissions(tier: int, posture: dict[str, list[str]]) -> dict[str, str]:
    """
    Map an Azoth posture block to an OpenCode permission object.

    Applies tier-based baseline, then tightens based on keyword scanning of
    never_auto and ask_first items. 'allow' can be narrowed to 'ask'; 'deny'
    from the baseline is never relaxed.
    """
    perms = dict(_TIER_BASE_PERMS.get(tier, _DEFAULT_PERMS))

    # D46 spec says never_auto → deny, but "deny" in OpenCode completely blocks the tool.
    # "ask" better matches the intent: confirmation required, not capability removal.
    # Both never_auto and ask_first items narrow "allow" → "ask" via keyword scan.
    # "deny" from the tier baseline is never relaxed.
    restricted = posture.get("never_auto", []) + posture.get("ask_first", [])
    for item in restricted:
        item_lower = item.lower()
        for tool, keywords in _TOOL_KEYWORDS.items():
            if (
                any(re.search(r"\b" + re.escape(kw) + r"\b", item_lower) for kw in keywords)
                and perms[tool] == "allow"
            ):
                perms[tool] = "ask"

    return perms


# ── Source loaders ───────────────────────────────────────────────────────────


def load_agents(root: Path) -> list[dict[str, Any]]:
    """Load all agent definitions from agents/**/*.agent.md."""
    agents = []
    for path in sorted(root.glob("agents/**/*.agent.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        if "name" not in meta:
            print(f"  warning: skipping {path} — no 'name' in frontmatter", file=sys.stderr)
            continue
        agents.append({"path": path, "meta": meta, "body": body})
    return agents


def _normalize_command_meta(
    contract: dict[str, Any],
    legacy_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the metadata fields consumed by deploy transforms."""
    meta: dict[str, Any] = {}
    for field in ("description", "agent", "azoth_effect"):
        value = contract.get(field)
        if value is not None:
            meta[field] = value
    if legacy_meta:
        for field in ("description", "agent", "azoth_effect"):
            if field not in meta and field in legacy_meta:
                meta[field] = legacy_meta[field]
    return meta


def _load_command_contract(root: Path, path: Path) -> dict[str, Any]:
    """Load one canonical command contract plus its resolved markdown body."""
    contract = safe_load_yaml(path.read_text(encoding="utf-8")) or {}
    if not isinstance(contract, dict):
        raise ValueError(f"{path}: command contract root must be a mapping")

    name = str(contract.get("name") or path.parent.name).strip()
    if not name:
        raise ValueError(f"{path}: command contract missing name")

    body_cfg = contract.get("body") or {}
    if not isinstance(body_cfg, dict):
        raise ValueError(f"{path}: body must be a mapping")

    body_mode = str(body_cfg.get("mode") or "").strip()
    body_source_path: Path | None = None
    legacy_meta: dict[str, Any] | None = None

    if body_mode == "legacy_claude_markdown":
        source_rel = str(body_cfg.get("source_path") or "").strip()
        if not source_rel:
            raise ValueError(f"{path}: legacy_claude_markdown requires body.source_path")
        body_source_path = root / source_rel
        legacy_text = body_source_path.read_text(encoding="utf-8")
        legacy_meta, body = parse_frontmatter(legacy_text)
    elif body_mode == "canonical_markdown":
        source_rel = str(body_cfg.get("source_path") or "").strip()
        body_source_path = root / source_rel if source_rel else path.parent / "body.md"
        body = body_source_path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"{path}: unsupported body.mode {body_mode!r}")

    return {
        "path": path,
        "name": name,
        "meta": _normalize_command_meta(contract, legacy_meta),
        "body": body,
        "contract": contract,
        "contract_path": path.relative_to(root).as_posix(),
        "body_source_path": body_source_path.relative_to(root).as_posix()
        if body_source_path is not None
        else None,
    }


def load_commands(root: Path) -> list[dict[str, Any]]:
    """Load commands with canonical contracts taking precedence over legacy markdown."""
    commands_by_name: dict[str, dict[str, Any]] = {}

    cmd_dir = root / ".claude" / "commands"
    if cmd_dir.is_dir():
        for path in sorted(cmd_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(text)
            commands_by_name[path.stem] = {
                "path": path,
                "name": path.stem,
                "meta": meta,
                "body": body,
            }

    contract_dir = root / "commands"
    if contract_dir.is_dir():
        for path in sorted(contract_dir.glob("*/command.yaml")):
            command = _load_command_contract(root, path)
            commands_by_name[command["name"]] = command

    return [commands_by_name[name] for name in sorted(commands_by_name)]


def load_skills(root: Path) -> list[dict[str, Any]]:
    """Load all skills from skills/**/SKILL.md."""
    skills = []
    for path in sorted(root.glob("skills/**/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        name = path.parent.name
        skills.append({"path": path, "name": name, "meta": meta, "body": body, "raw": text})
    return skills


# ── Agent transformations ────────────────────────────────────────────────────


def _description(meta: dict[str, Any]) -> str:
    """Derive a display description from available frontmatter fields."""
    return str(meta.get("description") or meta.get("role") or meta.get("name", ""))


def _toml_escape_basic(value: str) -> str:
    """Escape a TOML basic string value for one-line fields."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_multiline_literal(value: str) -> str:
    """Render a TOML multiline literal string."""
    if "'''" in value:
        raise ValueError("TOML multiline literal strings cannot contain triple single quotes")
    body = value.rstrip("\n")
    return "'''\n" + body + "\n'''"


def transform_agent_claude(agent: dict[str, Any]) -> str:
    """
    Claude Code agent format (.claude/agents/<name>.md).
    Frontmatter: name, description, model (optional).
    Body: source body passed through (contains full instructions).
    Azoth-specific fields (tier, role, skills, posture, etc.) are stripped.
    """
    meta = agent["meta"]
    fm: dict[str, Any] = {"name": meta["name"], "description": _description(meta)}
    if "model" in meta:
        fm["model"] = meta["model"]
    return render_frontmatter(fm) + agent["body"]


def transform_agent_copilot(agent: dict[str, Any]) -> str:
    """
    Copilot compatibility mirror format (.github/agents/<name>.agent.md).
    Frontmatter: name, description (required), tools (optional), model (optional).
    """
    meta = agent["meta"]
    fm: dict[str, Any] = {"name": meta["name"], "description": _description(meta)}
    if tools := meta.get("tools"):
        fm["tools"] = tools
    if "model" in meta:
        fm["model"] = meta["model"]
    return render_frontmatter(fm) + agent["body"]


def transform_agent_opencode(agent: dict[str, Any]) -> str:
    """
    OpenCode agent format (.opencode/agents/<name>.md).
    No name field — identity is derived from filename.
    Frontmatter: description, mode (inferred from tier), model (optional),
                 permission object (mapped from posture via posture_to_permissions).
    """
    meta = agent["meta"]
    tier = int(meta.get("tier", 3))
    raw_posture = meta.get("posture") or {}
    posture = {k: list(v) if isinstance(v, list) else v for k, v in raw_posture.items()}

    # Tier 1–2 agents are top-level orchestrators/workers; tier 3–4 are support subagents.
    mode = "all" if tier <= 2 else "subagent"

    fm: dict[str, Any] = {"description": _description(meta), "mode": mode}
    if "model" in meta:
        fm["model"] = meta["model"]
    effective = effective_posture_for_permissions(posture)
    fm["permission"] = posture_to_permissions(tier, effective)

    return render_frontmatter(fm) + agent["body"]


def transform_agent_codex(agent: dict[str, Any]) -> str:
    """
    Codex custom agent format (.codex/agents/<name>.toml).
    Required fields: name, description, developer_instructions.
    """
    meta = agent["meta"]
    lines = [
        f'name = "{_toml_escape_basic(str(meta["name"]))}"',
        f'description = "{_toml_escape_basic(_description(meta))}"',
        "developer_instructions = " + _toml_multiline_literal(agent["body"]),
    ]
    if "model" in meta:
        lines.append(f'model = "{_toml_escape_basic(str(meta["model"]))}"')
    return "\n".join(lines) + "\n"


def transform_agent_gemini(agent: dict[str, Any]) -> str:
    """
    Gemini CLI agent format (.gemini/agents/<name>.md).
    YAML frontmatter: name, description, kind (local), tools, model, max_turns.
    Body becomes the agent's system prompt.

    Tool name mapping strategy:
    - Azoth generic names (read, bash, ...) → Gemini CLI canonical names
    - Subagent references (researcher, evaluator, ...) → dropped; Gemini CLI
      subagents cannot call other subagents — multi-agent coordination must
      happen at the top-level session via @agent-name syntax.
    - Claude-Code-specific or Azoth-internal aliases (task, explore, research)
      → dropped (no Gemini equivalent).
    - If no valid tools remain after filtering → fall back to ["*"].
    """
    meta = agent["meta"]
    fm: dict[str, Any] = {
        "name": meta["name"],
        "description": _description(meta),
        "kind": "local",
    }
    # Map Azoth generic tool names to Gemini CLI canonical tool names.
    # Empty list = drop the tool (no Gemini equivalent or not valid for subagents).
    _TOOL_MAP: dict[str, list[str]] = {
        # File system
        "read": ["read_file", "read_many_files"],
        "grep": ["grep_search"],
        "glob": ["glob"],
        "ls": ["list_directory"],
        "edit": ["replace"],
        "write": ["write_file"],
        # Shell
        "bash": ["run_shell_command"],
        "test-runner": ["run_shell_command"],
        # Web
        "web": ["google_web_search", "web_fetch"],
        "web-search": ["google_web_search"],
        "web-fetch": ["web_fetch"],
        "search": ["grep_search"],
        # Claude Code-specific / Azoth-internal → drop
        "task": [],
        "explore": [],
        "research": [],
        # Subagent references → drop (Gemini subagents cannot call other subagents;
        # orchestration happens at the main session level via @agent-name syntax)
        "researcher": [],
        "evaluator": [],
        "prompt-engineer": [],
        "research-orchestrator": [],
        "architect": [],
        "planner": [],
        "builder": [],
        "reviewer": [],
        "agent-crafter": [],
        "context-architect": [],
    }
    if tools := meta.get("tools"):
        gemini_tools: list[str] = []
        for t in tools:
            mapped = _TOOL_MAP.get(t)
            if mapped is not None:
                gemini_tools.extend(mapped)
            else:
                gemini_tools.append(t)
        # Deduplicate while preserving order.
        seen: set[str] = set()
        deduped: list[str] = []
        for t in gemini_tools:
            if t and t not in seen:
                deduped.append(t)
                seen.add(t)
        fm["tools"] = deduped if deduped else ["*"]
    else:
        # Default: broad access for tier 1-2, read-only for tier 3-4.
        tier = int(meta.get("tier", 3))
        if tier <= 2:
            fm["tools"] = [
                "read_file",
                "read_many_files",
                "grep_search",
                "glob",
                "list_directory",
                "replace",
                "write_file",
                "run_shell_command",
                "google_web_search",
                "web_fetch",
            ]
        else:
            fm["tools"] = [
                "read_file",
                "read_many_files",
                "grep_search",
                "glob",
                "list_directory",
                "google_web_search",
                "web_fetch",
            ]
    if "model" in meta:
        fm["model"] = meta["model"]
    # Conservative defaults for subagent execution limits.
    fm["max_turns"] = 30
    fm["timeout_mins"] = 10
    return render_frontmatter(fm) + agent["body"]


# ── Command transformations ──────────────────────────────────────────────────


def transform_command_claude(command: dict[str, Any]) -> str:
    """
    Claude Code command format (.claude/commands/<name>.md).
    Contract-backed commands render fresh frontmatter; legacy commands pass through.
    """
    if "contract" not in command:
        path = command["path"]
        return Path(path).read_text(encoding="utf-8")

    fm: dict[str, Any] = {}
    if desc := command["meta"].get("description"):
        fm["description"] = desc
    if effect := command["meta"].get("azoth_effect"):
        fm["azoth_effect"] = effect
    if agent := command["meta"].get("agent"):
        fm["agent"] = agent
    return render_frontmatter(fm) + command["body"]


def _uses_legacy_claude_command_check(command: dict[str, Any]) -> bool:
    """Return True when Claude check mode should allow legacy semantic parity."""
    contract = command.get("contract")
    if not isinstance(contract, dict):
        return False
    body_cfg = contract.get("body")
    if not isinstance(body_cfg, dict):
        return False
    return body_cfg.get("mode") == "legacy_claude_markdown"


def check_claude_command_file(
    path: Path,
    command: dict[str, Any],
    content: str,
    root: Path,
) -> bool:
    """Check one contract-backed Claude command output without widening generic file parity."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    if not path.is_file():
        print(f"  [missing] {rel}")
        return False

    actual = path.read_text(encoding="utf-8")
    if actual == content:
        return True

    if _uses_legacy_claude_command_check(command):
        actual_meta, actual_body = parse_frontmatter(actual)
        expected_meta, expected_body = parse_frontmatter(content)
        if actual_meta == expected_meta and actual_body == expected_body:
            return True

    print(f"  [stale] {rel}")
    return False


def transform_command_copilot(command: dict[str, Any]) -> str:
    """
    Copilot prompt format (.github/prompts/<name>.prompt.md).
    Adds mode: agent so the prompt is accessible as a chat slash command.
    """
    fm: dict[str, Any] = {"mode": "agent"}
    if desc := command["meta"].get("description"):
        fm["description"] = desc
    if agent := command["meta"].get("agent"):
        fm["agent"] = agent
    return render_frontmatter(fm) + command["body"]


def transform_command_opencode(command: dict[str, Any]) -> str:
    """
    OpenCode command format (.opencode/commands/<name>.md).
    OpenCode reads $ARGUMENTS natively — body passes through unchanged.
    """
    fm: dict[str, Any] = {}
    if desc := command["meta"].get("description"):
        fm["description"] = desc
    if agent := command["meta"].get("agent"):
        fm["agent"] = agent
    if fm:
        return render_frontmatter(fm) + command["body"]
    return command["body"]


def transform_command_antigravity(command: dict[str, Any]) -> str:
    """
    Antigravity command format (.agents/workflows/<name>.md).
    Antigravity invokes these as /<name>. Body passes through unchanged.
    Frontmatter is stripped, as Antigravity rules and workflows are plain markdown.
    """
    return command["body"]


def transform_command_gemini(command: dict[str, Any]) -> str:
    """
    Gemini CLI custom command format (.gemini/commands/<name>.toml).
    Uses TOML with a `prompt` field (multiline literal string) and optional
    `description`. Shell injection (!{...}) and file injection (@{...}) are
    available but not used here — commands rely on the model following the
    prompt instructions to read files.
    """
    name = gemini_command_name(command["name"])
    desc = str(command["meta"].get("description") or f"Azoth /{name} workflow")
    body = command["body"]
    lines = [
        f"# Azoth /{name} command — generated by azoth-deploy.py",
        f'description = "{_toml_escape_basic(desc)}"',
        "prompt = " + _toml_multiline_literal(body),
    ]
    return "\n".join(lines) + "\n"


_GEMINI_COMMAND_NAME_MAP: dict[str, str] = {
    "dynamic-full-auto": "workspace.dynamic-full-auto",
    "plan": "workspace.plan",
    "remember": "workspace.remember",
}


def gemini_command_name(command_name: str) -> str:
    """Return the deployed Gemini command name.

    Gemini CLI merges workspace commands with built-ins and discovered skill
    commands. A small set of Azoth commands collide consistently in live
    sessions, so the Gemini-specific surface deploys stable names that avoid
    runtime renaming while keeping canonical Azoth command names unchanged in
    `.claude/commands/` and other platform adapters.
    """
    return _GEMINI_COMMAND_NAME_MAP.get(command_name, command_name)


_SHARED_SKILL_NAME_MAP: dict[str, str] = {
    "remember": "azoth-memory-capture",
    "structured-autonomy-plan": "azoth-structured-autonomy-plan",
}


def shared_skill_name(skill_name: str) -> str:
    """Return the deployed name for a skill on the shared `.agents/skills/` surface."""
    return _SHARED_SKILL_NAME_MAP.get(skill_name, skill_name)


def transform_shared_skill(skill: dict[str, Any]) -> str:
    """Render a skill for the shared `.agents/skills/` surface.

    Some generic canonical skill names collide with user-global Gemini skill
    catalogs. The shared surface uses collision-safe deployed names while the
    source repository keeps the canonical skill directory and semantics.
    """
    deployed_name = shared_skill_name(skill["name"])
    if deployed_name == skill["name"]:
        return skill["raw"]
    meta = dict(skill["meta"])
    meta["name"] = deployed_name
    description = str(meta.get("description") or "").strip()
    prefix = f"Shared-surface deployment name for Azoth's `{skill['name']}` skill."
    meta["description"] = f"{prefix} {description}".strip()
    return render_frontmatter(meta) + skill["body"]


def codex_command_skill_name(command: dict[str, Any]) -> str:
    """Stable Codex skill name for an Azoth command wrapper."""
    return f"azoth-{command['name']}"


def transform_command_codex_skill(command: dict[str, Any]) -> str:
    """
    Codex skill wrapper for Azoth commands.

    Codex does not document repo-defined slash-command registration, so each
    Azoth command gets an explicit skill wrapper for `/skills` / `$skill`
    discovery while keeping the `.claude/commands/*.md` file as the source of
    truth for execution semantics.
    """
    name = command["name"]
    skill_name = codex_command_skill_name(command)
    description = str(
        command["meta"].get("description")
        or f"Explicit Codex wrapper for Azoth's `/{name}` workflow."
    )
    fm = {
        "name": skill_name,
        "description": (
            f"Explicit Codex entrypoint for Azoth's `/{name}` workflow. "
            f"Use when the user wants to run `/{name}` in Codex via `/skills` or `${skill_name}`."
        ),
        # NOTE: `agent:` is intentionally absent from this frontmatter dict.
        # Codex skill metadata (SKILL.md frontmatter + openai.yaml) has no recognized
        # `agent:` routing field — there is no platform mechanism to bind a skill
        # invocation to a named agent via TOML/YAML metadata. The `agent:` binding from
        # the source command's frontmatter is preserved as advisory body prose below
        # (see `lines.append(f"- Preserve the command's `agent: {agent}` binding.")`),
        # so the model receives it as instructional context even though Codex cannot
        # enforce it mechanically (hook-soft platform, D46).
    }

    lines = [
        f"Use this skill as the Codex-visible entrypoint for Azoth's `/{name}` workflow.",
        "",
        "Codex uses skills as the custom command surface for Azoth workflows.",
        "In the Codex app, enabled skills may appear in the slash command list.",
        f"In Codex CLI/IDE, use `/skills` or `${skill_name}`.",
        f"This skill is the explicit Codex-native equivalent of typing `/{name}`.",
        "",
        "Execution contract:",
    ]
    if contract_path := command.get("contract_path"):
        lines.append(f"- Read `{contract_path}` and treat it as the source of truth.")
        if body_source_path := command.get("body_source_path"):
            lines.append(
                f"- Read the body source referenced by that contract: `{body_source_path}`."
            )
    else:
        lines.append(f"- Read `.claude/commands/{name}.md` and follow it as the source of truth.")
    lines.extend(
        [
            f"- Treat the rest of the user's prompt after `${skill_name}` as `$ARGUMENTS`.",
            "- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.",
        ]
    )
    if agent := command["meta"].get("agent"):
        lines.append(f"- Preserve the command's `agent: {agent}` binding.")
    if effect := command["meta"].get("azoth_effect"):
        lines.append(f"- Respect the command's `azoth_effect: {effect}` contract.")
    lines.extend(
        [
            f"- If the user typed literal `/{name}` in prompt text instead, apply the same workflow contract.",
            "",
            "Command metadata:",
            (
                f"- Contract path: `{contract_path}`"
                if contract_path
                else f"- Source path: `.claude/commands/{name}.md`"
            ),
            (
                f"- Body source path: `{command['body_source_path']}`"
                if command.get("body_source_path")
                else None
            ),
            f"- Description: {description}",
        ]
    )
    return render_frontmatter(fm) + "\n".join(line for line in lines if line is not None) + "\n"


def transform_command_codex_skill_metadata(command: dict[str, Any]) -> str:
    """Optional Codex UI metadata for Azoth command-wrapper skills."""
    name = command["name"]
    skill_name = codex_command_skill_name(command)
    description = str(command["meta"].get("description") or f"Azoth `/{name}` workflow")
    data = {
        "interface": {
            "display_name": f"/{name}",
            "short_description": description,
            "default_prompt": f"${skill_name} ",
        },
        "policy": {
            "allow_implicit_invocation": False,
        },
    }
    return render_yaml_document(data)


# ── AGENTS.md generation ─────────────────────────────────────────────────────

_TIER_LABELS: dict[int, str] = {1: "Core", 2: "Research", 3: "Meta", 4: "Utility"}


def generate_agents_md(agents: list[dict[str, Any]]) -> str:
    """
    Generate AGENTS.md cross-platform broadcast layer (AAIF standard).
    Read natively by Claude Code, GitHub Copilot, OpenCode, Cursor, Codex, Gemini.
    """
    by_tier: dict[int, list[dict[str, Any]]] = {}
    for agent in agents:
        tier = int(agent["meta"].get("tier", 99))
        by_tier.setdefault(tier, []).append(agent)

    lines: list[str] = [
        "# AGENTS.md — Azoth Agentic Toolkit",
        "",
        "This project uses the Azoth agentic toolkit.",
        "The agents below are available across all supported AI coding tools",
        "(Claude Code, GitHub Copilot, OpenCode, Cursor, Codex, Gemini).",
        "",
        "> AAIF-compliant agent manifest — generated by `scripts/azoth-deploy.py`.",
        "> Do not edit manually. Regenerate with: `python scripts/azoth-deploy.py`",
        "",
        "---",
        "",
        "## Agents",
        "",
    ]

    for tier_num in sorted(by_tier):
        label = _TIER_LABELS.get(tier_num, f"Tier {tier_num}")
        lines += [
            f"### Tier {tier_num} — {label}",
            "",
            "| Agent | Role | Trust |",
            "|-------|------|-------|",
        ]
        for agent in by_tier[tier_num]:
            meta = agent["meta"]
            name = meta.get("name", "")
            role = str(meta.get("role") or meta.get("description") or "")
            trust = str(meta.get("trust_level") or "—")
            lines.append(f"| {name} | {role} | {trust} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## Governance",
        "",
        "All agents operate under the Azoth Trust Contract:",
        "",
        "- **Entropy ceiling**: max 10 files changed per session",
        "- **Human gates**: kernel / governance changes always require human approval",
        "- **Posture tiers**: `always_do` / `ask_first` / `never_auto`",
        "  (see `kernel/TRUST_CONTRACT.md`)",
        "",
        "## Platform File Locations",
        "",
        "| Platform | Agents | Commands | Skills | IDE rules |",
        "|----------|--------|----------|--------|-----------|",
        "| Antigravity (Gemini) | — | `.agents/workflows/` | `.agents/skills/` | `.agents/rules/*.md` ← `azoth-deploy --platforms antigravity` |",
        "| Claude Code | `.claude/agents/` | `.claude/commands/` | `.claude/skills/` | hooks in `.claude/settings.json` |",
        "| Gemini CLI | `.gemini/agents/` | `.gemini/commands/` (TOML) | `.agents/skills/` | `GEMINI.md` + `.gemini/settings.json` |",
        "| GitHub Copilot | `.claude/agents/` default, `.github/agents/` optional mirror | `.github/prompts/` | `.github/skills/` | — |",
        "| OpenCode | `.opencode/agents/` | `.opencode/commands/` | `.opencode/skills/` | — |",
        "| Codex | `.codex/agents/*.toml` | skills (`azoth-*`; app slash list, CLI `/skills`) + literal Azoth tokens | `.agents/skills/` | `.codex/config.toml`, `.codex/hooks.json` |",
        "| Cursor | `.claude/agents/` (toggle) | `.claude/commands/` (toggle) | `skills/` (toggle) | `.cursor/rules/*.mdc` ← `azoth-deploy --platforms cursor` |",
        "",
    ]

    return "\n".join(lines)


# ── Cursor IDE rules (kernel templates → .cursor/rules/) ────────────────────

CURSOR_ADAPTER_DIR = Path("kernel/templates/platform-adapters/cursor")
CODEX_ADAPTER_DIR = Path("kernel/templates/platform-adapters/codex")


def cursor_rules_dest_dir(root: Path) -> Path:
    """
    Destination directory for deployed Cursor rules.

    Default: `<root>/.cursor/rules/`
    Override: set `AZOTH_CURSOR_RULES_DIR` to an absolute path (used by tests and
    sandboxes that block creating `.cursor/`).
    """
    env = os.environ.get("AZOTH_CURSOR_RULES_DIR")
    if env:
        return Path(env).resolve()
    return (root / ".cursor" / "rules").resolve()


def iter_cursor_rule_deployments(root: Path) -> list[tuple[Path, Path]]:
    """
    Map each *.mdc.template under the Cursor adapter dir to its deploy path.

    Returns (template_path, dest_path) pairs. Example:
      .../azoth-memory.mdc.template → .cursor/rules/azoth-memory.mdc
    """
    adapter = root / CURSOR_ADAPTER_DIR
    if not adapter.is_dir():
        return []
    dest_dir = cursor_rules_dest_dir(root)
    pairs: list[tuple[Path, Path]] = []
    for path in sorted(adapter.glob("*.mdc.template")):
        out_name = path.name.removesuffix(".template")
        dest = dest_dir / out_name
        pairs.append((path, dest))
    return pairs


def deploy_cursor_rules(root: Path, dry_run: bool, *, check: bool = False) -> tuple[int, int]:
    """Copy kernel Cursor templates into .cursor/rules/.

    Returns (files_processed, stale_count).
    """
    count = 0
    stale = 0
    for template_path, dest_path in iter_cursor_rule_deployments(root):
        content = template_path.read_text(encoding="utf-8")
        if not write_file(dest_path, content, root, dry_run, check=check):
            stale += 1
        count += 1
    return count, stale


def iter_codex_adapter_deployments(root: Path) -> list[tuple[Path, Path]]:
    """Map Codex adapter templates to their deployed .codex destinations."""
    adapter = root / CODEX_ADAPTER_DIR
    return [
        (adapter / CODEX_CONFIG_DEFAULT_TEMPLATE, root / ".codex" / "config.toml"),
        (adapter / CODEX_CONFIG_SEAMLESS_TEMPLATE, root / ".codex" / "config.seamless.toml"),
        (adapter / CODEX_HOOKS_DEFAULT_TEMPLATE, root / ".codex" / "hooks.json"),
        (adapter / CODEX_HOOKS_VERBOSE_TEMPLATE, root / ".codex" / "hooks.verbose.json"),
        (
            adapter / CODEX_RULES_TEMPLATE,
            root / ".codex" / "rules" / "azoth-seamless.star",
        ),
        (
            adapter / "user_prompt_submit_router.py.template",
            root / ".codex" / "hooks" / "user_prompt_submit_router.py",
        ),
    ]


def deploy_codex_adapter(root: Path, dry_run: bool, *, check: bool = False) -> tuple[int, int]:
    """Copy kernel Codex templates into .codex/."""
    count = 0
    stale = 0
    for template_path, dest_path in iter_codex_adapter_deployments(root):
        if not template_path.is_file():
            continue
        content = template_path.read_text(encoding="utf-8")
        if not write_file(dest_path, content, root, dry_run, check=check):
            stale += 1
        count += 1
    return count, stale


# ── Codex hook compatibility lint ────────────────────────────────────────────

# Scripts known to depend on unsupported Codex PreToolUse semantics.
_CODEX_UNSAFE_SCRIPTS: set[str] = {
    "edit_pretooluse_orchestrator.py",
    "scope-gate.py",
}


def lint_codex_hooks(root: Path) -> list[str]:
    """Check .codex/hooks.json for Codex hook protocol violations.

    Returns a list of warning strings (empty = clean).

    Checks:
    1. PreToolUse hooks must not use scripts that depend on unsupported non-Bash interception.
    2. Stop hook scripts must not print non-JSON text to stdout (need --quiet).
    3. PreToolUse/PostToolUse matchers should include Bash or they will not fire today.
    """
    hooks_path = root / ".codex" / "hooks.json"
    if not hooks_path.is_file():
        return []

    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ["  [error] .codex/hooks.json is not valid JSON"]

    hooks_section = data.get("hooks", {})
    warnings: list[str] = []

    for hook_type, hook_groups in hooks_section.items():
        if not isinstance(hook_groups, list):
            continue
        for group in hook_groups:
            hook_list = group.get("hooks", [])
            if not isinstance(hook_list, list):
                continue
            for hook in hook_list:
                cmd = hook.get("command", "")
                if not isinstance(cmd, str):
                    continue

                # Check 1: known unsupported PreToolUse scripts
                if hook_type == "PreToolUse":
                    for unsafe in _CODEX_UNSAFE_SCRIPTS:
                        if unsafe in cmd:
                            warnings.append(
                                f"  [codex-hook] PreToolUse: {unsafe} depends on unsupported "
                                f"non-Bash or Write/Edit interception in Codex"
                            )

                # Check 2: Stop hooks without --quiet for scripts that print to stdout
                if hook_type == "Stop" and "notify.py" in cmd and "--quiet" not in cmd:
                    warnings.append(
                        "  [codex-hook] Stop: notify.py prints to stdout without --quiet "
                        "— Codex parses Stop stdout as JSON"
                    )

                # Check 3: current Codex Pre/Post runtime only emits Bash tool events
                matcher = group.get("matcher")
                if hook_type in {"PreToolUse", "PostToolUse"} and isinstance(matcher, str):
                    if "Bash" not in matcher:
                        warnings.append(
                            f"  [codex-hook] {hook_type}: matcher {matcher!r} will not fire "
                            "today — current Codex runtime only emits Bash"
                        )

    return warnings


def _resolve_hook_script(root: Path, cmd: str) -> Path | None:
    """Best-effort resolve a hook command string to a script Path."""
    # Handle: python3 "$(git rev-parse --show-toplevel)/path/to/script.py"
    # Extract the path after the last git-root marker
    if "$(git rev-parse --show-toplevel)" in cmd:
        # Extract relative path from the git-root-relative command
        parts = cmd.split("$(git rev-parse --show-toplevel)")
        if len(parts) >= 2:
            rel = parts[-1].strip().strip('"').strip("'").lstrip("/")
            # Strip trailing arguments
            rel = rel.split('" ')[0].split("' ")[0]
            if " --" in rel:
                rel = rel.split(" --")[0].strip()
            return root / rel
    # Handle: python3 path/to/script.py
    tokens = cmd.split()
    for token in reversed(tokens):
        token = token.strip('"').strip("'")
        if token.endswith(".py"):
            candidate = root / token
            if candidate.is_file():
                return candidate
    return None


# ── File writing ─────────────────────────────────────────────────────────────


def write_file(path: Path, content: str, root: Path, dry_run: bool, *, check: bool = False) -> bool:
    """Write content to path, printing the relative path. Creates parent dirs.

    In check mode, compares computed content against on-disk content without
    writing.  Returns True when the file is (or would be) in sync.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    if check:
        if not path.is_file():
            print(f"  [missing] {rel}")
            return False
        if path.read_text(encoding="utf-8") != content:
            print(f"  [stale] {rel}")
            return False
        return True
    if dry_run:
        print(f"  [dry-run] {rel}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {rel}")
    return True


def remove_file(path: Path, root: Path, dry_run: bool, *, check: bool = False) -> bool:
    """Ensure a previously generated file no longer exists."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    if check:
        if path.exists():
            print(f"  [obsolete] {rel}")
            return False
        return True
    if dry_run:
        if path.exists():
            print(f"  [dry-run remove] {rel}")
        return True
    if not path.exists():
        return True
    if path.is_dir():
        return False
    path.unlink()
    parent = path.parent
    while parent != root and parent.exists():
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent
    print(f"  [remove] {rel}")
    return True


def remove_tree(path: Path, root: Path, dry_run: bool, *, check: bool = False) -> bool:
    """Ensure a previously generated directory tree no longer exists."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    if check:
        if path.exists():
            print(f"  [obsolete] {rel}")
            return False
        return True
    if dry_run:
        if path.exists():
            print(f"  [dry-run remove] {rel}")
        return True
    if not path.exists():
        return True
    if path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)
    print(f"  [remove] {rel}")
    return True


def prune_agents_skill_surface(
    root: Path,
    expected_skill_names: set[str],
    dry_run: bool,
    *,
    check: bool = False,
) -> tuple[int, int]:
    """Retire stale non-Azoth skills from the shared `.agents/skills/` surface.

    The shared Gemini/Codex/Antigravity skill surface is Azoth-managed. Canonical
    skills live under `skills/`, while `azoth-*` folders are reserved for wrapper
    skills and bootstrap-specific entries. Everything else is treated as stale.
    """
    skills_root = root / ".agents" / "skills"
    if not skills_root.is_dir():
        return 0, 0
    count = 0
    stale = 0
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        name = skill_dir.name
        if name in expected_skill_names or name.startswith("azoth-"):
            continue
        if not remove_tree(skill_dir, root, dry_run, check=check):
            stale += 1
        count += 1
    return count, stale


# ── Entry point ──────────────────────────────────────────────────────────────

ALL_PLATFORMS = ("claude", "copilot", "opencode", "cursor", "codex", "antigravity", "gemini")
COPILOT_AGENT_LOCATIONS = ("github", "claude", "both")


def _deploy_claude_agents(platforms: set[str], copilot_agent_location: str) -> bool:
    return "claude" in platforms or (
        "copilot" in platforms and copilot_agent_location in {"claude", "both"}
    )


def _deploy_github_agents(platforms: set[str], copilot_agent_location: str) -> bool:
    return "copilot" in platforms and copilot_agent_location in {"github", "both"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Translate canonical Azoth sources into platform-specific deployed files."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Project root directory (default: current directory)",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without writing anything",
    )
    mode_group.add_argument(
        "--check",
        action="store_true",
        help="Check that deployed files are in sync with sources (exit 1 if stale)",
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=ALL_PLATFORMS,
        default=list(ALL_PLATFORMS),
        metavar="PLATFORM",
        help=f"Platforms to target (default: all). Choices: {', '.join(ALL_PLATFORMS)}",
    )
    parser.add_argument(
        "--copilot-agent-location",
        choices=COPILOT_AGENT_LOCATIONS,
        default="claude",
        help=(
            "Where to deploy Copilot custom agents: 'claude' keeps Copilot agent discovery "
            "Claude-first via .claude/agents/ while preserving .github/prompts/, 'github' "
            "writes .github/agents/ only, and 'both' writes both agent locations. "
            "Default: claude"
        ),
    )
    args = parser.parse_args(argv)

    root: Path = args.root.resolve()
    platforms: set[str] = set(args.platforms)
    dry_run: bool = args.dry_run
    check: bool = args.check
    copilot_agent_location: str = args.copilot_agent_location

    if not root.is_dir():
        print(f"error: root not found: {root}", file=sys.stderr)
        return 1

    extra = ""
    if "copilot" in platforms:
        extra = f"  copilot-agent-location={copilot_agent_location}"
    mode_label = "check" if check else f"dry-run={dry_run}"
    print(f"azoth-deploy  root={root}  platforms={sorted(platforms)}  {mode_label}{extra}\n")

    agents = load_agents(root)
    commands = load_commands(root)
    skills = load_skills(root)

    print(f"sources: {len(agents)} agents, {len(commands)} commands, {len(skills)} skills\n")

    count = 0
    stale = 0

    # ── Agents ───────────────────────────────────────────────────────────────
    if agents:
        print("── agents ──────────────────────────────────────────────────────")

        if _deploy_claude_agents(platforms, copilot_agent_location):
            for agent in agents:
                name = agent["meta"]["name"]
                if not write_file(
                    root / ".claude" / "agents" / f"{name}.md",
                    transform_agent_claude(agent),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1

        if _deploy_github_agents(platforms, copilot_agent_location):
            for agent in agents:
                name = agent["meta"]["name"]
                if not write_file(
                    root / ".github" / "agents" / f"{name}.agent.md",
                    transform_agent_copilot(agent),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1

        if "opencode" in platforms:
            for agent in agents:
                name = agent["meta"]["name"]
                if not write_file(
                    root / ".opencode" / "agents" / f"{name}.md",
                    transform_agent_opencode(agent),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1

        if "codex" in platforms:
            for agent in agents:
                name = agent["meta"]["name"]
                if not write_file(
                    root / ".codex" / "agents" / f"{name}.toml",
                    transform_agent_codex(agent),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1

        if "gemini" in platforms:
            for agent in agents:
                name = agent["meta"]["name"]
                if not write_file(
                    root / ".gemini" / "agents" / f"{name}.md",
                    transform_agent_gemini(agent),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1

        print()

    # ── Commands ─────────────────────────────────────────────────────────────
    if commands:
        print("── commands ────────────────────────────────────────────────────")

        if "claude" in platforms or "cursor" in platforms:
            for cmd in commands:
                contract = cmd.get("contract")
                if not isinstance(contract, dict):
                    continue
                claude_projection = contract.get("projection", {}).get("claude", {})
                if not isinstance(claude_projection, dict):
                    continue
                output_rel = str(claude_projection.get("output_path") or "").strip()
                if not output_rel:
                    continue
                dest_path = root / output_rel
                content = transform_command_claude(cmd)
                in_sync = (
                    check_claude_command_file(dest_path, cmd, content, root)
                    if check
                    else write_file(dest_path, content, root, dry_run, check=False)
                )
                if not in_sync:
                    stale += 1
                count += 1

        if "copilot" in platforms:
            for cmd in commands:
                if not write_file(
                    root / ".github" / "prompts" / f"{cmd['name']}.prompt.md",
                    transform_command_copilot(cmd),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1

        if "opencode" in platforms:
            for cmd in commands:
                if not write_file(
                    root / ".opencode" / "commands" / f"{cmd['name']}.md",
                    transform_command_opencode(cmd),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1

        if "antigravity" in platforms:
            for cmd in commands:
                if not write_file(
                    root / ".agents" / "workflows" / f"{cmd['name']}.md",
                    transform_command_antigravity(cmd),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1

        if "codex" in platforms:
            for cmd in commands:
                skill_dir = root / ".agents" / "skills" / codex_command_skill_name(cmd)
                if not write_file(
                    skill_dir / "SKILL.md",
                    transform_command_codex_skill(cmd),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1
                if not write_file(
                    skill_dir / "agents" / "openai.yaml",
                    transform_command_codex_skill_metadata(cmd),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1

        if "gemini" in platforms:
            for cmd in commands:
                deployed_name = gemini_command_name(cmd["name"])
                if not write_file(
                    root / ".gemini" / "commands" / f"{deployed_name}.toml",
                    transform_command_gemini(cmd),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1
                if deployed_name != cmd["name"]:
                    if not remove_file(
                        root / ".gemini" / "commands" / f"{cmd['name']}.toml",
                        root,
                        dry_run,
                        check=check,
                    ):
                        stale += 1
                    count += 1

        print()

    # ── Skills ───────────────────────────────────────────────────────────────
    if skills and (
        "opencode" in platforms
        or "antigravity" in platforms
        or "codex" in platforms
        or "gemini" in platforms
    ):
        print("── skills ──────────────────────────────────────────────────────")
        for skill in skills:
            if "opencode" in platforms:
                if not write_file(
                    root / ".opencode" / "skills" / skill["name"] / "SKILL.md",
                    skill["raw"],
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1
            if "antigravity" in platforms or "codex" in platforms or "gemini" in platforms:
                if not write_file(
                    root / ".agents" / "skills" / shared_skill_name(skill["name"]) / "SKILL.md",
                    transform_shared_skill(skill),
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1
            if "gemini" in platforms:
                if not remove_file(
                    root / ".gemini" / "skills" / skill["name"] / "SKILL.md",
                    root,
                    dry_run,
                    check=check,
                ):
                    stale += 1
                count += 1
        if "antigravity" in platforms or "codex" in platforms or "gemini" in platforms:
            n, s = prune_agents_skill_surface(
                root,
                {shared_skill_name(skill["name"]) for skill in skills},
                dry_run,
                check=check,
            )
            count += n
            stale += s
        print()

    # ── Cursor rules (kernel templates) ──────────────────────────────────────
    if "cursor" in platforms:
        print("── cursor rules ────────────────────────────────────────────────")
        n, s = deploy_cursor_rules(root, dry_run, check=check)
        count += n
        stale += s
        if n == 0:
            print(
                f"  [warning] no *.mdc.template files under {CURSOR_ADAPTER_DIR}",
                file=sys.stderr,
            )
        print()

    # ── Codex adapter (kernel templates) ──────────────────────────────────────
    if "codex" in platforms:
        print("── codex adapter ───────────────────────────────────────────────")
        n, s = deploy_codex_adapter(root, dry_run, check=check)
        count += n
        stale += s
        if n == 0:
            print(
                f"  [warning] no template files under {CODEX_ADAPTER_DIR}",
                file=sys.stderr,
            )
        # Lint Codex hooks for protocol compatibility
        hook_warnings = lint_codex_hooks(root)
        for w in hook_warnings:
            print(w, file=sys.stderr)
            stale += 1
        print()

    # ── Antigravity rules (kernel templates) ─────────────────────────────────
    if "antigravity" in platforms:
        print("── antigravity rules ───────────────────────────────────────────")
        # Inline deploy_antigravity_rules logic here or define above
        adapter = root / "kernel/templates/platform-adapters/antigravity"
        if not adapter.is_dir():
            print(f"  [warning] no format files under {adapter}", file=sys.stderr)
        else:
            n = 0
            dest_dir = root / ".agents" / "rules"
            for path in sorted(adapter.glob("*.md.template")):
                out_name = path.name.removesuffix(".template")
                dest = dest_dir / out_name
                content = path.read_text(encoding="utf-8")
                if not write_file(dest, content, root, dry_run, check=check):
                    stale += 1
                n += 1
            count += n
        print()

    # ── Gemini CLI adapter (kernel templates) ────────────────────────────────
    if "gemini" in platforms:
        print("── gemini adapter ──────────────────────────────────────────────")
        gemini_adapter = root / "kernel/templates/platform-adapters/gemini"
        if not gemini_adapter.is_dir():
            print(f"  [warning] no template files under {gemini_adapter}", file=sys.stderr)
        else:
            n = 0
            # Deploy GEMINI.md context file to project root
            gemini_md_tmpl = gemini_adapter / "GEMINI.md.template"
            if gemini_md_tmpl.is_file():
                content = gemini_md_tmpl.read_text(encoding="utf-8")
                if not write_file(root / "GEMINI.md", content, root, dry_run, check=check):
                    stale += 1
                n += 1
            # Deploy settings.json to .gemini/
            settings_tmpl = gemini_adapter / "settings.json.template"
            if settings_tmpl.is_file():
                content = settings_tmpl.read_text(encoding="utf-8")
                if not write_file(
                    root / ".gemini" / "settings.json", content, root, dry_run, check=check
                ):
                    stale += 1
                n += 1
            count += n
        print()

    # ── AGENTS.md ────────────────────────────────────────────────────────────
    if agents:
        print("── AGENTS.md ───────────────────────────────────────────────────")
        if not write_file(
            root / "AGENTS.md", generate_agents_md(agents), root, dry_run, check=check
        ):
            stale += 1
        count += 1
        print()

    if check:
        if stale > 0:
            print(f"✗ {stale}/{count} file(s) out of sync. Run: python3 scripts/azoth-deploy.py")
            return 1
        print(f"done. All {count} file(s) in sync.")
        return 0

    verb = "Would write" if dry_run else "Wrote"
    print(f"done. {verb} {count} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

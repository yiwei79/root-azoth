#!/usr/bin/env python3
"""
azoth-deploy.py — Translate canonical Azoth sources into platform-specific deployed files.

Transforms:
  agents/**/*.agent.md  →  .claude/agents/<name>.md            (Claude Code)
                        →  .github/agents/<name>.agent.md      (GitHub Copilot)
                        →  .opencode/agents/<name>.md          (OpenCode)
  .claude/commands/*.md →  .github/prompts/<name>.prompt.md   (Copilot)
                        →  .opencode/commands/<name>.md        (OpenCode)
  skills/**/SKILL.md    →  .opencode/skills/<name>/SKILL.md   (OpenCode per-subdirectory)
  (synthesized)         →  AGENTS.md                          (AAIF cross-platform broadcast)

Usage:
  python scripts/azoth-deploy.py
  python scripts/azoth-deploy.py --dry-run
  python scripts/azoth-deploy.py --platforms claude copilot
  python scripts/azoth-deploy.py --root /path/to/project
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


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
    meta = yaml.safe_load(text[3:end]) or {}
    body = text[end + 4:].lstrip("\n")
    return meta, body


def render_frontmatter(data: dict[str, Any]) -> str:
    """Render a dict as a YAML frontmatter block."""
    return "---\n" + yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False) + "---\n\n"


# ── Posture → OpenCode permission mapping ────────────────────────────────────

# Tier-based baseline permissions (permissive for orchestrators, restricted for meta agents).
# Rationale: Tier 1 orchestrators need broad tool access; Tier 3 meta agents should
# not run bash by default (they inspect and evaluate, not execute).
_TIER_BASE_PERMS: dict[int, dict[str, str]] = {
    1: {"edit": "allow", "bash": "ask",  "webfetch": "allow", "task": "allow"},
    2: {"edit": "ask",   "bash": "ask",  "webfetch": "allow", "task": "allow"},
    3: {"edit": "ask",   "bash": "deny", "webfetch": "allow", "task": "ask"},
    4: {"edit": "allow", "bash": "ask",  "webfetch": "ask",   "task": "ask"},
}

_DEFAULT_PERMS: dict[str, str] = {"edit": "ask", "bash": "ask", "webfetch": "allow", "task": "ask"}

# Keywords to match posture item text against OpenCode tool names.
# Used to tighten tier baseline based on ask_first / never_auto content.
_TOOL_KEYWORDS: dict[str, set[str]] = {
    "edit":     {"kernel", "governance", "file", "write", "modify", "create", "delete", "edit"},
    "bash":     {"execute", "script", "command", "run", "shell", "bash", "hook"},
    "webfetch": {"web", "search", "fetch", "online", "internet", "lookup"},
    "task":     {"agent", "subagent", "invoke", "spawn", "delegate", "orchestrat", "pipeline self"},
}


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
            if any(re.search(r"\b" + re.escape(kw) + r"\b", item_lower) for kw in keywords) and perms[tool] == "allow":
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


def load_commands(root: Path) -> list[dict[str, Any]]:
    """Load all commands from .claude/commands/*.md."""
    cmd_dir = root / ".claude" / "commands"
    if not cmd_dir.is_dir():
        return []
    commands = []
    for path in sorted(cmd_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        commands.append({"path": path, "name": path.stem, "meta": meta, "body": body})
    return commands


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
    Copilot agent format (.github/agents/<name>.agent.md).
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
    posture: dict[str, list[str]] = meta.get("posture") or {}

    # Tier 1–2 agents are top-level orchestrators/workers; tier 3–4 are support subagents.
    mode = "all" if tier <= 2 else "subagent"

    fm: dict[str, Any] = {"description": _description(meta), "mode": mode}
    if "model" in meta:
        fm["model"] = meta["model"]
    fm["permission"] = posture_to_permissions(tier, posture)

    return render_frontmatter(fm) + agent["body"]


# ── Command transformations ──────────────────────────────────────────────────


def transform_command_copilot(command: dict[str, Any]) -> str:
    """
    Copilot prompt format (.github/prompts/<name>.prompt.md).
    Adds mode: agent so the prompt is accessible as a chat slash command.
    """
    fm: dict[str, Any] = {"mode": "agent"}
    if desc := command["meta"].get("description"):
        fm["description"] = desc
    return render_frontmatter(fm) + command["body"]


def transform_command_opencode(command: dict[str, Any]) -> str:
    """
    OpenCode command format (.opencode/commands/<name>.md).
    OpenCode reads $ARGUMENTS natively — body passes through unchanged.
    """
    fm: dict[str, Any] = {}
    if desc := command["meta"].get("description"):
        fm["description"] = desc
    if fm:
        return render_frontmatter(fm) + command["body"]
    return command["body"]


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
        "- **Entropy ceiling**: max 10 files changed per turn",
        "- **Human gates**: kernel / governance changes always require human approval",
        "- **Posture tiers**: `always_do` / `ask_first` / `never_auto`",
        "  (see `kernel/TRUST_CONTRACT.md`)",
        "",
        "## Platform File Locations",
        "",
        "| Platform | Agents | Commands | Skills |",
        "|----------|--------|----------|--------|",
        "| Claude Code | `.claude/agents/` | `.claude/commands/` | `.claude/skills/` |",
        "| GitHub Copilot | `.github/agents/` | `.github/prompts/` | `.github/skills/` |",
        "| OpenCode | `.opencode/agents/` | `.opencode/commands/` | `.opencode/skills/` |",
        "",
    ]

    return "\n".join(lines)


# ── File writing ─────────────────────────────────────────────────────────────


def write_file(path: Path, content: str, root: Path, dry_run: bool) -> None:
    """Write content to path, printing the relative path. Creates parent dirs."""
    rel = path.relative_to(root)
    if dry_run:
        print(f"  [dry-run] {rel}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {rel}")


# ── Entry point ──────────────────────────────────────────────────────────────

ALL_PLATFORMS = ("claude", "copilot", "opencode")


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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without writing anything",
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=ALL_PLATFORMS,
        default=list(ALL_PLATFORMS),
        metavar="PLATFORM",
        help=f"Platforms to target (default: all). Choices: {', '.join(ALL_PLATFORMS)}",
    )
    args = parser.parse_args(argv)

    root: Path = args.root.resolve()
    platforms: set[str] = set(args.platforms)
    dry_run: bool = args.dry_run

    if not root.is_dir():
        print(f"error: root not found: {root}", file=sys.stderr)
        return 1

    print(f"azoth-deploy  root={root}  platforms={sorted(platforms)}  dry-run={dry_run}\n")

    agents = load_agents(root)
    commands = load_commands(root)
    skills = load_skills(root)

    print(f"sources: {len(agents)} agents, {len(commands)} commands, {len(skills)} skills\n")

    count = 0

    # ── Agents ───────────────────────────────────────────────────────────────
    if agents:
        print("── agents ──────────────────────────────────────────────────────")

        if "claude" in platforms:
            for agent in agents:
                name = agent["meta"]["name"]
                write_file(root / ".claude" / "agents" / f"{name}.md",
                           transform_agent_claude(agent), root, dry_run)
                count += 1

        if "copilot" in platforms:
            for agent in agents:
                name = agent["meta"]["name"]
                write_file(root / ".github" / "agents" / f"{name}.agent.md",
                           transform_agent_copilot(agent), root, dry_run)
                count += 1

        if "opencode" in platforms:
            for agent in agents:
                name = agent["meta"]["name"]
                write_file(root / ".opencode" / "agents" / f"{name}.md",
                           transform_agent_opencode(agent), root, dry_run)
                count += 1

        print()

    # ── Commands ─────────────────────────────────────────────────────────────
    if commands:
        print("── commands ────────────────────────────────────────────────────")

        if "copilot" in platforms:
            for cmd in commands:
                write_file(root / ".github" / "prompts" / f"{cmd['name']}.prompt.md",
                           transform_command_copilot(cmd), root, dry_run)
                count += 1

        if "opencode" in platforms:
            for cmd in commands:
                write_file(root / ".opencode" / "commands" / f"{cmd['name']}.md",
                           transform_command_opencode(cmd), root, dry_run)
                count += 1

        print()

    # ── Skills ───────────────────────────────────────────────────────────────
    if skills and "opencode" in platforms:
        print("── skills ──────────────────────────────────────────────────────")
        for skill in skills:
            write_file(root / ".opencode" / "skills" / skill["name"] / "SKILL.md",
                       skill["raw"], root, dry_run)
            count += 1
        print()

    # ── AGENTS.md ────────────────────────────────────────────────────────────
    if agents:
        print("── AGENTS.md ───────────────────────────────────────────────────")
        write_file(root / "AGENTS.md", generate_agents_md(agents), root, dry_run)
        count += 1
        print()

    verb = "Would write" if dry_run else "Wrote"
    print(f"done. {verb} {count} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

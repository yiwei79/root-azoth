#!/usr/bin/env python3
"""Materialize consumer-safe Azoth release profiles."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml

FULL_PROFILE_TEMPLATE = Path("kernel/templates/release-profiles/full-consumer.yaml")
LEGACY_FULL_TEMPLATE_ROOT = Path("kernel/templates/release-profile/full/.azoth")

REQUIRED_RUNTIME_PATHS: tuple[str, ...] = (
    "commands",
    "pipelines",
    "scripts",
    ".agents/skills",
    "commands/start/command.yaml",
    "commands/roadmap/command.yaml",
    "pipelines/full.pipeline.yaml",
    "scripts/codex_control_plane.py",
    "scripts/roadmap_dashboard.py",
    "scripts/autonomous_loop.py",
    ".agents/skills/azoth-start/SKILL.md",
    ".agents/skills/azoth-roadmap/SKILL.md",
    ".agents/skills/azoth-autonomous-auto/SKILL.md",
)

REQUIRED_SEED_PATHS: tuple[str, ...] = (
    ".azoth/roadmap.yaml",
    ".azoth/backlog.yaml",
    ".azoth/roadmap-specs/v0.2.0/README.md",
    ".azoth/initiative-banks/.gitkeep",
    ".azoth/design-banks/.gitkeep",
    ".azoth/autonomous-loop-state.local.yaml.example",
)

RUNTIME_GITIGNORE_RULES: tuple[str, ...] = (
    ".azoth/scope-gate.json",
    "!.azoth/scope-gate.json.example",
    ".azoth/pipeline-gate.json",
    "!.azoth/pipeline-gate.json.example",
    ".azoth/run-ledger.local.yaml",
    "!.azoth/run-ledger.local.yaml.example",
    ".azoth/run-ledger.local.yaml.lock",
    ".azoth/autonomous-loop-state.local.yaml",
    "!.azoth/autonomous-loop-state.local.yaml.example",
    ".azoth/final-delivery-approvals.jsonl",
    ".azoth/write-claim*.json",
    ".azoth/telemetry/",
)

LOCAL_ARTIFACT_NAMES = {".DS_Store", "__pycache__"}
LOCAL_ARTIFACT_SUFFIXES = {".pyc", ".pyo"}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".toml"}
CLAUDE_COMMAND_REF_RE = re.compile(
    r"(?<![\w./-])\.claude/commands/[A-Za-z0-9_-]+\.md"
)


class ReleaseProfileError(RuntimeError):
    """Raised when a release profile cannot be materialized safely."""


def _ignore_local_artifacts(directory: str, names: list[str]) -> set[str]:
    del directory
    return {
        name
        for name in names
        if name in LOCAL_ARTIFACT_NAMES or Path(name).suffix in LOCAL_ARTIFACT_SUFFIXES
    }


def _safe_target_path(root: Path, rel_path: str) -> Path:
    path = Path(rel_path)
    if path.is_absolute() or ".." in path.parts:
        raise ReleaseProfileError(f"unsafe release profile seed path: {rel_path}")
    return root / path


def _validate_full_profile_source(source_root: Path) -> None:
    missing: list[str] = []
    for rel_path in REQUIRED_RUNTIME_PATHS:
        path = source_root / rel_path
        if not path.exists():
            missing.append(rel_path)

    azoth_skill_dirs = [
        path for path in (source_root / ".agents" / "skills").glob("azoth-*") if path.is_dir()
    ]
    if not azoth_skill_dirs:
        missing.append(".agents/skills/azoth-*")

    has_template = (source_root / FULL_PROFILE_TEMPLATE).is_file() or (
        source_root / LEGACY_FULL_TEMPLATE_ROOT
    ).is_dir()
    if not has_template:
        missing.append(str(FULL_PROFILE_TEMPLATE))

    if missing:
        formatted = ", ".join(sorted(missing))
        raise FileNotFoundError(
            f"Full release profile runtime/template source is incomplete; missing: {formatted}"
        )


def _load_full_profile_template(source_root: Path) -> dict[str, str]:
    template_path = source_root / FULL_PROFILE_TEMPLATE
    if template_path.is_file():
        data = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ReleaseProfileError(
                f"release profile template must be a mapping: {template_path}"
            )
        if data.get("profile") != "full":
            raise ReleaseProfileError("release profile template must declare profile: full")
        seeds = data.get("seeds")
        if not isinstance(seeds, Mapping):
            raise ReleaseProfileError("release profile template must contain seeds mapping")
        result: dict[str, str] = {}
        for rel_path, content in seeds.items():
            if not isinstance(rel_path, str) or not isinstance(content, str):
                raise ReleaseProfileError("release profile seed paths and contents must be strings")
            result[rel_path] = content
    else:
        result = _load_legacy_full_profile_template(source_root)

    missing = [rel_path for rel_path in REQUIRED_SEED_PATHS if rel_path not in result]
    if missing:
        formatted = ", ".join(missing)
        raise ReleaseProfileError(f"release profile template missing required seeds: {formatted}")
    return {rel_path: result[rel_path] for rel_path in REQUIRED_SEED_PATHS}


def _load_legacy_full_profile_template(source_root: Path) -> dict[str, str]:
    legacy_root = source_root / LEGACY_FULL_TEMPLATE_ROOT
    if not legacy_root.is_dir():
        raise FileNotFoundError(
            f"Full release profile template missing: {source_root / FULL_PROFILE_TEMPLATE}"
        )

    seeds: dict[str, str] = {}
    for rel_path in REQUIRED_SEED_PATHS:
        parts = Path(rel_path).parts
        legacy_path = legacy_root.joinpath(*parts[1:])
        if not legacy_path.is_file():
            raise FileNotFoundError(f"legacy Full release profile seed missing: {legacy_path}")
        seeds[rel_path] = legacy_path.read_text(encoding="utf-8")
    return seeds


def _copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(
        source,
        target,
        dirs_exist_ok=True,
        ignore=_ignore_local_artifacts,
    )


def _copy_runtime_bundle(source_root: Path, target_root: Path) -> None:
    _copy_tree(source_root / "commands", target_root / "commands")
    _copy_tree(source_root / "pipelines", target_root / "pipelines")

    scripts_target = target_root / "scripts"
    scripts_target.mkdir(parents=True, exist_ok=True)
    for script in sorted((source_root / "scripts").glob("*.py")):
        shutil.copy2(script, scripts_target / script.name)

    skills_target = target_root / ".agents" / "skills"
    skills_target.mkdir(parents=True, exist_ok=True)
    for skill_dir in sorted((source_root / ".agents" / "skills").glob("azoth-*")):
        if skill_dir.is_dir():
            _copy_tree(skill_dir, skills_target / skill_dir.name)


def _referenced_claude_command_bodies(root: Path) -> list[str]:
    references: set[str] = set()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        references.update(match.group(0) for match in CLAUDE_COMMAND_REF_RE.finditer(text))
    return sorted(references)


def _command_frontmatter(contract: Mapping[str, Any]) -> str:
    fields = {
        "description": contract.get("description"),
        "azoth_effect": contract.get("azoth_effect"),
        "agent": contract.get("agent"),
    }
    lines = ["---"]
    for key, value in fields.items():
        if value:
            lines.append(f"{key}: {value}")
    lines.extend(["---", ""])
    return "\n".join(lines)


def _load_command_contract(command_yaml: Path) -> dict[str, Any]:
    data = yaml.safe_load(command_yaml.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ReleaseProfileError(f"command contract must be a mapping: {command_yaml}")
    return data


def _synthesize_claude_command_body(source_root: Path, command_name: str) -> str:
    command_root = source_root / "commands" / command_name
    command_yaml = command_root / "command.yaml"
    if not command_yaml.is_file():
        return _synthesize_claude_body_from_skill_wrapper(source_root, command_name)

    contract = _load_command_contract(command_yaml)
    body_md = command_root / "body.md"
    if body_md.is_file():
        body = body_md.read_text(encoding="utf-8")
        return _command_frontmatter(contract) + body

    display_name = str(contract.get("display_name") or f"/{command_name}")
    description = str(contract.get("description") or "Azoth command")
    return (
        _command_frontmatter(contract)
        + f"# {display_name}\n\n"
        + f"{description}\n\n"
        + "This consumer-safe command body is synthesized from the public command "
        + f"contract at `commands/{command_name}/command.yaml`.\n\n"
        + "Follow that contract as the source of truth for agent binding, effect, "
        + "projection metadata, references, and execution rules.\n"
    )


def _synthesize_claude_body_from_skill_wrapper(source_root: Path, command_name: str) -> str:
    skill_path = source_root / ".agents" / "skills" / f"azoth-{command_name}" / "SKILL.md"
    if not skill_path.is_file():
        raise FileNotFoundError(
            "referenced Claude command body has no public command contract or "
            f"Azoth skill wrapper: {skill_path}"
        )
    return (
        "---\n"
        f"description: Compatibility body for /{command_name}\n"
        "azoth_effect: follow-wrapper\n"
        "agent: orchestrator\n"
        "---\n\n"
        f"# /{command_name}\n\n"
        "This consumer-safe command body is synthesized from the shipped Azoth "
        f"skill wrapper at `.agents/skills/azoth-{command_name}/SKILL.md`.\n\n"
        "Read that wrapper and follow its execution contract as the source of truth.\n"
    )


def _materialize_claude_command_bodies(source_root: Path, target_root: Path) -> None:
    for rel_path in _referenced_claude_command_bodies(target_root):
        target = target_root / rel_path
        if target.is_file():
            continue
        source = source_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_file():
            shutil.copy2(source, target)
            continue
        command_name = Path(rel_path).stem
        target.write_text(
            _synthesize_claude_command_body(source_root, command_name),
            encoding="utf-8",
        )


def _write_profile_seeds(seeds: Mapping[str, str], target_root: Path) -> None:
    for rel_path, content in seeds.items():
        target = _safe_target_path(target_root, rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _append_gitignore_rules(target_root: Path) -> None:
    gitignore = target_root / ".gitignore"
    existing_text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    existing_rules = {
        line.strip()
        for line in existing_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    missing_rules = [rule for rule in RUNTIME_GITIGNORE_RULES if rule not in existing_rules]
    if not missing_rules:
        return

    chunks: list[str] = []
    if existing_text and not existing_text.endswith("\n"):
        chunks.append("\n")
    if "# Azoth private runtime state" not in existing_text:
        if existing_text:
            chunks.append("\n")
        chunks.append("# Azoth private runtime state\n")
    chunks.extend(f"{rule}\n" for rule in missing_rules)

    gitignore.parent.mkdir(parents=True, exist_ok=True)
    with gitignore.open("a", encoding="utf-8") as handle:
        handle.write("".join(chunks))


def materialize_full_profile(source_root: str | Path, target_root: str | Path) -> None:
    """Copy the Full runtime bundle and generate neutral consumer .azoth seeds."""
    source = Path(source_root).expanduser().resolve()
    target = Path(target_root).expanduser().resolve()

    if not source.is_dir():
        raise FileNotFoundError(f"Full release profile source is not a directory: {source}")

    _validate_full_profile_source(source)
    seeds = _load_full_profile_template(source)

    target.mkdir(parents=True, exist_ok=True)
    _copy_runtime_bundle(source, target)
    _materialize_claude_command_bodies(source, target)
    _write_profile_seeds(seeds, target)
    _append_gitignore_rules(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("full",), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()

    if args.profile == "full":
        materialize_full_profile(args.source, args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())

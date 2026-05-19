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

MODE_ORDER: tuple[str, ...] = ("guide", "assisted", "managed", "governed_autonomy")

DEFAULT_MODE_MATRIX = Path(".azoth/research/t-059-deployment-readiness-mode-matrix.yaml")

MODE_AUTHORITY_NOTES: dict[str, tuple[str, ...]] = {
    "managed": (
        "project-local approval is required before applying planning-bank seeds",
    ),
    "governed_autonomy": (
        "fresh autonomy budget, ledger/write-claim proof, and stop conditions are required",
    ),
}

MODE_AUTHORITY_ASSET_CLASSES: dict[str, tuple[str, ...]] = {
    "managed": ("project-local receipt",),
}

PROJECT_LOCAL_RECEIPT_PATHS: tuple[str, ...] = (
    ".azoth/project-local-mode-receipt.yaml",
    ".azoth/project-local-receipt.yaml",
)
PROJECT_LOCAL_RECEIPT_REQUIRED_FIELDS: tuple[str, ...] = (
    "project_id",
    "repo_path",
    "receipt_owner",
    "selected_mode",
    "release_profile_ref",
    "readiness_state",
    "freshness_status",
    "installed_asset_classes",
    "missing_asset_classes",
    "approval_scope",
    "active_write_claim",
    "next_safe_action",
    "stop_reason",
    "handoff_receipt_ref",
)
PROJECT_LOCAL_RECEIPT_LIST_FIELDS = {
    "installed_asset_classes",
    "missing_asset_classes",
}
PROJECT_LOCAL_RECEIPT_TEXT_FIELDS = (
    set(PROJECT_LOCAL_RECEIPT_REQUIRED_FIELDS)
    - PROJECT_LOCAL_RECEIPT_LIST_FIELDS
    - {"active_write_claim"}
)
PROJECT_LOCAL_AUTHORITY_MODES = {"managed", "governed_autonomy"}

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
CLAUDE_COMMAND_REF_RE = re.compile(r"(?<![\w./-])\.claude/commands/[A-Za-z0-9_-]+\.md")


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


def _string_list(value: Any, *, field: str, mode: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ReleaseProfileError(f"mode_matrix.{mode}.{field} must be a list of strings")
    return list(value)


def _load_mode_matrix(mode_matrix_path: Path) -> dict[str, dict[str, Any]]:
    try:
        data = yaml.safe_load(mode_matrix_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ReleaseProfileError(f"failed to parse mode matrix: {mode_matrix_path}") from exc
    if not isinstance(data, Mapping):
        raise ReleaseProfileError(f"mode matrix must be a mapping: {mode_matrix_path}")

    mode_matrix = data.get("mode_matrix")
    if not isinstance(mode_matrix, Mapping):
        raise ReleaseProfileError("mode matrix must contain mode_matrix mapping")

    missing_modes = [mode for mode in MODE_ORDER if mode not in mode_matrix]
    if missing_modes:
        formatted = ", ".join(missing_modes)
        raise ReleaseProfileError(f"mode_matrix missing required modes: {formatted}")

    unknown_modes = sorted(str(mode) for mode in mode_matrix if mode not in MODE_ORDER)
    if unknown_modes:
        formatted = ", ".join(unknown_modes)
        raise ReleaseProfileError(f"mode_matrix contains unknown modes: {formatted}")

    result: dict[str, dict[str, Any]] = {}
    for mode in MODE_ORDER:
        entry = mode_matrix[mode]
        if not isinstance(entry, Mapping):
            raise ReleaseProfileError(f"mode_matrix.{mode} must be a mapping")
        next_safe_action = entry.get("next_safe_action")
        if not isinstance(next_safe_action, str) or not next_safe_action.strip():
            raise ReleaseProfileError(f"mode_matrix.{mode}.next_safe_action must be a string")
        result[mode] = {
            "installed_asset_classes": _string_list(
                entry.get("installed_asset_classes"),
                field="installed_asset_classes",
                mode=mode,
            ),
            "explicit_exclusions": _string_list(
                entry.get("explicit_exclusions"),
                field="explicit_exclusions",
                mode=mode,
            ),
            "next_safe_action": next_safe_action,
        }
    return result


def _has_any_path(source_root: Path, rel_paths: tuple[str, ...]) -> bool:
    return any((source_root / rel_path).exists() for rel_path in rel_paths)


def is_project_local_mode_receipt(receipt: Mapping[str, Any]) -> bool:
    """Return true when a receipt claims the T-062 project-local contract."""
    return (
        receipt.get("artifact_type") == "project_local_mode_receipt"
        or "receipt_owner" in receipt
        or "release_profile_ref" in receipt
    )


def _repo_relative_file_path(value: Any, *, field: str) -> str | None:
    text = str(value or "").strip()
    path = Path(text)
    if not text or path.is_absolute() or ".." in path.parts or text.endswith("/"):
        return f"{field} must be a repo-relative file path"
    return None


def _scope_authorizes_mode(approval_scope: str, selected_mode: str) -> bool:
    scope = approval_scope.casefold().replace("-", "_")
    if selected_mode == "managed":
        return "managed" in scope
    if selected_mode == "governed_autonomy":
        return "governed" in scope or "autonomy" in scope
    return True


def validate_project_local_mode_receipt(
    receipt: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    expected_project_id: str | None = None,
    expected_repo_path: str | Path | None = None,
    expected_selected_mode: str | None = None,
    expected_handoff_receipt_ref: str | None = None,
) -> list[str]:
    """Validate the T-062 project-local mode receipt contract."""
    errors: list[str] = []
    missing = sorted(field for field in PROJECT_LOCAL_RECEIPT_REQUIRED_FIELDS if field not in receipt)
    for field in missing:
        errors.append(f"missing required field {field}")

    for field in sorted(PROJECT_LOCAL_RECEIPT_TEXT_FIELDS):
        if field in receipt and not str(receipt.get(field) or "").strip():
            errors.append(f"{field} must be a non-empty string")

    for field in sorted(PROJECT_LOCAL_RECEIPT_LIST_FIELDS):
        if field not in receipt:
            continue
        values = receipt.get(field)
        if not isinstance(values, list):
            errors.append(f"{field} must be a list")
        elif any(not isinstance(item, str) or not item.strip() for item in values):
            errors.append(f"{field} must contain only non-empty strings")

    if "active_write_claim" in receipt and not isinstance(receipt.get("active_write_claim"), bool):
        errors.append("active_write_claim must be a boolean")

    if receipt.get("receipt_owner") != "project_local":
        errors.append("receipt_owner must be project_local")

    selected_mode = str(receipt.get("selected_mode") or "").strip()
    if selected_mode and selected_mode not in MODE_ORDER:
        errors.append(f"selected_mode must be one of {list(MODE_ORDER)}")
    if expected_selected_mode and selected_mode and selected_mode != expected_selected_mode:
        errors.append(
            f"selected_mode {selected_mode} must match expected mode {expected_selected_mode}"
        )

    freshness_status = str(receipt.get("freshness_status") or "").strip()
    if freshness_status and not freshness_status.startswith("current"):
        errors.append("freshness_status must be current")

    approval_scope = str(receipt.get("approval_scope") or "").strip()
    if selected_mode and approval_scope and not _scope_authorizes_mode(approval_scope, selected_mode):
        errors.append(f"approval_scope must authorize {selected_mode}")

    if expected_project_id:
        project_id = str(receipt.get("project_id") or "").strip()
        if project_id and project_id != expected_project_id:
            errors.append(f"project_id {project_id} must match cockpit project_id {expected_project_id}")

    if expected_repo_path is not None:
        repo_path = str(receipt.get("repo_path") or "").strip()
        if repo_path:
            expected_path = Path(expected_repo_path).expanduser().resolve()
            actual_path = Path(repo_path).expanduser().resolve()
            if actual_path != expected_path:
                errors.append(f"repo_path {actual_path} must match cockpit repo_path {expected_path}")

    handoff_ref = str(receipt.get("handoff_receipt_ref") or "").strip()
    if handoff_ref:
        path_error = _repo_relative_file_path(handoff_ref, field="handoff_receipt_ref")
        if path_error:
            errors.append(path_error)
        elif repo_root is not None and not (repo_root / handoff_ref).is_file():
            errors.append("handoff_receipt_ref must resolve to an existing file")
    if expected_handoff_receipt_ref and handoff_ref and handoff_ref != expected_handoff_receipt_ref:
        errors.append(
            f"handoff_receipt_ref {handoff_ref} must match cockpit handoff_receipt_ref "
            f"{expected_handoff_receipt_ref}"
        )

    return errors


def _project_local_receipt_validation_errors(
    source_root: Path,
    *,
    expected_selected_mode: str | None = None,
) -> list[str]:
    for rel_path in PROJECT_LOCAL_RECEIPT_PATHS:
        path = source_root / rel_path
        if not path.is_file():
            continue
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            return [f"{rel_path}: failed to parse project-local receipt: {exc}"]
        if not isinstance(loaded, Mapping):
            return [f"{rel_path}: project-local receipt must be a mapping"]
        return [
            f"{rel_path}: {error}"
            for error in validate_project_local_mode_receipt(
                loaded,
                repo_root=source_root,
                expected_selected_mode=expected_selected_mode,
            )
        ]
    return ["project-local receipt missing"]


def _has_skill(source_root: Path, skill_name: str | None = None) -> bool:
    skills_root = source_root / ".agents" / "skills"
    if skill_name:
        return (skills_root / skill_name / "SKILL.md").is_file()
    return skills_root.is_dir() and any(skills_root.glob("*/SKILL.md"))


def _has_agent(source_root: Path) -> bool:
    agent_roots = (
        source_root / "agents",
        source_root / ".codex" / "agents",
        source_root / ".claude" / "agents",
        source_root / ".github" / "agents",
    )
    return any(root.is_dir() and any(root.rglob("*agent.*")) for root in agent_roots)


def _has_command_wrapper(source_root: Path) -> bool:
    commands_root = source_root / "commands"
    if not commands_root.is_dir():
        return False
    return any((path / "command.yaml").is_file() for path in commands_root.iterdir() if path.is_dir())


def _full_profile_seeds(source_root: Path) -> dict[str, str]:
    try:
        return _load_full_profile_template(source_root)
    except (FileNotFoundError, ReleaseProfileError):
        return {}


def _asset_class_present(
    source_root: Path,
    seeds: Mapping[str, str],
    asset_class: str,
    *,
    target_mode: str | None = None,
) -> bool:
    if asset_class == "trust and governance reading surface":
        return _has_any_path(
            source_root,
            (
                "kernel/TRUST_CONTRACT.md",
                "kernel/GOVERNANCE.md",
                ".azoth/kernel/TRUST_CONTRACT.md",
                ".azoth/kernel/GOVERNANCE.md",
            ),
        )
    if asset_class == "orientation or first prompt guidance":
        return _has_any_path(source_root, ("commands/start/command.yaml",)) or _has_skill(
            source_root,
            "azoth-start",
        )
    if asset_class == "starter documentation/playbook":
        return _has_any_path(source_root, ("README.md", "docs/playbook/README.md"))
    if asset_class == "skills":
        return _has_skill(source_root)
    if asset_class == "tier-1 agents or generated equivalents":
        return _has_agent(source_root)
    if asset_class == "command wrappers":
        return _has_command_wrapper(source_root)
    if asset_class == "runtime helper references":
        scripts_root = source_root / "scripts"
        return scripts_root.is_dir() and any(scripts_root.glob("*.py"))
    if asset_class == "starter receipts":
        return _has_any_path(source_root, ("azoth.yaml", ".azoth/source-profile-receipt.yaml"))
    if asset_class == "roadmap seed":
        return ".azoth/roadmap.yaml" in seeds
    if asset_class == "backlog seed":
        return ".azoth/backlog.yaml" in seeds
    if asset_class == "planning-bank seed":
        return ".azoth/initiative-banks/.gitkeep" in seeds and ".azoth/design-banks/.gitkeep" in seeds
    if asset_class == "validation helpers":
        return _has_any_path(
            source_root,
            ("scripts/planning_bank_validate.py", "scripts/roadmap_dashboard.py"),
        )
    if asset_class == "project-local receipt":
        return not _project_local_receipt_validation_errors(
            source_root,
            expected_selected_mode=target_mode,
        )
    if asset_class == "run ledger":
        return _has_any_path(
            source_root,
            (
                ".azoth/run-ledger.local.yaml.example",
                "pipelines/run-ledger.schema.yaml",
                "scripts/run_ledger.py",
            ),
        )
    if asset_class == "loop-state examples":
        return ".azoth/autonomous-loop-state.local.yaml.example" in seeds or _has_any_path(
            source_root,
            (".azoth/autonomous-loop-state.local.yaml.example",),
        )
    if asset_class == "stage-evidence requirements":
        return _has_any_path(
            source_root,
            ("pipelines/stage-summary.schema.yaml", "scripts/run_ledger.py"),
        )
    if asset_class == "stop-condition contract":
        return _has_any_path(source_root, ("scripts/autonomous_loop.py",))
    if asset_class == "bounded replay budget":
        return _has_any_path(
            source_root,
            (
                ".agents/skills/auto-router/SKILL.md",
                ".agents/skills/autonomous-auto/SKILL.md",
                "pipelines/full.pipeline.yaml",
            ),
        )
    return False


def compile_release_profile_readiness(
    source_root: str | Path,
    mode_matrix_path: str | Path = DEFAULT_MODE_MATRIX,
) -> dict[str, Any]:
    """Compile root-local release-profile readiness by Azoth deployment mode."""
    source = Path(source_root).expanduser().resolve()
    matrix_path = Path(mode_matrix_path).expanduser()
    if not matrix_path.is_absolute():
        matrix_path = source / matrix_path
    matrix_path = matrix_path.resolve()

    if not source.is_dir():
        raise FileNotFoundError(f"release profile source is not a directory: {source}")
    if not matrix_path.is_file():
        raise FileNotFoundError(f"release profile mode matrix is missing: {matrix_path}")

    matrix = _load_mode_matrix(matrix_path)
    seeds = _full_profile_seeds(source)
    modes: dict[str, dict[str, Any]] = {}
    for mode in MODE_ORDER:
        mode_spec = matrix[mode]
        missing_asset_classes = [
            asset_class
            for asset_class in mode_spec["installed_asset_classes"]
            if not _asset_class_present(source, seeds, asset_class, target_mode=mode)
        ]
        authority_asset_classes = set(MODE_AUTHORITY_ASSET_CLASSES.get(mode, ()))
        blocking_missing_asset_classes = [
            asset_class
            for asset_class in missing_asset_classes
            if asset_class not in authority_asset_classes
        ]
        authority_notes = list(MODE_AUTHORITY_NOTES.get(mode, ()))
        authority_required = bool(authority_notes)
        unsafe_claims = (
            _project_local_receipt_validation_errors(source, expected_selected_mode=mode)
            if "project-local receipt" in mode_spec["installed_asset_classes"]
            else []
        )
        readiness_state = (
            "blocked"
            if blocking_missing_asset_classes
            else "requires_authority"
            if authority_required
            else "ready"
        )
        modes[mode] = {
            "readiness_state": readiness_state,
            "authority_required": authority_required,
            "authority_notes": authority_notes,
            "installed_asset_classes": mode_spec["installed_asset_classes"],
            "missing_asset_classes": missing_asset_classes,
            "blocking_missing_asset_classes": blocking_missing_asset_classes,
            "explicit_exclusions": mode_spec["explicit_exclusions"],
            "next_safe_action": mode_spec["next_safe_action"],
            "unsafe_claims": unsafe_claims,
        }

    return {
        "schema_version": 1,
        "artifact_type": "release_profile_readiness",
        "source_root": str(source),
        "mode_matrix_path": str(matrix_path),
        "profile": "full",
        "readiness_policy": "ready_requires_assets_and_truthful_authority",
        "modes": modes,
    }


def assert_release_profile_readiness(report: Mapping[str, Any]) -> None:
    """Fail when a compiled release-profile readiness report contains blocked modes."""
    modes = report.get("modes")
    if not isinstance(modes, Mapping):
        raise ReleaseProfileError("release profile readiness report missing modes")
    blocked = [
        str(mode)
        for mode, mode_report in modes.items()
        if isinstance(mode_report, Mapping) and mode_report.get("readiness_state") == "blocked"
    ]
    if blocked:
        formatted = ", ".join(blocked)
        raise ReleaseProfileError(f"release profile readiness blocked for modes: {formatted}")


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
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--profile", choices=("full",))
    action.add_argument("--readiness", action="store_true")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--mode-matrix", type=Path, default=DEFAULT_MODE_MATRIX)
    args = parser.parse_args()

    if args.readiness:
        report = compile_release_profile_readiness(args.source, args.mode_matrix)
        print(yaml.safe_dump(report, sort_keys=False), end="")
        return 0

    if args.profile == "full":
        if args.target is None:
            parser.error("--target is required when --profile full is selected")
        materialize_full_profile(args.source, args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())

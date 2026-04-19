"""Shared scope-gate evaluation for PreToolUse (D43/D50). Used by scope-gate.py and edit_pretooluse_orchestrator."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from research_sufficiency import (  # noqa: E402
    evaluate_research_sufficiency,
    validate_research_evidence_reference,
)

_WRITE_TOOL_NAMES = {"write", "create_file", "createfile"}
_EDIT_TOOL_NAMES = {
    "edit",
    "replace_string_in_file",
    "replacestringinfile",
    "insert_edit_into_file",
    "inserteditintofile",
    "editfiles",
    "apply_patch",
}
_PATCH_TARGET_RE = re.compile(r"^\*\*\* (?:Update|Add|Delete) File: ([^\n]+)$", re.MULTILINE)
_PIPELINE_COMMANDS = frozenset({"auto", "dynamic-full-auto", "deliver", "deliver-full"})

_REMINDER = (
    "[scope-gate] Write/Edit blocked — no approved scope card found.\n"
    "\n"
    "Before building, run /next to declare your intent and receive an approved scope card. "
    "This moves the confirm-before-building rule from memory to mechanical enforcement (D43/D50).\n"
    "\n"
    "To unblock: run /next, confirm the scope card, then retry your tool call."
)

_GOVERNED_REMINDER = (
    "[pipeline-gate] Write/Edit blocked — governed scope requires pipeline gate.\n"
    "\n"
    "Your scope-gate.json indicates M1 or governed delivery. You must run one of "
    "`/deliver-full`, `/auto`, or `/deliver` and execute **Stage 0 — Pipeline gate** first: "
    "Write `.azoth/pipeline-gate.json` with `session_id` matching scope-gate and the correct "
    "`pipeline` key. The PreToolUse hook enforces this (D51 mechanical layer).\n"
    "\n"
    "Do not implement governed backlog work inline without the delivery pipeline + subagent routing. "
    "After Stage 0, Write/Edit to other paths is allowed until scope expires."
)


@dataclass(frozen=True)
class ScopeGateResult:
    """Result of scope evaluation for Write/Edit tools."""

    allowed: bool
    deny_reason: str = ""
    scope_data: dict | None = None
    skip_entropy: bool = False


def tool_input_dict(payload: dict) -> dict:
    raw = payload.get("tool_input")
    return raw if isinstance(raw, dict) else {}


def _path_from_value(value: object) -> str:
    if not isinstance(value, str):
        return ""
    raw = value.strip()
    if not raw:
        return ""
    if raw.startswith("file://"):
        parsed = urlparse(raw)
        return unquote(parsed.path)
    return raw


def _first_path_from_files(value: object) -> str:
    paths = _paths_from_files(value)
    return paths[0] if paths else ""


def _paths_from_files(value: object) -> list[str]:
    paths: list[str] = []
    if not isinstance(value, list):
        return paths
    for item in value:
        if isinstance(item, str):
            path_str = _path_from_value(item)
            if path_str:
                paths.append(path_str)
            continue
        if not isinstance(item, dict):
            continue
        for key in ("file_path", "filePath", "path", "uri"):
            path_str = _path_from_value(item.get(key))
            if path_str:
                paths.append(path_str)
                break
    return paths


def extract_target_path_strs(payload: dict) -> list[str]:
    tool_input = tool_input_dict(payload)
    paths: list[str] = []
    for key in ("file_path", "filePath", "path", "uri"):
        path_str = _path_from_value(tool_input.get(key))
        if path_str:
            paths.append(path_str)

    paths.extend(_paths_from_files(tool_input.get("files")))

    for key in ("input", "patch"):
        patch_text = tool_input.get(key)
        if not isinstance(patch_text, str):
            continue
        for match in _PATCH_TARGET_RE.finditer(patch_text):
            paths.append(match.group(1).split(" -> ", 1)[0].strip())

    deduped: list[str] = []
    for path_str in paths:
        if path_str and path_str not in deduped:
            deduped.append(path_str)
    return deduped


def extract_target_path_str(payload: dict) -> str:
    paths = extract_target_path_strs(payload)
    return paths[0] if paths else ""


def extract_write_content(tool_input: dict) -> str | None:
    for key in ("content", "text", "new_text", "newText"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def extract_old_new_strings(tool_input: dict) -> tuple[str | None, str | None]:
    old_s = tool_input.get("old_string")
    if not isinstance(old_s, str):
        old_s = (
            tool_input.get("oldString") if isinstance(tool_input.get("oldString"), str) else None
        )
    new_s = tool_input.get("new_string")
    if not isinstance(new_s, str):
        new_s = (
            tool_input.get("newString") if isinstance(tool_input.get("newString"), str) else None
        )
    return old_s, new_s


def normalized_write_action(payload: dict) -> str | None:
    tool_name = str(payload.get("tool_name", "") or "")
    normalized = tool_name.replace("-", "_").strip().lower()
    if normalized in _WRITE_TOOL_NAMES:
        return "write"
    if normalized in _EDIT_TOOL_NAMES:
        return "edit"

    tool_input = tool_input_dict(payload)
    old_s, new_s = extract_old_new_strings(tool_input)
    if old_s is not None and new_s is not None:
        return "edit"
    if extract_target_path_str(payload) and extract_write_content(tool_input) is not None:
        return "write"
    return None


def parse_expires_at(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def governance_mode(data: dict) -> str:
    mode = str(data.get("governance_mode") or "").strip()
    if mode in {"standard", "governed"}:
        return mode
    if str(data.get("target_layer") or "").strip() == "M1":
        return "governed"
    legacy = str(data.get("delivery_pipeline") or "").strip()
    if legacy == "governed":
        return "governed"
    if legacy == "standard":
        return "standard"
    return "standard"


def is_governed_scope(data: dict) -> bool:
    return governance_mode(data) == "governed"


def selected_pipeline_command(scope_data: dict) -> str:
    candidate = str(scope_data.get("pipeline_command") or "").strip()
    if candidate:
        return candidate
    legacy = str(scope_data.get("delivery_pipeline") or "").strip()
    if legacy in _PIPELINE_COMMANDS:
        return legacy
    return ""


def pipeline_gate_path(repo_root: Path) -> Path:
    env = os.environ.get("AZOTH_PIPELINE_GATE_PATH")
    if env:
        return Path(env)
    return repo_root / ".azoth" / "pipeline-gate.json"


def _research_evidence_ok(pg: dict) -> bool:
    return bool(validate_research_evidence_reference(pg).get("ok"))


def pipeline_gate_ok(pg_path: Path, scope_data: dict, repo_root: Path) -> bool:
    sid = scope_data.get("session_id")
    if not sid or not pg_path.is_file():
        return False
    try:
        pg = json.loads(pg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if pg.get("approved") is not True:
        return False
    pipeline_name = str(pg.get("pipeline_command") or pg.get("pipeline") or "").strip()
    if pipeline_name not in _PIPELINE_COMMANDS:
        return False
    if pg.get("session_id") != sid:
        return False
    opened_at = parse_expires_at(str(pg.get("opened_at", "")))
    if opened_at is None:
        return False
    exp = parse_expires_at(str(pg.get("expires_at", "")))
    if exp is None:
        return False
    scope_exp = parse_expires_at(str(scope_data.get("expires_at", "")))
    if scope_exp is not None and exp != scope_exp:
        return False
    if opened_at > exp:
        return False
    if datetime.now(timezone.utc) >= exp:
        return False
    selected_pipeline = selected_pipeline_command(scope_data)
    if selected_pipeline and selected_pipeline != pipeline_name:
        return False
    if not _research_evidence_ok(pg):
        return False
    reference = validate_research_evidence_reference(pg)
    evidence_path = reference.get("evidence_path")
    if isinstance(evidence_path, str) and evidence_path:
        evaluate_research_sufficiency(
            repo_root=repo_root,
            evidence_path=evidence_path,
            goal=str(scope_data.get("goal") or "").strip() or None,
            backlog_id=str(scope_data.get("backlog_id") or "").strip() or None,
        )
    return True


def resolve_gate_paths(repo_root: Path) -> tuple[Path, Path]:
    gate_path_env = os.environ.get("AZOTH_SCOPE_GATE_PATH")
    if gate_path_env:
        gate_path = Path(gate_path_env)
    else:
        gate_path = repo_root / ".azoth" / "scope-gate.json"
    return gate_path, pipeline_gate_path(repo_root)


def resolved_target(repo_root: Path, file_path_str: str) -> Path | None:
    if not file_path_str:
        return None
    try:
        p = Path(file_path_str)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        else:
            p = p.resolve()
        return p
    except (OSError, ValueError):
        return None


def entropy_state_path(repo_root: Path) -> Path:
    env = os.environ.get("AZOTH_ENTROPY_STATE_PATH")
    if env:
        return Path(env)
    return repo_root / ".azoth" / "entropy-state.json"


def emit_hook_response(allow: bool, reason: str = "") -> None:
    """Print Claude Code PreToolUse hook JSON and exit 0 (deny is still exit 0 per scope-gate contract)."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if allow else "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def evaluate_scope_gate(payload: dict, *, repo_root: Path | None = None) -> ScopeGateResult:
    """Evaluate scope card and pipeline gate for a Write/Edit PreToolUse payload."""
    root = repo_root or REPO_ROOT
    gate_path, pg_path = resolve_gate_paths(root)
    if normalized_write_action(payload) is None:
        return ScopeGateResult(allowed=True, skip_entropy=True)

    targets = [
        target
        for target in (
            resolved_target(root, path_str) for path_str in extract_target_path_strs(payload)
        )
        if target is not None
    ]

    def _is_scope_bootstrap_target(target: Path) -> bool:
        try:
            return target.resolve() == gate_path.resolve()
        except (OSError, ValueError):
            return False

    def _is_post_scope_exempt_target(target: Path) -> bool:
        try:
            resolved = target.resolve()
            if resolved == pg_path.resolve():
                return True
        except (OSError, ValueError):
            return False
        return False

    if targets and all(_is_scope_bootstrap_target(target) for target in targets):
        return ScopeGateResult(allowed=True, skip_entropy=True)

    # Claude Code plan-mode writes to ~/.claude/plans/ before any scope card exists.
    # Exempting only this specific sub-path avoids a bootstrap deadlock (BL-064).
    _claude_plans_root = (Path.home() / ".claude" / "plans").resolve()

    def _is_claude_plans_path(target: Path) -> bool:
        try:
            target.resolve().relative_to(_claude_plans_root)
            return True
        except (ValueError, OSError):
            return False

    if targets and all(_is_claude_plans_path(target) for target in targets):
        return ScopeGateResult(allowed=True, skip_entropy=True)

    if not gate_path.exists():
        return ScopeGateResult(allowed=False, deny_reason=_REMINDER)

    try:
        data = json.loads(gate_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ScopeGateResult(allowed=False, deny_reason="scope-gate.json is malformed")

    if data.get("approved") is not True:
        return ScopeGateResult(allowed=False, deny_reason=_REMINDER)

    exp_scope = parse_expires_at(str(data.get("expires_at", "")))
    if exp_scope is None:
        return ScopeGateResult(
            allowed=False, deny_reason="scope-gate.json expires_at is invalid ISO 8601"
        )
    if datetime.now(timezone.utc) >= exp_scope:
        return ScopeGateResult(allowed=False, deny_reason=_REMINDER)

    session_id = str(data.get("session_id") or "").strip()
    if not session_id:
        return ScopeGateResult(allowed=False, deny_reason="scope-gate.json missing session_id")

    if targets and all(_is_post_scope_exempt_target(target) for target in targets):
        return ScopeGateResult(allowed=True, scope_data=data, skip_entropy=True)

    is_pg_write = any(
        (lambda target: target.resolve() == pg_path.resolve() if target is not None else False)(
            target
        )
        for target in targets
    )

    if is_governed_scope(data):
        if not is_pg_write and not pipeline_gate_ok(pg_path, data, root):
            return ScopeGateResult(allowed=False, deny_reason=_GOVERNED_REMINDER)

    return ScopeGateResult(allowed=True, scope_data=data, skip_entropy=False)

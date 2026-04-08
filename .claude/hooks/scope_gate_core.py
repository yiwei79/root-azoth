"""Shared scope-gate evaluation for PreToolUse (D43/D50). Used by scope-gate.py and edit_pretooluse_orchestrator."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

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
    "Your scope-gate.json indicates M1 or delivery_pipeline: governed. You must run one of "
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


def is_governed_scope(data: dict) -> bool:
    return data.get("delivery_pipeline") == "governed" or data.get("target_layer") == "M1"


def pipeline_gate_path(repo_root: Path) -> Path:
    env = os.environ.get("AZOTH_PIPELINE_GATE_PATH")
    if env:
        return Path(env)
    return repo_root / ".azoth" / "pipeline-gate.json"


def pipeline_gate_ok(pg_path: Path, scope_data: dict) -> bool:
    sid = scope_data.get("session_id")
    if not sid or not pg_path.is_file():
        return False
    try:
        pg = json.loads(pg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if pg.get("approved") is not True:
        return False
    if pg.get("session_id") != sid:
        return False
    exp = parse_expires_at(str(pg.get("expires_at", "")))
    if exp is None:
        return False
    if datetime.now(timezone.utc) >= exp:
        return False
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
    tool_name = payload.get("tool_name", "")
    if tool_name not in {"Write", "Edit"}:
        return ScopeGateResult(allowed=True, skip_entropy=True)

    file_path_str = payload.get("tool_input", {}).get("file_path", "")
    target = resolved_target(root, file_path_str)

    if target is not None:
        try:
            if target == gate_path.resolve():
                return ScopeGateResult(allowed=True, skip_entropy=True)
        except (OSError, ValueError):
            pass

    est_path = entropy_state_path(root)

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

    if is_governed_scope(data):
        is_pg_write = False
        if target is not None:
            try:
                is_pg_write = target == pg_path.resolve()
            except (OSError, ValueError):
                pass
        if not is_pg_write and not pipeline_gate_ok(pg_path, data):
            return ScopeGateResult(allowed=False, deny_reason=_GOVERNED_REMINDER)

    if target is not None:
        try:
            if target == est_path.resolve():
                return ScopeGateResult(allowed=True, scope_data=data, skip_entropy=True)
        except (OSError, ValueError):
            pass

    return ScopeGateResult(allowed=True, scope_data=data, skip_entropy=False)

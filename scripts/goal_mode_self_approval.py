#!/usr/bin/env python3
"""Bounded Goal-mode self-approval for planning-seed scopes.

This helper does not relax Azoth's normal gate validators. It validates a
request, then writes ordinary scope/pipeline gates for planning-only artifacts.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import urlparse


APPROVED_BY = "goal-mode-self-approval"
DEFAULT_TTL_MINUTES = 120
MAX_TTL_MINUTES = 120
DEFAULT_PIPELINE_COMMAND = "auto"
DEFAULT_TARGET_LAYER = "infrastructure"
DEFAULT_BACKLOG_ID = "AD-HOC-GOAL-MODE"

ALLOWED_WRITE_PREFIXES = (
    ".azoth/proposals/",
    ".azoth/initiative-banks/",
    ".azoth/design-banks/",
    ".azoth/research/",
    ".azoth/handoffs/goal-mode/",
)

FORBIDDEN_EXACT_PATHS = {
    ".azoth/backlog.yaml",
    ".azoth/pipeline-gate.json",
    ".azoth/roadmap.yaml",
    ".azoth/run-ledger.local.yaml",
    ".azoth/scope-gate.json",
    "azoth.yaml",
}

FORBIDDEN_PREFIXES = (
    ".azoth/autonomous-loop-state",
    ".azoth/final-delivery-approvals",
    ".azoth/kernel/",
    ".azoth/memory/",
    ".azoth/roadmap-specs/",
    ".azoth/run-ledger",
    ".azoth/write-claim",
    ".claude/",
    ".codex/",
    ".cursor/",
    ".gemini/",
    ".github/",
    ".opencode/",
    ".agents/",
    "agents/",
    "commands/",
    "docs/",
    "kernel/",
    "pipelines/",
    "scripts/",
    "skills/",
    "tests/",
)

FORBIDDEN_TARGET_LAYERS = {"kernel", "m1", "governance"}


class GoalModeSelfApprovalError(ValueError):
    """Raised when a Goal-mode request is not safe to self-approve."""


@dataclass(frozen=True)
class GoalModeSelfApprovalRequest:
    """Validated input for one self-approved planning-seed scope."""

    active_goal: str
    session_id: str
    goal: str
    allowed_writes: tuple[str, ...]
    backlog_id: str = DEFAULT_BACKLOG_ID
    target_layer: str = DEFAULT_TARGET_LAYER
    ttl_minutes: int = DEFAULT_TTL_MINUTES
    pipeline_command: str = DEFAULT_PIPELINE_COMMAND

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "GoalModeSelfApprovalRequest":
        active_goal = _require_string(payload, "active_goal", max_length=4096)
        session_id = _require_string(payload, "session_id", max_length=128)
        goal = _require_string(payload, "goal", max_length=512)
        allowed_writes = tuple(_normalize_allowed_writes(payload.get("allowed_writes")))
        if not allowed_writes:
            raise GoalModeSelfApprovalError("allowed_writes must contain at least one path")

        ttl_minutes = int(payload.get("ttl_minutes") or DEFAULT_TTL_MINUTES)
        if ttl_minutes < 1 or ttl_minutes > MAX_TTL_MINUTES:
            raise GoalModeSelfApprovalError(
                f"ttl_minutes must be between 1 and {MAX_TTL_MINUTES}"
            )

        pipeline_command = str(payload.get("pipeline_command") or DEFAULT_PIPELINE_COMMAND)
        if pipeline_command != DEFAULT_PIPELINE_COMMAND:
            raise GoalModeSelfApprovalError("Goal-mode self-approval v1 only supports auto")

        target_layer = str(payload.get("target_layer") or DEFAULT_TARGET_LAYER).strip()
        if target_layer.casefold() in FORBIDDEN_TARGET_LAYERS:
            raise GoalModeSelfApprovalError(
                f"target_layer {target_layer!r} requires human approval"
            )

        return cls(
            active_goal=active_goal,
            session_id=session_id,
            goal=goal,
            allowed_writes=allowed_writes,
            backlog_id=str(payload.get("backlog_id") or DEFAULT_BACKLOG_ID).strip()
            or DEFAULT_BACKLOG_ID,
            target_layer=target_layer,
            ttl_minutes=ttl_minutes,
            pipeline_command=pipeline_command,
        )


def _require_string(payload: Mapping[str, Any], key: str, *, max_length: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GoalModeSelfApprovalError(f"{key} must be a non-empty string")
    text = value.strip()
    if len(text) > max_length:
        raise GoalModeSelfApprovalError(f"{key} must be at most {max_length} characters")
    return text


def _normalize_repo_path(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise GoalModeSelfApprovalError("allowed_writes entries must be non-empty strings")
    text = raw.strip().replace("\\", "/")
    parsed = urlparse(text)
    if parsed.scheme:
        raise GoalModeSelfApprovalError(f"{raw!r} must be a repo-relative path")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise GoalModeSelfApprovalError(f"{raw!r} must be a repo-relative path")
    normalized = path.as_posix()
    if normalized == "." or normalized.endswith("/"):
        raise GoalModeSelfApprovalError(f"{raw!r} must point to a file path")
    return normalized


def _normalize_allowed_writes(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise GoalModeSelfApprovalError("allowed_writes must be a list")
    paths = [_normalize_repo_path(item) for item in value]
    for path in paths:
        validate_allowed_write_path(path)
    return paths


def validate_allowed_write_path(path: str) -> None:
    """Fail unless *path* is a planning-seed artifact path."""
    if path in FORBIDDEN_EXACT_PATHS:
        raise GoalModeSelfApprovalError(f"{path} is protected and requires human approval")
    for prefix in FORBIDDEN_PREFIXES:
        if path.startswith(prefix):
            raise GoalModeSelfApprovalError(f"{path} is outside Goal-mode self-approval")
    if not any(path.startswith(prefix) for prefix in ALLOWED_WRITE_PREFIXES):
        raise GoalModeSelfApprovalError(f"{path} is not an allowed planning-seed artifact")


def _parse_iso(raw: str) -> datetime | None:
    try:
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _active_scope_gate(path: Path, *, now: datetime) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        gate = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GoalModeSelfApprovalError(f"existing scope-gate.json is malformed: {exc}") from exc
    if not isinstance(gate, dict) or gate.get("approved") is not True:
        return None
    expires_at = _parse_iso(str(gate.get("expires_at") or ""))
    if expires_at is None or expires_at <= now:
        return None
    return gate


def assert_can_open_scope(
    repo_root: Path,
    request: GoalModeSelfApprovalRequest,
    *,
    now: datetime | None = None,
) -> None:
    """Reject attempts to replace unrelated active scopes."""
    checked_at = now or datetime.now(timezone.utc)
    gate = _active_scope_gate(repo_root / ".azoth" / "scope-gate.json", now=checked_at)
    if gate is None:
        return
    if gate.get("session_id") == request.session_id:
        return
    if gate.get("goal_mode_bootstrap") is True and gate.get("approved_by") == "human":
        return
    raise GoalModeSelfApprovalError(
        "active scope gate belongs to another session; do not replace it with Goal-mode"
    )


def build_gate_payloads(
    request: GoalModeSelfApprovalRequest,
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build scope-gate and pipeline-gate payloads for a validated request."""
    opened_at = now or datetime.now(timezone.utc)
    expires_at = opened_at + timedelta(minutes=request.ttl_minutes)
    opened_text = opened_at.isoformat().replace("+00:00", "Z")
    expires_text = expires_at.isoformat().replace("+00:00", "Z")
    metadata = {
        "schema_version": 1,
        "active_goal_excerpt": request.active_goal[:512],
        "allowed_writes": list(request.allowed_writes),
        "forbidden_boundaries": [
            "kernel/governance",
            "roadmap/backlog/spec hydration",
            "public/cockpit/project repos",
            "commits/pushes/releases/dependencies/credentials/destructive actions",
        ],
    }
    scope_gate = {
        "approved": True,
        "expires_at": expires_text,
        "goal": request.goal,
        "session_id": request.session_id,
        "approved_by": APPROVED_BY,
        "approval_basis": (
            "Goal-mode self-approval v1 opened this planning-seed scope from an "
            "active Codex Goal after validating the allowed write set."
        ),
        "backlog_id": request.backlog_id,
        "delivery_pipeline": "standard",
        "governance_mode": "standard",
        "pipeline_command": request.pipeline_command,
        "target_layer": request.target_layer,
        "alignment_mode": "async",
        "operator_lines_are_sequential_gates": False,
        "goal_mode_self_approval": metadata,
    }
    pipeline_gate = {
        "approved": True,
        "expires_at": expires_text,
        "opened_at": opened_text,
        "pipeline": request.pipeline_command,
        "pipeline_command": request.pipeline_command,
        "research_required": False,
        "session_id": request.session_id,
    }
    return scope_gate, pipeline_gate


def write_self_approved_gates(
    repo_root: Path,
    request: GoalModeSelfApprovalRequest,
    *,
    now: datetime | None = None,
) -> tuple[Path, Path]:
    """Write scope and pipeline gates for one self-approved planning-seed scope."""
    checked_at = now or datetime.now(timezone.utc)
    assert_can_open_scope(repo_root, request, now=checked_at)
    scope_gate, pipeline_gate = build_gate_payloads(request, now=checked_at)
    azoth_dir = repo_root / ".azoth"
    azoth_dir.mkdir(parents=True, exist_ok=True)
    scope_path = azoth_dir / "scope-gate.json"
    pipeline_path = azoth_dir / "pipeline-gate.json"
    scope_path.write_text(json.dumps(scope_gate, indent=2) + "\n", encoding="utf-8")
    pipeline_path.write_text(json.dumps(pipeline_gate, indent=2) + "\n", encoding="utf-8")
    return scope_path, pipeline_path


def _load_request(path: Path) -> GoalModeSelfApprovalRequest:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise GoalModeSelfApprovalError("request JSON must be an object")
    return GoalModeSelfApprovalRequest.from_mapping(loaded)


def _cmd_check(args: argparse.Namespace) -> int:
    _load_request(args.request)
    print("OK: Goal-mode request is self-approvable")
    return 0


def _cmd_open(args: argparse.Namespace) -> int:
    request = _load_request(args.request)
    scope_path, pipeline_path = write_self_approved_gates(args.root, request)
    print(f"OK: wrote {scope_path.relative_to(args.root)}")
    print(f"OK: wrote {pipeline_path.relative_to(args.root)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Validate a Goal-mode self-approval request.")
    check.add_argument("request", type=Path)
    check.set_defaults(func=_cmd_check)
    open_cmd = sub.add_parser("open", help="Validate request and write scope/pipeline gates.")
    open_cmd.add_argument("request", type=Path)
    open_cmd.add_argument("--root", type=Path, default=Path.cwd())
    open_cmd.set_defaults(func=_cmd_open)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (GoalModeSelfApprovalError, json.JSONDecodeError) as exc:
        print(f"goal_mode_self_approval: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

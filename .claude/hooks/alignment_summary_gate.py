#!/usr/bin/env python3
"""
PreToolUse gate: enforce BL-012 stage-summary shape for writes under .azoth/handoffs/**/*.yaml|yml.

Non-handoff Write/Edit and non-Write/Edit tools pass through (allow). Malformed stdin: allow (fail-open).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from scope_gate_core import emit_hook_response
from stage_summary_validate import StageSummaryValidationError, validate_stage_summary

_PREFIX = "[alignment-summary] "


def resolve_repo_root() -> Path:
    env = os.environ.get("AZOTH_REPO_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent.parent


def _repo_root() -> Path:
    return resolve_repo_root()


@dataclass(frozen=True)
class AlignmentHandoffResult:
    allowed: bool
    deny_reason: str = ""


def evaluate_alignment_handoff(
    payload: dict, *, repo_root: Path | None = None
) -> AlignmentHandoffResult:
    """Validate BL-012 YAML for Write/Edit targeting `.azoth/handoffs/**/*.yaml|yml`."""
    tool_name = payload.get("tool_name", "")
    if tool_name not in {"Write", "Edit"}:
        return AlignmentHandoffResult(allowed=True)

    root = repo_root if repo_root is not None else resolve_repo_root()
    tool_input = payload.get("tool_input") or {}
    file_path_str = tool_input.get("file_path", "")
    if not _is_handoff_target(root, file_path_str):
        return AlignmentHandoffResult(allowed=True)

    try:
        target = Path(file_path_str)
        if not target.is_absolute():
            target = (root / target).resolve()
        else:
            target = target.resolve()
    except (OSError, ValueError):
        return AlignmentHandoffResult(allowed=False, deny_reason=_PREFIX + "invalid file_path")

    text = ""
    if tool_name == "Write":
        c = tool_input.get("content")
        if not isinstance(c, str):
            return AlignmentHandoffResult(
                allowed=False, deny_reason=_PREFIX + "Write requires string content"
            )
        text = c
    else:
        try:
            text = target.read_text(encoding="utf-8")
        except OSError:
            return AlignmentHandoffResult(
                allowed=False, deny_reason=_PREFIX + "cannot read file for Edit"
            )
        old_s = tool_input.get("old_string")
        new_s = tool_input.get("new_string")
        if not isinstance(old_s, str) or not isinstance(new_s, str):
            return AlignmentHandoffResult(
                allowed=False,
                deny_reason=_PREFIX + "Edit requires old_string and new_string",
            )
        try:
            text = _apply_single_edit(text, old_s, new_s, label="handoff")
        except StageSummaryValidationError as e:
            return AlignmentHandoffResult(allowed=False, deny_reason=_PREFIX + str(e))

    try:
        doc = _parse_single_yaml_document(text, label="handoff")
        validate_stage_summary(doc, label="handoff")
    except (yaml.YAMLError, StageSummaryValidationError) as e:
        return AlignmentHandoffResult(allowed=False, deny_reason=_PREFIX + str(e))

    return AlignmentHandoffResult(allowed=True)


def _handoffs_root(root: Path) -> Path:
    return (root / ".azoth" / "handoffs").resolve()


def _is_handoff_target(root: Path, file_path_str: str) -> bool:
    if not file_path_str:
        return False
    try:
        p = Path(file_path_str)
        if not p.is_absolute():
            p = (root / p).resolve()
        else:
            p = p.resolve()
    except (OSError, ValueError):
        return False
    hr = _handoffs_root(root)
    try:
        p.relative_to(hr)
    except ValueError:
        return False
    return p.suffix.lower() in {".yaml", ".yml"}


def _parse_single_yaml_document(text: str, *, label: str) -> dict:
    docs = list(yaml.safe_load_all(text))
    if len(docs) != 1:
        raise StageSummaryValidationError(
            f"{label}: expected exactly one YAML document, got {len(docs)}"
        )
    doc = docs[0]
    if doc is None:
        raise StageSummaryValidationError(f"{label}: empty YAML document")
    return doc


def _apply_single_edit(content: str, old_string: str, new_string: str, *, label: str) -> str:
    n = content.count(old_string)
    if n == 0:
        raise StageSummaryValidationError(f"{label}: old_string not found in file")
    if n > 1:
        raise StageSummaryValidationError(f"{label}: old_string must match exactly once, found {n}")
    return content.replace(old_string, new_string, 1)


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        emit_hook_response(allow=True)
        return

    r = evaluate_alignment_handoff(payload)
    if not r.allowed:
        emit_hook_response(allow=False, reason=r.deny_reason)
        return
    emit_hook_response(allow=True)


if __name__ == "__main__":
    main()

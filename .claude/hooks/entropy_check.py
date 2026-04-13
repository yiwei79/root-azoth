"""
Entropy delta and TRUST_CONTRACT §1 zones for PreToolUse (see kernel/TRUST_CONTRACT.md §1).

§1 defines session-scoped limits. This hook enforces them on each Write/Edit tool call.
Accumulation is keyed to scope-gate.json session_id and resets when the scope card
changes (see also docs/AZOTH_ARCHITECTURE.md — Cursor parity / PreToolUse entropy).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from entropy_state import load_state, reset_if_session_changed, save_state
from scope_gate_core import (
    REPO_ROOT,
    entropy_state_path,
    extract_old_new_strings,
    extract_target_path_str,
    extract_write_content,
    normalized_write_action,
    resolved_target,
    tool_input_dict,
)

# When tool_input lacks content strings, use conservative placeholder (planner r3).
PLACEHOLDER_LINES = 250

# §1 table caps: enforced here using session-scoped unique paths + lines_total (see module docstring).
MAX_FILES_MODIFIED = 10
MAX_FILES_CREATED = 10
MAX_LINES_PER_SESSION = 1000

# Zone thresholds on cumulative entropy_delta (TRUST_CONTRACT §1).
ZONE_YELLOW_MIN = 12.0
ZONE_RED_MIN = 25.0


def _entropy_zone(cumulative: float) -> str:
    if cumulative >= ZONE_RED_MIN:
        return "RED"
    if cumulative >= ZONE_YELLOW_MIN:
        return "YELLOW"
    return "GREEN"


@dataclass(frozen=True)
class EntropyCheckResult:
    allowed: bool
    reason: str = ""
    yellow_advisory: bool = False
    entropy_delta: float | None = None
    cumulative_entropy: float | None = None
    entropy_zone: str | None = None


def estimate_lines_changed(payload: dict) -> int:
    """Best-effort line count from Claude or VS Code write/edit payloads."""
    action = normalized_write_action(payload)
    tool_input = tool_input_dict(payload)
    if action == "write":
        content = extract_write_content(tool_input)
        if isinstance(content, str) and content.strip():
            return max(1, len(content.splitlines()))
        return PLACEHOLDER_LINES
    if action == "edit":
        old_s, new_s = extract_old_new_strings(tool_input)
        if isinstance(old_s, str) and isinstance(new_s, str) and (old_s or new_s):
            return max(1, len(old_s.splitlines()) + len(new_s.splitlines()))
        return PLACEHOLDER_LINES
    return PLACEHOLDER_LINES


def _norm_path(p: Path) -> str:
    try:
        return str(p.resolve())
    except (OSError, ValueError):
        return str(p)


def evaluate_entropy(
    payload: dict,
    scope_data: dict,
    *,
    repo_root: Path | None = None,
) -> EntropyCheckResult:
    """
    After scope allows, compute §1 entropy_delta and zones.
    Mutates entropy state file on disk when returning allowed.
    """
    root = repo_root or REPO_ROOT
    state_path = entropy_state_path(root)
    action = normalized_write_action(payload)
    if action is None:
        return EntropyCheckResult(allowed=True)
    file_path_str = extract_target_path_str(payload)
    target = resolved_target(root, file_path_str)

    sid = str(scope_data.get("session_id", "") or "default")
    state = load_state(state_path)
    state = reset_if_session_changed(state, sid)
    state.session_id = sid

    if target is None:
        return EntropyCheckResult(allowed=True)

    try:
        existed = target.exists()
    except OSError:
        existed = False

    path_key = _norm_path(target)
    lines_this = estimate_lines_changed(payload)

    modified = set(state.modified_paths)
    created = set(state.created_paths)

    if existed:
        if path_key in created:
            created.discard(path_key)
        modified.add(path_key)
    else:
        created.add(path_key)

    files_changed = 1 if existed else 0
    files_created = 0 if existed else 1
    files_deleted = 0

    lines_total = state.lines_total + lines_this

    lines_changed_metric = float(lines_this)
    delta = (
        float(files_changed + files_created)
        + float(files_deleted) * 3.0
        + lines_changed_metric / 100.0
    )

    cumulative = state.cumulative_entropy + delta

    if len(modified) > MAX_FILES_MODIFIED or len(created) > MAX_FILES_CREATED:
        return EntropyCheckResult(
            allowed=False,
            reason=(
                "[entropy-check] TRUST_CONTRACT §1: file count cap exceeded "
                f"(modified≤{MAX_FILES_MODIFIED}, created≤{MAX_FILES_CREATED})."
            ),
            entropy_delta=delta,
            cumulative_entropy=cumulative,
            entropy_zone=_entropy_zone(cumulative),
        )

    if lines_total > MAX_LINES_PER_SESSION:
        return EntropyCheckResult(
            allowed=False,
            reason=(
                f"[entropy-check] TRUST_CONTRACT §1: lines changed cap exceeded "
                f"({MAX_LINES_PER_SESSION} per session; observed {lines_total})."
            ),
            entropy_delta=delta,
            cumulative_entropy=cumulative,
            entropy_zone=_entropy_zone(cumulative),
        )

    if cumulative >= ZONE_RED_MIN:
        return EntropyCheckResult(
            allowed=False,
            reason=(
                "[entropy-check] red zone — cumulative entropy_delta ≥ "
                f"{ZONE_RED_MIN} (checkpoint required per TRUST_CONTRACT §1; delta≈{cumulative:.2f}). "
                "Before continuing, run `python3 scripts/azoth_checkpoint.py create` from the repo "
                "root (see TRUST_CONTRACT §4 Recovery Protocol)."
            ),
            entropy_delta=delta,
            cumulative_entropy=cumulative,
            entropy_zone="RED",
        )

    state.cumulative_entropy = cumulative
    state.modified_paths = sorted(modified)
    state.created_paths = sorted(created)
    state.lines_total = lines_total
    save_state(state_path, state)

    if cumulative >= ZONE_YELLOW_MIN:
        return EntropyCheckResult(
            allowed=True,
            reason=(
                f"[entropy-check] yellow zone — cumulative entropy_delta in [{ZONE_YELLOW_MIN}, "
                f"{ZONE_RED_MIN}); checkpoint recommended (≈{cumulative:.2f})."
            ),
            yellow_advisory=True,
            entropy_delta=delta,
            cumulative_entropy=cumulative,
            entropy_zone="YELLOW",
        )

    return EntropyCheckResult(
        allowed=True,
        entropy_delta=delta,
        cumulative_entropy=cumulative,
        entropy_zone="GREEN",
    )

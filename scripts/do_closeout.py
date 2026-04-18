#!/usr/bin/env python3
"""Apply the documented W1–W4 closeout sequence."""

from __future__ import annotations

import copy
import json
import pathlib
import re
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from typing import Any

import yaml
from reinforcement_count import ReinforcementError, increment_reinforcement_count
from run_ledger import load_write_claim, release_write_claim, upsert_run, upsert_session

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FINAL_DELIVERY_APPROVALS = pathlib.Path(".azoth") / "final-delivery-approvals.jsonl"
_SESSION_STATE_CHECKPOINT_FIELDS = (
    "pipeline",
    "pipeline_position",
    "current_stage_id",
    "completed_stages",
    "pending_stages",
    "pause_reason",
    "active_run_id",
)
_ROADMAP_TASK_SECTIONS = ("tasks", "completed_tasks", "deferred_tasks")
_CLOSEOUT_SCHEMA_VERSION = 1
_CLOSEOUT_STEP_SEQUENCE = ("W1", "W1b", "W2", "W3", "W4")
_CLOSEOUT_STEP_SET = frozenset(_CLOSEOUT_STEP_SEQUENCE)
_CLOSEOUT_CHECKPOINTS_KEY = "closeouts"
_ALLOWED_EPISODE_TYPES = {"success", "failure", "decision", "pattern"}
_ALLOWED_W3_MODES = {"defer", "attempt"}


class CloseoutError(RuntimeError):
    """Base error for closeout preconditions and execution failures."""


class ApprovalEvidenceError(CloseoutError):
    """Raised when governed closeout lacks valid final-delivery approval evidence."""


class ReinforcementValidationError(CloseoutError):
    """Raised when requested reinforcement targets are not safe to apply."""


class CloseoutSemanticsError(CloseoutError):
    """Raised when structured closeout semantics are malformed."""


class CloseoutCheckpointError(CloseoutError):
    """Raised when resumable closeout checkpoint state is invalid or contradictory."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise CloseoutError(f"Invalid JSON in {path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise CloseoutError(f"Expected JSON object in {path}")
    return data


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ApprovalEvidenceError(
                    f"Invalid JSON in {path} line {line_number}: {exc.msg}"
                ) from exc
            if not isinstance(record, dict):
                raise ApprovalEvidenceError(f"Expected JSON object in {path} line {line_number}")
            records.append(record)
    return records


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise CloseoutError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CloseoutError(f"Expected YAML mapping in {path}")
    return data


def write_yaml(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def default_next_action() -> str:
    return "Run `/next` to select the next scoped task."


def _parse_iso8601(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _scope_is_live(scope: dict[str, Any]) -> bool:
    if scope.get("approved") is not True:
        return False
    if str(scope.get("scope_status") or "active").strip() not in {"", "active"}:
        return False
    expires_at = _parse_iso8601(str(scope.get("expires_at") or ""))
    return expires_at is not None and expires_at > utc_now()


def _normalized_string_list(value: Any, *, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CloseoutSemanticsError(f"Closeout semantics blocked: {label} must be a list.")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise CloseoutSemanticsError(
                f"Closeout semantics blocked: {label}[{index}] must be a string."
            )
        text = item.strip()
        if text:
            normalized.append(text)
    return normalized


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def normalize_closeout_semantics(
    raw: dict[str, Any] | None,
    *,
    scope: dict[str, Any],
) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise CloseoutSemanticsError("Closeout semantics blocked: root must be a mapping.")

    schema_version = raw.get("schema_version", _CLOSEOUT_SCHEMA_VERSION)
    if schema_version != _CLOSEOUT_SCHEMA_VERSION:
        raise CloseoutSemanticsError(
            "Closeout semantics blocked: schema_version must be "
            f"{_CLOSEOUT_SCHEMA_VERSION}."
        )

    session_summary_cfg = raw.get("session_summary") or {}
    if not isinstance(session_summary_cfg, dict):
        raise CloseoutSemanticsError(
            "Closeout semantics blocked: session_summary must be a mapping."
        )
    episode_cfg = raw.get("episode") or {}
    if not isinstance(episode_cfg, dict):
        raise CloseoutSemanticsError("Closeout semantics blocked: episode must be a mapping.")
    handoff_cfg = raw.get("handoff") or {}
    if not isinstance(handoff_cfg, dict):
        raise CloseoutSemanticsError("Closeout semantics blocked: handoff must be a mapping.")
    w3_cfg = raw.get("w3") or {}
    if not isinstance(w3_cfg, dict):
        raise CloseoutSemanticsError("Closeout semantics blocked: w3 must be a mapping.")

    summary = str(
        episode_cfg.get("summary")
        or session_summary_cfg.get("summary")
        or "Completed session closeout via scripts/do_closeout.py (W1-W4)."
    ).strip()
    if not summary:
        raise CloseoutSemanticsError(
            "Closeout semantics blocked: episode.summary must be non-empty."
        )

    episode_type = str(episode_cfg.get("type") or "success").strip().lower()
    if episode_type not in _ALLOWED_EPISODE_TYPES:
        raise CloseoutSemanticsError(
            "Closeout semantics blocked: episode.type must be one of "
            f"{sorted(_ALLOWED_EPISODE_TYPES)}."
        )

    context = episode_cfg.get("context") or {}
    if not isinstance(context, dict):
        raise CloseoutSemanticsError(
            "Closeout semantics blocked: episode.context must be a mapping when present."
        )

    next_action = str(handoff_cfg.get("next_action") or "").strip() or None
    w3_mode = str(w3_cfg.get("mode") or "defer").strip().lower() or "defer"
    if w3_mode not in _ALLOWED_W3_MODES:
        raise CloseoutSemanticsError(
            "Closeout semantics blocked: w3.mode must be one of "
            f"{sorted(_ALLOWED_W3_MODES)}."
        )

    return {
        "schema_version": _CLOSEOUT_SCHEMA_VERSION,
        "session_summary": {
            "summary": summary,
        },
        "episode": {
            "type": episode_type,
            "summary": summary,
            "lessons": _normalized_string_list(episode_cfg.get("lessons"), label="episode.lessons"),
            "tags": _dedupe_preserve_order(
                ["closeout", "session-closeout"]
                + _normalized_string_list(episode_cfg.get("tags"), label="episode.tags")
            ),
            "m2_candidate": episode_cfg.get("m2_candidate") is True,
            "context": copy.deepcopy(context),
        },
        "handoff": {
            "next_action": next_action,
            "pending_decisions": _normalized_string_list(
                handoff_cfg.get("pending_decisions"),
                label="handoff.pending_decisions",
            ),
            "files_changed": _dedupe_preserve_order(
                _normalized_string_list(handoff_cfg.get("files_changed"), label="handoff.files_changed")
            ),
        },
        "w3": {
            "mode": w3_mode,
            "reason": str(w3_cfg.get("reason") or "").strip(),
        },
        "scope": {
            "session_id": str(scope.get("session_id") or "unknown-session"),
            "goal": str(scope.get("goal") or "Session closeout"),
        },
    }


def load_closeout_semantics_input(
    *,
    semantics_file: str | None = None,
    semantics_json: str | None = None,
) -> dict[str, Any] | None:
    if semantics_file and semantics_json:
        raise CloseoutSemanticsError(
            "Closeout semantics blocked: use either --semantics-file or --semantics-json, not both."
        )
    if semantics_json:
        try:
            payload = json.loads(semantics_json)
        except json.JSONDecodeError as exc:
            raise CloseoutSemanticsError(
                f"Closeout semantics blocked: invalid JSON for --semantics-json: {exc.msg}"
            ) from exc
        if not isinstance(payload, dict):
            raise CloseoutSemanticsError(
                "Closeout semantics blocked: --semantics-json must decode to a mapping."
            )
        return payload
    if semantics_file:
        path = pathlib.Path(semantics_file)
        if not path.exists():
            raise CloseoutSemanticsError(
                f"Closeout semantics blocked: semantics file not found at {path}."
            )
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise CloseoutSemanticsError(
                f"Closeout semantics blocked: invalid YAML in semantics file {path}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise CloseoutSemanticsError(
                f"Closeout semantics blocked: semantics file {path} must contain a mapping."
            )
        return payload
    return None


def _normalize_reinforcement_ids(reinforce_episode_ids: list[str] | None) -> list[str]:
    if not reinforce_episode_ids:
        return []
    normalized: list[str] = []
    for item in reinforce_episode_ids:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def is_governed_scope(scope: dict[str, Any]) -> bool:
    governance_mode = str(scope.get("governance_mode") or "").strip()
    if governance_mode == "governed":
        return True
    if governance_mode == "standard":
        return False
    return scope.get("delivery_pipeline") == "governed" or scope.get("target_layer") == "M1"


def _is_human_approved_final_delivery(record: dict[str, Any]) -> bool:
    if str(record.get("gate") or "") != "final-delivery":
        return False
    if str(record.get("actor_type") or "").lower() != "human":
        return False
    return record.get("approved") is True


def _latest_final_delivery_record(
    records: list[dict[str, Any]],
    *,
    session_id: str,
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for record in records:
        if str(record.get("session_id") or "") != session_id:
            continue
        if str(record.get("gate") or "") != "final-delivery":
            continue
        latest = record
    return latest


def enforce_governed_closeout_approval(
    repo_root: pathlib.Path,
    scope: dict[str, Any],
) -> None:
    if not is_governed_scope(scope):
        return

    session_id = str(scope.get("session_id") or "")
    if not session_id:
        raise ApprovalEvidenceError(
            "Governed closeout blocked: scope-gate.json is missing session_id."
        )

    approvals_path = repo_root / FINAL_DELIVERY_APPROVALS
    if not approvals_path.exists():
        raise ApprovalEvidenceError(
            f"Governed closeout blocked: missing {approvals_path}. "
            "Record human final delivery approval before W1-W4."
        )

    latest = _latest_final_delivery_record(load_jsonl(approvals_path), session_id=session_id)
    if latest is None:
        raise ApprovalEvidenceError(
            "Governed closeout blocked: no matching final-delivery approval record "
            f"for session_id={session_id!r}."
        )
    if not _is_human_approved_final_delivery(latest):
        raise ApprovalEvidenceError(
            "Governed closeout blocked: latest matching final-delivery record must be "
            "actor_type=human and approved=true."
        )


def _next_episode_id(episodes: list[dict[str, Any]]) -> str:
    last_num = 0
    for episode in episodes:
        try:
            episode_id = str(episode.get("id") or "")
            if episode_id.startswith("ep-"):
                last_num = max(last_num, int(episode_id.split("-")[1]))
        except ValueError:
            continue
    return f"ep-{last_num + 1:03d}"


def append_episode(
    repo_root: pathlib.Path,
    scope: dict[str, Any],
    semantics: dict[str, Any],
    timestamp: str,
    *,
    files_changed: list[str],
) -> tuple[str, dict[str, Any], int]:
    episodes_path = repo_root / ".azoth" / "memory" / "episodes.jsonl"
    episodes = load_jsonl(episodes_path)
    new_id = _next_episode_id(episodes)

    new_episode = {
        "id": new_id,
        "timestamp": timestamp,
        "session_id": str(scope.get("session_id") or "unknown-session"),
        "type": semantics["episode"]["type"],
        "goal": str(scope.get("goal") or "Session closeout"),
        "summary": semantics["episode"]["summary"],
        "lessons": semantics["episode"]["lessons"],
        "tags": semantics["episode"]["tags"],
        "reinforcement_count": 0,
        "m2_candidate": semantics["episode"]["m2_candidate"],
        "context": {
            **copy.deepcopy(semantics["episode"]["context"]),
            "files_changed": _dedupe_preserve_order(
                files_changed + semantics["handoff"]["files_changed"]
            ),
        },
    }

    episodes_path.parent.mkdir(parents=True, exist_ok=True)
    with open(episodes_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(new_episode) + "\n")

    print(f"W1: Appended episode {new_id} to {episodes_path}")
    return new_id, new_episode, len(episodes) + 1


def validate_reinforcement_targets(
    repo_root: pathlib.Path,
    reinforce_episode_ids: list[str],
) -> None:
    if not reinforce_episode_ids:
        return

    episodes = load_jsonl(repo_root / ".azoth" / "memory" / "episodes.jsonl")
    existing_ids = {str(episode.get("id") or "") for episode in episodes}
    missing_ids = [
        episode_id for episode_id in reinforce_episode_ids if episode_id not in existing_ids
    ]
    if missing_ids:
        quoted_ids = ", ".join(repr(episode_id) for episode_id in missing_ids)
        raise ReinforcementValidationError(
            "Closeout blocked: unknown reinforce episode id(s): "
            f"{quoted_ids}. Confirm exact existing episode ids before running closeout."
        )


def load_closeout_checkpoint(
    repo_root: pathlib.Path,
    *,
    session_id: str,
) -> dict[str, Any] | None:
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    ledger = load_yaml(ledger_path)
    closeouts = ledger.get(_CLOSEOUT_CHECKPOINTS_KEY)
    if not isinstance(closeouts, dict):
        return None
    checkpoint = closeouts.get(session_id)
    return checkpoint if isinstance(checkpoint, dict) else None


def write_closeout_checkpoint(
    repo_root: pathlib.Path,
    *,
    session_id: str,
    checkpoint: dict[str, Any],
) -> None:
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    ledger = load_yaml(ledger_path) if ledger_path.exists() else {"schema_version": 1, "runs": []}
    if "schema_version" not in ledger:
        ledger["schema_version"] = 1
    if not isinstance(ledger.get("runs"), list):
        ledger["runs"] = []
    closeouts = ledger.get(_CLOSEOUT_CHECKPOINTS_KEY)
    if not isinstance(closeouts, dict):
        closeouts = {}
        ledger[_CLOSEOUT_CHECKPOINTS_KEY] = closeouts
    closeouts[session_id] = checkpoint
    write_yaml(ledger_path, ledger)


def record_closeout_checkpoint(
    repo_root: pathlib.Path,
    *,
    session_id: str,
    previous: dict[str, Any] | None,
    semantics: dict[str, Any],
    reinforce_episode_ids: list[str],
    administrative_finalize: bool,
    status: str,
    next_step: str | None,
    updated_at: str,
    completed_steps: list[str] | None = None,
    deferred_steps: list[str] | None = None,
    failed_step: str | None = None,
    latest_episode: dict[str, Any] | None = None,
    episode_count: int | None = None,
    next_action: str | None = None,
    session_status: str | None = None,
    w3_status: str | None = None,
    w3_note: str | None = None,
) -> dict[str, Any]:
    checkpoint = copy.deepcopy(previous) if isinstance(previous, dict) else {}
    checkpoint["schema_version"] = _CLOSEOUT_SCHEMA_VERSION
    checkpoint["session_id"] = session_id
    checkpoint["status"] = status
    checkpoint["semantics"] = copy.deepcopy(semantics)
    checkpoint["reinforce_episode_ids"] = list(reinforce_episode_ids)
    checkpoint["administrative_finalize"] = administrative_finalize
    checkpoint["updated_at"] = updated_at
    checkpoint.setdefault("started_at", updated_at)
    if next_step:
        checkpoint["next_step"] = next_step
    else:
        checkpoint.pop("next_step", None)

    if completed_steps is not None:
        checkpoint["completed_steps"] = _dedupe_preserve_order(
            list(checkpoint.get("completed_steps") or []) + completed_steps
        )
    if deferred_steps is not None:
        checkpoint["deferred_steps"] = _dedupe_preserve_order(
            list(checkpoint.get("deferred_steps") or []) + deferred_steps
        )

    if failed_step:
        checkpoint["failed_step"] = failed_step
    else:
        checkpoint.pop("failed_step", None)

    if latest_episode is not None:
        checkpoint["latest_episode"] = copy.deepcopy(latest_episode)
        checkpoint["latest_episode_id"] = str(latest_episode.get("id") or "")
    if isinstance(episode_count, int):
        checkpoint["episode_count"] = episode_count
    if next_action is not None:
        checkpoint["next_action"] = next_action
    if session_status is not None:
        checkpoint["session_status"] = session_status
    if w3_status is not None:
        checkpoint["w3_status"] = w3_status
    if w3_note:
        checkpoint["w3_note"] = w3_note
    elif "w3_note" in checkpoint and w3_status == "complete":
        checkpoint.pop("w3_note", None)

    write_closeout_checkpoint(repo_root, session_id=session_id, checkpoint=checkpoint)
    return checkpoint


def _step_index(step: str) -> int:
    if step not in _CLOSEOUT_STEP_SET:
        raise CloseoutCheckpointError(f"Closeout checkpoint blocked: unknown next_step {step!r}.")
    return _CLOSEOUT_STEP_SEQUENCE.index(step)


def resolve_closeout_plan(
    repo_root: pathlib.Path,
    *,
    scope: dict[str, Any],
    provided_semantics: dict[str, Any] | None,
    reinforce_episode_ids: list[str],
    administrative_finalize: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any], list[str], str]:
    session_id = str(scope.get("session_id") or "").strip()
    if not session_id:
        raise CloseoutError("Closeout blocked: scope-gate.json is missing session_id.")

    checkpoint = load_closeout_checkpoint(repo_root, session_id=session_id)
    normalized_semantics = (
        normalize_closeout_semantics(provided_semantics, scope=scope)
        if provided_semantics is not None
        else None
    )
    normalized_reinforcement_ids = _normalize_reinforcement_ids(reinforce_episode_ids)

    if checkpoint is None:
        if not _scope_is_live(scope):
            raise CloseoutError(
                "Closeout blocked: scope-gate.json must be approved and unexpired "
                "before starting a new closeout."
            )
        return (
            None,
            normalized_semantics or normalize_closeout_semantics({}, scope=scope),
            normalized_reinforcement_ids,
            "W1",
        )

    checkpoint_status = str(checkpoint.get("status") or "").strip()
    if checkpoint_status == "complete":
        raise CloseoutCheckpointError(
            f"Closeout already complete for session_id={session_id!r}; "
            "refuse to append W1 again."
        )

    next_step = str(checkpoint.get("next_step") or "").strip()
    if next_step not in _CLOSEOUT_STEP_SET:
        raise CloseoutCheckpointError(
            f"Closeout retry blocked: checkpoint for session_id={session_id!r} "
            f"is missing a valid next_step; got {next_step!r}."
        )

    stored_semantics_raw = checkpoint.get("semantics")
    if not isinstance(stored_semantics_raw, dict):
        raise CloseoutCheckpointError(
            f"Closeout retry blocked: checkpoint for session_id={session_id!r} "
            "is missing saved semantics."
        )
    stored_semantics = normalize_closeout_semantics(stored_semantics_raw, scope=scope)
    if normalized_semantics is not None and normalized_semantics != stored_semantics:
        raise CloseoutCheckpointError(
            f"Closeout retry blocked: provided semantics do not match the saved "
            f"checkpoint for session_id={session_id!r}."
        )

    stored_reinforcement_ids = _normalize_reinforcement_ids(
        checkpoint.get("reinforce_episode_ids")
        if isinstance(checkpoint.get("reinforce_episode_ids"), list)
        else []
    )
    if normalized_reinforcement_ids and normalized_reinforcement_ids != stored_reinforcement_ids:
        raise CloseoutCheckpointError(
            f"Closeout retry blocked: provided reinforcement ids do not match the saved "
            f"checkpoint for session_id={session_id!r}."
        )

    if bool(checkpoint.get("administrative_finalize")) != administrative_finalize:
        raise CloseoutCheckpointError(
            f"Closeout retry blocked: --administrative-finalize does not match the saved "
            f"checkpoint for session_id={session_id!r}."
        )

    print(f"Resuming closeout for session '{session_id}' from {next_step}")
    return checkpoint, stored_semantics, stored_reinforcement_ids, next_step


def enforce_closeout_preflight(
    repo_root: pathlib.Path,
    *,
    scope: dict[str, Any],
    session_id: str,
    next_step: str,
) -> None:
    if next_step == "W1" and not _scope_is_live(scope):
        raise CloseoutError(
            "Closeout blocked: scope-gate.json must be approved and unexpired "
            "before the first W1 mutation."
        )

    if next_step in {"W1", "W2", "W4"}:
        write_claim = load_write_claim(repo_root)
        if isinstance(write_claim, dict):
            holder = str(write_claim.get("session_id") or "").strip()
            if holder and holder != session_id:
                location = str(write_claim.get("worktree_path") or "").strip()
                expires_at = str(write_claim.get("expires_at") or "unknown")
                location_note = f" at {location}" if location else ""
                raise CloseoutError(
                    f"Closeout blocked before {next_step}: write claim held by "
                    f"{holder!r}{location_note} until {expires_at}."
                )


def close_scope_gate(repo_root: pathlib.Path, timestamp: str) -> dict[str, Any]:
    gate_path = repo_root / ".azoth" / "scope-gate.json"
    gate_data = load_json(gate_path)
    gate_data["approved"] = False
    gate_data["closed_at"] = timestamp
    with open(gate_path, "w", encoding="utf-8") as handle:
        json.dump(gate_data, handle, indent=2)
    print(f"W2: scope gate closed at {gate_path}")
    return gate_data


def _completed_date(timestamp: str) -> str:
    return timestamp.split("T", 1)[0]


def _normalize_decision_refs(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _find_top_level_item_block(text: str, item_id: str) -> tuple[int, int] | None:
    start_match = re.search(
        rf'^\s*-\s+id:\s*["\']?{re.escape(item_id)}["\']?\s*$',
        text,
        flags=re.MULTILINE,
    )
    if not start_match:
        return None
    next_match = re.search(r"^\s*-\s+id:\s", text[start_match.end() :], flags=re.MULTILINE)
    end = start_match.end() + next_match.start() if next_match else len(text)
    return start_match.start(), end


def _mark_backlog_item_complete(
    repo_root: pathlib.Path,
    *,
    backlog_id: str,
    completed_date: str,
) -> tuple[dict[str, Any] | None, bool]:
    backlog_path = repo_root / ".azoth" / "backlog.yaml"
    backlog_data = load_yaml(backlog_path)
    items = backlog_data.get("items")
    if not isinstance(items, list):
        print(f"W2c: backlog item {backlog_id!r} not found in {backlog_path} (items missing)")
        return None, False

    metadata: dict[str, Any] | None = None
    for item in items:
        if isinstance(item, dict) and str(item.get("id") or "") == backlog_id:
            metadata = item
            break

    if metadata is None:
        print(f"W2c: backlog item {backlog_id!r} not found in {backlog_path}")
        return None, False

    text = backlog_path.read_text(encoding="utf-8")
    bounds = _find_top_level_item_block(text, backlog_id)
    if bounds is None:
        print(f"W2c: backlog item {backlog_id!r} not found as a text block in {backlog_path}")
        return metadata, False

    start, end = bounds
    block = text[start:end]
    new_block = re.sub(r"^(\s+status:\s*).*$", r"\1complete", block, count=1, flags=re.MULTILINE)
    if re.search(r"^\s+completed_date:\s*", new_block, flags=re.MULTILINE):
        new_block = re.sub(
            r"^(\s+)completed_date:\s*.*$",
            lambda m: f"{m.group(1)}completed_date: '{completed_date}'",
            new_block,
            count=1,
            flags=re.MULTILINE,
        )
    elif re.search(r"^\s+created_date:\s*.*$", new_block, flags=re.MULTILINE):
        new_block = re.sub(
            r"^(\s+)created_date:\s*.*\n",
            lambda m: f"{m.group(0)}{m.group(1)}completed_date: '{completed_date}'\n",
            new_block,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        new_block = re.sub(
            r"^(\s+)status:\s*complete\n",
            lambda m: f"{m.group(0)}{m.group(1)}completed_date: '{completed_date}'\n",
            new_block,
            count=1,
            flags=re.MULTILINE,
        )

    changed = new_block != block
    if changed:
        backlog_path.write_text(text[:start] + new_block + text[end:], encoding="utf-8")
        print(f"W2c: backlog item {backlog_id} marked complete")
    else:
        print(f"W2c: backlog item {backlog_id} already complete")
    return metadata, changed


def _find_version_block(text: str, version_id: str) -> tuple[int, int] | None:
    versions_match = re.search(r"^versions:\s*$", text, re.MULTILINE)
    if not versions_match:
        return None
    next_top_level = re.search(r"^[A-Za-z0-9_]+:\s", text[versions_match.end() :], re.MULTILINE)
    versions_end = (
        versions_match.end() + next_top_level.start() if next_top_level else len(text)
    )
    versions_block = text[versions_match.end() :versions_end]
    start_match = re.search(
        r'^(?P<indent>\s*)-\s+id:\s*["\']?' + re.escape(version_id) + r'["\']?\s*$',
        versions_block,
        re.MULTILINE,
    )
    if not start_match:
        return None
    item_indent = re.escape(start_match.group("indent"))
    next_match = re.search(
        rf"^{item_indent}-\s+id:\s",
        versions_block[start_match.end() :],
        re.MULTILINE,
    )
    block_start = versions_match.end() + start_match.start()
    block_end = (
        versions_match.end() + start_match.end() + next_match.start()
        if next_match
        else versions_end
    )
    return block_start, block_end


def _find_initiative_block(text: str, initiative_id: str) -> tuple[int, int] | None:
    initiatives_match = re.search(r"^initiatives:\s*$", text, re.MULTILINE)
    if not initiatives_match:
        return None

    initiatives_block = text[initiatives_match.end() :]
    start_match = re.search(
        r'^(?P<indent>\s*)-\s+id:\s*["\']?' + re.escape(initiative_id) + r'["\']?\s*$',
        initiatives_block,
        re.MULTILINE,
    )
    if not start_match:
        return None

    item_indent = re.escape(start_match.group("indent"))
    next_match = re.search(
        rf"^{item_indent}-\s+id:\s",
        initiatives_block[start_match.end() :],
        re.MULTILINE,
    )
    block_start = initiatives_match.end() + start_match.start()
    block_end = (
        initiatives_match.end() + start_match.end() + next_match.start()
        if next_match
        else len(text)
    )
    return block_start, block_end


def _find_roadmap_version(
    roadmap: dict[str, Any],
    *,
    version_id: str,
) -> dict[str, Any] | None:
    versions = roadmap.get("versions")
    if not isinstance(versions, list):
        return None
    for version in versions:
        if isinstance(version, dict) and str(version.get("id") or "") == version_id:
            return version
    return None


def _find_initiative_for_task(
    roadmap: dict[str, Any],
    *,
    task_id: str,
) -> dict[str, Any] | None:
    for initiative in roadmap.get("initiatives") or []:
        if not isinstance(initiative, dict):
            continue
        if str(initiative.get("task_ref") or "") == task_id:
            return initiative
        for item in initiative.get("slices") or []:
            if isinstance(item, dict) and str(item.get("task_ref") or "") == task_id:
                return initiative
    return None


def _completed_task_ids(roadmap: dict[str, Any]) -> set[str]:
    completed: set[str] = set()
    for version in roadmap.get("versions") or []:
        if not isinstance(version, dict):
            continue
        for entry in version.get("completed_tasks") or []:
            if isinstance(entry, dict):
                task_id = str(entry.get("id") or "").strip()
                if task_id:
                    completed.add(task_id)
    return completed


def _initiative_slices(initiative: dict[str, Any]) -> list[dict[str, Any]]:
    raw = initiative.get("slices")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    task_ref = str(initiative.get("task_ref") or "").strip()
    spec_ref = str(initiative.get("spec_ref") or "").strip()
    phase = initiative.get("phase")
    if not task_ref and not spec_ref and phase is None:
        return []

    return [
        {
            "task_ref": task_ref or None,
            "spec_ref": spec_ref or None,
            "phase": phase,
            "status": "active" if phase else "historical",
            "role": "primary",
        }
    ]


def _rewrite_initiative_block(
    roadmap_path: pathlib.Path,
    *,
    initiative: dict[str, Any],
) -> bool:
    initiative_id = str(initiative.get("id") or "").strip()
    if not initiative_id:
        return False

    text = roadmap_path.read_text(encoding="utf-8")
    bounds = _find_initiative_block(text, initiative_id)
    if bounds is None:
        return False

    rendered = textwrap.indent(
        yaml.safe_dump([initiative], sort_keys=False, allow_unicode=True).rstrip("\n"),
        "  ",
    ) + "\n"
    start, end = bounds
    if start > 0 and text[start - 1] != "\n":
        rendered = "\n" + rendered
    roadmap_path.write_text(text[:start] + rendered + text[end:], encoding="utf-8")
    return True


def _sync_initiative_alias_after_task_completion(
    repo_root: pathlib.Path,
    *,
    roadmap_task_id: str,
) -> bool:
    roadmap_path = repo_root / ".azoth" / "roadmap.yaml"
    roadmap = load_yaml(roadmap_path)
    initiative = _find_initiative_for_task(roadmap, task_id=roadmap_task_id)
    if initiative is None:
        return False

    slices = _initiative_slices(initiative)
    if not slices:
        return False

    completed_ids = _completed_task_ids(roadmap)
    changed = False
    current_alias = str(initiative.get("task_ref") or "").strip()

    for item in slices:
        task_ref = str(item.get("task_ref") or "").strip()
        if task_ref and task_ref in completed_ids and str(item.get("status") or "") != "complete":
            item["status"] = "complete"
            if str(item.get("role") or "") == "primary":
                item["role"] = "historical"
            changed = True

    if current_alias == roadmap_task_id:
        next_slice = next(
            (
                item
                for item in slices
                if str(item.get("task_ref") or "").strip() != roadmap_task_id
                and str(item.get("task_ref") or "").strip() not in completed_ids
                and str(item.get("status") or "") not in {"complete", "historical"}
            ),
            None,
        )
        if next_slice is not None:
            for item in slices:
                if item is next_slice:
                    item["role"] = "primary"
                    item["status"] = "active"
                elif str(item.get("role") or "") == "primary":
                    item["role"] = "historical"
            initiative["task_ref"] = next_slice.get("task_ref")
            initiative["spec_ref"] = next_slice.get("spec_ref")
            initiative["phase"] = next_slice.get("phase")
            changed = True
            print(
                f"W2c: initiative {initiative['id']} retargeted to next slice "
                f"{initiative['task_ref']}"
            )

    if not changed:
        return False

    initiative["slices"] = slices
    return _rewrite_initiative_block(roadmap_path, initiative=initiative)


def _resolve_roadmap_task_id(
    repo_root: pathlib.Path,
    *,
    backlog_id: str,
    roadmap_ref: str,
    target_version: str,
) -> tuple[str | None, str]:
    candidate = (roadmap_ref or backlog_id).strip()
    if not candidate:
        return None, f"backlog item {backlog_id} has no roadmap task reference"
    if not target_version:
        return (
            None,
            f"skipping roadmap completion for backlog item {backlog_id}; "
            f"target_version missing for ref {candidate!r}",
        )

    roadmap = load_yaml(repo_root / ".azoth" / "roadmap.yaml")
    version = _find_roadmap_version(roadmap, version_id=target_version)
    if version is None:
        return (
            None,
            f"skipping roadmap completion for backlog item {backlog_id}; "
            f"roadmap version {target_version!r} not found for ref {candidate!r}",
        )

    for section_name in _ROADMAP_TASK_SECTIONS:
        section = version.get(section_name)
        if not isinstance(section, list):
            continue
        for entry in section:
            if isinstance(entry, dict) and str(entry.get("id") or "") == candidate:
                return candidate, ""

    return (
        None,
        f"skipping roadmap completion for backlog item {backlog_id}; "
        f"ref {candidate!r} is not a roadmap task id in {target_version}",
    )


def _find_section_bounds(block: str, section_name: str) -> tuple[int, int] | None:
    start_match = re.search(
        rf"^(\s*){re.escape(section_name)}:\s*(?:null|\[\])?\s*$",
        block,
        flags=re.MULTILINE,
    )
    if not start_match:
        return None
    section_indent = re.escape(start_match.group(1))
    next_match = re.search(
        rf"^{section_indent}[A-Za-z0-9_]+:\s",
        block[start_match.end() :],
        flags=re.MULTILINE,
    )
    end = start_match.end() + next_match.start() if next_match else len(block)
    return start_match.start(), end


def _version_field_indent(block: str) -> str:
    for line in block.splitlines():
        if re.match(r"^\s*-\s+id:\s", line):
            continue
        match = re.match(r"^(\s+)[A-Za-z0-9_]+:\s", line)
        if match:
            return match.group(1)
    return "  "


def _remove_multiline_task_entry(block: str, task_id: str) -> tuple[str, bool]:
    lines = block.splitlines(keepends=True)
    start_idx: int | None = None
    entry_indent = 0
    for index, line in enumerate(lines):
        match = re.match(rf'^(\s*)-\s+id:\s*["\']?{re.escape(task_id)}["\']?\s*$', line)
        if match:
            start_idx = index
            entry_indent = len(match.group(1))
            break
    if start_idx is None:
        return block, False

    end_idx = start_idx + 1
    while end_idx < len(lines):
        stripped = lines[end_idx].strip()
        if not stripped:
            end_idx += 1
            continue
        indent = len(lines[end_idx]) - len(lines[end_idx].lstrip(" "))
        if indent <= entry_indent:
            break
        end_idx += 1
    return "".join(lines[:start_idx] + lines[end_idx:]), True


def _mark_roadmap_task_complete(
    repo_root: pathlib.Path,
    *,
    backlog_id: str,
    roadmap_task_id: str,
    target_version: str,
    title: str,
    decision_ref: list[str],
    completed_date: str,
) -> bool:
    roadmap_path = repo_root / ".azoth" / "roadmap.yaml"
    text = roadmap_path.read_text(encoding="utf-8")
    bounds = _find_version_block(text, target_version)
    if bounds is None:
        print(
            f"W2c: roadmap version {target_version!r} not found while completing {backlog_id}"
        )
        return False

    start, end = bounds
    block = text[start:end]
    task_id = roadmap_task_id
    changed = False

    block, removed_task = _remove_multiline_task_entry(block, task_id)
    if removed_task:
        changed = True

    deferred_bounds = _find_section_bounds(block, "deferred_tasks")
    if deferred_bounds is not None:
        deferred_start, deferred_end = deferred_bounds
        deferred_block = block[deferred_start:deferred_end]
        deferred_entry = re.search(
            rf'^\s*-\s+\{{id:\s*["\']?{re.escape(task_id)}["\']?,.*(?:\n|$)',
            deferred_block,
            flags=re.MULTILINE,
        )
        if deferred_entry:
            deferred_block = (
                deferred_block[: deferred_entry.start()] + deferred_block[deferred_entry.end() :]
            )
            block = block[:deferred_start] + deferred_block + block[deferred_end:]
            changed = True

    completed_pattern = rf'^\s*-\s+\{{id:\s*["\']?{re.escape(task_id)}["\']?,.*$'
    completed_entry = re.search(completed_pattern, block, flags=re.MULTILINE)
    decision_text = f"[{', '.join(decision_ref)}]" if decision_ref else "[]"
    title_text = title.replace("\\", "\\\\").replace('"', '\\"')
    if completed_entry:
        new_line = re.sub(
            r'completed_date: "[^"]*"',
            f'completed_date: "{completed_date}"',
            completed_entry.group(0),
            count=1,
        )
        if new_line != completed_entry.group(0):
            block = (
                block[: completed_entry.start()]
                + new_line
                + block[completed_entry.end() :]
            )
            changed = True
    else:
        completed_bounds = _find_section_bounds(block, "completed_tasks")
        if completed_bounds is None:
            key_indent = _version_field_indent(block)
            item_indent = key_indent + "  "
            completed_line = (
                f'{item_indent}- {{id: {task_id}, title: "{title_text}", '
                f'completed_date: "{completed_date}", decision_ref: {decision_text}}}\n'
            )
            completed_block = f"{key_indent}completed_tasks:\n{completed_line}"
            block = block.rstrip("\n") + "\n" + completed_block
        else:
            completed_start, completed_end = completed_bounds
            completed_block = block[completed_start:completed_end]
            header_match = re.search(
                r"^(\s*)completed_tasks:\s*(?:null|\[\])?\s*$",
                completed_block,
                flags=re.MULTILINE,
            )
            assert header_match is not None
            key_indent = header_match.group(1)
            item_indent = key_indent + "  "
            completed_line = (
                f'{item_indent}- {{id: {task_id}, title: "{title_text}", '
                f'completed_date: "{completed_date}", decision_ref: {decision_text}}}\n'
            )
            completed_block = (
                f"{key_indent}completed_tasks:\n"
                + completed_block[header_match.end() :].lstrip("\n")
            )
            completed_block = completed_block.rstrip("\n") + "\n" + completed_line
            block = block[:completed_start] + completed_block + block[completed_end:]
        changed = True

    if changed:
        roadmap_path.write_text(text[:start] + block + text[end:], encoding="utf-8")
        print(f"W2c: roadmap task {task_id} moved to completed_tasks in {target_version}")
    else:
        print(f"W2c: roadmap task {task_id} already complete in {target_version}")
    return changed


def update_planning_completion(
    repo_root: pathlib.Path,
    *,
    scope: dict[str, Any],
    timestamp: str,
    session_status: str,
) -> list[str]:
    if session_status != "closed":
        return []

    backlog_id = str(scope.get("backlog_id") or "").strip()
    if not backlog_id or backlog_id == "AD-HOC":
        return []

    completed_date = _completed_date(timestamp)
    changed_paths: list[str] = []
    metadata, backlog_changed = _mark_backlog_item_complete(
        repo_root,
        backlog_id=backlog_id,
        completed_date=completed_date,
    )
    if backlog_changed:
        changed_paths.append(".azoth/backlog.yaml")
    if metadata is None:
        return changed_paths

    target_version = str(
        metadata.get("target_version")
        or load_yaml(repo_root / ".azoth" / "roadmap.yaml").get("active_version")
        or ""
    )
    roadmap_task_id, warning = _resolve_roadmap_task_id(
        repo_root,
        backlog_id=backlog_id,
        roadmap_ref=str(metadata.get("roadmap_ref") or backlog_id),
        target_version=target_version,
    )
    if roadmap_task_id is None:
        print(f"W2c: {warning}")
        return changed_paths

    roadmap_changed = _mark_roadmap_task_complete(
        repo_root,
        backlog_id=backlog_id,
        roadmap_task_id=roadmap_task_id,
        target_version=target_version,
        title=str(metadata.get("title") or backlog_id),
        decision_ref=_normalize_decision_refs(metadata.get("decision_ref")),
        completed_date=completed_date,
    )
    if roadmap_changed:
        changed_paths.append(".azoth/roadmap.yaml")
        initiative_changed = _sync_initiative_alias_after_task_completion(
            repo_root,
            roadmap_task_id=roadmap_task_id,
        )
        if initiative_changed and ".azoth/roadmap.yaml" not in changed_paths:
            changed_paths.append(".azoth/roadmap.yaml")
    return changed_paths


def _resumable_run_for_session(
    ledger: dict[str, Any],
    *,
    session_id: str,
    preferred_run_id: str | None = None,
) -> dict[str, Any] | None:
    runs = ledger.get("runs")
    if not isinstance(runs, list):
        return None

    resumable = [
        run
        for run in runs
        if isinstance(run, dict)
        and str(run.get("session_id") or "") == session_id
        and str(run.get("status") or "") == "paused"
        and (
            str(run.get("active_stage_id") or "").strip()
            or bool(run.get("pending_stage_ids"))
        )
    ]
    if not resumable:
        return None
    if preferred_run_id:
        for run in reversed(resumable):
            if str(run.get("run_id") or "") == preferred_run_id:
                return run
    return resumable[-1]


def _open_run_for_session(
    ledger: dict[str, Any],
    *,
    session_id: str,
    preferred_run_id: str | None = None,
) -> dict[str, Any] | None:
    runs = ledger.get("runs")
    if not isinstance(runs, list):
        return None

    open_runs = [
        run
        for run in runs
        if isinstance(run, dict)
        and str(run.get("session_id") or "") == session_id
        and str(run.get("status") or "") in {"active", "paused"}
    ]
    if not open_runs:
        return None
    if preferred_run_id:
        for run in reversed(open_runs):
            if str(run.get("run_id") or "") == preferred_run_id:
                return run
    return open_runs[-1]


def update_session_registry(
    repo_root: pathlib.Path,
    *,
    scope: dict[str, Any],
    timestamp: str,
    closeout_next_action: str | None = None,
    selected_ide: str | None = None,
    administrative_finalize: bool = False,
) -> tuple[str, str, str]:
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    ledger = load_yaml(ledger_path) if ledger_path.exists() else {"schema_version": 1, "runs": []}
    sessions = ledger.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
        ledger["sessions"] = sessions

    session_id = str(scope.get("session_id") or "")
    matching_session = next(
        (
            entry
            for entry in sessions
            if isinstance(entry, dict) and str(entry.get("session_id") or "") == session_id
        ),
        None,
    )

    preferred_run_id = (
        str(matching_session.get("active_run_id") or "")
        if isinstance(matching_session, dict)
        else ""
    ) or None
    open_run = _open_run_for_session(
        ledger,
        session_id=session_id,
        preferred_run_id=preferred_run_id,
    )
    resumable_run = _resumable_run_for_session(
        ledger,
        session_id=session_id,
        preferred_run_id=preferred_run_id,
    )
    backlog_id = str(scope.get("backlog_id") or "AD-HOC")
    goal = str(scope.get("goal") or "Session closeout")
    ide = str(
        (
            (matching_session.get("ide") if isinstance(matching_session, dict) else None)
            or selected_ide
            or (resumable_run.get("ide") if isinstance(resumable_run, dict) else None)
            or "unknown"
        )
    )
    closed_next_action = (
        "Administrative finalize complete — run `/next` to select the next scoped task."
        if administrative_finalize
        else default_next_action()
    )
    if resumable_run is not None and not administrative_finalize:
        next_action = str(
            resumable_run.get("next_action")
            or (matching_session.get("next_action") if isinstance(matching_session, dict) else None)
            or default_next_action()
        )
        upsert_session(
            repo_root,
            session_id=session_id,
            backlog_id=backlog_id,
            goal=goal,
            status="parked",
            ide=ide,
            next_action=next_action,
            updated_at=timestamp,
            active_run_id=str(resumable_run.get("run_id") or preferred_run_id or ""),
        )
        session_status = "parked"
    else:
        next_action = closeout_next_action or closed_next_action
        run_to_close = open_run or resumable_run
        if run_to_close is not None:
            upsert_run(
                repo_root,
                run_id=str(run_to_close.get("run_id") or preferred_run_id or ""),
                mode=str(run_to_close.get("mode") or "auto"),
                goal=str(run_to_close.get("goal") or goal),
                status="complete",
                next_action=closed_next_action,
                session_id=session_id,
                backlog_id=backlog_id,
                ide=ide,
                updated_at=timestamp,
                stages_completed=run_to_close.get("stages_completed") or [],
                active_stage_id=None,
                pending_stage_ids=[],
                pause_reason=None,
            )
        upsert_session(
            repo_root,
            session_id=session_id,
            backlog_id=backlog_id,
            goal=goal,
            status="closed",
            ide=ide,
            next_action=next_action,
            updated_at=timestamp,
            closed_at=timestamp,
        )
        session_status = "closed"

    suffix = " — administrative finalize" if administrative_finalize else ""
    return next_action, session_status, f"W2: session registry updated ({session_status}){suffix}"


def update_episode_count(repo_root: pathlib.Path, episode_count: int) -> None:
    azoth_path = repo_root / "azoth.yaml"
    if not azoth_path.exists():
        return

    with open(azoth_path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    with open(azoth_path, "w", encoding="utf-8") as handle:
        for line in lines:
            if line.startswith("  episodes: "):
                handle.write(f"  episodes: {episode_count}\n")
            else:
                handle.write(line)

    print("W2b: azoth.yaml episode count updated")


def claude_project_memory_dir(repo_root: pathlib.Path) -> pathlib.Path:
    resolved = repo_root.resolve()
    normalized = resolved.as_posix()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    project_key = "-" + normalized.lstrip("/").replace("/", "-")
    return pathlib.Path.home() / ".claude" / "projects" / project_key / "memory"


def _active_version_snapshot(repo_root: pathlib.Path) -> tuple[str, int | None]:
    roadmap = load_yaml(repo_root / ".azoth" / "roadmap.yaml")
    active_version = str(roadmap.get("active_version") or "unknown")
    versions = roadmap.get("versions")
    if not isinstance(versions, list):
        return active_version, None
    for version in versions:
        if not isinstance(version, dict):
            continue
        if str(version.get("id") or "") != active_version:
            continue
        current_patch = version.get("current_patch")
        return active_version, int(current_patch) if isinstance(current_patch, int) else None
    return active_version, None


def update_bootloader_state(
    repo_root: pathlib.Path,
    *,
    scope: dict[str, Any],
    latest_episode: dict[str, Any],
    session_summary: str,
    next_action: str,
    session_status: str,
    pending_decisions: list[str],
) -> None:
    azoth_data = load_yaml(repo_root / "azoth.yaml")
    active_version, current_patch = _active_version_snapshot(repo_root)
    version = azoth_data.get("version", "unknown")
    phase = azoth_data.get("phase", "unknown")
    goal = str(scope.get("goal") or "Session closeout")
    pipeline = str(scope.get("pipeline_command") or scope.get("delivery_pipeline") or "standard")

    lines = [
        "# Azoth Bootloader State",
        "",
        "## Current Phase",
        (
            f"{version} · Phase {phase} · active_version: {active_version} · current_patch: "
            f"{current_patch if current_patch is not None else 'unknown'}"
        ),
        "",
        "## Last Session",
        f"- **Session**: {scope.get('session_id', 'unknown-session')}",
        f"- **Goal**: {goal}",
        f"- **Pipeline**: {pipeline}",
        f"- **Outcome**: {session_status}",
        f"- **Episode**: {latest_episode.get('id', 'unknown')} ({latest_episode.get('type', 'unknown')})",
        "",
        "## Session Summary",
        f"- {session_summary}",
        "",
        "## Key Changes This Session",
        "1. W1 appended the closeout episode.",
        "2. W2 closed the scope gate and refreshed .azoth/session-state.md as the repo-local handoff artifact.",
        "3. W3/W4 should mirror and finalize this closeout state without changing W2 authority.",
        "",
        "## Open Decisions",
    ]
    if pending_decisions:
        lines.extend(f"- {decision}" for decision in pending_decisions)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Next Action",
            f"- {next_action}",
            "",
        ]
    )

    (repo_root / ".azoth" / "bootloader-state.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    print("W2: bootloader-state.md refreshed")


def _normalized_stage_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def extract_session_checkpoint(session_state: dict[str, Any]) -> dict[str, Any]:
    checkpoint: dict[str, Any] = {}
    pipeline = str(session_state.get("pipeline") or "").strip()
    if pipeline:
        checkpoint["pipeline"] = pipeline

    pipeline_position = session_state.get("pipeline_position")
    if isinstance(pipeline_position, int) and pipeline_position > 0:
        checkpoint["pipeline_position"] = pipeline_position

    current_stage_id = str(session_state.get("current_stage_id") or "").strip()
    if current_stage_id:
        checkpoint["current_stage_id"] = current_stage_id

    completed_stages = _normalized_stage_list(session_state.get("completed_stages"))
    if completed_stages:
        checkpoint["completed_stages"] = completed_stages

    pending_stages = _normalized_stage_list(session_state.get("pending_stages"))
    if pending_stages:
        checkpoint["pending_stages"] = pending_stages

    pause_reason = str(session_state.get("pause_reason") or "").strip()
    if pause_reason:
        checkpoint["pause_reason"] = pause_reason

    active_run_id = str(session_state.get("active_run_id") or "").strip()
    if active_run_id:
        checkpoint["active_run_id"] = active_run_id

    return checkpoint


def write_session_state(
    repo_root: pathlib.Path,
    *,
    session_id: str,
    state: str,
    timestamp: str,
    active_task: str,
    active_files: list[str],
    pending_decisions: list[str],
    approved_scope: str,
    next_action: str,
    selected_ide: str | None = None,
    create_if_missing: bool = False,
    checkpoint: dict[str, Any] | None = None,
) -> str:
    session_state_path = repo_root / ".azoth" / "session-state.md"
    if not session_state_path.exists() and not create_if_missing:
        return "W2: .azoth/session-state.md not present (skipped)"
    session_state = {
        "session_id": session_id,
        "state": state,
        "last_ide": str(selected_ide or "unknown"),
        "timestamp": timestamp,
        "active_task": active_task,
        "active_files": active_files,
        "pending_decisions": pending_decisions,
        "approved_scope": approved_scope,
        "next_action": next_action,
    }
    session_state.update(extract_session_checkpoint(checkpoint or {}))
    session_state_path.write_text(yaml.safe_dump(session_state, sort_keys=False), encoding="utf-8")
    return "W2: .azoth/session-state.md refreshed as the repo-local handoff artifact"


def emit_closeout_summary(
    *,
    session_status: str,
    w3_status: str,
    w3_note: str | None,
    next_action: str,
) -> None:
    w3_disposition = "completed" if w3_status == "complete" else "deferred"
    print("Closeout summary:")
    print(f"- Outcome: {session_status}")
    print("- W2 handoff artifact: .azoth/session-state.md")
    print(f"- W3 disposition: {w3_disposition}")
    if w3_note and w3_disposition == "deferred":
        print(f"- W3 note: {w3_note}")
    print(f"- Next operator action: {next_action}")


def update_session_state(
    repo_root: pathlib.Path,
    *,
    scope: dict[str, Any],
    timestamp: str,
    session_status: str,
    active_files: list[str],
    next_action: str,
    existing_session_state: dict[str, Any],
    pending_decisions: list[str] | None = None,
    selected_ide: str | None = None,
    clear_checkpoint: bool = False,
) -> str:
    goal = str(scope.get("goal") or "Session closeout")
    if pending_decisions is None:
        pending_decisions = existing_session_state.get("pending_decisions")
        if not isinstance(pending_decisions, list):
            pending_decisions = []
    state = "parked" if session_status == "parked" else "closed"
    active_task = f"Parked — {goal}" if state == "parked" else f"Closed — {goal}"
    approved_scope = goal if state == "parked" else f"Completed: {goal}"
    return write_session_state(
        repo_root,
        session_id=str(scope.get("session_id") or "unknown-session"),
        state=state,
        timestamp=timestamp,
        active_task=active_task,
        active_files=active_files,
        pending_decisions=pending_decisions,
        approved_scope=approved_scope,
        next_action=next_action,
        selected_ide=str(existing_session_state.get("last_ide") or selected_ide or "unknown"),
        checkpoint={} if clear_checkpoint else extract_session_checkpoint(existing_session_state),
    )


def write_claude_memory_mirror(
    repo_root: pathlib.Path,
    *,
    latest_episode: dict[str, Any] | None = None,
    next_action: str | None = None,
) -> None:
    memory_dir = claude_project_memory_dir(repo_root)
    memory_dir.mkdir(parents=True, exist_ok=True)

    azoth_data = load_yaml(repo_root / "azoth.yaml")
    active_version, current_patch = _active_version_snapshot(repo_root)
    if latest_episode is None:
        episodes = load_jsonl(repo_root / ".azoth" / "memory" / "episodes.jsonl")
        latest_episode = episodes[-1] if episodes else {}
    next_step = next_action or default_next_action()

    summary_lines = [
        "# Project Status",
        "",
        f"- Last updated: {utc_now().strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- Workspace: {repo_root.resolve()}",
        f"- Toolkit version: {azoth_data.get('version', 'unknown')}",
        f"- Milestone phase: {azoth_data.get('phase', 'unknown')}",
        f"- Roadmap active_version: {active_version}",
        f"- Current patch: {current_patch if current_patch is not None else 'unknown'}",
        f"- Last episode: {latest_episode.get('id', 'none')} — {latest_episode.get('summary', 'No episode recorded.')}",
        f"- Last delivery goal: {latest_episode.get('goal', 'unknown')}",
        f"- Next action: {next_step}",
        "- Open gaps: consult .azoth/bootloader-state.md and .azoth/session-state.md for live handoff details.",
        "",
        "Authoritative sources: .azoth/memory/episodes.jsonl, .azoth/bootloader-state.md, .azoth/scope-gate.json, azoth.yaml",
    ]
    (memory_dir / "project_status.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    memory_index = [
        "# Memory Index",
        "",
        "- [Project Status](project_status.md) — mirrored from Azoth W1/W2/W4 closeout state.",
    ]
    (memory_dir / "MEMORY.md").write_text("\n".join(memory_index) + "\n", encoding="utf-8")
    print(f"W3: Claude memory mirror updated at {memory_dir}")


def run_version_bump(repo_root: pathlib.Path) -> None:
    print("W4: Running version-bump.py...")
    subprocess.run(
        [sys.executable, "scripts/version-bump.py", "--patch"],
        cwd=repo_root,
        check=True,
    )


def finalize_closeout_artifacts(
    repo_root: pathlib.Path,
    *,
    administrative_finalize: bool = False,
) -> None:
    if administrative_finalize:
        print("W4: Administrative finalize — skipping version-bump.py --patch")
    else:
        run_version_bump(repo_root)
    orientation_path = repo_root / ".azoth" / "session-orientation.txt"
    if orientation_path.exists():
        orientation_path.unlink()
        print("W4: Removed session-orientation.txt")
    else:
        print("W4: session-orientation.txt not found (skipped)")


def run_closeout(
    repo_root: pathlib.Path = REPO_ROOT,
    *,
    closeout_semantics: dict[str, Any] | None = None,
    reinforce_episode_ids: list[str] | None = None,
    administrative_finalize: bool = False,
) -> None:
    scope = load_json(repo_root / ".azoth" / "scope-gate.json")
    session_id = str(scope.get("session_id") or "").strip()
    checkpoint, semantics, reinforce_episode_ids, next_step = resolve_closeout_plan(
        repo_root,
        scope=scope,
        provided_semantics=closeout_semantics,
        reinforce_episode_ids=reinforce_episode_ids or [],
        administrative_finalize=administrative_finalize,
    )
    enforce_governed_closeout_approval(repo_root, scope)
    if _step_index(next_step) <= _step_index("W1b"):
        validate_reinforcement_targets(repo_root, reinforce_episode_ids)
    enforce_closeout_preflight(
        repo_root,
        scope=scope,
        session_id=session_id,
        next_step=next_step,
    )

    timestamp = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    backlog_id = str(scope.get("backlog_id") or "").strip()
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    session_state_path = repo_root / ".azoth" / "session-state.md"
    existing_session_state = load_yaml(session_state_path)
    authoritative_files = [
        ".azoth/memory/episodes.jsonl",
        ".azoth/bootloader-state.md",
        ".azoth/scope-gate.json",
        ".azoth/run-ledger.local.yaml",
        "azoth.yaml",
    ]
    if backlog_id and backlog_id != "AD-HOC":
        authoritative_files.extend([".azoth/backlog.yaml", ".azoth/roadmap.yaml"])
    if session_state_path.exists():
        authoritative_files.append(".azoth/session-state.md")
    latest_episode = (
        copy.deepcopy(checkpoint.get("latest_episode"))
        if isinstance(checkpoint, dict) and isinstance(checkpoint.get("latest_episode"), dict)
        else None
    )
    episode_count = (
        int(checkpoint.get("episode_count"))
        if isinstance(checkpoint, dict) and isinstance(checkpoint.get("episode_count"), int)
        else None
    )
    if latest_episode is None and _step_index(next_step) > _step_index("W1"):
        latest_episode_id = (
            str(checkpoint.get("latest_episode_id") or "") if isinstance(checkpoint, dict) else ""
        )
        episodes = load_jsonl(repo_root / ".azoth" / "memory" / "episodes.jsonl")
        latest_episode = next(
            (
                episode
                for episode in reversed(episodes)
                if str(episode.get("id") or "") == latest_episode_id
            ),
            None,
        )
        if latest_episode is None:
            raise CloseoutCheckpointError(
                f"Closeout retry blocked: checkpoint for session_id={session_id!r} "
                "does not point at a recoverable W1 episode."
            )
        if episode_count is None:
            episode_count = len(episodes)

    if _step_index(next_step) <= _step_index("W1"):
        _episode_id, latest_episode, episode_count = append_episode(
            repo_root,
            scope,
            semantics,
            timestamp,
            files_changed=authoritative_files,
        )
        checkpoint = record_closeout_checkpoint(
            repo_root,
            session_id=session_id,
            previous=checkpoint,
            semantics=semantics,
            reinforce_episode_ids=reinforce_episode_ids,
            administrative_finalize=administrative_finalize,
            status="in_progress",
            next_step="W1b",
            updated_at=timestamp,
            completed_steps=["W1"],
            latest_episode=latest_episode,
            episode_count=episode_count,
        )

    assert latest_episode is not None
    assert episode_count is not None

    if _step_index(next_step) <= _step_index("W1b"):
        try:
            for episode_id in reinforce_episode_ids:
                result = increment_reinforcement_count(
                    repo_root,
                    episode_id,
                    session_id,
                    source="closeout",
                )
                status = "incremented" if result.changed else "already reinforced this session"
                print(
                    f"W1b: reinforcement {status} for {result.episode_id} "
                    f"(count={result.reinforcement_count})"
                )
        except ReinforcementError as exc:
            checkpoint = record_closeout_checkpoint(
                repo_root,
                session_id=session_id,
                previous=checkpoint,
                semantics=semantics,
                reinforce_episode_ids=reinforce_episode_ids,
                administrative_finalize=administrative_finalize,
                status="retryable",
                next_step="W1b",
                updated_at=timestamp,
                failed_step="W1b",
                latest_episode=latest_episode,
                episode_count=episode_count,
            )
            raise CloseoutError(
                f"Closeout blocked: failed to apply reinforcement update for {episode_id}: {exc}"
            ) from exc
        checkpoint = record_closeout_checkpoint(
            repo_root,
            session_id=session_id,
            previous=checkpoint,
            semantics=semantics,
            reinforce_episode_ids=reinforce_episode_ids,
            administrative_finalize=administrative_finalize,
            status="in_progress",
            next_step="W2",
            updated_at=timestamp,
            completed_steps=["W1b"],
            latest_episode=latest_episode,
            episode_count=episode_count,
        )

    selected_ide = str(existing_session_state.get("last_ide") or "")
    next_action = (
        str(checkpoint.get("next_action") or "").strip()
        if isinstance(checkpoint, dict)
        else ""
    )
    session_status = (
        str(checkpoint.get("session_status") or "").strip()
        if isinstance(checkpoint, dict)
        else ""
    )
    w3_status = (
        str(checkpoint.get("w3_status") or "").strip()
        if isinstance(checkpoint, dict)
        else ""
    )
    w3_note = (
        str(checkpoint.get("w3_note") or "").strip()
        if isinstance(checkpoint, dict)
        else ""
    )

    if _step_index(next_step) <= _step_index("W2"):
        try:
            close_scope_gate(repo_root, timestamp)
            next_action, session_status, registry_note = update_session_registry(
                repo_root,
                scope=scope,
                timestamp=timestamp,
                closeout_next_action=semantics["handoff"]["next_action"],
                selected_ide=selected_ide or None,
                administrative_finalize=administrative_finalize,
            )
            print(registry_note)
            update_planning_completion(
                repo_root,
                scope=scope,
                timestamp=timestamp,
                session_status=session_status,
            )
            if release_write_claim(repo_root, session_id):
                print(f"W2: write claim released for session '{session_id}'")
            else:
                print(f"W2: write claim not held by '{session_id}' — no-op")
            if ledger_path.exists():
                ledger_after_registry = load_yaml(ledger_path)
                sessions = ledger_after_registry.get("sessions")
                if isinstance(sessions, list):
                    matching_session = next(
                        (
                            entry
                            for entry in sessions
                            if isinstance(entry, dict)
                            and str(entry.get("session_id") or "") == session_id
                        ),
                        None,
                    )
                    if isinstance(matching_session, dict):
                        selected_ide = str(matching_session.get("ide") or selected_ide)
            active_files = authoritative_files.copy()
            session_state_note = update_session_state(
                repo_root,
                scope=scope,
                timestamp=timestamp,
                session_status=session_status,
                active_files=active_files,
                next_action=next_action,
                existing_session_state=existing_session_state,
                pending_decisions=semantics["handoff"]["pending_decisions"],
                selected_ide=selected_ide or None,
                clear_checkpoint=administrative_finalize or session_status == "closed",
            )
            print(session_state_note)
            update_bootloader_state(
                repo_root,
                scope=scope,
                latest_episode=latest_episode,
                session_summary=semantics["session_summary"]["summary"],
                next_action=next_action,
                session_status=session_status,
                pending_decisions=semantics["handoff"]["pending_decisions"],
            )
            update_episode_count(repo_root, episode_count)
        except Exception as exc:
            checkpoint = record_closeout_checkpoint(
                repo_root,
                session_id=session_id,
                previous=checkpoint,
                semantics=semantics,
                reinforce_episode_ids=reinforce_episode_ids,
                administrative_finalize=administrative_finalize,
                status="retryable",
                next_step="W2",
                updated_at=timestamp,
                failed_step="W2",
                latest_episode=latest_episode,
                episode_count=episode_count,
                next_action=next_action or None,
                session_status=session_status or None,
            )
            raise CloseoutError(f"Closeout blocked during W2: {exc}") from exc
        checkpoint = record_closeout_checkpoint(
            repo_root,
            session_id=session_id,
            previous=checkpoint,
            semantics=semantics,
            reinforce_episode_ids=reinforce_episode_ids,
            administrative_finalize=administrative_finalize,
            status="in_progress",
            next_step="W3",
            updated_at=timestamp,
            completed_steps=["W2"],
            latest_episode=latest_episode,
            episode_count=episode_count,
            next_action=next_action,
            session_status=session_status,
        )

    if not next_action:
        next_action = (
            str(checkpoint.get("next_action") or "").strip()
            if isinstance(checkpoint, dict)
            else default_next_action()
        ) or default_next_action()
    if not session_status:
        session_status = (
            str(checkpoint.get("session_status") or "").strip()
            if isinstance(checkpoint, dict)
            else "closed"
        ) or "closed"

    if _step_index(next_step) <= _step_index("W3"):
        w3_status = "deferred"
        w3_note = ""
        if semantics["w3"]["mode"] == "attempt":
            try:
                write_claude_memory_mirror(
                    repo_root,
                    latest_episode=latest_episode,
                    next_action=next_action,
                )
                w3_status = "complete"
            except Exception as exc:
                w3_note = (
                    "W3 deferred — sync ~/.claude/.../memory/ manually or rerun closeout "
                    f"in Claude Code ({exc})"
                )
                print(w3_note)
        else:
            reason = semantics["w3"]["reason"] or (
                "Codex keeps W3 supplemental; rerun with w3.mode=attempt when "
                "~/.claude project memory sync is desired."
            )
            w3_note = f"W3 deferred — {reason}"
            print(w3_note)

        checkpoint = record_closeout_checkpoint(
            repo_root,
            session_id=session_id,
            previous=checkpoint,
            semantics=semantics,
            reinforce_episode_ids=reinforce_episode_ids,
            administrative_finalize=administrative_finalize,
            status="in_progress",
            next_step="W4",
            updated_at=timestamp,
            completed_steps=["W3"] if w3_status == "complete" else [],
            deferred_steps=["W3"] if w3_status == "deferred" else [],
            latest_episode=latest_episode,
            episode_count=episode_count,
            next_action=next_action,
            session_status=session_status,
            w3_status=w3_status,
            w3_note=w3_note or None,
        )

    if _step_index(next_step) <= _step_index("W4"):
        try:
            finalize_closeout_artifacts(
                repo_root,
                administrative_finalize=administrative_finalize,
            )
        except Exception as exc:
            checkpoint = record_closeout_checkpoint(
                repo_root,
                session_id=session_id,
                previous=checkpoint,
                semantics=semantics,
                reinforce_episode_ids=reinforce_episode_ids,
                administrative_finalize=administrative_finalize,
                status="retryable",
                next_step="W4",
                updated_at=timestamp,
                failed_step="W4",
                latest_episode=latest_episode,
                episode_count=episode_count,
                next_action=next_action,
                session_status=session_status,
            )
            raise CloseoutError(f"Closeout blocked during W4: {exc}") from exc
        checkpoint = record_closeout_checkpoint(
            repo_root,
            session_id=session_id,
            previous=checkpoint,
            semantics=semantics,
            reinforce_episode_ids=reinforce_episode_ids,
            administrative_finalize=administrative_finalize,
            status="complete",
            next_step=None,
            updated_at=timestamp,
            completed_steps=["W4"],
            latest_episode=latest_episode,
            episode_count=episode_count,
            next_action=next_action,
            session_status=session_status,
        )

    emit_closeout_summary(
        session_status=session_status,
        w3_status=w3_status or "deferred",
        w3_note=w3_note or None,
        next_action=next_action,
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Apply the documented W1–W4 closeout sequence.")
    parser.add_argument(
        "--semantics-file",
        help="Path to a JSON or YAML mapping with structured closeout semantics.",
    )
    parser.add_argument(
        "--semantics-json",
        help="Inline JSON mapping with structured closeout semantics.",
    )
    parser.add_argument(
        "--reinforce-episode",
        action="append",
        dest="reinforce_episode_ids",
        default=[],
        help="Exact prior episode id confirmed by the human for one reinforcement_count increment.",
    )
    parser.add_argument(
        "--administrative-finalize",
        action="store_true",
        help=(
            "Close lifecycle state without a W4 patch bump. Use for bookkeeping-only "
            "or already-bumped sessions that should end closed, not parked."
        ),
    )
    args = parser.parse_args()

    try:
        closeout_semantics = load_closeout_semantics_input(
            semantics_file=args.semantics_file,
            semantics_json=args.semantics_json,
        )
        run_closeout(
            closeout_semantics=closeout_semantics,
            reinforce_episode_ids=args.reinforce_episode_ids,
            administrative_finalize=args.administrative_finalize,
        )
    except CloseoutError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Shared helpers for Azoth's append-only M3 episode store."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


VERBATIM_SOURCE_FIELD = "verbatim_source"
VERBATIM_PAYLOAD_FIELD = "verbatim_payload"
LOSSY_CONTEXT_KEYS = frozenset(
    {
        "compressed_context",
        "compressed_payload",
        "summarized_context",
        "summarized_payload",
        "summary_only",
    }
)
REINFORCEMENT_CONTEXT_FIELDS = frozenset(
    {
        "reinforced_by_sessions",
        "last_reinforced_source",
        "last_reinforced_session",
    }
)


class EpisodeStoreError(RuntimeError):
    """Raised when M3 episode storage or validation fails."""


def _canonical_json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _episode_numeric_suffix(episode_id: str) -> int | None:
    match = re.fullmatch(r"ep-(\d+)", episode_id)
    if match is None:
        return None
    return int(match.group(1))


def _next_episode_id(existing_ids: set[str]) -> str:
    last_num = 0
    for episode_id in existing_ids:
        suffix = _episode_numeric_suffix(episode_id)
        if suffix is None:
            continue
        last_num = max(last_num, suffix)
    return f"ep-{last_num + 1:03d}"


def _reconcilable_episode_key(record: dict[str, Any]) -> tuple[str, str, str] | None:
    """Return a key for sanctioned same-id rewrites that preserve verbatim payload."""

    context = record.get("context")
    if not isinstance(context, dict):
        return None

    episode_id = str(record.get("id") or "").strip()
    source = str(context.get(VERBATIM_SOURCE_FIELD) or "").strip()
    if not episode_id or not source or VERBATIM_PAYLOAD_FIELD not in context:
        return None

    return episode_id, source, _canonical_json_text(context[VERBATIM_PAYLOAD_FIELD])


def _is_allowed_reinforcement_rewrite(
    existing: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    existing_context = dict(existing.get("context") or {})
    candidate_context = dict(candidate.get("context") or {})

    existing_base_context = {
        key: value
        for key, value in existing_context.items()
        if key not in REINFORCEMENT_CONTEXT_FIELDS
    }
    candidate_base_context = {
        key: value
        for key, value in candidate_context.items()
        if key not in REINFORCEMENT_CONTEXT_FIELDS
    }
    if existing_base_context != candidate_base_context:
        return False

    existing_base_record = {
        key: value
        for key, value in existing.items()
        if key not in {"reinforcement_count", "context"}
    }
    candidate_base_record = {
        key: value
        for key, value in candidate.items()
        if key not in {"reinforcement_count", "context"}
    }
    if existing_base_record != candidate_base_record:
        return False

    existing_count = int(existing.get("reinforcement_count") or 0)
    candidate_count = int(candidate.get("reinforcement_count") or 0)
    existing_sessions = existing_context.get("reinforced_by_sessions")
    candidate_sessions = candidate_context.get("reinforced_by_sessions")
    if not isinstance(existing_sessions, list):
        existing_sessions = []
    if not isinstance(candidate_sessions, list):
        candidate_sessions = []
    if any(not isinstance(session_id, str) or not session_id.strip() for session_id in existing_sessions):
        return False
    if any(not isinstance(session_id, str) or not session_id.strip() for session_id in candidate_sessions):
        return False
    if len(existing_sessions) != len(set(existing_sessions)):
        return False
    if len(candidate_sessions) != len(set(candidate_sessions)):
        return False
    if candidate_sessions[: len(existing_sessions)] != existing_sessions:
        return False

    delta_count = candidate_count - existing_count
    delta_sessions = len(candidate_sessions) - len(existing_sessions)
    if not (delta_count > 0 and delta_count == delta_sessions):
        return False

    appended_sessions = candidate_sessions[len(existing_sessions) :]
    if not appended_sessions:
        return False
    last_session = str(candidate_context.get("last_reinforced_session") or "").strip()
    last_source = str(candidate_context.get("last_reinforced_source") or "").strip()
    return last_session == appended_sessions[-1] and bool(last_source)


def validate_episode_record(
    record: dict[str, Any],
    *,
    require_verbatim: bool = False,
    label: str = "episode",
) -> None:
    """Validate the invariant surface for one M3 episode record."""

    if not isinstance(record, dict):
        raise EpisodeStoreError(f"{label} must be a JSON object")

    episode_id = str(record.get("id") or "").strip()
    if not episode_id:
        raise EpisodeStoreError(f"{label} is missing a non-empty 'id'")

    context = record.get("context")
    if context is None:
        context = {}
    if not isinstance(context, dict):
        raise EpisodeStoreError(f"{label} context must be a JSON object")

    lossy_keys = sorted(key for key in context if key in LOSSY_CONTEXT_KEYS)
    if lossy_keys:
        joined = ", ".join(lossy_keys)
        raise EpisodeStoreError(
            f"{label} uses lossy context keys ({joined}); store raw verbatim payload instead"
        )

    has_source = VERBATIM_SOURCE_FIELD in context
    has_payload = VERBATIM_PAYLOAD_FIELD in context
    if has_source != has_payload:
        raise EpisodeStoreError(
            f"{label} must set both '{VERBATIM_SOURCE_FIELD}' and '{VERBATIM_PAYLOAD_FIELD}' together"
        )

    if require_verbatim and not has_source:
        raise EpisodeStoreError(
            f"{label} must capture verbatim context via '{VERBATIM_SOURCE_FIELD}' and '{VERBATIM_PAYLOAD_FIELD}'"
        )

    if has_source:
        source = str(context.get(VERBATIM_SOURCE_FIELD) or "").strip()
        if not source:
            raise EpisodeStoreError(f"{label} has an empty '{VERBATIM_SOURCE_FIELD}'")
        payload = context.get(VERBATIM_PAYLOAD_FIELD)
        if payload is None:
            raise EpisodeStoreError(f"{label} is missing '{VERBATIM_PAYLOAD_FIELD}'")
        try:
            _canonical_json_text(payload)
        except (TypeError, ValueError) as exc:
            raise EpisodeStoreError(
                f"{label} '{VERBATIM_PAYLOAD_FIELD}' must be JSON-serializable"
            ) from exc


def with_verbatim_context(
    record: dict[str, Any],
    *,
    source: str,
    payload: Any,
) -> dict[str, Any]:
    """Return a shallow copy of record with verbatim context fields attached."""

    updated = dict(record)
    context = dict(updated.get("context") or {})
    context[VERBATIM_SOURCE_FIELD] = source
    context[VERBATIM_PAYLOAD_FIELD] = payload
    updated["context"] = context
    return updated


def load_episode_records(path: Path) -> list[dict[str, Any]]:
    """Load and minimally validate episode JSONL records from path."""

    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EpisodeStoreError(
                    f"invalid JSON in {path} line {line_number}: {exc.msg}"
                ) from exc
            validate_episode_record(record, label=f"{path.name} line {line_number}")
            records.append(record)
    return records


def append_episode_record(
    path: Path,
    record: dict[str, Any],
    *,
    require_verbatim: bool = False,
) -> None:
    """Append one validated episode record to the JSONL store."""

    validate_episode_record(record, require_verbatim=require_verbatim)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical_json_text(record))
        handle.write("\n")


def rewrite_episode_records(path: Path, records: list[dict[str, Any]]) -> None:
    """Rewrite the full JSONL store after validating every record."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for index, record in enumerate(records, start=1):
            validate_episode_record(record, label=f"episode[{index}]")
            handle.write(_canonical_json_text(record))
            handle.write("\n")


def merge_episode_records(
    target_records: list[dict[str, Any]],
    producer_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge episode records, reconciling same-id verbatim-preserving producer rewrites."""

    merged: list[dict[str, Any]] = []
    seen_payloads: set[str] = set()
    reconciled_indexes: dict[tuple[str, str, str], int] = {}
    target_ids: set[str] = set()
    target_session_ids_by_id: dict[str, set[str]] = {}
    target_fingerprints: set[str] = set()
    producer_fingerprints: set[str] = set()

    for index, record in enumerate(target_records, start=1):
        validate_episode_record(record, label=f"episode[{index}]")
        fingerprint = _canonical_json_text(record)
        episode_id = str(record.get("id") or "").strip()
        if fingerprint in target_fingerprints:
            raise EpisodeStoreError(
                f"target records contain duplicate exact episode row for id '{episode_id}'"
            )
        target_fingerprints.add(fingerprint)
        seen_payloads.add(fingerprint)
        merged.append(record)
        if episode_id:
            target_ids.add(episode_id)
            session_id = str(record.get("session_id") or "").strip()
            if session_id:
                target_session_ids_by_id.setdefault(episode_id, set()).add(session_id)
        reconcilable_key = _reconcilable_episode_key(record)
        if reconcilable_key is not None:
            if reconcilable_key in reconciled_indexes:
                raise EpisodeStoreError(
                    "target records contain duplicate verbatim-backed episode identity "
                    f"for id '{reconcilable_key[0]}'"
                )
            reconciled_indexes[reconcilable_key] = len(merged) - 1

    baseline_target_ids = set(target_ids)

    for index, record in enumerate(producer_records, start=len(target_records) + 1):
        validate_episode_record(record, label=f"episode[{index}]")
        fingerprint = _canonical_json_text(record)
        episode_id = str(record.get("id") or "").strip()
        if fingerprint in producer_fingerprints:
            raise EpisodeStoreError(
                f"producer records contain duplicate exact episode row for id '{episode_id}'"
            )
        producer_fingerprints.add(fingerprint)
        if fingerprint in seen_payloads:
            continue
        reconcilable_key = _reconcilable_episode_key(record)
        if reconcilable_key is not None and reconcilable_key in reconciled_indexes:
            existing = merged[reconciled_indexes[reconcilable_key]]
            if not _is_allowed_reinforcement_rewrite(existing, record):
                episode_id = reconcilable_key[0]
                raise EpisodeStoreError(
                    f"episode[{index}] attempts a non-audited rewrite of existing episode id '{episode_id}'"
                )
            merged[reconciled_indexes[reconcilable_key]] = record
            seen_payloads.add(fingerprint)
            continue
        if episode_id in target_ids:
            if episode_id not in baseline_target_ids:
                raise EpisodeStoreError(
                    f"episode[{index}] attempts an ambiguous same-id rewrite of existing episode id '{episode_id}'"
                )
            producer_session_id = str(record.get("session_id") or "").strip()
            target_session_ids = target_session_ids_by_id.get(episode_id, set())
            if producer_session_id and producer_session_id not in target_session_ids:
                remapped = dict(record)
                remapped["id"] = _next_episode_id(target_ids)
                fingerprint = _canonical_json_text(remapped)
                seen_payloads.add(fingerprint)
                merged.append(remapped)
                target_ids.add(str(remapped["id"]))
                target_session_ids_by_id.setdefault(str(remapped["id"]), set()).add(producer_session_id)
                reconcilable_key = _reconcilable_episode_key(remapped)
                if reconcilable_key is not None:
                    reconciled_indexes[reconcilable_key] = len(merged) - 1
                continue
            raise EpisodeStoreError(
                f"episode[{index}] attempts an ambiguous same-id rewrite of existing episode id '{episode_id}'"
            )
        seen_payloads.add(fingerprint)
        merged.append(record)
        if episode_id:
            target_ids.add(episode_id)
            session_id = str(record.get("session_id") or "").strip()
            if session_id:
                target_session_ids_by_id.setdefault(episode_id, set()).add(session_id)
        if reconcilable_key is not None:
            reconciled_indexes[reconcilable_key] = len(merged) - 1
    return merged

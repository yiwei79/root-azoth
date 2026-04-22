#!/usr/bin/env python3
"""Backend preflight for Azoth /worktree-sync.

Producer branches are refreshed against the local integration branch before
commit creation. Integration branches fail closed when the target worktree is
dirty so only one clean integrator pass happens at a time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from episode_store import EpisodeStoreError, merge_episode_records as merge_episode_records_shared
from episode_store import rewrite_episode_records

KEEP_TARGET_PATHS = (
    ".azoth/scope-gate.json",
    ".azoth/pipeline-gate.json",
    ".azoth/run-ledger.local.yaml",
    ".azoth/session-state.md",
    ".azoth/bootloader-state.md",
)
APPEND_DEDUPE_PATHS = (
    ".azoth/memory/episodes.jsonl",
    ".azoth/final-delivery-approvals.jsonl",
)
GOVERNED_PATHS = (
    ".azoth/backlog.yaml",
    ".azoth/roadmap.yaml",
)
GOVERNED_APPROVAL_ROOT = Path(".azoth") / "governed-state-approvals"
GOVERNED_APPROVAL_PREFIX = f"{GOVERNED_APPROVAL_ROOT.as_posix()}/"
RECONCILED_PATHS = (*KEEP_TARGET_PATHS, *APPEND_DEDUPE_PATHS, *GOVERNED_PATHS, "azoth.yaml")
STATUS_RANK = {"pending": 0, "active": 1, "complete": 2}


def _git_top(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(result.stdout.strip())


def _run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _run_cmd(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _unmerged_paths(repo: Path) -> list[str]:
    result = _run_git(repo, "diff", "--name-only", "--diff-filter=U", check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git diff failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _merge_in_progress(repo: Path) -> bool:
    result = _run_git(repo, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False)
    return result.returncode == 0


def _resolve_git_common_dir(repo: Path) -> Path | None:
    env_override = os.environ.get("AZOTH_GIT_COMMON_DIR")
    if env_override:
        return Path(env_override).expanduser().resolve()
    result = _run_git(repo, "rev-parse", "--git-common-dir", check=False)
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (repo / path).resolve()
    return path.resolve()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _handoff_queue_path(repo: Path) -> Path | None:
    explicit_path = os.environ.get("AZOTH_WORKTREE_HANDOFF_QUEUE_PATH")
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()

    common_dir = _resolve_git_common_dir(repo)
    if common_dir is None:
        return None

    digest = hashlib.sha1(str(common_dir).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / "azoth-worktree-handoffs" / f"{digest}.jsonl"


def _append_jsonl_record(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
        handle.write("\n")


def _load_jsonl_records(path: Path | None) -> list[dict[str, object]]:
    if path is None or not path.exists():
        return []
    records: list[dict[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            records.append(_normalize_handoff_record(data))
    return records


def _current_head(repo: Path) -> str:
    result = _run_git(repo, "rev-parse", "HEAD")
    return result.stdout.strip()


def _short_head(repo: Path, rev: str = "HEAD", *, length: int = 8) -> str:
    result = _run_git(repo, "rev-parse", f"--short={length}", rev)
    return result.stdout.strip()


def _commit_subject(repo: Path, rev: str) -> str:
    result = _run_git(repo, "show", "-s", "--format=%s", rev)
    return result.stdout.strip()


def _handoff_id(target_branch: str, producer_branch: str, head_sha: str) -> str:
    payload = "\x00".join((target_branch, producer_branch, head_sha)).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def _normalize_handoff_record(record: dict[str, object]) -> dict[str, object]:
    normalized = dict(record)
    handoff_id = str(normalized.get("handoff_id") or "").strip()
    if handoff_id:
        normalized["handoff_id"] = handoff_id
        return normalized

    event = str(normalized.get("event") or "").strip()
    target_branch = str(normalized.get("target_branch") or "").strip()
    producer_branch = str(normalized.get("producer_branch") or "").strip()
    if not target_branch or not producer_branch:
        return normalized

    if event == "producer-ready":
        head_sha = str(normalized.get("head_sha") or "").strip()
    elif event == "integrated":
        head_sha = str(
            normalized.get("producer_head_sha") or normalized.get("head_sha") or ""
        ).strip()
    else:
        head_sha = ""
    if head_sha:
        normalized["handoff_id"] = _handoff_id(target_branch, producer_branch, head_sha)
    return normalized


def _unresolved_ready_handoffs(repo: Path, *, target_branch: str) -> list[dict[str, object]]:
    queue_path = _handoff_queue_path(repo)
    ready_by_id: dict[str, dict[str, object]] = {}
    integrated_ids: set[str] = set()
    for record in _load_jsonl_records(queue_path):
        event = str(record.get("event") or "").strip()
        handoff_id = str(record.get("handoff_id") or "").strip()
        target = str(record.get("target_branch") or "").strip()
        if not handoff_id or target != target_branch:
            continue
        if event == "producer-ready":
            if handoff_id not in integrated_ids:
                ready_by_id[handoff_id] = record
        elif event == "integrated":
            integrated_ids.add(handoff_id)
            ready_by_id.pop(handoff_id, None)

    ready_records = [
        record for handoff_id, record in ready_by_id.items() if handoff_id not in integrated_ids
    ]
    ready_records.sort(key=lambda record: str(record.get("recorded_at") or ""))
    return ready_records


def _handoff_match_summary(record: dict[str, object]) -> str:
    return (
        f"{record.get('handoff_id')} "
        f"(producer={record.get('producer_branch')}, head={record.get('head_sha')})"
    )


def _ready_handoff_not_found_error(
    target_branch: str,
    *,
    producer_branch: str | None,
    handoff_id: str | None,
) -> str:
    if handoff_id:
        return (
            "worktree-sync: no ready producer handoff found for target "
            f"'{target_branch}' with handoff id '{handoff_id}'"
        )
    if producer_branch:
        return (
            "worktree-sync: no ready producer handoff found for target "
            f"'{target_branch}' for '{producer_branch}'"
        )
    return f"worktree-sync: no ready producer handoff found for target '{target_branch}'"


def _resolve_ready_handoff(
    repo: Path,
    *,
    target_branch: str,
    producer_branch: str | None = None,
    handoff_id: str | None = None,
) -> tuple[dict[str, object] | None, str | None]:
    ready_records = _unresolved_ready_handoffs(repo, target_branch=target_branch)
    if handoff_id:
        for record in ready_records:
            if str(record.get("handoff_id") or "").strip() != handoff_id:
                continue
            if (
                producer_branch
                and str(record.get("producer_branch") or "").strip() != producer_branch
            ):
                return (
                    None,
                    "worktree-sync: handoff id "
                    f"'{handoff_id}' does not match producer branch '{producer_branch}'",
                )
            return record, None
        return None, _ready_handoff_not_found_error(
            target_branch,
            producer_branch=producer_branch,
            handoff_id=handoff_id,
        )

    if producer_branch:
        matches = [
            record
            for record in ready_records
            if str(record.get("producer_branch") or "").strip() == producer_branch
        ]
        if not matches:
            return None, _ready_handoff_not_found_error(
                target_branch,
                producer_branch=producer_branch,
                handoff_id=None,
            )
        if len(matches) > 1:
            match_lines = "\n".join(f"- {_handoff_match_summary(record)}" for record in matches)
            return (
                None,
                "worktree-sync: ambiguous unresolved handoff match for producer "
                f"'{producer_branch}' on '{target_branch}'. Re-run with --handoff-id.\n"
                f"{match_lines}",
            )
        return matches[0], None

    if not ready_records:
        return None, _ready_handoff_not_found_error(
            target_branch,
            producer_branch=None,
            handoff_id=None,
        )
    return ready_records[-1], None


def _git_show_text(repo: Path, rev: str, relpath: str) -> str | None:
    result = _run_git(repo, "show", f"{rev}:{relpath}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def _git_path_exists(repo: Path, rev: str, relpath: str) -> bool:
    result = _run_git(repo, "cat-file", "-e", f"{rev}:{relpath}", check=False)
    return result.returncode == 0


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalize_string_list(values: object) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError("expected list")
    normalized = sorted({str(value).strip() for value in values if str(value).strip()})
    return normalized


def _load_json_mapping(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _load_yaml_mapping_text(raw: str, *, label: str) -> dict[str, Any]:
    data = yaml.safe_load(raw) if raw.strip() else {}
    if not isinstance(data, dict):
        raise ValueError(f"{label} must parse to a YAML mapping")
    return data


def _write_text_or_remove(root: Path, relpath: str, text: str | None) -> None:
    target = root / relpath
    if text is None:
        if target.exists():
            target.unlink()
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _load_jsonl_text(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    records: list[dict[str, Any]] = []
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        data = json.loads(line)
        if not isinstance(data, dict):
            raise ValueError("jsonl row must be a mapping")
        records.append(data)
    return records


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if path.name == "episodes.jsonl":
        try:
            rewrite_episode_records(path, records)
        except EpisodeStoreError as exc:
            raise ValueError(str(exc)) from exc
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
            handle.write("\n")


def _merge_episode_records(
    target_records: list[dict[str, Any]], producer_records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    try:
        return merge_episode_records_shared(target_records, producer_records)
    except EpisodeStoreError as exc:
        raise ValueError(str(exc)) from exc


def _merge_approval_records(
    target_records: list[dict[str, Any]], producer_records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in [*target_records, *producer_records]:
        fingerprint = _sha256_hex(_canonical_json_bytes(record))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        merged.append(record)
    return merged


def _status_progression_allowed(target_status: str, producer_status: str) -> bool:
    if target_status == producer_status:
        return True
    if target_status not in STATUS_RANK or producer_status not in STATUS_RANK:
        return False
    return STATUS_RANK[producer_status] >= STATUS_RANK[target_status]


def _merge_allowlisted_items(
    target_items: list[dict[str, Any]],
    producer_items: list[dict[str, Any]],
    *,
    allowed_ids: set[str],
    protected_fields: tuple[str, ...],
    status_field: str | None = None,
) -> list[dict[str, Any]]:
    target_index = {str(item.get("id") or "").strip(): item for item in target_items}
    producer_index = {str(item.get("id") or "").strip(): item for item in producer_items}
    producer_allowed_counts: dict[str, int] = {}
    for producer_item in producer_items:
        item_id = str(producer_item.get("id") or "").strip()
        if item_id and item_id in allowed_ids:
            producer_allowed_counts[item_id] = producer_allowed_counts.get(item_id, 0) + 1
            if producer_allowed_counts[item_id] > 1:
                raise ValueError(f"duplicate allowlisted producer row {item_id!r}")
    union_ids = {item_id for item_id in [*target_index.keys(), *producer_index.keys()] if item_id}

    changed_ids = {
        item_id for item_id in union_ids if target_index.get(item_id) != producer_index.get(item_id)
    }
    unauthorized = sorted(changed_ids - allowed_ids)
    if unauthorized:
        raise ValueError(f"non-allowlisted rows changed: {', '.join(unauthorized)}")

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for target_item in target_items:
        item_id = str(target_item.get("id") or "").strip()
        if not item_id:
            raise ValueError("item list contains a row without id")
        seen.add(item_id)
        if item_id not in allowed_ids:
            merged.append(target_item)
            continue

        producer_item = producer_index.get(item_id)
        if producer_item is None:
            raise ValueError(f"allowlisted row {item_id!r} may not be deleted")
        for field in protected_fields:
            if target_item.get(field) != producer_item.get(field):
                raise ValueError(f"row {item_id!r} changed protected field {field!r}")
        if status_field:
            target_status = str(target_item.get(status_field) or "").strip()
            producer_status = str(producer_item.get(status_field) or "").strip()
            if not _status_progression_allowed(target_status, producer_status):
                raise ValueError(
                    f"row {item_id!r} has non-monotonic status transition "
                    f"{target_status!r} -> {producer_status!r}"
                )
        merged.append(producer_item)

    for producer_item in producer_items:
        item_id = str(producer_item.get("id") or "").strip()
        if item_id and item_id in allowed_ids:
            if item_id in seen:
                continue
            merged.append(producer_item)
            seen.add(item_id)
    return merged


def _roadmap_rows_by_id(
    rows: list[dict[str, Any]],
    *,
    label: str,
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = str(row.get("id") or "").strip()
        if not row_id:
            raise ValueError(f"{label} contains a row without id")
        if row_id in index:
            raise ValueError(f"{label} contains duplicate row {row_id!r}")
        index[row_id] = row
    return index


def _normalize_roadmap_task_lists(
    version_block: dict[str, Any],
    *,
    label: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tasks = version_block.get("tasks")
    completed = version_block.get("completed_tasks")
    if tasks is None:
        tasks = []
    if completed is None:
        completed = []
    if not isinstance(tasks, list) or not isinstance(completed, list):
        raise ValueError(f"{label} task collections must be lists")
    return tasks, completed


def _merge_versioned_roadmap_lists(
    baseline_tasks: list[dict[str, Any]],
    baseline_completed: list[dict[str, Any]],
    producer_tasks: list[dict[str, Any]],
    producer_completed: list[dict[str, Any]],
    *,
    allowed_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline_tasks_by_id = _roadmap_rows_by_id(baseline_tasks, label="baseline roadmap tasks")
    baseline_completed_by_id = _roadmap_rows_by_id(
        baseline_completed, label="baseline roadmap completed_tasks"
    )
    producer_tasks_by_id = _roadmap_rows_by_id(producer_tasks, label="producer roadmap tasks")
    producer_completed_by_id = _roadmap_rows_by_id(
        producer_completed, label="producer roadmap completed_tasks"
    )

    duplicate_baseline_ids = sorted(set(baseline_tasks_by_id) & set(baseline_completed_by_id))
    if duplicate_baseline_ids:
        raise ValueError(
            "baseline roadmap duplicates task refs across tasks/completed_tasks: "
            + ", ".join(duplicate_baseline_ids)
        )
    duplicate_producer_ids = sorted(set(producer_tasks_by_id) & set(producer_completed_by_id))
    if duplicate_producer_ids:
        raise ValueError(
            "producer roadmap duplicates task refs across tasks/completed_tasks: "
            + ", ".join(duplicate_producer_ids)
        )

    baseline_locations = {
        **{row_id: ("tasks", row) for row_id, row in baseline_tasks_by_id.items()},
        **{row_id: ("completed_tasks", row) for row_id, row in baseline_completed_by_id.items()},
    }
    producer_locations = {
        **{row_id: ("tasks", row) for row_id, row in producer_tasks_by_id.items()},
        **{row_id: ("completed_tasks", row) for row_id, row in producer_completed_by_id.items()},
    }
    union_ids = set(baseline_locations) | set(producer_locations)
    unauthorized = sorted(
        row_id
        for row_id in union_ids
        if row_id not in allowed_ids and baseline_locations.get(row_id) != producer_locations.get(row_id)
    )
    if unauthorized:
        raise ValueError(
            "non-allowlisted roadmap task refs changed: " + ", ".join(unauthorized)
        )

    merged_tasks: list[dict[str, Any]] = []
    merged_completed: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append(destination: str, row: dict[str, Any]) -> None:
        if destination == "tasks":
            merged_tasks.append(row)
        else:
            merged_completed.append(row)

    for destination, rows in (("tasks", baseline_tasks), ("completed_tasks", baseline_completed)):
        for row in rows:
            row_id = str(row.get("id") or "").strip()
            if row_id in seen:
                continue
            if row_id in allowed_ids and row_id in producer_locations:
                producer_destination, producer_row = producer_locations[row_id]
                if row_id in baseline_locations:
                    baseline_row = baseline_locations[row_id][1]
                    for field in ("id", "title"):
                        if baseline_row.get(field) != producer_row.get(field):
                            raise ValueError(
                                f"allowlisted roadmap task ref {row_id!r} changed protected field {field!r}"
                            )
                _append(producer_destination, producer_row)
            else:
                _append(destination, row)
            seen.add(row_id)

    for row_id, (destination, row) in producer_locations.items():
        if row_id in seen or row_id not in allowed_ids:
            continue
        _append(destination, row)
        seen.add(row_id)

    return merged_tasks, merged_completed


def _reconcile_versioned_roadmap(
    baseline: dict[str, Any],
    producer: dict[str, Any],
    *,
    allowed_ids: set[str],
) -> dict[str, Any]:
    baseline_versions = baseline.get("versions")
    producer_versions = producer.get("versions")
    if not isinstance(baseline_versions, list) or not isinstance(producer_versions, list):
        raise ValueError("roadmap.yaml versions must be lists")

    baseline_meta = {key: value for key, value in baseline.items() if key != "versions"}
    producer_meta = {key: value for key, value in producer.items() if key != "versions"}
    if baseline_meta != producer_meta:
        raise ValueError("roadmap selectors changed outside explicit task-level governance")

    producer_versions_by_id = _roadmap_rows_by_id(producer_versions, label="producer roadmap versions")
    merged_versions: list[dict[str, Any]] = []
    seen_versions: set[str] = set()

    for baseline_version in baseline_versions:
        version_id = str(baseline_version.get("id") or "").strip()
        if not version_id:
            raise ValueError("baseline roadmap version block is missing id")
        producer_version = producer_versions_by_id.get(version_id)
        if producer_version is None:
            raise ValueError(f"producer roadmap is missing version block {version_id!r}")
        seen_versions.add(version_id)

        baseline_tasks, baseline_completed = _normalize_roadmap_task_lists(
            baseline_version, label=f"baseline roadmap version {version_id}"
        )
        producer_tasks, producer_completed = _normalize_roadmap_task_lists(
            producer_version, label=f"producer roadmap version {version_id}"
        )

        baseline_version_meta = {
            key: value
            for key, value in baseline_version.items()
            if key not in {"tasks", "completed_tasks", "current_patch"}
        }
        producer_version_meta = {
            key: value
            for key, value in producer_version.items()
            if key not in {"tasks", "completed_tasks", "current_patch"}
        }
        if baseline_version_meta != producer_version_meta:
            raise ValueError("roadmap selectors changed outside explicit task-level governance")

        merged_tasks, merged_completed = _merge_versioned_roadmap_lists(
            baseline_tasks,
            baseline_completed,
            producer_tasks,
            producer_completed,
            allowed_ids=allowed_ids,
        )

        merged_version = {
            key: value
            for key, value in baseline_version.items()
            if key not in {"tasks", "completed_tasks"}
        }
        merged_version["tasks"] = merged_tasks
        merged_version["completed_tasks"] = merged_completed
        merged_versions.append(merged_version)

    extra_versions = sorted(set(producer_versions_by_id) - seen_versions)
    if extra_versions:
        raise ValueError(
            "producer roadmap added unexpected version blocks: " + ", ".join(extra_versions)
        )

    merged = dict(baseline_meta)
    merged["versions"] = merged_versions
    return merged


def _scope_payload_from_capsule(capsule: dict[str, Any]) -> dict[str, Any]:
    allowlist = capsule.get("shared_state_allowlist")
    if not isinstance(allowlist, dict):
        raise ValueError("shared_state_allowlist must be a mapping")
    allowlist_unit = str(capsule.get("allowlist_unit") or "").strip()
    if allowlist_unit not in {"task", "initiative"}:
        raise ValueError("allowlist_unit must be 'task' or 'initiative'")
    whole_initiative_approved = bool(capsule.get("whole_initiative_approved"))
    initiative_refs = _normalize_string_list(allowlist.get("initiative_refs"))
    if allowlist_unit == "initiative" and not whole_initiative_approved:
        raise ValueError("initiative allowlists require whole_initiative_approved=true")
    return {
        "session_id": str(capsule.get("session_id") or "").strip(),
        "backlog_id": str(capsule.get("backlog_id") or "").strip(),
        "goal": str(capsule.get("goal") or "").strip(),
        "allowlist_unit": allowlist_unit,
        "whole_initiative_approved": whole_initiative_approved,
        "shared_state_allowlist": {
            "backlog_ids": _normalize_string_list(allowlist.get("backlog_ids")),
            "roadmap_task_refs": _normalize_string_list(allowlist.get("roadmap_task_refs")),
            "initiative_refs": initiative_refs,
        },
    }


def _scope_fingerprint(payload: dict[str, Any]) -> str:
    return _sha256_hex(_canonical_json_bytes(payload))


def _validate_governed_capsule(
    capsule: dict[str, Any],
    *,
    session_id: str,
    backlog_id: str,
    goal: str,
    label: str,
) -> tuple[dict[str, Any], str]:
    if int(capsule.get("schema_version") or 0) != 1:
        raise ValueError(f"{label}: schema_version must be 1")
    if str(capsule.get("artifact_kind") or "").strip() != "governed-shared-state-approval":
        raise ValueError(f"{label}: artifact_kind must be governed-shared-state-approval")
    if str(capsule.get("session_id") or "").strip() != session_id:
        raise ValueError(f"{label}: session_id mismatch")
    if str(capsule.get("backlog_id") or "").strip() != backlog_id:
        raise ValueError(f"{label}: backlog_id mismatch")
    if str(capsule.get("goal") or "").strip() != goal:
        raise ValueError(f"{label}: goal mismatch")
    if str(capsule.get("actor_type") or "").strip() != "human":
        raise ValueError(f"{label}: actor_type must be human")
    if str(capsule.get("decision") or "").strip() != "approved":
        raise ValueError(f"{label}: decision must be approved")
    if not str(capsule.get("approved_at") or "").strip():
        raise ValueError(f"{label}: approved_at missing")

    scope_payload = _scope_payload_from_capsule(capsule)
    if (
        not scope_payload["session_id"]
        or not scope_payload["backlog_id"]
        or not scope_payload["goal"]
    ):
        raise ValueError(f"{label}: scope payload is incomplete")
    fingerprint = _scope_fingerprint(scope_payload)
    if str(capsule.get("scope_fingerprint") or "").strip() != fingerprint:
        raise ValueError(f"{label}: scope_fingerprint mismatch")
    return scope_payload, fingerprint


def _current_scope_gate(repo: Path) -> dict[str, Any] | None:
    return _load_json_mapping(repo / ".azoth" / "scope-gate.json")


def _governed_queue_metadata_from_head(repo: Path) -> dict[str, Any] | None:
    scope_gate = _current_scope_gate(repo)
    if scope_gate is None:
        return None
    session_id = str(scope_gate.get("session_id") or "").strip()
    backlog_id = str(scope_gate.get("backlog_id") or "").strip()
    goal = str(scope_gate.get("goal") or "").strip()
    if not session_id or not backlog_id or not goal:
        return None

    relpath = (GOVERNED_APPROVAL_ROOT / f"{session_id}-{backlog_id}.yaml").as_posix()
    if not (repo / relpath).exists():
        return None
    if not _git_path_exists(repo, "HEAD", relpath):
        raise ValueError(
            f"governed approval capsule {relpath} must be tracked in HEAD before handoff recording"
        )

    raw = (repo / relpath).read_text(encoding="utf-8")
    capsule = _load_yaml_mapping_text(raw, label=relpath)
    scope_payload, fingerprint = _validate_governed_capsule(
        capsule,
        session_id=session_id,
        backlog_id=backlog_id,
        goal=goal,
        label=relpath,
    )
    return {
        "scope_session_id": scope_payload["session_id"],
        "scope_backlog_id": scope_payload["backlog_id"],
        "scope_goal": scope_payload["goal"],
        "scope_fingerprint": fingerprint,
        "approval_evidence_path": relpath,
        "approval_evidence_sha256": _sha256_hex(raw.encode("utf-8")),
        "allowlist_unit": scope_payload["allowlist_unit"],
        "whole_initiative_approved": scope_payload["whole_initiative_approved"],
        "shared_state_allowlist": scope_payload["shared_state_allowlist"],
    }


def _record_requests_governed_reconcile(record: dict[str, object]) -> bool:
    return bool(str(record.get("approval_evidence_path") or "").strip())


def _load_capsule_from_ready_record(
    repo: Path,
    ready: dict[str, object],
    *,
    queued_head_sha: str,
) -> dict[str, Any] | None:
    approval_path = str(ready.get("approval_evidence_path") or "").strip()
    if not approval_path:
        return None
    if not approval_path.startswith(GOVERNED_APPROVAL_PREFIX):
        raise ValueError("approval_evidence_path must point to a tracked governed approval capsule")
    raw = _git_show_text(repo, queued_head_sha, approval_path)
    if raw is None:
        raise ValueError(
            f"queued producer commit does not contain approval artifact {approval_path}"
        )
    sha = _sha256_hex(raw.encode("utf-8"))
    if sha != str(ready.get("approval_evidence_sha256") or "").strip():
        raise ValueError("approval_evidence_sha256 mismatch")

    capsule = _load_yaml_mapping_text(raw, label=approval_path)
    scope_payload, fingerprint = _validate_governed_capsule(
        capsule,
        session_id=str(ready.get("scope_session_id") or "").strip(),
        backlog_id=str(ready.get("scope_backlog_id") or "").strip(),
        goal=str(ready.get("scope_goal") or "").strip(),
        label=approval_path,
    )
    if fingerprint != str(ready.get("scope_fingerprint") or "").strip():
        raise ValueError("queue scope_fingerprint does not match capsule-derived fingerprint")
    if str(ready.get("allowlist_unit") or "").strip() != scope_payload["allowlist_unit"]:
        raise ValueError("queue allowlist_unit does not match tracked capsule")

    ready_allowlist = ready.get("shared_state_allowlist")
    if not isinstance(ready_allowlist, dict):
        raise ValueError("queue shared_state_allowlist missing")
    queue_payload = {
        "session_id": str(ready.get("scope_session_id") or "").strip(),
        "backlog_id": str(ready.get("scope_backlog_id") or "").strip(),
        "goal": str(ready.get("scope_goal") or "").strip(),
        "allowlist_unit": str(ready.get("allowlist_unit") or "").strip(),
        "whole_initiative_approved": bool(ready.get("whole_initiative_approved")),
        "shared_state_allowlist": {
            "backlog_ids": _normalize_string_list(ready_allowlist.get("backlog_ids")),
            "roadmap_task_refs": _normalize_string_list(ready_allowlist.get("roadmap_task_refs")),
            "initiative_refs": _normalize_string_list(ready_allowlist.get("initiative_refs")),
        },
    }
    if queue_payload != scope_payload:
        raise ValueError("queue scope metadata widens or differs from tracked approval capsule")
    capsule["_validated_scope_payload"] = scope_payload
    return capsule


def _changed_paths(repo: Path, base_rev: str, head_rev: str, paths: tuple[str, ...]) -> set[str]:
    result = _run_git(repo, "diff", "--name-only", base_rev, head_rev, "--", *paths, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git diff failed")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _reconcile_backlog(
    repo: Path,
    sandbox_dir: Path,
    *,
    baseline_head: str,
    queued_head_sha: str,
    capsule: dict[str, Any],
) -> None:
    baseline_raw = _git_show_text(repo, baseline_head, ".azoth/backlog.yaml")
    producer_raw = _git_show_text(repo, queued_head_sha, ".azoth/backlog.yaml")
    if baseline_raw is None or producer_raw is None:
        raise ValueError("backlog reconciliation requires backlog.yaml on both sides")
    baseline = _load_yaml_mapping_text(baseline_raw, label="target backlog")
    producer = _load_yaml_mapping_text(producer_raw, label="producer backlog")
    baseline_items = baseline.get("items")
    producer_items = producer.get("items")
    if not isinstance(baseline_items, list) or not isinstance(producer_items, list):
        raise ValueError("backlog.yaml items must be lists")
    baseline_meta = {key: value for key, value in baseline.items() if key != "items"}
    producer_meta = {key: value for key, value in producer.items() if key != "items"}
    if baseline_meta != producer_meta:
        raise ValueError("backlog.yaml top-level metadata changed outside governed row merge")

    scope_payload = capsule["_validated_scope_payload"]
    allowlist = scope_payload["shared_state_allowlist"]
    merged = dict(baseline_meta)
    merged["items"] = _merge_allowlisted_items(
        baseline_items,
        producer_items,
        allowed_ids=set(allowlist["backlog_ids"]),
        protected_fields=("id", "title", "target_layer", "delivery_pipeline", "roadmap_ref"),
        status_field="status",
    )
    _write_text_or_remove(
        sandbox_dir,
        ".azoth/backlog.yaml",
        yaml.safe_dump(merged, sort_keys=False, allow_unicode=True),
    )


def _reconcile_roadmap(
    repo: Path,
    sandbox_dir: Path,
    *,
    baseline_head: str,
    queued_head_sha: str,
    capsule: dict[str, Any],
) -> None:
    baseline_raw = _git_show_text(repo, baseline_head, ".azoth/roadmap.yaml")
    producer_raw = _git_show_text(repo, queued_head_sha, ".azoth/roadmap.yaml")
    if baseline_raw is None or producer_raw is None:
        raise ValueError("roadmap reconciliation requires roadmap.yaml on both sides")
    baseline = _load_yaml_mapping_text(baseline_raw, label="target roadmap")
    producer = _load_yaml_mapping_text(producer_raw, label="producer roadmap")
    scope_payload = capsule["_validated_scope_payload"]
    allowlist = scope_payload["shared_state_allowlist"]
    roadmap_task_refs = set(allowlist["roadmap_task_refs"])
    if isinstance(baseline.get("versions"), list) and isinstance(producer.get("versions"), list):
        merged = _reconcile_versioned_roadmap(
            baseline,
            producer,
            allowed_ids=roadmap_task_refs,
        )
    elif isinstance(baseline.get("tasks"), list) and isinstance(producer.get("tasks"), list):
        baseline_tasks = baseline.get("tasks") or []
        producer_tasks = producer.get("tasks") or []
        baseline_meta = {key: value for key, value in baseline.items() if key != "tasks"}
        producer_meta = {key: value for key, value in producer.items() if key != "tasks"}
        if baseline_meta != producer_meta:
            raise ValueError("roadmap selectors changed outside explicit task-level governance")
        merged = dict(baseline_meta)
        merged["tasks"] = _merge_allowlisted_items(
            baseline_tasks,
            producer_tasks,
            allowed_ids=roadmap_task_refs,
            protected_fields=("id", "title"),
            status_field="status",
        )
    else:
        raise ValueError("roadmap.yaml must use either versioned tasks or top-level tasks")
    _write_text_or_remove(
        sandbox_dir,
        ".azoth/roadmap.yaml",
        yaml.safe_dump(merged, sort_keys=False, allow_unicode=True),
    )


def _recompute_azoth_manifest(sandbox_dir: Path, baseline_text: str | None) -> None:
    if baseline_text is None:
        return
    target = sandbox_dir / "azoth.yaml"
    target.write_text(baseline_text, encoding="utf-8")

    decisions_count = 0
    decisions_index = sandbox_dir / "docs" / "DECISIONS_INDEX.md"
    if decisions_index.exists():
        decisions_count = sum(
            1
            for line in decisions_index.read_text(encoding="utf-8").splitlines()
            if line.startswith("| D")
        )
    episode_count = len(
        _load_jsonl_text(
            (sandbox_dir / ".azoth" / "memory" / "episodes.jsonl").read_text(encoding="utf-8")
            if (sandbox_dir / ".azoth" / "memory" / "episodes.jsonl").exists()
            else ""
        )
    )
    patterns_count = 0
    patterns_path = sandbox_dir / ".azoth" / "memory" / "patterns.yaml"
    if patterns_path.exists():
        patterns_doc = yaml.safe_load(patterns_path.read_text(encoding="utf-8")) or {}
        if isinstance(patterns_doc, dict) and isinstance(patterns_doc.get("patterns"), list):
            patterns_count = len(patterns_doc["patterns"])

    lines = []
    for line in baseline_text.splitlines():
        if line.startswith("decisions: "):
            lines.append(f"decisions: {decisions_count}")
        elif line.startswith("  episodes: "):
            lines.append(f"  episodes: {episode_count}")
        elif line.startswith("  patterns: "):
            lines.append(f"  patterns: {patterns_count}")
        else:
            lines.append(line)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _reconcile_shared_state(
    repo: Path,
    sandbox_dir: Path,
    *,
    baseline_head: str,
    queued_head_sha: str,
    ready: dict[str, object],
) -> None:
    for relpath in KEEP_TARGET_PATHS:
        _write_text_or_remove(sandbox_dir, relpath, _git_show_text(repo, baseline_head, relpath))

    target_episodes_raw = _git_show_text(repo, baseline_head, APPEND_DEDUPE_PATHS[0])
    producer_episodes_raw = _git_show_text(repo, queued_head_sha, APPEND_DEDUPE_PATHS[0])
    if target_episodes_raw is None and producer_episodes_raw is None:
        _write_text_or_remove(sandbox_dir, APPEND_DEDUPE_PATHS[0], None)
    else:
        target_episodes = _load_jsonl_text(target_episodes_raw)
        producer_episodes = _load_jsonl_text(producer_episodes_raw)
        _write_jsonl(
            sandbox_dir / APPEND_DEDUPE_PATHS[0],
            _merge_episode_records(target_episodes, producer_episodes),
        )

    target_approvals_raw = _git_show_text(repo, baseline_head, APPEND_DEDUPE_PATHS[1])
    producer_approvals_raw = _git_show_text(repo, queued_head_sha, APPEND_DEDUPE_PATHS[1])
    if target_approvals_raw is None and producer_approvals_raw is None:
        _write_text_or_remove(sandbox_dir, APPEND_DEDUPE_PATHS[1], None)
    else:
        target_approvals = _load_jsonl_text(target_approvals_raw)
        producer_approvals = _load_jsonl_text(producer_approvals_raw)
        _write_jsonl(
            sandbox_dir / APPEND_DEDUPE_PATHS[1],
            _merge_approval_records(target_approvals, producer_approvals),
        )

    governed_changes = _changed_paths(repo, baseline_head, queued_head_sha, GOVERNED_PATHS)
    capsule = None
    if _record_requests_governed_reconcile(ready):
        capsule = _load_capsule_from_ready_record(repo, ready, queued_head_sha=queued_head_sha)
    if governed_changes and capsule is None:
        changed = ", ".join(sorted(governed_changes))
        raise ValueError(
            f"producer touched governed shared state without valid tracked approval capsule: {changed}"
        )

    if ".azoth/backlog.yaml" in governed_changes:
        assert capsule is not None
        _reconcile_backlog(
            repo,
            sandbox_dir,
            baseline_head=baseline_head,
            queued_head_sha=queued_head_sha,
            capsule=capsule,
        )
    else:
        _write_text_or_remove(
            sandbox_dir,
            ".azoth/backlog.yaml",
            _git_show_text(repo, baseline_head, ".azoth/backlog.yaml"),
        )

    if ".azoth/roadmap.yaml" in governed_changes:
        assert capsule is not None
        _reconcile_roadmap(
            repo,
            sandbox_dir,
            baseline_head=baseline_head,
            queued_head_sha=queued_head_sha,
            capsule=capsule,
        )
    else:
        _write_text_or_remove(
            sandbox_dir,
            ".azoth/roadmap.yaml",
            _git_show_text(repo, baseline_head, ".azoth/roadmap.yaml"),
        )

    _recompute_azoth_manifest(sandbox_dir, _git_show_text(repo, baseline_head, "azoth.yaml"))


def _persist_reconciled_state(sandbox_dir: Path) -> None:
    status_result = _run_git(
        sandbox_dir, "status", "--porcelain", "--", *RECONCILED_PATHS, check=False
    )
    if status_result.returncode != 0:
        raise RuntimeError(
            status_result.stderr.strip() or status_result.stdout.strip() or "git status failed"
        )
    if not status_result.stdout.strip():
        return
    changed_paths = [path for path in dirty_paths(sandbox_dir) if path in set(RECONCILED_PATHS)]
    if not changed_paths:
        return
    add_result = _run_git(sandbox_dir, "add", "--", *changed_paths, check=False)
    if add_result.returncode != 0:
        raise RuntimeError(
            add_result.stderr.strip() or add_result.stdout.strip() or "git add failed"
        )
    if _merge_in_progress(sandbox_dir):
        commit_result = _run_git(sandbox_dir, "commit", "--no-edit", check=False)
    else:
        commit_result = _run_git(sandbox_dir, "commit", "--amend", "--no-edit", check=False)
    if commit_result.returncode != 0:
        raise RuntimeError(
            commit_result.stderr.strip()
            or commit_result.stdout.strip()
            or "git commit failed"
        )


def register_producer_handoff(repo: Path, current: str, target_branch: str) -> int:
    if current == target_branch:
        print(
            "worktree-sync: cannot record a producer handoff from the integration branch",
            file=sys.stderr,
        )
        return 1
    if working_tree_dirty(repo):
        print(
            "worktree-sync: producer handoff requires a clean worktree. Commit or park local changes first.",
            file=sys.stderr,
        )
        return 1

    queue_path = _handoff_queue_path(repo)
    if queue_path is None:
        print("worktree-sync: could not resolve the shared handoff queue path", file=sys.stderr)
        return 1

    head_sha = _current_head(repo)
    record: dict[str, object] = {
        "event": "producer-ready",
        "recorded_at": _utc_now_iso(),
        "producer_branch": current,
        "target_branch": target_branch,
        "head_sha": head_sha,
        "handoff_id": _handoff_id(target_branch, current, head_sha),
        "cleanup_candidates": _cleanup_candidates_for_branch(repo, current, head_sha),
        "worktree_path": str(repo.resolve()),
        "queue_path": str(queue_path),
    }
    common_dir = _resolve_git_common_dir(repo)
    if common_dir is not None:
        record["git_common_dir"] = str(common_dir)
    try:
        governed_metadata = _governed_queue_metadata_from_head(repo)
    except ValueError as exc:
        print(f"worktree-sync: {exc}", file=sys.stderr)
        return 1
    if governed_metadata:
        record.update(governed_metadata)

    try:
        _append_jsonl_record(queue_path, record)
    except OSError as exc:
        print(
            f"worktree-sync: could not record producer handoff: {exc}",
            file=sys.stderr,
        )
        return 1
    print(
        "worktree-sync: recorded producer handoff "
        f"'{current}' -> '{target_branch}' as {record['handoff_id']} at {record['head_sha']} "
        f"in {queue_path}"
    )
    return 0


def show_ready_handoff(
    repo: Path,
    target_branch: str,
    producer_branch: str | None,
    *,
    handoff_id: str | None,
    as_json: bool,
) -> int:
    record, error = _resolve_ready_handoff(
        repo,
        target_branch=target_branch,
        producer_branch=producer_branch,
        handoff_id=handoff_id,
    )
    if record is None:
        print(error or "worktree-sync: no ready producer handoff found", file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps(record, ensure_ascii=True, sort_keys=True))
    else:
        print(
            "worktree-sync: selected ready producer handoff "
            f"'{record['producer_branch']}' at {record['head_sha']} "
            f"({record['handoff_id']}) targeting '{target_branch}'"
        )
    return 0


def mark_integrated(
    repo: Path,
    current: str,
    target_branch: str,
    producer_branch: str | None,
    *,
    handoff_id: str | None,
    quiet: bool = False,
) -> int:
    if current != target_branch:
        print(
            "worktree-sync: integration completion can only be recorded from the active integration branch",
            file=sys.stderr,
        )
        return 1

    ready, error = _resolve_ready_handoff(
        repo,
        target_branch=target_branch,
        producer_branch=producer_branch,
        handoff_id=handoff_id,
    )
    if ready is None:
        print(error or "worktree-sync: no ready producer handoff found", file=sys.stderr)
        return 1

    queue_path = _handoff_queue_path(repo)
    if queue_path is None:
        print("worktree-sync: could not resolve the shared handoff queue path", file=sys.stderr)
        return 1

    resolved_handoff_id = str(ready.get("handoff_id") or "").strip()
    resolved_producer = str(ready.get("producer_branch") or "").strip()
    record: dict[str, object] = {
        "event": "integrated",
        "recorded_at": _utc_now_iso(),
        "handoff_id": resolved_handoff_id,
        "producer_branch": resolved_producer,
        "producer_head_sha": ready.get("head_sha"),
        "target_branch": target_branch,
        "integrator_branch": current,
        "integrated_head_sha": _current_head(repo),
        "worktree_path": str(repo.resolve()),
        "queue_path": str(queue_path),
    }
    common_dir = _resolve_git_common_dir(repo)
    if common_dir is not None:
        record["git_common_dir"] = str(common_dir)

    try:
        _append_jsonl_record(queue_path, record)
    except OSError as exc:
        print(
            f"worktree-sync: could not update the handoff queue after promotion: {exc}",
            file=sys.stderr,
        )
        return 1
    if not quiet:
        print(
            "worktree-sync: marked producer handoff "
            f"'{resolved_producer}' integrated into '{target_branch}' at "
            f"{record['integrated_head_sha']} ({resolved_handoff_id})"
        )
    return 0


def _roadmap_target_branch(repo: Path) -> str | None:
    roadmap_path = repo / ".azoth" / "roadmap.yaml"
    if not roadmap_path.exists():
        return None
    try:
        data = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    active_version = str(data.get("active_version") or "").strip()
    if not active_version:
        return None
    return f"phase/{active_version}"


def _fallback_phase_branch(repo: Path) -> str | None:
    result = _run_git(
        repo,
        "for-each-ref",
        "--format=%(refname:short)",
        "refs/heads/phase",
        "refs/heads/phase/*",
        check=False,
    )
    branches = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(branches) == 1:
        return branches[0]
    return None


def resolve_target_branch(repo: Path, override: str | None) -> str:
    if override:
        return override
    roadmap_branch = _roadmap_target_branch(repo)
    if roadmap_branch:
        return roadmap_branch
    fallback = _fallback_phase_branch(repo)
    if fallback:
        return fallback
    raise RuntimeError(
        "Could not resolve the integration branch. Pass --target-branch explicitly "
        "or ensure .azoth/roadmap.yaml has active_version."
    )


def current_branch(repo: Path) -> str | None:
    result = _run_git(repo, "branch", "--show-current", check=False)
    branch = result.stdout.strip()
    return branch or None


def branch_exists(repo: Path, branch: str) -> bool:
    result = _run_git(repo, "show-ref", "--verify", f"refs/heads/{branch}", check=False)
    return result.returncode == 0


def _branch_tip(repo: Path, branch: str) -> str | None:
    result = _run_git(repo, "rev-parse", f"refs/heads/{branch}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _codex_worktree_token(repo: Path) -> str | None:
    parts = repo.resolve().parts
    for idx in range(len(parts) - 2):
        if parts[idx] == ".codex" and parts[idx + 1] == "worktrees":
            token = parts[idx + 2].strip()
            if token:
                return token
    return None


def _sanitize_branch_token(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return normalized or "detached"


def _detached_branch_base(repo: Path, head_sha: str) -> str:
    worktree_token = _codex_worktree_token(repo)
    if worktree_token is None:
        worktree_token = hashlib.sha1(str(repo.resolve()).encode("utf-8")).hexdigest()[:8]
    branch_token = _sanitize_branch_token(worktree_token)
    head_token = _short_head(repo, head_sha)
    return f"codex/wt-{branch_token}-{head_token}"


def _switch_to_branch(repo: Path, branch: str, *, create: bool) -> subprocess.CompletedProcess[str]:
    args = ["switch"]
    if create:
        args.extend(["-c", branch])
    else:
        args.append(branch)
    return _run_git(repo, *args, check=False)


def resolve_producer_branch(repo: Path) -> tuple[str, str | None]:
    branch = current_branch(repo)
    if branch:
        return branch, None

    head_sha = _current_head(repo)
    short_head = _short_head(repo, head_sha)
    base_branch = _detached_branch_base(repo, head_sha)
    suffix = 1
    while True:
        candidate = base_branch if suffix == 1 else f"{base_branch}-{suffix}"
        existing_tip = _branch_tip(repo, candidate)
        if existing_tip is None:
            switch_result = _switch_to_branch(repo, candidate, create=True)
            if switch_result.returncode == 0:
                return (
                    candidate,
                    "worktree-sync: attached detached producer HEAD at "
                    f"{short_head} to auto-created local branch '{candidate}'.",
                )
            detail = (
                switch_result.stderr.strip()
                or switch_result.stdout.strip()
                or "git switch -c failed"
            )
            raise RuntimeError(
                "worktree-sync: could not attach detached producer HEAD to "
                f"'{candidate}': {detail}"
            )

        if existing_tip != head_sha:
            suffix += 1
            continue

        switch_result = _switch_to_branch(repo, candidate, create=False)
        if switch_result.returncode == 0:
            return (
                candidate,
                "worktree-sync: attached detached producer HEAD at "
                f"{short_head} to existing local branch '{candidate}'.",
            )

        detail = switch_result.stderr.strip() or switch_result.stdout.strip() or "git switch failed"
        if "already checked out" in detail:
            suffix += 1
            continue
        raise RuntimeError(
            "worktree-sync: could not reuse detached producer branch "
            f"'{candidate}': {detail}"
        )


def working_tree_dirty(repo: Path) -> bool:
    result = _run_git(repo, "status", "--porcelain", check=False)
    return bool(result.stdout.strip())


def dirty_paths(repo: Path) -> list[str]:
    result = _run_git(repo, "status", "--porcelain", check=False)
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def target_is_ancestor_of_head(repo: Path, target_branch: str) -> bool:
    result = _run_git(repo, "merge-base", "--is-ancestor", target_branch, "HEAD", check=False)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "merge-base failed")


def _stash_ref_for_message(repo: Path, message: str) -> str | None:
    result = _run_git(repo, "stash", "list", "--format=%gd%x00%gs", check=False)
    for line in result.stdout.splitlines():
        if "\x00" not in line:
            continue
        ref, subject = line.split("\x00", 1)
        if message in subject:
            return ref.strip()
    return None


def create_stash(repo: Path) -> str:
    message = f"azoth-worktree-sync-{int(time.time())}-{os.getpid()}"
    result = _run_git(repo, "stash", "push", "-u", "-m", message, check=False)
    output = (result.stderr or "") + (result.stdout or "")
    if result.returncode != 0:
        raise RuntimeError(output.strip() or "git stash push failed")
    stash_ref = _stash_ref_for_message(repo, message)
    if not stash_ref:
        raise RuntimeError("created worktree-sync stash, but could not resolve its stash ref")
    return stash_ref


def restore_stash(repo: Path, stash_ref: str) -> None:
    apply_result = _run_git(repo, "stash", "apply", stash_ref, check=False)
    if apply_result.returncode != 0:
        detail = (
            apply_result.stderr.strip() or apply_result.stdout.strip() or "git stash apply failed"
        )
        raise RuntimeError(
            f"stashed work could not be restored cleanly from {stash_ref}: {detail}. "
            f"Resolve the conflicts and rerun /worktree-sync. The stash remains available."
        )
    drop_result = _run_git(repo, "stash", "drop", stash_ref, check=False)
    if drop_result.returncode != 0:
        detail = drop_result.stderr.strip() or drop_result.stdout.strip() or "git stash drop failed"
        print(
            f"worktree-sync: warning: restored {stash_ref} but could not drop it cleanly: {detail}",
            file=sys.stderr,
        )


def producer_refresh(repo: Path, current: str, target_branch: str) -> int:
    if target_is_ancestor_of_head(repo, target_branch):
        print(
            f"worktree-sync: producer branch '{current}' already contains '{target_branch}'. "
            "No pre-commit refresh needed."
        )
        return 0

    stash_ref: str | None = None
    if working_tree_dirty(repo):
        stash_ref = create_stash(repo)
        print(f"worktree-sync: stashed local changes in {stash_ref} before rebasing.")

    rebase_result = _run_git(repo, "rebase", target_branch, check=False)
    if rebase_result.returncode != 0:
        detail = rebase_result.stderr.strip() or rebase_result.stdout.strip() or "git rebase failed"
        preserved = f" Stashed work is preserved in {stash_ref}." if stash_ref else ""
        print(
            "worktree-sync: producer refresh blocked — rebase onto "
            f"'{target_branch}' hit conflicts. Resolve conflicts, then rerun /worktree-sync."
            f"{preserved}\n{detail}",
            file=sys.stderr,
        )
        return 1

    if stash_ref:
        try:
            restore_stash(repo, stash_ref)
        except RuntimeError as exc:
            print(f"worktree-sync: producer refresh blocked — {exc}", file=sys.stderr)
            return 1

    print(
        f"worktree-sync: producer branch '{current}' rebased onto '{target_branch}'. "
        "Continue with explicit staging, commit, and optional push."
    )
    return 0


def integrator_preflight(
    repo: Path, current: str, target_branch: str, *, quiet: bool = False
) -> int:
    if working_tree_dirty(repo):
        paths = "\n".join(f"- {path}" for path in dirty_paths(repo))
        print(
            "worktree-sync: integration blocked — the target branch worktree is dirty.\n"
            "Parallel integration is unsafe until those changes are finished or parked.\n"
            f"{paths}",
            file=sys.stderr,
        )
        return 1

    if not quiet:
        print(
            f"worktree-sync: integrator branch '{current}' is clean and ready to merge exactly "
            "one producer branch."
        )
    return 0


def _cleanup_candidates_for_branch(
    repo: Path, producer_branch: str, head_sha: str
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = [
        {
            "branch": producer_branch,
            "expected_sha": head_sha,
            "reason": "queued-producer-branch",
        }
    ]
    if producer_branch.endswith("-integrable"):
        sibling_branch = producer_branch[: -len("-integrable")]
        sibling_tip = _branch_tip(repo, sibling_branch)
        if sibling_tip:
            candidates.append(
                {
                    "branch": sibling_branch,
                    "expected_sha": sibling_tip,
                    "reason": "superseded-by-integrable",
                }
            )
    return candidates


def _normalize_cleanup_candidates(ready: dict[str, object]) -> list[dict[str, str]]:
    raw_candidates = ready.get("cleanup_candidates")
    normalized: list[dict[str, str]] = []
    if isinstance(raw_candidates, list):
        for raw_candidate in raw_candidates:
            if not isinstance(raw_candidate, dict):
                continue
            branch = str(raw_candidate.get("branch") or "").strip()
            expected_sha = str(raw_candidate.get("expected_sha") or "").strip()
            reason = str(raw_candidate.get("reason") or "").strip()
            if branch and expected_sha:
                normalized.append(
                    {
                        "branch": branch,
                        "expected_sha": expected_sha,
                        "reason": reason or "cleanup-candidate",
                    }
                )
    if normalized:
        return normalized

    producer_branch = str(ready.get("producer_branch") or "").strip()
    head_sha = str(ready.get("head_sha") or "").strip()
    if producer_branch and head_sha:
        normalized.append(
            {
                "branch": producer_branch,
                "expected_sha": head_sha,
                "reason": "queued-producer-branch",
            }
        )
    return normalized


def _git_worktree_entries(repo: Path) -> list[dict[str, object]]:
    result = _run_git(repo, "worktree", "list", "--porcelain", check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git worktree list failed")

    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in result.stdout.splitlines():
        if not line.strip():
            if current is not None:
                entries.append(current)
                current = None
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            if current is not None:
                entries.append(current)
            current = {"worktree": value.strip()}
            continue
        if current is None:
            continue
        if key == "detached":
            current["detached"] = True
        else:
            current[key] = value.strip()
    if current is not None:
        entries.append(current)
    return entries


def _branch_worktrees(repo: Path, branch: str) -> list[Path]:
    target_ref = f"refs/heads/{branch}"
    paths: list[Path] = []
    for entry in _git_worktree_entries(repo):
        if str(entry.get("branch") or "").strip() != target_ref:
            continue
        worktree_path = str(entry.get("worktree") or "").strip()
        if worktree_path:
            paths.append(Path(worktree_path).resolve())
    return paths


def _commit_is_reachable_from(repo: Path, commit_sha: str, branch: str) -> bool:
    result = _run_git(repo, "merge-base", "--is-ancestor", commit_sha, branch, check=False)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "merge-base failed")


def _new_cleanup_summary() -> dict[str, object]:
    return {
        "removed_branches": [],
        "removed_worktrees": [],
        "skipped_cleanup": [],
    }


def _cleanup_skip(
    summary: dict[str, object],
    *,
    branch: str,
    reason: str,
    detail: str | None = None,
    worktree_path: str | None = None,
) -> None:
    item: dict[str, str] = {"branch": branch, "reason": reason}
    if detail:
        item["detail"] = detail
    if worktree_path:
        item["worktree_path"] = worktree_path
    skipped = summary.setdefault("skipped_cleanup", [])
    assert isinstance(skipped, list)
    skipped.append(item)


def cleanup_integrated_branches(
    repo: Path,
    *,
    target_branch: str,
    current_branch_name: str,
    ready: dict[str, object],
) -> dict[str, object]:
    summary = _new_cleanup_summary()
    seen_branches: set[str] = set()
    for candidate in _normalize_cleanup_candidates(ready):
        branch = candidate["branch"]
        if branch in seen_branches:
            continue
        seen_branches.add(branch)

        expected_sha = candidate["expected_sha"]
        if branch in {target_branch, current_branch_name}:
            _cleanup_skip(summary, branch=branch, reason="protected-branch")
            continue

        current_tip = _branch_tip(repo, branch)
        if current_tip is None:
            _cleanup_skip(summary, branch=branch, reason="branch-missing")
            continue
        if current_tip != expected_sha:
            _cleanup_skip(summary, branch=branch, reason="tip-moved")
            continue
        try:
            merged = _commit_is_reachable_from(repo, current_tip, target_branch)
        except RuntimeError as exc:
            _cleanup_skip(summary, branch=branch, reason="reachability-check-failed", detail=str(exc))
            continue
        if not merged:
            _cleanup_skip(summary, branch=branch, reason="not-merged-into-target")
            continue

        attached_worktrees = _branch_worktrees(repo, branch)
        blocked = False
        for worktree_path in attached_worktrees:
            if worktree_path == repo.resolve():
                _cleanup_skip(
                    summary,
                    branch=branch,
                    reason="branch-attached-to-live-worktree",
                    worktree_path=str(worktree_path),
                )
                blocked = True
                break
            if working_tree_dirty(worktree_path):
                _cleanup_skip(
                    summary,
                    branch=branch,
                    reason="attached-worktree-dirty",
                    worktree_path=str(worktree_path),
                )
                blocked = True
                break
            remove_result = _run_git(
                repo, "worktree", "remove", "--force", str(worktree_path), check=False
            )
            if remove_result.returncode != 0:
                detail = (
                    remove_result.stderr.strip()
                    or remove_result.stdout.strip()
                    or "git worktree remove failed"
                )
                _cleanup_skip(
                    summary,
                    branch=branch,
                    reason="worktree-remove-failed",
                    detail=detail,
                    worktree_path=str(worktree_path),
                )
                blocked = True
                break
            removed_worktrees = summary.setdefault("removed_worktrees", [])
            assert isinstance(removed_worktrees, list)
            removed_worktrees.append(str(worktree_path))
        if blocked:
            continue

        delete_result = _run_git(repo, "branch", "-d", branch, check=False)
        if delete_result.returncode != 0:
            detail = (
                delete_result.stderr.strip()
                or delete_result.stdout.strip()
                or "git branch -d failed"
            )
            _cleanup_skip(
                summary,
                branch=branch,
                reason="branch-delete-failed",
                detail=detail,
            )
            continue

        removed_branches = summary.setdefault("removed_branches", [])
        assert isinstance(removed_branches, list)
        removed_branches.append(branch)

    return summary


def _cleanup_summary_lines(summary: dict[str, object]) -> list[str]:
    lines: list[str] = []
    removed_branches = summary.get("removed_branches")
    if isinstance(removed_branches, list) and removed_branches:
        lines.append(
            "worktree-sync: cleanup removed branches "
            + ", ".join(str(branch) for branch in removed_branches)
            + "."
        )
    removed_worktrees = summary.get("removed_worktrees")
    if isinstance(removed_worktrees, list) and removed_worktrees:
        lines.append(
            "worktree-sync: cleanup removed worktrees "
            + ", ".join(str(path) for path in removed_worktrees)
            + "."
        )
    skipped_cleanup = summary.get("skipped_cleanup")
    if isinstance(skipped_cleanup, list) and skipped_cleanup:
        skipped_bits: list[str] = []
        for item in skipped_cleanup:
            if not isinstance(item, dict):
                continue
            branch = str(item.get("branch") or "").strip() or "<unknown>"
            reason = str(item.get("reason") or "").strip() or "skipped"
            worktree_path = str(item.get("worktree_path") or "").strip()
            if worktree_path:
                skipped_bits.append(f"{branch} ({reason}: {worktree_path})")
            else:
                skipped_bits.append(f"{branch} ({reason})")
        if skipped_bits:
            lines.append("worktree-sync: cleanup skipped " + ", ".join(skipped_bits) + ".")
    return lines


def integrate_ready_handoff(
    repo: Path,
    current: str,
    target_branch: str,
    *,
    producer_branch: str | None,
    handoff_id: str | None,
    verify_commands: list[str],
    as_json: bool,
) -> int:
    ready, error = _resolve_ready_handoff(
        repo,
        target_branch=target_branch,
        producer_branch=producer_branch,
        handoff_id=handoff_id,
    )
    if ready is None:
        print(error or "worktree-sync: no ready producer handoff found", file=sys.stderr)
        return 1

    producer = str(ready.get("producer_branch") or "").strip()
    resolved_handoff_id = str(ready.get("handoff_id") or "").strip()
    queued_head_sha = str(ready.get("head_sha") or "").strip()
    if not producer:
        print(
            "worktree-sync: ready handoff is malformed — producer branch missing",
            file=sys.stderr,
        )
        return 1
    if not resolved_handoff_id or not queued_head_sha:
        print(
            "worktree-sync: ready handoff is malformed — handoff id or queued head missing",
            file=sys.stderr,
        )
        return 1

    baseline_head = _current_head(repo)
    if target_is_ancestor_of_head(repo, queued_head_sha):
        if (
            mark_integrated(
                repo,
                current,
                target_branch,
                producer,
                handoff_id=resolved_handoff_id,
                quiet=True,
            )
            != 0
        ):
            print(
                "worktree-sync: promoted the tested merge but could not update the handoff queue.",
                file=sys.stderr,
            )
            return 1
        cleanup_summary = cleanup_integrated_branches(
            repo,
            target_branch=target_branch,
            current_branch_name=current,
            ready=ready,
        )
        result_payload = {
            "event": "integrated",
            "producer_branch": producer,
            "target_branch": target_branch,
            "handoff_id": resolved_handoff_id,
            "baseline_head": baseline_head,
            "queued_head_sha": queued_head_sha,
            "integrated_head_sha": _current_head(repo),
            "sandbox_path": "",
            "verification_commands": [],
            "verification_count": 0,
            "repair_only": True,
            "cleanup_summary": cleanup_summary,
        }
        if as_json:
            print(json.dumps(result_payload, ensure_ascii=True, sort_keys=True))
        else:
            print(
                "worktree-sync: repaired handoff queue state for already-promoted handoff "
                f"'{producer}' ({resolved_handoff_id})."
            )
            for line in _cleanup_summary_lines(cleanup_summary):
                print(line)
        return 0

    sandbox_dir = Path(tempfile.mkdtemp(prefix="azoth-integrate-run-"))
    worktree_added = False
    succeeded = False
    try:
        add_result = _run_git(
            repo,
            "worktree",
            "add",
            "--detach",
            str(sandbox_dir),
            target_branch,
            check=False,
        )
        if add_result.returncode != 0:
            detail = (
                add_result.stderr.strip() or add_result.stdout.strip() or "git worktree add failed"
            )
            print(
                f"worktree-sync: could not create integration sandbox worktree: {detail}",
                file=sys.stderr,
            )
            return 1
        worktree_added = True

        merge_message = f"Merge branch '{producer}' into '{target_branch}'"
        merge_result = _run_git(
            sandbox_dir,
            "merge",
            "--no-ff",
            "--no-edit",
            "-m",
            merge_message,
            queued_head_sha,
            check=False,
        )
        if merge_result.returncode != 0:
            try:
                unmerged_paths = _unmerged_paths(sandbox_dir)
            except RuntimeError as exc:
                detail = str(exc)
                print(
                    "worktree-sync: sandbox integrate-run blocked — merge hit conflicts.\n"
                    f"Sandbox preserved at {sandbox_dir}\n{detail}",
                    file=sys.stderr,
                )
                return 1
            if not unmerged_paths or any(path not in set(RECONCILED_PATHS) for path in unmerged_paths):
                detail = (
                    merge_result.stderr.strip() or merge_result.stdout.strip() or "git merge failed"
                )
                print(
                    "worktree-sync: sandbox integrate-run blocked — merge hit conflicts.\n"
                    f"Sandbox preserved at {sandbox_dir}\n{detail}",
                    file=sys.stderr,
                )
                return 1

            # Allow the deterministic reconciliation step to overwrite conflicts only in
            # known shared-state files such as episodes.jsonl and azoth.yaml.
        if merge_result.returncode != 0:
            detail = (
                merge_result.stderr.strip() or merge_result.stdout.strip() or "git merge conflicted only in reconciled paths"
            )

        try:
            _reconcile_shared_state(
                repo,
                sandbox_dir,
                baseline_head=baseline_head,
                queued_head_sha=queued_head_sha,
                ready=ready,
            )
            _persist_reconciled_state(sandbox_dir)
        except ValueError as exc:
            print(
                "worktree-sync: sandbox integrate-run blocked — reconciliation failed.\n"
                f"Sandbox preserved at {sandbox_dir}\n{exc}",
                file=sys.stderr,
            )
            return 1
        except RuntimeError as exc:
            print(
                "worktree-sync: sandbox integrate-run blocked — could not persist reconciled state.\n"
                f"Sandbox preserved at {sandbox_dir}\n{exc}",
                file=sys.stderr,
            )
            return 1

        verification_results: list[dict[str, object]] = []
        for raw_command in verify_commands:
            argv = shlex.split(raw_command)
            if not argv:
                continue
            verify_result = _run_cmd(sandbox_dir, argv)
            verification_results.append(
                {
                    "command": raw_command,
                    "returncode": verify_result.returncode,
                }
            )
            if verify_result.returncode != 0:
                detail = (
                    verify_result.stderr.strip()
                    or verify_result.stdout.strip()
                    or "verification command failed"
                )
                print(
                    "worktree-sync: sandbox integrate-run blocked — verification failed.\n"
                    f"Command: {raw_command}\n"
                    f"Sandbox preserved at {sandbox_dir}\n{detail}",
                    file=sys.stderr,
                )
                return 1

        if _current_head(repo) != baseline_head:
            print(
                "worktree-sync: target branch moved during sandbox integration. "
                "Refresh and rerun the integrate pass.",
                file=sys.stderr,
            )
            return 1

        sandbox_head = _current_head(sandbox_dir)
        promote_result = _run_git(repo, "merge", "--ff-only", sandbox_head, check=False)
        if promote_result.returncode != 0:
            detail = (
                promote_result.stderr.strip()
                or promote_result.stdout.strip()
                or "fast-forward promotion failed"
            )
            print(
                "worktree-sync: sandbox merge succeeded but target branch could not be promoted.\n"
                f"Sandbox preserved at {sandbox_dir}\n{detail}",
                file=sys.stderr,
            )
            return 1

        if (
            mark_integrated(
                repo,
                current,
                target_branch,
                producer,
                handoff_id=resolved_handoff_id,
                quiet=as_json,
            )
            != 0
        ):
            print(
                "worktree-sync: promoted the tested merge but could not update the handoff queue.\n"
                f"Sandbox preserved at {sandbox_dir}",
                file=sys.stderr,
            )
            return 1
        cleanup_summary = cleanup_integrated_branches(
            repo,
            target_branch=target_branch,
            current_branch_name=current,
            ready=ready,
        )

        result_payload = {
            "event": "integrated",
            "producer_branch": producer,
            "target_branch": target_branch,
            "handoff_id": resolved_handoff_id,
            "baseline_head": baseline_head,
            "queued_head_sha": queued_head_sha,
            "integrated_head_sha": sandbox_head,
            "sandbox_path": str(sandbox_dir),
            "verification_commands": verify_commands,
            "verification_count": len(verification_results),
            "repair_only": False,
            "cleanup_summary": cleanup_summary,
        }
        succeeded = True
        if as_json:
            print(json.dumps(result_payload, ensure_ascii=True, sort_keys=True))
        else:
            subject = _commit_subject(repo, sandbox_head)
            print(
                "worktree-sync: integrated ready producer handoff "
                f"'{producer}' ({resolved_handoff_id}) into '{target_branch}' via sandbox {sandbox_dir}.\n"
                f"worktree-sync: promoted tested merge {sandbox_head} ({subject})."
            )
            for line in _cleanup_summary_lines(cleanup_summary):
                print(line)
        return 0
    finally:
        if worktree_added and succeeded:
            _run_git(repo, "worktree", "remove", "--force", str(sandbox_dir), check=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backend preflight for Azoth /worktree-sync.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Git repository root or any path inside it (default: cwd).",
    )
    parser.add_argument(
        "--target-branch",
        default=None,
        help="Optional integration branch override. Defaults to phase/<active_version>.",
    )
    parser.add_argument(
        "--record-producer-handoff",
        action="store_true",
        help="Record the current clean producer branch as ready for integrator handoff.",
    )
    parser.add_argument(
        "--next-ready-handoff",
        action="store_true",
        help="Show the next ready producer handoff for the target branch.",
    )
    parser.add_argument(
        "--integrate-ready-handoff",
        action="store_true",
        help="Merge one queued producer branch in a temporary sandbox worktree and promote it if verification passes.",
    )
    parser.add_argument(
        "--producer-branch",
        default=None,
        help="Optional producer branch selector for ready/integrated handoff actions.",
    )
    parser.add_argument(
        "--handoff-id",
        default=None,
        help="Optional exact handoff selector for ready/integrated handoff actions.",
    )
    parser.add_argument(
        "--mark-integrated",
        nargs="?",
        const="",
        default=None,
        metavar="BRANCH",
        help="Mark a queued producer handoff as integrated into the target branch.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON for ready handoff selection.",
    )
    parser.add_argument(
        "--verify-command",
        action="append",
        default=[],
        help="Verification command to run inside the temporary integration worktree (repeatable).",
    )
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    root = _git_top(repo)
    if root is None:
        print("worktree-sync: not a git repository", file=sys.stderr)
        return 1

    try:
        target_branch = resolve_target_branch(root, args.target_branch)
        if not branch_exists(root, target_branch):
            raise RuntimeError(
                f"target branch '{target_branch}' does not exist locally. "
                "Refresh your local repo or pass a valid --target-branch."
            )
        raw_branch = current_branch(root)
    except RuntimeError as exc:
        print(f"worktree-sync: {exc}", file=sys.stderr)
        return 1

    is_integrator = raw_branch is not None and raw_branch == target_branch
    if raw_branch is None:
        try:
            branch, attach_message = resolve_producer_branch(root)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if attach_message:
            print(attach_message)
    else:
        branch = raw_branch

    if (
        args.next_ready_handoff
        or args.integrate_ready_handoff
        or args.mark_integrated is not None
    ) and not is_integrator:
        print(
            "worktree-sync: integrate actions require the active integration branch to be checked out.",
            file=sys.stderr,
        )
        return 1

    if is_integrator:
        result = integrator_preflight(
            root,
            branch,
            target_branch,
            quiet=args.json and (args.next_ready_handoff or args.integrate_ready_handoff),
        )
    else:
        result = producer_refresh(root, branch, target_branch)
    if result != 0:
        return result

    if args.record_producer_handoff:
        return register_producer_handoff(root, branch, target_branch)
    if args.next_ready_handoff:
        return show_ready_handoff(
            root,
            target_branch,
            args.producer_branch,
            handoff_id=args.handoff_id,
            as_json=args.json,
        )
    if args.integrate_ready_handoff:
        return integrate_ready_handoff(
            root,
            branch,
            target_branch,
            producer_branch=args.producer_branch,
            handoff_id=args.handoff_id,
            verify_commands=args.verify_command,
            as_json=args.json,
        )
    if args.mark_integrated is not None:
        return mark_integrated(
            root,
            branch,
            target_branch,
            args.mark_integrated or None,
            handoff_id=args.handoff_id,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

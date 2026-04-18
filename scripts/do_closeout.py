#!/usr/bin/env python3
"""Apply the documented W1–W4 closeout sequence."""

from __future__ import annotations

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
from run_ledger import release_write_claim, upsert_run, upsert_session

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


class CloseoutError(RuntimeError):
    """Base error for closeout preconditions and execution failures."""


class ApprovalEvidenceError(CloseoutError):
    """Raised when governed closeout lacks valid final-delivery approval evidence."""


class ReinforcementValidationError(CloseoutError):
    """Raised when requested reinforcement targets are not safe to apply."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
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
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise CloseoutError(f"Expected YAML mapping in {path}")
    return data


def write_yaml(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def default_next_action() -> str:
    return "Run `/next` to select the next scoped task."


def is_governed_scope(scope: dict[str, Any]) -> bool:
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
        "type": "success",
        "goal": str(scope.get("goal") or "Session closeout"),
        "summary": "Completed session closeout via scripts/do_closeout.py (W1-W4).",
        "lessons": [],
        "tags": ["closeout", "session-closeout"],
        "reinforcement_count": 0,
        "m2_candidate": False,
        "context": {"files_changed": files_changed},
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
        and str(run.get("status") or "") in {"active", "paused"}
    ]
    if not resumable:
        return None
    if preferred_run_id:
        for run in reversed(resumable):
            if str(run.get("run_id") or "") == preferred_run_id:
                return run
    return resumable[-1]


def update_session_registry(
    repo_root: pathlib.Path,
    *,
    scope: dict[str, Any],
    timestamp: str,
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
        next_action = closed_next_action
        if resumable_run is not None and administrative_finalize:
            upsert_run(
                repo_root,
                run_id=str(resumable_run.get("run_id") or preferred_run_id or ""),
                mode=str(resumable_run.get("mode") or "auto"),
                goal=str(resumable_run.get("goal") or goal),
                status="complete",
                next_action=closed_next_action,
                session_id=session_id,
                backlog_id=backlog_id,
                ide=ide,
                updated_at=timestamp,
                stages_completed=resumable_run.get("stages_completed") or [],
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
    next_action: str,
    session_status: str,
    pending_decisions: list[str],
) -> None:
    azoth_data = load_yaml(repo_root / "azoth.yaml")
    active_version, current_patch = _active_version_snapshot(repo_root)
    version = azoth_data.get("version", "unknown")
    phase = azoth_data.get("phase", "unknown")
    goal = str(scope.get("goal") or "Session closeout")
    pipeline = str(scope.get("delivery_pipeline") or "standard")

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
        "## Key Changes This Session",
        "1. W1 appended the closeout episode.",
        "2. W2 closed the scope gate and refreshed repo-local handoff state.",
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
        return "W2: session-state.md not present (skipped)"
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
    return "W2: session-state.md refreshed"


def update_session_state(
    repo_root: pathlib.Path,
    *,
    scope: dict[str, Any],
    timestamp: str,
    session_status: str,
    active_files: list[str],
    next_action: str,
    existing_session_state: dict[str, Any],
    selected_ide: str | None = None,
    clear_checkpoint: bool = False,
) -> str:
    goal = str(scope.get("goal") or "Session closeout")
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
    reinforce_episode_ids: list[str] | None = None,
    administrative_finalize: bool = False,
) -> None:
    scope = load_json(repo_root / ".azoth" / "scope-gate.json")
    enforce_governed_closeout_approval(repo_root, scope)
    reinforce_episode_ids = reinforce_episode_ids or []
    validate_reinforcement_targets(repo_root, reinforce_episode_ids)

    timestamp = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    session_id = str(scope.get("session_id") or "unknown-session")
    backlog_id = str(scope.get("backlog_id") or "").strip()
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    session_state_path = repo_root / ".azoth" / "session-state.md"
    existing_session_state = load_yaml(session_state_path)
    authoritative_files = [
        ".azoth/memory/episodes.jsonl",
        ".azoth/bootloader-state.md",
        ".azoth/scope-gate.json",
        "azoth.yaml",
    ]
    if backlog_id and backlog_id != "AD-HOC":
        authoritative_files.extend([".azoth/backlog.yaml", ".azoth/roadmap.yaml"])
    if ledger_path.exists():
        authoritative_files.append(".azoth/run-ledger.local.yaml")
    if session_state_path.exists():
        authoritative_files.append(".azoth/session-state.md")

    _episode_id, latest_episode, episode_count = append_episode(
        repo_root,
        scope,
        timestamp,
        files_changed=authoritative_files,
    )
    for episode_id in reinforce_episode_ids:
        try:
            result = increment_reinforcement_count(
                repo_root,
                episode_id,
                session_id,
                source="closeout",
            )
        except ReinforcementError as exc:
            raise CloseoutError(
                f"Closeout blocked: failed to apply reinforcement update for {episode_id}: {exc}"
            ) from exc
        status = "incremented" if result.changed else "already reinforced this session"
        print(
            f"W1b: reinforcement {status} for {result.episode_id} "
            f"(count={result.reinforcement_count})"
        )
    selected_ide = str(existing_session_state.get("last_ide") or "")
    close_scope_gate(repo_root, timestamp)
    next_action, session_status, registry_note = update_session_registry(
        repo_root,
        scope=scope,
        timestamp=timestamp,
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
                    if isinstance(entry, dict) and str(entry.get("session_id") or "") == session_id
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
        selected_ide=selected_ide or None,
        clear_checkpoint=administrative_finalize,
    )
    print(session_state_note)
    update_bootloader_state(
        repo_root,
        scope=scope,
        latest_episode=latest_episode,
        next_action=next_action,
        session_status=session_status,
        pending_decisions=(
            existing_session_state.get("pending_decisions")
            if isinstance(existing_session_state.get("pending_decisions"), list)
            else []
        ),
    )
    update_episode_count(repo_root, episode_count)
    write_claude_memory_mirror(
        repo_root,
        latest_episode=latest_episode,
        next_action=next_action,
    )
    finalize_closeout_artifacts(
        repo_root,
        administrative_finalize=administrative_finalize,
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Apply the documented W1–W4 closeout sequence.")
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
        run_closeout(
            reinforce_episode_ids=args.reinforce_episode_ids,
            administrative_finalize=args.administrative_finalize,
        )
    except CloseoutError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

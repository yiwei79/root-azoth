#!/usr/bin/env python3
"""Apply the documented W1–W4 closeout sequence."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FINAL_DELIVERY_APPROVALS = pathlib.Path(".azoth") / "final-delivery-approvals.jsonl"


class CloseoutError(RuntimeError):
    """Base error for closeout preconditions and execution failures."""


class ApprovalEvidenceError(CloseoutError):
    """Raised when governed closeout lacks valid final-delivery approval evidence."""


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
                raise ApprovalEvidenceError(
                    f"Expected JSON object in {path} line {line_number}"
                )
            records.append(record)
    return records


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


def append_episode(repo_root: pathlib.Path, scope: dict[str, Any], timestamp: str) -> str:
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
        "context": {
            "files_changed": [
                ".azoth/memory/episodes.jsonl",
                ".azoth/scope-gate.json",
                "azoth.yaml",
                ".azoth/backlog.yaml",
            ]
        },
    }

    episodes_path.parent.mkdir(parents=True, exist_ok=True)
    with open(episodes_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(new_episode) + "\n")

    print(f"W1: Appended episode {new_id} to {episodes_path}")
    return new_id


def close_scope_gate(repo_root: pathlib.Path, timestamp: str) -> dict[str, Any]:
    gate_path = repo_root / ".azoth" / "scope-gate.json"
    gate_data = load_json(gate_path)
    gate_data["approved"] = False
    gate_data["closed_at"] = timestamp
    with open(gate_path, "w", encoding="utf-8") as handle:
        json.dump(gate_data, handle, indent=2)
    print(f"W2: scope gate closed at {gate_path}")
    return gate_data


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


def update_backlog(repo_root: pathlib.Path, backlog_id: str | None) -> None:
    if not backlog_id:
        print("W3: No backlog_id in scope gate, skipped backlog update")
        return

    backlog_path = repo_root / ".azoth" / "backlog.yaml"
    if not backlog_path.exists():
        print("W3: backlog.yaml not found, skipped backlog update")
        return

    with open(backlog_path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    in_target = False
    updated = False
    date_str = utc_now().strftime("%Y-%m-%d")
    new_lines: list[str] = []

    for line in lines:
        if line.startswith("  - id:"):
            current_id = line.split(":", 1)[1].strip().strip("\"'")
            in_target = current_id == backlog_id

        if in_target and line.lstrip().startswith("status:"):
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}status: complete\n")
            new_lines.append(f'{indent}completed_date: "{date_str}"\n')
            updated = True
            continue

        new_lines.append(line)

    if not updated:
        print(f"W3: Backlog item {backlog_id} not found or no status updated")
        return

    with open(backlog_path, "w", encoding="utf-8") as handle:
        handle.writelines(new_lines)
    print(f"W3: Updated backlog item {backlog_id} to status: complete")


def run_version_bump(repo_root: pathlib.Path) -> None:
    print("W4: Running version-bump.py...")
    subprocess.run(
        [sys.executable, "scripts/version-bump.py", "--patch"],
        cwd=repo_root,
        check=True,
    )

    orientation_path = repo_root / ".azoth" / "session-orientation.txt"
    if orientation_path.exists():
        orientation_path.unlink()
        print("W4: Removed session-orientation.txt")
    else:
        print("W4: session-orientation.txt not found (skipped)")


def run_closeout(repo_root: pathlib.Path = REPO_ROOT) -> None:
    scope = load_json(repo_root / ".azoth" / "scope-gate.json")
    enforce_governed_closeout_approval(repo_root, scope)

    timestamp = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    append_episode(repo_root, scope, timestamp)
    gate_data = close_scope_gate(repo_root, timestamp)
    episode_count = len(load_jsonl(repo_root / ".azoth" / "memory" / "episodes.jsonl"))
    update_episode_count(repo_root, episode_count)
    update_backlog(repo_root, gate_data.get("backlog_id"))
    run_version_bump(repo_root)


def main() -> int:
    try:
        run_closeout()
    except CloseoutError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

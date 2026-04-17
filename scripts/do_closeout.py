#!/usr/bin/env python3
"""Apply the documented W1–W4 closeout sequence."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

import yaml
from reinforcement_count import ReinforcementError, increment_reinforcement_count
from run_ledger import release_write_claim

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FINAL_DELIVERY_APPROVALS = pathlib.Path(".azoth") / "final-delivery-approvals.jsonl"


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
) -> tuple[str, str, str]:
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    if not ledger_path.exists():
        return default_next_action(), "closed", "W2: session registry not present (skipped)"

    ledger = load_yaml(ledger_path)
    sessions = ledger.get("sessions")
    if not isinstance(sessions, list):
        return default_next_action(), "closed", "W2: session registry not present (skipped)"

    session_id = str(scope.get("session_id") or "")
    matching_session = next(
        (
            entry
            for entry in sessions
            if isinstance(entry, dict) and str(entry.get("session_id") or "") == session_id
        ),
        None,
    )
    if matching_session is None:
        return (
            default_next_action(),
            "closed",
            f"W2: session registry entry not found for '{session_id}'",
        )

    preferred_run_id = str(matching_session.get("active_run_id") or "") or None
    resumable_run = _resumable_run_for_session(
        ledger,
        session_id=session_id,
        preferred_run_id=preferred_run_id,
    )
    if resumable_run is not None:
        next_action = str(
            resumable_run.get("next_action")
            or matching_session.get("next_action")
            or default_next_action()
        )
        matching_session["status"] = "parked"
        matching_session["next_action"] = next_action
        matching_session["active_run_id"] = str(
            resumable_run.get("run_id") or preferred_run_id or ""
        )
        matching_session.pop("closed_at", None)
        session_status = "parked"
    else:
        next_action = default_next_action()
        matching_session["status"] = "closed"
        matching_session["next_action"] = next_action
        matching_session.pop("active_run_id", None)
        matching_session["closed_at"] = timestamp
        session_status = "closed"

    matching_session["updated_at"] = timestamp
    write_yaml(ledger_path, ledger)
    return next_action, session_status, f"W2: session registry updated ({session_status})"


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


def update_session_state(
    repo_root: pathlib.Path,
    *,
    scope: dict[str, Any],
    timestamp: str,
    active_files: list[str],
    next_action: str,
    existing_session_state: dict[str, Any],
    selected_ide: str | None = None,
) -> str:
    session_state_path = repo_root / ".azoth" / "session-state.md"
    if not session_state_path.exists():
        return "W2: session-state.md not present (skipped)"

    goal = str(scope.get("goal") or "Session closeout")
    pending_decisions = existing_session_state.get("pending_decisions")
    if not isinstance(pending_decisions, list):
        pending_decisions = []
    session_state = {
        "session_id": str(scope.get("session_id") or "unknown-session"),
        "state": "closed",
        "last_ide": str(existing_session_state.get("last_ide") or selected_ide or "unknown"),
        "timestamp": timestamp,
        "active_task": f"Closed — {goal}",
        "active_files": active_files,
        "pending_decisions": pending_decisions,
        "approved_scope": f"Completed: {goal}",
        "next_action": next_action,
    }
    session_state_path.write_text(yaml.safe_dump(session_state, sort_keys=False), encoding="utf-8")
    return "W2: session-state.md refreshed"


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
) -> None:
    scope = load_json(repo_root / ".azoth" / "scope-gate.json")
    enforce_governed_closeout_approval(repo_root, scope)
    reinforce_episode_ids = reinforce_episode_ids or []
    validate_reinforcement_targets(repo_root, reinforce_episode_ids)

    timestamp = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    session_id = str(scope.get("session_id") or "unknown-session")
    ledger_path = repo_root / ".azoth" / "run-ledger.local.yaml"
    session_state_path = repo_root / ".azoth" / "session-state.md"
    existing_session_state = load_yaml(session_state_path)
    authoritative_files = [
        ".azoth/memory/episodes.jsonl",
        ".azoth/bootloader-state.md",
        ".azoth/scope-gate.json",
        "azoth.yaml",
    ]
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
    close_scope_gate(repo_root, timestamp)
    next_action, session_status, registry_note = update_session_registry(
        repo_root,
        scope=scope,
        timestamp=timestamp,
    )
    print(registry_note)
    if release_write_claim(repo_root, session_id):
        print(f"W2: write claim released for session '{session_id}'")
    else:
        print(f"W2: write claim not held by '{session_id}' — no-op")
    selected_ide = str(existing_session_state.get("last_ide") or "")
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
        active_files=active_files,
        next_action=next_action,
        existing_session_state=existing_session_state,
        selected_ide=selected_ide or None,
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
    run_version_bump(repo_root)


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
    args = parser.parse_args()

    try:
        run_closeout(reinforce_episode_ids=args.reinforce_episode_ids)
    except CloseoutError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

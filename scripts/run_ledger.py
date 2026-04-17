#!/usr/bin/env python3
"""
run_ledger.py — Azoth run ledger CLI (P1-001).

Manages durable run state for multi-wave /eval-swarm and long /auto runs.
Ledger lives at .azoth/run-ledger.local.yaml (gitignored).
Schema: pipelines/run-ledger.schema.yaml

Usage:
  python scripts/run_ledger.py validate [--ledger PATH]
  python scripts/run_ledger.py status   [--ledger PATH]
  python scripts/run_ledger.py append   --run-id ID --mode MODE --goal GOAL
                                        --status STATUS --next-action TEXT
                                        [--stage-completed STAGE] ...
                                        [--wave JSON]
                                        [--ledger PATH]
  python scripts/run_ledger.py park-session SESSION_ID BACKLOG_ID --goal GOAL
                                        --ide IDE --next-action TEXT
                                        [--active-run-id ID]
                                        [--ledger PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / ".azoth" / "run-ledger.local.yaml"

_STATUS_ENUM = {"active", "complete", "failed", "paused"}
_SESSION_STATUS_ENUM = {"active", "parked", "closed"}
_WAVE_STATUS_ENUM = {"pass", "fail", "partial"}
_BRANCH_DISPOSITION_ENUM = {"merged", "discarded", "pending"}
_PAUSE_REASON_ENUM = {"human-gate", "handoff", "retry"}
_ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_STAGE_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_UNSET = object()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _die(msg: str) -> None:
    print(f"[run-ledger] error: {msg}", file=sys.stderr)
    sys.exit(1)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _load_ledger(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "runs": []}
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        _die(f"could not parse ledger YAML: {exc}")
    if not isinstance(data, dict):
        _die("ledger root is not a YAML mapping")
    return data


def _write_ledger(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _load_ledger_for_helpers(root: Path) -> dict | None:
    ledger_path = root / ".azoth" / "run-ledger.local.yaml"
    if not ledger_path.exists():
        return None
    try:
        with ledger_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


# ── Validator ─────────────────────────────────────────────────────────────────


def validate_ledger(data: dict) -> list[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["root must be a YAML mapping"]

    sv = data.get("schema_version")
    if sv != 1:
        errors.append(f"schema_version must be 1, got {sv!r}")

    runs = data.get("runs")
    if runs is None:
        errors.append("missing required field: runs")
        return errors
    if not isinstance(runs, list):
        errors.append("runs must be a list")
        return errors

    sessions = data.get("sessions")
    if sessions is not None:
        if not isinstance(sessions, list):
            errors.append("sessions must be a list")
        else:
            for i, entry in enumerate(sessions):
                prefix = f"sessions[{i}]"
                if not isinstance(entry, dict):
                    errors.append(f"{prefix} must be a mapping")
                    continue

                for field in ("session_id", "backlog_id", "goal", "ide", "next_action"):
                    val = entry.get(field)
                    if val is None:
                        errors.append(f"{prefix}: missing required field '{field}'")
                    elif not isinstance(val, str) or not val.strip():
                        errors.append(f"{prefix}: '{field}' must be a non-empty string")

                for field, max_len in (("session_id", 128), ("backlog_id", 64), ("ide", 64)):
                    val = entry.get(field) or ""
                    if isinstance(val, str) and len(val) > max_len:
                        errors.append(f"{prefix}: {field} exceeds {max_len} characters")

                status = entry.get("status")
                if status is None:
                    errors.append(f"{prefix}: missing required field 'status'")
                elif status not in _SESSION_STATUS_ENUM:
                    errors.append(
                        f"{prefix}: status {status!r} not in {sorted(_SESSION_STATUS_ENUM)}"
                    )

                updated_at = entry.get("updated_at")
                if updated_at is None:
                    errors.append(f"{prefix}: missing required field 'updated_at'")
                elif not isinstance(updated_at, str) or not _ISO8601_RE.match(updated_at):
                    errors.append(
                        f"{prefix}: 'updated_at' must match ISO-8601 (YYYY-MM-DDTHH:MM:SS…), got {updated_at!r}"
                    )

                for optional_ts in ("closed_at",):
                    val = entry.get(optional_ts)
                    if val is not None and (not isinstance(val, str) or not _ISO8601_RE.match(val)):
                        errors.append(
                            f"{prefix}: '{optional_ts}' must match ISO-8601 (YYYY-MM-DDTHH:MM:SS…), got {val!r}"
                        )

                active_run_id = entry.get("active_run_id")
                if active_run_id is not None and (
                    not isinstance(active_run_id, str) or not active_run_id.strip()
                ):
                    errors.append(f"{prefix}: active_run_id must be a non-empty string")

    for i, entry in enumerate(runs):
        prefix = f"runs[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be a mapping")
            continue

        for field, max_len in (("session_id", 128), ("backlog_id", 64), ("ide", 64)):
            val = entry.get(field)
            if val is not None:
                if not isinstance(val, str) or not val.strip():
                    errors.append(f"{prefix}: '{field}' must be a non-empty string")
                elif len(val) > max_len:
                    errors.append(f"{prefix}: {field} exceeds {max_len} characters")

        # Required string fields
        for field in ("run_id", "mode", "goal", "next_action"):
            val = entry.get(field)
            if val is None:
                errors.append(f"{prefix}: missing required field '{field}'")
            elif not isinstance(val, str) or not val.strip():
                errors.append(f"{prefix}: '{field}' must be a non-empty string")

        # run_id length
        run_id = entry.get("run_id") or ""
        if len(run_id) > 128:
            errors.append(f"{prefix}: run_id exceeds 128 characters")

        # status enum
        status = entry.get("status")
        if status is None:
            errors.append(f"{prefix}: missing required field 'status'")
        elif status not in _STATUS_ENUM:
            errors.append(f"{prefix}: status {status!r} not in {sorted(_STATUS_ENUM)}")

        # ISO-8601 timestamps
        for ts_field in ("created_at", "updated_at"):
            val = entry.get(ts_field)
            if val is None:
                errors.append(f"{prefix}: missing required field '{ts_field}'")
            elif not isinstance(val, str) or not _ISO8601_RE.match(val):
                errors.append(
                    f"{prefix}: '{ts_field}' must match ISO-8601 (YYYY-MM-DDTHH:MM:SS…), got {val!r}"
                )

        # stages_completed
        sc = entry.get("stages_completed")
        if sc is not None:
            if not isinstance(sc, list):
                errors.append(f"{prefix}: stages_completed must be a list")
            else:
                for j, s in enumerate(sc):
                    if not isinstance(s, str) or not s.strip():
                        errors.append(f"{prefix}.stages_completed[{j}] must be a non-empty string")
                    elif not _STAGE_ID_RE.match(s):
                        errors.append(
                            f"{prefix}.stages_completed[{j}] must match stage id pattern, got {s!r}"
                        )

        active_stage_id = entry.get("active_stage_id")
        if active_stage_id is not None:
            if not isinstance(active_stage_id, str) or not active_stage_id.strip():
                errors.append(f"{prefix}: active_stage_id must be a non-empty string")
            elif not _STAGE_ID_RE.match(active_stage_id):
                errors.append(
                    f"{prefix}: active_stage_id must match stage id pattern, got {active_stage_id!r}"
                )

        pending_stage_ids = entry.get("pending_stage_ids")
        if pending_stage_ids is not None:
            if not isinstance(pending_stage_ids, list):
                errors.append(f"{prefix}: pending_stage_ids must be a list")
            else:
                for j, stage_id in enumerate(pending_stage_ids):
                    if not isinstance(stage_id, str) or not stage_id.strip():
                        errors.append(f"{prefix}.pending_stage_ids[{j}] must be a non-empty string")
                    elif not _STAGE_ID_RE.match(stage_id):
                        errors.append(
                            f"{prefix}.pending_stage_ids[{j}] must match stage id pattern, got {stage_id!r}"
                        )

        pause_reason = entry.get("pause_reason")
        if pause_reason is not None and pause_reason not in _PAUSE_REASON_ENUM:
            errors.append(
                f"{prefix}: pause_reason {pause_reason!r} not in {sorted(_PAUSE_REASON_ENUM)}"
            )

        # waves
        waves = entry.get("waves")
        if waves is not None:
            if not isinstance(waves, list):
                errors.append(f"{prefix}: waves must be a list")
            else:
                for j, w in enumerate(waves):
                    wp = f"{prefix}.waves[{j}]"
                    if not isinstance(w, dict):
                        errors.append(f"{wp} must be a mapping")
                        continue
                    wn = w.get("wave")
                    if wn is None:
                        errors.append(f"{wp}: missing required field 'wave'")
                    elif not isinstance(wn, int) or wn < 1:
                        errors.append(f"{wp}: wave must be a positive integer")
                    ws = w.get("status")
                    if ws is None:
                        errors.append(f"{wp}: missing required field 'status'")
                    elif ws not in _WAVE_STATUS_ENUM:
                        errors.append(f"{wp}: status {ws!r} not in {sorted(_WAVE_STATUS_ENUM)}")

        # branches
        branches = entry.get("branches")
        if branches is not None:
            if not isinstance(branches, list):
                errors.append(f"{prefix}: branches must be a list")
            else:
                for j, b in enumerate(branches):
                    bp = f"{prefix}.branches[{j}]"
                    if not isinstance(b, dict):
                        errors.append(f"{bp} must be a mapping")
                        continue
                    bid = b.get("branch_id")
                    if bid is None:
                        errors.append(f"{bp}: missing required field 'branch_id'")
                    elif not isinstance(bid, str) or not bid.strip():
                        errors.append(f"{bp}: branch_id must be a non-empty string")
                    bd = b.get("disposition")
                    if bd is None:
                        errors.append(f"{bp}: missing required field 'disposition'")
                    elif bd not in _BRANCH_DISPOSITION_ENUM:
                        errors.append(
                            f"{bp}: disposition {bd!r} not in {sorted(_BRANCH_DISPOSITION_ENUM)}"
                        )

    # write_claim (optional top-level field)
    write_claim = data.get("write_claim")
    if write_claim is not None:
        if not isinstance(write_claim, dict):
            errors.append("write_claim must be a mapping")
        else:
            for field in ("session_id", "acquired_at"):
                val = write_claim.get(field)
                if val is None:
                    errors.append(f"write_claim: missing required field '{field}'")
                elif not isinstance(val, str) or not val.strip():
                    errors.append(f"write_claim: '{field}' must be a non-empty string")
            # expires_at: required, must be valid ISO-8601
            expires_val = write_claim.get("expires_at")
            if expires_val is None:
                errors.append("write_claim: missing required field 'expires_at'")
            elif not isinstance(expires_val, str) or not _ISO8601_RE.match(expires_val):
                errors.append(
                    f"write_claim: 'expires_at' must match ISO-8601 (YYYY-MM-DDTHH:MM:SS…), "
                    f"got {expires_val!r}"
                )

    return errors


# ── Write-claim helpers (P1-015) ──────────────────────────────────────────────


def _ledger_path_from_root(root: Path) -> Path:
    return root / ".azoth" / "run-ledger.local.yaml"


def _root_from_ledger_path(path: Path) -> Path:
    if path.parent.name == ".azoth":
        return path.parent.parent
    return path.parent


def load_write_claim(root: Path) -> dict | None:
    """Return the write_claim dict from the ledger, or None if absent."""
    data = _load_ledger_for_helpers(root)
    if data is None:
        return None
    claim = data.get("write_claim")
    return claim if isinstance(claim, dict) else None


def acquire_write_claim(
    root: Path,
    session_id: str,
    expires_at: str,
    harness: str | None = None,
) -> tuple[bool, str]:
    """Attempt to acquire the write claim for session_id.

    Returns (True, session_id) on success.
    Returns (False, reason) if an unexpired claim already exists for a different session.
    """
    ledger_path = _ledger_path_from_root(root)
    data = _load_ledger_for_helpers(root)
    if data is None:
        data = {"schema_version": 1, "runs": []}

    existing = data.get("write_claim")
    if isinstance(existing, dict):
        holder = existing.get("session_id", "")
        if holder == session_id:
            # Re-acquire: update expiry
            existing["expires_at"] = expires_at
            existing["acquired_at"] = utc_now_iso()
            if harness is not None:
                existing["harness"] = harness
            _write_ledger(ledger_path, data)
            return True, session_id
        # Check if the existing claim is expired
        raw_exp = existing.get("expires_at", "")
        from datetime import datetime, timezone as _tz

        try:
            normalized = raw_exp.replace("Z", "+00:00") if raw_exp.endswith("Z") else raw_exp
            exp_dt = datetime.fromisoformat(normalized)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=_tz.utc)
        except (ValueError, TypeError):
            exp_dt = None
        if exp_dt is not None and datetime.now(_tz.utc) < exp_dt:
            return False, f"write claim held by '{holder}' until {raw_exp}"

    # No unexpired foreign claim — acquire it
    new_claim: dict = {
        "session_id": session_id,
        "expires_at": expires_at,
        "acquired_at": utc_now_iso(),
    }
    if harness is not None:
        new_claim["harness"] = harness
    data["write_claim"] = new_claim
    _write_ledger(ledger_path, data)
    return True, session_id


def release_write_claim(root: Path, session_id: str) -> bool:
    """Release the write claim if the caller is the owner.

    Returns True when the claim was owned by session_id and has been removed.
    Returns False (no-op) when no claim exists or the caller is not the owner.
    """
    ledger_path = _ledger_path_from_root(root)
    data = _load_ledger_for_helpers(root)
    if data is None:
        return False
    existing = data.get("write_claim")
    if not isinstance(existing, dict):
        return False
    if existing.get("session_id") != session_id:
        return False
    del data["write_claim"]
    _write_ledger(ledger_path, data)
    return True


def resolve_stale_claims(root: Path) -> bool:
    """Check the write claim against the clock; clear it if expired.

    Returns True when a stale claim was found and cleared.
    Returns False when no claim exists or the claim is unexpired.
    Clock-only check — no external bypass signal (ADV-2).
    """
    ledger_path = _ledger_path_from_root(root)
    data = _load_ledger_for_helpers(root)
    if data is None:
        return False
    existing = data.get("write_claim")
    if not isinstance(existing, dict):
        return False
    raw_exp = existing.get("expires_at", "")
    from datetime import datetime, timezone as _tz

    try:
        normalized = raw_exp.replace("Z", "+00:00") if raw_exp.endswith("Z") else raw_exp
        exp_dt = datetime.fromisoformat(normalized)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=_tz.utc)
    except (ValueError, TypeError):
        # Unparseable expiry — treat as expired
        del data["write_claim"]
        _write_ledger(ledger_path, data)
        return True
    if datetime.now(_tz.utc) >= exp_dt:
        del data["write_claim"]
        _write_ledger(ledger_path, data)
        return True
    return False


def upsert_session(
    root: Path,
    *,
    session_id: str,
    backlog_id: str,
    goal: str,
    status: str,
    ide: str,
    next_action: str,
    updated_at: str | None = None,
    active_run_id: str | None = None,
    closed_at: str | None = None,
    ledger_path: Path | None = None,
) -> tuple[bool, dict]:
    """Create or update a session registry entry.

    Returns (created, entry).
    """
    if status not in _SESSION_STATUS_ENUM:
        raise ValueError(f"status {status!r} not in {sorted(_SESSION_STATUS_ENUM)}")

    resolved_ledger_path = ledger_path or _ledger_path_from_root(root)
    data = (
        _load_ledger(resolved_ledger_path)
        if ledger_path is not None
        else _load_ledger_for_helpers(root)
    )
    if data is None:
        data = _load_ledger(resolved_ledger_path)

    sessions = data.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
        data["sessions"] = sessions

    entry = next(
        (
            item
            for item in sessions
            if isinstance(item, dict) and str(item.get("session_id") or "") == session_id
        ),
        None,
    )
    created = entry is None
    if entry is None:
        entry = {"session_id": session_id}
        sessions.append(entry)

    timestamp = updated_at or utc_now_iso()
    entry["session_id"] = session_id
    entry["backlog_id"] = backlog_id
    entry["goal"] = goal
    entry["status"] = status
    entry["ide"] = ide
    entry["next_action"] = next_action
    entry["updated_at"] = timestamp

    if active_run_id:
        entry["active_run_id"] = active_run_id
    else:
        entry.pop("active_run_id", None)

    if closed_at:
        entry["closed_at"] = closed_at
    elif status == "closed":
        entry["closed_at"] = timestamp
    else:
        entry.pop("closed_at", None)

    errors = validate_ledger(data)
    if errors:
        raise ValueError("; ".join(errors))

    _write_ledger(resolved_ledger_path, data)
    return created, entry


def load_run(root: Path, run_id: str) -> dict | None:
    """Return a single run entry by run_id, or None when absent."""
    data = _load_ledger_for_helpers(root)
    if data is None:
        return None
    runs = data.get("runs")
    if not isinstance(runs, list):
        return None
    for entry in runs:
        if isinstance(entry, dict) and str(entry.get("run_id") or "") == run_id:
            return entry
    return None


def upsert_run(
    root: Path,
    *,
    run_id: str,
    mode: str,
    goal: str,
    status: str,
    next_action: str,
    session_id: str | None = None,
    backlog_id: str | None = None,
    ide: str | None = None,
    updated_at: str | None = None,
    stages_completed: list[str] | object = _UNSET,
    active_stage_id: str | None | object = _UNSET,
    pending_stage_ids: list[str] | object = _UNSET,
    pause_reason: str | None | object = _UNSET,
    wave_entry: dict | object = _UNSET,
    ledger_path: Path | None = None,
) -> tuple[bool, dict]:
    """Create or update a run entry.

    Returns (created, entry).
    """
    if status not in _STATUS_ENUM:
        raise ValueError(f"status {status!r} not in {sorted(_STATUS_ENUM)}")

    resolved_ledger_path = ledger_path or _ledger_path_from_root(root)
    data = (
        _load_ledger(resolved_ledger_path)
        if ledger_path is not None
        else _load_ledger_for_helpers(root)
    )
    if data is None:
        data = _load_ledger(resolved_ledger_path)

    runs = data.get("runs")
    if not isinstance(runs, list):
        runs = []
        data["runs"] = runs

    entry = next(
        (
            item
            for item in runs
            if isinstance(item, dict) and str(item.get("run_id") or "") == run_id
        ),
        None,
    )
    created = entry is None
    if entry is None:
        entry = {"run_id": run_id, "created_at": updated_at or utc_now_iso()}
        runs.append(entry)

    timestamp = updated_at or utc_now_iso()
    entry["run_id"] = run_id
    entry["mode"] = mode
    entry["goal"] = goal
    entry["status"] = status
    entry["updated_at"] = timestamp
    entry["next_action"] = next_action
    entry.setdefault("created_at", timestamp)

    for field, value in (("session_id", session_id), ("backlog_id", backlog_id), ("ide", ide)):
        if value is not None:
            entry[field] = value

    if stages_completed is not _UNSET:
        if stages_completed:
            entry["stages_completed"] = list(stages_completed)
        else:
            entry.pop("stages_completed", None)

    if active_stage_id is not _UNSET:
        if active_stage_id:
            entry["active_stage_id"] = active_stage_id
        else:
            entry.pop("active_stage_id", None)

    if pending_stage_ids is not _UNSET:
        if pending_stage_ids:
            entry["pending_stage_ids"] = list(pending_stage_ids)
        else:
            entry.pop("pending_stage_ids", None)

    if pause_reason is not _UNSET:
        if pause_reason:
            entry["pause_reason"] = pause_reason
        else:
            entry.pop("pause_reason", None)

    if wave_entry is not _UNSET:
        if wave_entry is not None:
            entry.setdefault("waves", []).append(wave_entry)

    errors = validate_ledger(data)
    if errors:
        raise ValueError("; ".join(errors))

    _write_ledger(resolved_ledger_path, data)
    return created, entry


# ── Business-logic helpers (testable without CLI) ─────────────────────────────


def load_active_run(root: Path) -> dict | None:
    """Return the last active run entry from the ledger, or None if absent."""
    data = _load_ledger_for_helpers(root)
    if data is None:
        return None
    runs = data.get("runs")
    if not isinstance(runs, list):
        return None
    active = [r for r in runs if isinstance(r, dict) and r.get("status") == "active"]
    return active[-1] if active else None


def load_sessions(root: Path) -> list[dict]:
    """Return session registry entries from the ledger, newest first by updated_at."""
    data = _load_ledger_for_helpers(root)
    if data is None:
        return []
    sessions = data.get("sessions")
    if not isinstance(sessions, list):
        return []
    valid_sessions = [entry for entry in sessions if isinstance(entry, dict)]
    return sorted(valid_sessions, key=lambda entry: str(entry.get("updated_at", "")), reverse=True)


def load_session(root: Path, session_id: str) -> dict | None:
    """Return a single session registry entry by session_id, or None when absent."""
    for entry in load_sessions(root):
        if entry.get("session_id") == session_id:
            return entry
    return None


def load_open_sessions(root: Path) -> list[dict]:
    """Return active or parked sessions from the ledger, newest first."""
    return [entry for entry in load_sessions(root) if entry.get("status") in {"active", "parked"}]


# ── Subcommands ───────────────────────────────────────────────────────────────


def cmd_validate(args: argparse.Namespace) -> None:
    path: Path = args.ledger
    if not path.exists():
        print(f"no ledger file at {path}")
        sys.exit(0)
    data = _load_ledger(path)
    errors = validate_ledger(data)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    print("ledger OK")


def cmd_status(args: argparse.Namespace) -> None:
    path: Path = args.ledger
    if not path.exists():
        print("no active run")
        sys.exit(0)
    data = _load_ledger(path)
    runs = data.get("runs") or []
    active = [r for r in runs if isinstance(r, dict) and r.get("status") == "active"]
    if active:
        run = active[-1]
        run_id = run.get("run_id", "?")
        mode = run.get("mode", "?")
        next_action = (run.get("next_action") or "")[:80]
        print(f"Active run  {run_id}  ({mode})  → {next_action}")
        sc = run.get("stages_completed") or []
        if sc:
            print(f"  stages completed: {len(sc)}")
        active_stage_id = run.get("active_stage_id")
        if active_stage_id:
            print(f"  active stage: {active_stage_id}")
    else:
        print("no active run")
    # Write-claim info
    write_claim = data.get("write_claim")
    if isinstance(write_claim, dict):
        holder = write_claim.get("session_id", "?")
        expires = write_claim.get("expires_at", "?")
        print(f"Write claim: HELD by '{holder}'  expires {expires}")
    else:
        print("Write claim: none")


def cmd_claim(args: argparse.Namespace) -> None:
    path: Path = args.ledger
    root = _root_from_ledger_path(path)
    ok, info = acquire_write_claim(root, args.session_id, args.expires_at, harness=args.harness)
    if ok:
        print(f"write claim acquired: {info}")
    else:
        print(f"write claim denied: {info}", file=sys.stderr)
        sys.exit(1)


def cmd_release_claim(args: argparse.Namespace) -> None:
    path: Path = args.ledger
    root = _root_from_ledger_path(path)
    released = release_write_claim(root, args.session_id)
    if released:
        print(f"write claim released for session '{args.session_id}'")
    else:
        print(f"write claim not held by '{args.session_id}' — no-op", file=sys.stderr)
        sys.exit(1)


def cmd_resolve_stale(args: argparse.Namespace) -> None:
    path: Path = args.ledger
    root = _root_from_ledger_path(path)
    cleared = resolve_stale_claims(root)
    if cleared:
        print("stale write claim cleared")
    else:
        print("no stale claim found")


def cmd_park_session(args: argparse.Namespace) -> None:
    path: Path = args.ledger
    root = _root_from_ledger_path(path)
    created, entry = upsert_session(
        root,
        session_id=args.session_id,
        backlog_id=args.backlog_id,
        goal=args.goal,
        status="parked",
        ide=args.ide,
        next_action=args.next_action,
        updated_at=utc_now_iso(),
        active_run_id=args.active_run_id,
        ledger_path=path,
    )
    verb = "created" if created else "updated"
    print(f"session {entry['session_id']} {verb} as parked")


def cmd_append(args: argparse.Namespace) -> None:
    path: Path = args.ledger
    data = _load_ledger(path)
    root = _root_from_ledger_path(path)
    wave_entry: dict | None = None
    if args.wave:
        try:
            wave_entry = json.loads(args.wave)
        except json.JSONDecodeError as exc:
            _die(f"--wave is not valid JSON: {exc}")
        if not isinstance(wave_entry, dict):
            _die("--wave must be a JSON object")
    existing = next(
        (
            entry
            for entry in data.get("runs", [])
            if isinstance(entry, dict) and str(entry.get("run_id") or "") == args.run_id
        ),
        None,
    )
    stages_completed = _UNSET
    if args.stages_completed:
        merged_stages = (
            list(existing.get("stages_completed", []))
            if isinstance(existing, dict) and isinstance(existing.get("stages_completed"), list)
            else []
        )
        merged_stages.extend(args.stages_completed)
        stages_completed = merged_stages
    created, _ = upsert_run(
        root,
        run_id=args.run_id,
        session_id=args.session_id,
        backlog_id=args.backlog_id,
        ide=args.ide,
        mode=args.mode,
        goal=args.goal,
        status=args.status,
        next_action=args.next_action,
        updated_at=utc_now_iso(),
        stages_completed=stages_completed,
        active_stage_id=args.active_stage_id if args.active_stage_id is not None else _UNSET,
        pending_stage_ids=(
            args.pending_stage_ids if args.pending_stage_ids is not None else _UNSET
        ),
        pause_reason=args.pause_reason if args.pause_reason is not None else _UNSET,
        wave_entry=wave_entry if wave_entry is not None else _UNSET,
        ledger_path=path,
    )
    verb = "created" if created else "updated"
    print(f"run {args.run_id} {verb}")


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Azoth run ledger — durable state for long pipeline runs (P1-001).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=LEDGER_PATH,
        metavar="PATH",
        help=f"Path to ledger file (default: {LEDGER_PATH})",
    )
    subs = parser.add_subparsers(dest="command", required=True)

    subs.add_parser("validate", help="Validate ledger against schema; exit 1 on errors.")
    subs.add_parser("status", help="Print current active run summary and write-claim info.")

    # write-claim subcommands (P1-015)
    cp = subs.add_parser("claim", help="Acquire the write claim for a session.")
    cp.add_argument(
        "session_id", metavar="SESSION_ID", help="Session identifier acquiring the claim."
    )
    cp.add_argument("expires_at", metavar="EXPIRES_AT", help="ISO-8601 expiry timestamp.")
    cp.add_argument(
        "--harness", metavar="HARNESS", help="Optional IDE/harness label.", default=None
    )

    rp = subs.add_parser("release-claim", help="Release the write claim for a session.")
    rp.add_argument(
        "session_id", metavar="SESSION_ID", help="Session identifier releasing the claim."
    )

    subs.add_parser("resolve-stale", help="Clear an expired write claim (clock-only check).")

    ps = subs.add_parser(
        "park-session",
        help="Create or update a parked session registry entry.",
    )
    ps.add_argument("session_id", metavar="SESSION_ID", help="Session identifier to park.")
    ps.add_argument("backlog_id", metavar="BACKLOG_ID", help="Backlog identifier or AD-HOC.")
    ps.add_argument("--goal", required=True, metavar="GOAL", help="Human-readable session goal.")
    ps.add_argument("--ide", required=True, metavar="IDE", help="Harness or IDE label.")
    ps.add_argument(
        "--next-action",
        required=True,
        metavar="TEXT",
        help="Resume instruction shown by /resume.",
    )
    ps.add_argument(
        "--active-run-id",
        metavar="RUN_ID",
        default=None,
        help="Optional resumable run linked to the parked session.",
    )

    ap = subs.add_parser("append", help="Create or update a run entry.")
    ap.add_argument("--run-id", required=True, metavar="ID", help="Unique run identifier.")
    ap.add_argument("--session-id", metavar="SESSION_ID", help="Optional linked session id.")
    ap.add_argument("--backlog-id", metavar="BACKLOG_ID", help="Optional linked backlog id.")
    ap.add_argument("--ide", metavar="IDE", help="Optional IDE or client label.")
    ap.add_argument("--mode", required=True, metavar="MODE", help="Pipeline mode/preset.")
    ap.add_argument("--goal", required=True, metavar="GOAL", help="Human-readable goal.")
    ap.add_argument(
        "--status",
        required=True,
        choices=["active", "complete", "failed", "paused"],
        help="Run status.",
    )
    ap.add_argument("--next-action", required=True, metavar="TEXT", help="Resume instruction.")
    ap.add_argument(
        "--stage-completed",
        action="append",
        dest="stages_completed",
        default=[],
        metavar="STAGE",
        help="Stage name to append to stages_completed (repeatable).",
    )
    ap.add_argument(
        "--wave",
        metavar="JSON",
        help='Wave outcome as JSON object, e.g. \'{"wave": 1, "status": "pass"}\'.',
    )
    ap.add_argument(
        "--active-stage-id",
        metavar="STAGE_ID",
        default=None,
        help="Current stage identifier for a resumable checkpoint.",
    )
    ap.add_argument(
        "--pending-stage-id",
        action="append",
        dest="pending_stage_ids",
        default=None,
        metavar="STAGE_ID",
        help="Stage id to include in pending_stage_ids (repeatable).",
    )
    ap.add_argument(
        "--pause-reason",
        choices=sorted(_PAUSE_REASON_ENUM),
        default=None,
        help="Why the run is paused, when applicable.",
    )

    args = parser.parse_args()
    {
        "validate": cmd_validate,
        "status": cmd_status,
        "append": cmd_append,
        "claim": cmd_claim,
        "release-claim": cmd_release_claim,
        "resolve-stale": cmd_resolve_stale,
        "park-session": cmd_park_session,
    }[args.command](args)


if __name__ == "__main__":
    main()

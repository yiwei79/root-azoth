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
from contextlib import contextmanager
import errno
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from session_continuity import active_scope, session_registry_entry_is_resumable
from yaml_helpers import safe_load_yaml_path

try:
    import fcntl
except ImportError:  # pragma: no cover - fcntl is available on supported Unix hosts.
    fcntl = None

ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / ".azoth" / "run-ledger.local.yaml"

_STATUS_ENUM = {"active", "complete", "failed", "paused"}
_SESSION_STATUS_ENUM = {"active", "parked", "closed"}
_SESSION_MODE_ENUM = {"exploratory", "delivery"}
_WAVE_STATUS_ENUM = {"pass", "fail", "partial"}
_BRANCH_DISPOSITION_ENUM = {"merged", "discarded", "pending"}
_PAUSE_REASON_ENUM = {"human-gate", "handoff", "retry"}
_SUMMARY_STATUS_ENUM = {"complete", "blocked", "needs-input"}
_NONBLOCKING_SUMMARY_DISPOSITIONS = {
    "approved",
    "approve",
    "accepted",
    "complete",
    "pass",
    "passed",
    "no-changes",
}
_GOVERNED_RUN_MODES = {"auto", "autonomous-auto", "dynamic-full-auto", "deliver", "deliver-full"}
_ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_STAGE_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_UNSET = object()
_LEDGER_LOCK_TIMEOUT_SECONDS = 10.0
_LEDGER_LOCK_POLL_SECONDS = 0.05


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
        data = safe_load_yaml_path(path)
    except Exception as exc:
        _die(f"could not parse ledger YAML: {exc}")
    if not isinstance(data, dict):
        _die("ledger root is not a YAML mapping")
    return data


def _load_yaml_mapping(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = safe_load_yaml_path(path)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _write_yaml_mapping(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_path.replace(path)


def _write_ledger(path: Path, data: dict) -> None:
    _write_yaml_mapping(path, data)


def _ledger_lock_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.lock")


def _ledger_lock_failure_message(ledger_path: Path, lock_path: Path, exc: BaseException) -> str:
    return (
        f"could not acquire run ledger lock at {lock_path} for ledger {ledger_path}: {exc}. "
        "Retry after the current writer finishes, or serialize record-spawn/record-summary "
        "writers for this ledger."
    )


def _is_lock_contention_error(exc: OSError) -> bool:
    return isinstance(exc, BlockingIOError) or exc.errno in {errno.EACCES, errno.EAGAIN}


def _try_acquire_ledger_lock(lock_file: object) -> bool:
    if fcntl is None:
        raise OSError("fcntl file locking is unavailable on this platform")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as exc:
        if _is_lock_contention_error(exc):
            return False
        raise


def _acquire_ledger_lock(lock_file: object) -> None:
    deadline = time.monotonic() + _LEDGER_LOCK_TIMEOUT_SECONDS
    while True:
        if _try_acquire_ledger_lock(lock_file):
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"timed out after {_LEDGER_LOCK_TIMEOUT_SECONDS:.2f}s waiting for ledger lock"
            )
        time.sleep(_LEDGER_LOCK_POLL_SECONDS)


def _release_ledger_lock(lock_file: object) -> None:
    if fcntl is not None:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def _locked_ledger_update(ledger_path: Path):
    lock_path = _ledger_lock_path(ledger_path)
    lock_file = None
    acquired = False
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError(_ledger_lock_failure_message(ledger_path, lock_path, exc)) from exc
    try:
        lock_file = lock_path.open("a+", encoding="utf-8")
    except OSError as exc:
        raise ValueError(_ledger_lock_failure_message(ledger_path, lock_path, exc)) from exc
    try:
        try:
            _acquire_ledger_lock(lock_file)
            acquired = True
        except OSError as exc:
            message = _ledger_lock_failure_message(ledger_path, lock_path, exc)
            raise ValueError(message) from exc
        yield
    finally:
        try:
            if acquired:
                _release_ledger_lock(lock_file)
        finally:
            lock_file.close()


def _load_ledger_for_helpers(root: Path) -> dict | None:
    ledger_path = root / ".azoth" / "run-ledger.local.yaml"
    return _load_yaml_mapping(ledger_path)


def _load_optional_ledger_for_evidence(
    root: Path,
    ledger_path: Path | None = None,
) -> dict | None:
    resolved_ledger_path = ledger_path or _ledger_path_from_root(root)
    if not resolved_ledger_path.exists():
        return None
    try:
        data = safe_load_yaml_path(resolved_ledger_path)
    except Exception as exc:
        raise ValueError(
            f"could not read/parse ledger YAML at {resolved_ledger_path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"ledger root at {resolved_ledger_path} is not a YAML mapping")
    return data


def _require_valid_ledger_for_evidence(data: dict, *, ledger_path: Path) -> None:
    errors = validate_ledger(data)
    if errors:
        raise ValueError(
            f"malformed governed run evidence ledger at {ledger_path}: {'; '.join(errors)}"
        )


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

                session_mode = entry.get("session_mode")
                if session_mode is not None and session_mode not in _SESSION_MODE_ENUM:
                    errors.append(
                        f"{prefix}: session_mode {session_mode!r} not in {sorted(_SESSION_MODE_ENUM)}"
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
        if status in {"complete", "failed"}:
            stale_fields = [
                field
                for field in ("active_stage_id", "pending_stage_ids", "pause_reason")
                if field in entry
            ]
            if stale_fields:
                errors.append(
                    f"{prefix}: terminal status {status!r} must not keep resumable fields: "
                    f"{', '.join(stale_fields)}"
                )

        for field_name, timestamp_field, extra_required in (
            ("stage_spawns", "spawned_at", ()),
            (
                "stage_summaries",
                "summary_recorded_at",
                ("summary_status", "summary_disposition"),
            ),
        ):
            entries = entry.get(field_name)
            if entries is None:
                continue
            if not isinstance(entries, list):
                errors.append(f"{prefix}: {field_name} must be a list")
                continue
            for j, evidence in enumerate(entries):
                ep = f"{prefix}.{field_name}[{j}]"
                if not isinstance(evidence, dict):
                    errors.append(f"{ep} must be a mapping")
                    continue
                required_fields = (
                    "run_id",
                    "stage_id",
                    "subagent_type",
                    "trigger",
                    "role_hint",
                    "dependency_summary_refs",
                    timestamp_field,
                    *extra_required,
                )
                allowed_fields = set(required_fields)
                for evidence_field in evidence:
                    if evidence_field not in allowed_fields:
                        errors.append(f"{ep}: unexpected field '{evidence_field}'")
                for evidence_field in required_fields:
                    val = evidence.get(evidence_field)
                    if val is None:
                        errors.append(f"{ep}: missing required field '{evidence_field}'")
                    elif evidence_field == "dependency_summary_refs":
                        if not isinstance(val, list):
                            errors.append(f"{ep}: dependency_summary_refs must be a list")
                        else:
                            for k, ref in enumerate(val):
                                if not isinstance(ref, str) or not ref.strip():
                                    errors.append(
                                        f"{ep}.dependency_summary_refs[{k}] must be a non-empty string"
                                    )
                    elif not isinstance(val, str) or not val.strip():
                        errors.append(f"{ep}: '{evidence_field}' must be a non-empty string")

                evidence_run_id = evidence.get("run_id")
                if isinstance(evidence_run_id, str) and evidence_run_id != run_id:
                    errors.append(
                        f"{ep}: run_id {evidence_run_id!r} must match parent run_id {run_id!r}"
                    )

                evidence_stage_id = evidence.get("stage_id")
                if isinstance(evidence_stage_id, str) and evidence_stage_id.strip():
                    if not _STAGE_ID_RE.match(evidence_stage_id):
                        errors.append(
                            f"{ep}: stage_id must match stage id pattern, got {evidence_stage_id!r}"
                        )

                timestamp_value = evidence.get(timestamp_field)
                if timestamp_value is not None and (
                    not isinstance(timestamp_value, str) or not _ISO8601_RE.match(timestamp_value)
                ):
                    errors.append(
                        f"{ep}: '{timestamp_field}' must match ISO-8601 "
                        f"(YYYY-MM-DDTHH:MM:SS…), got {timestamp_value!r}"
                    )

                summary_status = evidence.get("summary_status")
                if summary_status is not None and summary_status not in _SUMMARY_STATUS_ENUM:
                    errors.append(
                        f"{ep}: summary_status {summary_status!r} not in "
                        f"{sorted(_SUMMARY_STATUS_ENUM)}"
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
            for optional_field in ("worktree_path", "branch", "git_common_dir", "harness"):
                optional_val = write_claim.get(optional_field)
                if optional_val is not None and (
                    not isinstance(optional_val, str) or not optional_val.strip()
                ):
                    errors.append(
                        f"write_claim: '{optional_field}' must be a non-empty string when present"
                    )

    return errors


# ── Write-claim helpers (P1-015) ──────────────────────────────────────────────


def _ledger_path_from_root(root: Path) -> Path:
    return root / ".azoth" / "run-ledger.local.yaml"


def _root_from_ledger_path(path: Path) -> Path:
    if path.parent.name == ".azoth":
        return path.parent.parent
    return path.parent


def _resolve_git_common_dir(root: Path) -> Path | None:
    env_override = os.environ.get("AZOTH_GIT_COMMON_DIR")
    if env_override:
        return Path(env_override).expanduser().resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None
    if result is None:
        return None
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (root / path).resolve()
    return path.resolve()


def _current_branch(root: Path) -> str | None:
    env_override = os.environ.get("AZOTH_GIT_BRANCH")
    if env_override:
        return env_override.strip() or None
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None
    if result is None:
        return None
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch or None


def shared_write_claim_path(root: Path) -> Path | None:
    explicit_path = os.environ.get("AZOTH_SHARED_WRITE_CLAIM_PATH")
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()

    common_dir = _resolve_git_common_dir(root)
    if common_dir is None:
        return None

    digest = hashlib.sha1(str(common_dir).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / "azoth-write-claims" / f"{digest}.yaml"


def _load_shared_write_claim(root: Path) -> dict | None:
    claim_path = shared_write_claim_path(root)
    if claim_path is None:
        return None
    return _load_yaml_mapping(claim_path)


def _write_shared_write_claim(root: Path, claim: dict) -> None:
    claim_path = shared_write_claim_path(root)
    if claim_path is None:
        return
    _write_yaml_mapping(claim_path, claim)


def _clear_shared_write_claim(root: Path) -> bool:
    claim_path = shared_write_claim_path(root)
    if claim_path is None or not claim_path.exists():
        return False
    claim_path.unlink()
    return True


def _write_local_claim_mirror(root: Path, claim: dict | None) -> None:
    ledger_path = _ledger_path_from_root(root)
    data = _load_ledger_for_helpers(root)
    if data is None:
        data = {"schema_version": 1, "runs": []}
    if claim is None:
        data.pop("write_claim", None)
    else:
        data["write_claim"] = claim
    _write_ledger(ledger_path, data)


def _parse_claim_expiry(raw_expiry: str) -> datetime | None:
    try:
        normalized = raw_expiry.replace("Z", "+00:00") if raw_expiry.endswith("Z") else raw_expiry
        exp_dt = datetime.fromisoformat(normalized)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        return exp_dt
    except (ValueError, TypeError):
        return None


def _build_write_claim(
    root: Path,
    *,
    session_id: str,
    expires_at: str,
    harness: str | None,
) -> dict:
    claim: dict[str, str] = {
        "session_id": session_id,
        "expires_at": expires_at,
        "acquired_at": utc_now_iso(),
        "worktree_path": str(root.resolve()),
    }
    if harness is not None:
        claim["harness"] = harness
    branch = _current_branch(root)
    if branch:
        claim["branch"] = branch
    common_dir = _resolve_git_common_dir(root)
    if common_dir is not None:
        claim["git_common_dir"] = str(common_dir)
    return claim


def load_write_claim(root: Path) -> dict | None:
    """Return the write_claim dict from the ledger, or None if absent."""
    shared_claim = _load_shared_write_claim(root)
    if shared_write_claim_path(root) is not None:
        return shared_claim if isinstance(shared_claim, dict) else None

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
    current_worktree = str(root.resolve())
    existing = load_write_claim(root)
    if isinstance(existing, dict):
        holder = existing.get("session_id", "")
        if holder == session_id:
            recorded_worktree = str(existing.get("worktree_path") or "").strip()
            raw_exp = str(existing.get("expires_at") or "")
            exp_dt = _parse_claim_expiry(raw_exp)
            if recorded_worktree and recorded_worktree != current_worktree:
                if exp_dt is not None and datetime.now(timezone.utc) < exp_dt:
                    return (
                        False,
                        "write claim already held by this session from another worktree "
                        f"({recorded_worktree}) until {raw_exp}; release it there first",
                    )
            else:
                new_claim = _build_write_claim(
                    root,
                    session_id=session_id,
                    expires_at=expires_at,
                    harness=harness,
                )
                if shared_write_claim_path(root) is not None:
                    _write_shared_write_claim(root, new_claim)
                _write_local_claim_mirror(root, new_claim)
                return True, session_id

        raw_exp = str(existing.get("expires_at") or "")
        exp_dt = _parse_claim_expiry(raw_exp)
        if exp_dt is not None and datetime.now(timezone.utc) < exp_dt:
            holder_worktree = str(existing.get("worktree_path") or "").strip()
            location = f" at {holder_worktree}" if holder_worktree else ""
            return False, f"write claim held by '{holder}'{location} until {raw_exp}"

    new_claim = _build_write_claim(
        root,
        session_id=session_id,
        expires_at=expires_at,
        harness=harness,
    )
    if shared_write_claim_path(root) is not None:
        _write_shared_write_claim(root, new_claim)
    _write_local_claim_mirror(root, new_claim)
    return True, session_id


def release_write_claim(root: Path, session_id: str) -> bool:
    """Release the write claim if the caller is the owner.

    Returns True when the claim was owned by session_id and has been removed.
    Returns False (no-op) when no claim exists or the caller is not the owner.
    """
    existing = load_write_claim(root)
    if not isinstance(existing, dict):
        return False
    if existing.get("session_id") != session_id:
        return False
    if shared_write_claim_path(root) is not None:
        _clear_shared_write_claim(root)
    _write_local_claim_mirror(root, None)
    return True


def resolve_stale_claims(root: Path) -> bool:
    """Check the write claim against the clock; clear it if expired.

    Returns True when a stale claim was found and cleared.
    Returns False when no claim exists or the claim is unexpired.
    Clock-only check — no external bypass signal (ADV-2).
    """
    existing = load_write_claim(root)
    if not isinstance(existing, dict):
        return False
    raw_exp = str(existing.get("expires_at") or "")
    exp_dt = _parse_claim_expiry(raw_exp)
    if exp_dt is None or datetime.now(timezone.utc) >= exp_dt:
        if shared_write_claim_path(root) is not None:
            _clear_shared_write_claim(root)
        _write_local_claim_mirror(root, None)
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
    session_mode: str | None = "delivery",
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
    if session_mode is not None:
        if session_mode not in _SESSION_MODE_ENUM:
            raise ValueError(f"session_mode {session_mode!r} not in {sorted(_SESSION_MODE_ENUM)}")
        entry["session_mode"] = session_mode

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


def load_run(root: Path, run_id: str, *, ledger_path: Path | None = None) -> dict | None:
    """Return a single run entry by run_id, or None when absent."""
    resolved_ledger_path = ledger_path or _ledger_path_from_root(root)
    data = (
        _load_ledger(resolved_ledger_path)
        if ledger_path is not None
        else _load_ledger_for_helpers(root)
    )
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

    if status in {"complete", "failed"}:
        entry.pop("active_stage_id", None)
        entry.pop("pending_stage_ids", None)
        entry.pop("pause_reason", None)

    if wave_entry is not _UNSET:
        if wave_entry is not None:
            entry.setdefault("waves", []).append(wave_entry)

    errors = validate_ledger(data)
    if errors:
        raise ValueError("; ".join(errors))

    _write_ledger(resolved_ledger_path, data)
    return created, entry


def _require_run_entry(root: Path, run_id: str, *, ledger_path: Path | None) -> tuple[Path, dict, dict]:
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
        raise ValueError("ledger runs must be a list")
    for entry in runs:
        if isinstance(entry, dict) and str(entry.get("run_id") or "") == run_id:
            return resolved_ledger_path, data, entry
    raise ValueError(f"run {run_id!r} not found")


def _stage_evidence_entry(
    *,
    run_id: str,
    stage_id: str,
    subagent_type: str,
    trigger: str,
    role_hint: str,
    dependency_summary_refs: list[str] | None,
    timestamp_field: str,
    timestamp: str,
    summary_status: str | None = None,
    summary_disposition: str | None = None,
) -> dict:
    entry = {
        "run_id": run_id,
        "stage_id": stage_id,
        "subagent_type": subagent_type,
        "trigger": trigger,
        "role_hint": role_hint,
        "dependency_summary_refs": list(dependency_summary_refs or []),
        timestamp_field: timestamp,
    }
    if summary_status is not None:
        entry["summary_status"] = summary_status
    if summary_disposition is not None:
        entry["summary_disposition"] = summary_disposition
    return entry


def record_stage_spawn(
    root: Path,
    *,
    run_id: str,
    stage_id: str,
    subagent_type: str,
    trigger: str,
    role_hint: str,
    dependency_summary_refs: list[str] | None = None,
    spawned_at: str | None = None,
    ledger_path: Path | None = None,
) -> dict:
    """Append durable evidence that a pipeline stage was delegated."""
    resolved_ledger_path = ledger_path or _ledger_path_from_root(root)
    with _locked_ledger_update(resolved_ledger_path):
        resolved_ledger_path, data, run = _require_run_entry(
            root,
            run_id,
            ledger_path=resolved_ledger_path,
        )
        evidence = _stage_evidence_entry(
            run_id=run_id,
            stage_id=stage_id,
            subagent_type=subagent_type,
            trigger=trigger,
            role_hint=role_hint,
            dependency_summary_refs=dependency_summary_refs,
            timestamp_field="spawned_at",
            timestamp=spawned_at or utc_now_iso(),
        )
        run.setdefault("stage_spawns", []).append(evidence)
        run["updated_at"] = utc_now_iso()
        errors = validate_ledger(data)
        if errors:
            raise ValueError("; ".join(errors))
        _write_ledger(resolved_ledger_path, data)
        return evidence


def record_stage_summary(
    root: Path,
    *,
    run_id: str,
    stage_id: str,
    subagent_type: str,
    trigger: str,
    role_hint: str,
    dependency_summary_refs: list[str] | None = None,
    summary_status: str,
    summary_disposition: str,
    summary_recorded_at: str | None = None,
    ledger_path: Path | None = None,
) -> dict:
    """Append durable evidence that a delegated stage returned a typed summary."""
    resolved_ledger_path = ledger_path or _ledger_path_from_root(root)
    with _locked_ledger_update(resolved_ledger_path):
        resolved_ledger_path, data, run = _require_run_entry(
            root,
            run_id,
            ledger_path=resolved_ledger_path,
        )
        evidence = _stage_evidence_entry(
            run_id=run_id,
            stage_id=stage_id,
            subagent_type=subagent_type,
            trigger=trigger,
            role_hint=role_hint,
            dependency_summary_refs=dependency_summary_refs,
            timestamp_field="summary_recorded_at",
            timestamp=summary_recorded_at or utc_now_iso(),
            summary_status=summary_status,
            summary_disposition=summary_disposition,
        )
        run.setdefault("stage_summaries", []).append(evidence)
        run["updated_at"] = utc_now_iso()
        errors = validate_ledger(data)
        if errors:
            raise ValueError("; ".join(errors))
        _write_ledger(resolved_ledger_path, data)
        return evidence


def _latest_stage_evidence(run: dict, field_name: str, *, stage_id: str) -> dict | None:
    entries = run.get(field_name)
    if not isinstance(entries, list):
        return None
    for entry in reversed(entries):
        if isinstance(entry, dict) and str(entry.get("stage_id") or "") == stage_id:
            return entry
    return None


def _normalize_dependency_refs(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _parse_ledger_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _assert_field_match(
    evidence: dict,
    *,
    field_name: str,
    expected: str | list[str] | None,
    evidence_label: str,
) -> None:
    if expected is None:
        return
    actual = (
        _normalize_dependency_refs(evidence.get(field_name))
        if field_name == "dependency_summary_refs"
        else str(evidence.get(field_name) or "")
    )
    if actual != expected:
        raise ValueError(
            f"{evidence_label} {field_name} mismatch: expected {expected!r}, got {actual!r}"
        )


def require_stage_evidence(
    root: Path,
    *,
    run_id: str,
    stage_id: str,
    subagent_type: str | None = None,
    trigger: str | None = None,
    role_hint: str | None = None,
    dependency_summary_refs: list[str] | None = None,
    ledger_path: Path | None = None,
) -> dict[str, dict]:
    """Return latest paired spawn/summary evidence, or fail closed with context."""
    resolved_ledger_path, data, run = _require_run_entry(root, run_id, ledger_path=ledger_path)
    _require_valid_ledger_for_evidence(data, ledger_path=resolved_ledger_path)
    spawn = _latest_stage_evidence(run, "stage_spawns", stage_id=stage_id)
    if spawn is None:
        raise ValueError(f"missing stage spawn evidence for run {run_id!r} stage {stage_id!r}")
    summary = _latest_stage_evidence(run, "stage_summaries", stage_id=stage_id)
    if summary is None:
        raise ValueError(f"missing stage summary evidence for run {run_id!r} stage {stage_id!r}")

    spawn_dt = _parse_ledger_timestamp(spawn.get("spawned_at"))
    summary_dt = _parse_ledger_timestamp(summary.get("summary_recorded_at"))
    if spawn_dt is None or summary_dt is None:
        raise ValueError(
            f"malformed stage evidence timestamp for run {run_id!r} stage {stage_id!r}"
        )
    if summary_dt < spawn_dt:
        raise ValueError(
            f"stage summary is older than latest spawn for run {run_id!r} stage {stage_id!r}"
        )

    for field_name in ("subagent_type", "trigger", "role_hint", "dependency_summary_refs"):
        spawn_value = (
            _normalize_dependency_refs(spawn.get(field_name))
            if field_name == "dependency_summary_refs"
            else str(spawn.get(field_name) or "")
        )
        summary_value = (
            _normalize_dependency_refs(summary.get(field_name))
            if field_name == "dependency_summary_refs"
            else str(summary.get(field_name) or "")
        )
        if summary_value != spawn_value:
            raise ValueError(
                f"stage summary does not match latest spawn for run {run_id!r} "
                f"stage {stage_id!r}: {field_name}"
            )

    expected_dependency_refs = (
        list(dependency_summary_refs) if dependency_summary_refs is not None else None
    )
    for evidence, label in ((spawn, "stage spawn"), (summary, "stage summary")):
        _assert_field_match(
            evidence,
            field_name="subagent_type",
            expected=subagent_type,
            evidence_label=label,
        )
        _assert_field_match(
            evidence,
            field_name="trigger",
            expected=trigger,
            evidence_label=label,
        )
        _assert_field_match(
            evidence,
            field_name="role_hint",
            expected=role_hint,
            evidence_label=label,
        )
        _assert_field_match(
            evidence,
            field_name="dependency_summary_refs",
            expected=expected_dependency_refs,
            evidence_label=label,
        )

    summary_status = str(summary.get("summary_status") or "")
    summary_disposition = str(summary.get("summary_disposition") or "")
    if summary_status != "complete" or summary_disposition not in _NONBLOCKING_SUMMARY_DISPOSITIONS:
        raise ValueError(
            f"blocking stage summary for run {run_id!r} stage {stage_id!r}: "
            f"status={summary_status!r}, disposition={summary_disposition!r}"
        )
    return {"spawn": spawn, "summary": summary}


def assert_no_unresolved_governed_run_evidence(
    root: Path,
    *,
    session_id: str,
    governed_modes: set[str] | None = None,
    ledger_path: Path | None = None,
) -> None:
    """Fail closed if a matching live/paused governed run has unresolved stage evidence."""
    resolved_ledger_path = ledger_path or _ledger_path_from_root(root)
    data = _load_optional_ledger_for_evidence(root, resolved_ledger_path)
    if data is None:
        return
    _require_valid_ledger_for_evidence(data, ledger_path=resolved_ledger_path)
    modes = governed_modes or _GOVERNED_RUN_MODES
    runs = data.get("runs")
    if not isinstance(runs, list):
        raise ValueError("malformed governed run ledger: runs must be a list")
    for run in runs:
        if not isinstance(run, dict):
            continue
        if str(run.get("session_id") or "") != session_id:
            continue
        if str(run.get("status") or "") not in {"active", "paused"}:
            continue
        if str(run.get("mode") or "") not in modes:
            continue
        spawns = run.get("stage_spawns")
        run_id = str(run.get("run_id") or "")
        if not isinstance(spawns, list):
            if "stage_spawns" in run:
                raise ValueError(
                    "malformed governed run evidence for "
                    f"session {session_id!r}, run {run_id!r}: stage_spawns must be a list"
                )
            continue
        for index, spawn in enumerate(spawns):
            if not isinstance(spawn, dict):
                raise ValueError(
                    "malformed governed run evidence for "
                    f"session {session_id!r}, run {run_id!r}: "
                    f"stage_spawns[{index}] must be a mapping"
                )
            stage_id = str(spawn.get("stage_id") or "").strip()
            if not stage_id:
                raise ValueError(
                    f"unresolved governed run evidence for run {run_id!r}: missing stage_id"
                )
            try:
                require_stage_evidence(
                    root,
                    run_id=run_id,
                    stage_id=stage_id,
                    ledger_path=resolved_ledger_path,
                )
            except ValueError as exc:
                raise ValueError(
                    "unresolved governed run evidence for "
                    f"session {session_id!r}, run {run_id!r}, stage {stage_id!r}: {exc}"
                ) from exc


def consume_human_gate_approval(
    root: Path,
    *,
    run_id: str,
    next_action: str | None = None,
    ledger_path: Path | None = None,
) -> dict:
    """Advance a paused human-gate run to its next executable stage.

    This is the shared fail-closed runtime transition for governed approval
    consumption. It only succeeds when the targeted run is paused specifically at
    a human gate and still has a pending executable stage to promote.
    """
    resolved_ledger_path = ledger_path or _ledger_path_from_root(root)
    entry = load_run(root, run_id, ledger_path=resolved_ledger_path)
    if entry is None:
        raise ValueError(f"run {run_id!r} not found")

    if entry.get("status") != "paused":
        raise ValueError("approval consumption requires a paused run")
    if entry.get("pause_reason") != "human-gate":
        raise ValueError("approval consumption requires pause_reason='human-gate'")

    prior_stage_id = str(entry.get("active_stage_id") or "").strip()
    if not prior_stage_id:
        raise ValueError("approval consumption requires active_stage_id")

    pending_stage_ids = entry.get("pending_stage_ids")
    if not isinstance(pending_stage_ids, list) or not pending_stage_ids:
        raise ValueError("approval consumption requires a non-empty pending_stage_ids list")

    next_stage_id = str(pending_stage_ids[0] or "").strip()
    if not next_stage_id:
        raise ValueError("approval consumption requires the next pending stage id")

    stages_completed = list(entry.get("stages_completed") or [])
    if prior_stage_id not in stages_completed:
        stages_completed.append(prior_stage_id)

    promoted_next_action = (
        next_action
        or f"Execute next executable stage `{next_stage_id}` in pipeline "
        f"`{entry.get('mode', 'unknown')}`."
    )

    _, updated_entry = upsert_run(
        root,
        run_id=run_id,
        mode=str(entry.get("mode") or ""),
        goal=str(entry.get("goal") or ""),
        status="active",
        next_action=promoted_next_action,
        session_id=str(entry.get("session_id") or "") or None,
        backlog_id=str(entry.get("backlog_id") or "") or None,
        ide=str(entry.get("ide") or "") or None,
        updated_at=utc_now_iso(),
        stages_completed=stages_completed,
        active_stage_id=next_stage_id,
        pending_stage_ids=pending_stage_ids[1:],
        pause_reason=None,
        ledger_path=resolved_ledger_path,
    )
    return updated_entry


def rewrite_request_changes_replay(
    root: Path,
    *,
    run_id: str,
    finding_class: str | None = None,
    threshold_limit: int | None = None,
    next_action: str | None = None,
    ledger_path: Path | None = None,
) -> dict:
    """Requeue the last completed upstream stage ahead of the active review stage.

    This is the fail-closed runtime transition for reviewer/evaluator
    `request-changes` dispositions. It uses only current run-ledger lineage:
    `stages_completed[-1]`, `active_stage_id`, and `pending_stage_ids`.
    """
    resolved_ledger_path = ledger_path or _ledger_path_from_root(root)
    entry = load_run(root, run_id, ledger_path=resolved_ledger_path)
    if entry is None:
        raise ValueError(f"run {run_id!r} not found")

    current_stage_id = str(entry.get("active_stage_id") or "").strip()
    if not current_stage_id:
        raise ValueError("request-changes replay requires active_stage_id")

    stages_completed = list(entry.get("stages_completed") or [])
    if not stages_completed:
        raise ValueError("request-changes replay requires lineage proof from stages_completed")

    revision_stage_id = _resolve_replay_target_stage(
        stages_completed,
        current_stage_id=current_stage_id,
        finding_class=finding_class,
    )
    if revision_stage_id == current_stage_id:
        raise ValueError(
            "unsupported request-changes replay shape: revision stage matches active stage"
        )
    effective_threshold = threshold_limit or _default_replay_threshold(entry)
    replay_iteration = sum(1 for stage_id in stages_completed if stage_id == revision_stage_id) + 1
    if replay_iteration > effective_threshold:
        raise ValueError(
            "request-changes replay threshold exhausted; recompose scope or escalate to human"
        )

    pending_stage_ids = list(entry.get("pending_stage_ids") or [])
    if not pending_stage_ids:
        raise ValueError("unsupported request-changes replay shape: no downstream stages to replay")

    already_rewritten = (
        len(pending_stage_ids) >= 2
        and pending_stage_ids[0] == revision_stage_id
        and pending_stage_ids[1] == current_stage_id
        and entry.get("pause_reason") == "human-gate"
    )
    if already_rewritten:
        raise ValueError("request-changes replay already rewritten for this run")

    if revision_stage_id in pending_stage_ids or current_stage_id in pending_stage_ids:
        raise ValueError(
            "unsupported request-changes replay shape: queue already contains replay stages"
        )

    finding_suffix = f" after `{finding_class}` findings" if finding_class else ""
    replay_next_action = (
        next_action
        or f"Resume at human gate for stage `{current_stage_id}` in pipeline "
        f"`{entry.get('mode', 'unknown')}`; approval replays `{revision_stage_id}`"
        f"{finding_suffix} (iteration {replay_iteration}/{effective_threshold})."
    )

    _, updated_entry = upsert_run(
        root,
        run_id=run_id,
        mode=str(entry.get("mode") or ""),
        goal=str(entry.get("goal") or ""),
        status="paused",
        next_action=replay_next_action,
        session_id=str(entry.get("session_id") or "") or None,
        backlog_id=str(entry.get("backlog_id") or "") or None,
        ide=str(entry.get("ide") or "") or None,
        updated_at=utc_now_iso(),
        stages_completed=stages_completed,
        active_stage_id=current_stage_id,
        pending_stage_ids=[revision_stage_id, current_stage_id, *pending_stage_ids],
        pause_reason="human-gate",
        ledger_path=resolved_ledger_path,
    )
    return updated_entry


def _default_replay_threshold(entry: dict) -> int:
    return 3 if str(entry.get("mode") or "").strip() == "deliver-full" else 2


def _resolve_replay_target_stage(
    stages_completed: list[str],
    *,
    current_stage_id: str,
    finding_class: str | None,
) -> str:
    if not stages_completed:
        raise ValueError("request-changes replay requires lineage proof from stages_completed")

    if not finding_class:
        revision_stage_id = str(stages_completed[-1] or "").strip()
        if not revision_stage_id:
            raise ValueError("request-changes replay requires lineage proof from stages_completed")
        return revision_stage_id

    normalized = finding_class.strip().lower()
    if normalized in {"architecture", "scope", "governance", "contract"}:
        tokens = ("architect",)
    elif normalized in {"planning", "test-strategy", "handoff-completeness"}:
        tokens = ("planner",)
    elif normalized in {"implementation", "failing-acceptance"}:
        tokens = ("builder",)
    elif normalized == "evidence-insufficient":
        tokens = ("discovery", "research", "architect", "planner")
    else:
        raise ValueError(f"unsupported finding_class for replay routing: {finding_class!r}")

    for stage_id in reversed(stages_completed):
        candidate = str(stage_id or "").strip()
        if (
            candidate
            and candidate != current_stage_id
            and any(token in candidate for token in tokens)
        ):
            return candidate

    raise ValueError(
        "request-changes replay requires lineage proof for the requested finding class"
    )


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


def load_resumable_sessions(root: Path) -> list[dict]:
    """Return only sessions backed by a real resume signal, newest first."""
    scope = active_scope(root)
    return [
        entry
        for entry in load_open_sessions(root)
        if session_registry_entry_is_resumable(root, entry, scope=scope)
    ]


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
    write_claim = load_write_claim(_root_from_ledger_path(path))
    claim_scope = (
        "shared" if shared_write_claim_path(_root_from_ledger_path(path)) is not None else "local"
    )
    if isinstance(write_claim, dict):
        holder = write_claim.get("session_id", "?")
        expires = write_claim.get("expires_at", "?")
        print(f"Write claim ({claim_scope}): HELD by '{holder}'  expires {expires}")
        worktree_path = write_claim.get("worktree_path")
        if worktree_path:
            print(f"  worktree: {worktree_path}")
        branch = write_claim.get("branch")
        if branch:
            print(f"  branch: {branch}")
    else:
        print(f"Write claim ({claim_scope}): none")


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


def cmd_record_spawn(args: argparse.Namespace) -> None:
    root = _root_from_ledger_path(args.ledger)
    evidence = record_stage_spawn(
        root,
        run_id=args.run_id,
        stage_id=args.stage_id,
        subagent_type=args.subagent_type,
        trigger=args.trigger,
        role_hint=args.role_hint,
        dependency_summary_refs=args.dependency_summary_refs,
        ledger_path=args.ledger,
    )
    print(f"stage spawn recorded: {evidence['run_id']} {evidence['stage_id']}")


def cmd_record_summary(args: argparse.Namespace) -> None:
    root = _root_from_ledger_path(args.ledger)
    evidence = record_stage_summary(
        root,
        run_id=args.run_id,
        stage_id=args.stage_id,
        subagent_type=args.subagent_type,
        trigger=args.trigger,
        role_hint=args.role_hint,
        dependency_summary_refs=args.dependency_summary_refs,
        summary_status=args.summary_status,
        summary_disposition=args.summary_disposition,
        ledger_path=args.ledger,
    )
    print(f"stage summary recorded: {evidence['run_id']} {evidence['stage_id']}")


def cmd_require_stage_evidence(args: argparse.Namespace) -> None:
    root = _root_from_ledger_path(args.ledger)
    try:
        require_stage_evidence(
            root,
            run_id=args.run_id,
            stage_id=args.stage_id,
            subagent_type=args.subagent_type,
            trigger=args.trigger,
            role_hint=args.role_hint,
            dependency_summary_refs=args.dependency_summary_refs,
            ledger_path=args.ledger,
        )
    except ValueError as exc:
        print(f"stage evidence blocked: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"stage evidence OK: {args.run_id} {args.stage_id}")


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

    rsp = subs.add_parser("record-spawn", help="Append subagent stage-spawn evidence.")
    rsp.add_argument("--run-id", required=True, metavar="ID", help="Run identifier.")
    rsp.add_argument("--stage-id", required=True, metavar="STAGE_ID", help="Delegated stage id.")
    rsp.add_argument(
        "--subagent-type", required=True, metavar="TYPE", help="Spawned subagent type."
    )
    rsp.add_argument("--trigger", required=True, metavar="TRIGGER", help="Isolation trigger.")
    rsp.add_argument("--role-hint", required=True, metavar="TEXT", help="Canonical role hint.")
    rsp.add_argument(
        "--dependency-summary-ref",
        action="append",
        dest="dependency_summary_refs",
        default=[],
        metavar="STAGE_ID",
        help="Required upstream stage-summary ref (repeatable).",
    )

    rsu = subs.add_parser("record-summary", help="Append typed stage-summary evidence.")
    rsu.add_argument("--run-id", required=True, metavar="ID", help="Run identifier.")
    rsu.add_argument("--stage-id", required=True, metavar="STAGE_ID", help="Completed stage id.")
    rsu.add_argument(
        "--subagent-type", required=True, metavar="TYPE", help="Stage subagent type."
    )
    rsu.add_argument("--trigger", required=True, metavar="TRIGGER", help="Isolation trigger.")
    rsu.add_argument("--role-hint", required=True, metavar="TEXT", help="Canonical role hint.")
    rsu.add_argument(
        "--dependency-summary-ref",
        action="append",
        dest="dependency_summary_refs",
        default=[],
        metavar="STAGE_ID",
        help="Required upstream stage-summary ref (repeatable).",
    )
    rsu.add_argument(
        "--summary-status",
        required=True,
        choices=sorted(_SUMMARY_STATUS_ENUM),
        help="Typed stage summary status.",
    )
    rsu.add_argument(
        "--summary-disposition",
        required=True,
        metavar="DISPOSITION",
        help="Stage summary disposition, e.g. approved or request-changes.",
    )

    rse = subs.add_parser(
        "require-stage-evidence",
        help="Fail closed unless latest spawn and summary evidence are paired.",
    )
    rse.add_argument("--run-id", required=True, metavar="ID", help="Run identifier.")
    rse.add_argument("--stage-id", required=True, metavar="STAGE_ID", help="Stage id.")
    rse.add_argument("--subagent-type", metavar="TYPE", help="Expected subagent type.")
    rse.add_argument("--trigger", metavar="TRIGGER", help="Expected isolation trigger.")
    rse.add_argument("--role-hint", metavar="TEXT", help="Expected canonical role hint.")
    rse.add_argument(
        "--dependency-summary-ref",
        action="append",
        dest="dependency_summary_refs",
        default=None,
        metavar="STAGE_ID",
        help="Expected upstream stage-summary ref (repeatable).",
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
        "record-spawn": cmd_record_spawn,
        "record-summary": cmd_record_summary,
        "require-stage-evidence": cmd_require_stage_evidence,
    }[args.command](args)


if __name__ == "__main__":
    main()

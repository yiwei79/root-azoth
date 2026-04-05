from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "scope-gate.py"


def _run(tool_name: str, gate_path: Path, file_path: str | None = None) -> dict:
    tool_input: dict = {}
    if file_path is not None:
        tool_input["file_path"] = file_path
    stdin_payload = json.dumps(
        {
            "tool_name": tool_name,
            "hook_event_name": "PreToolUse",
            "tool_input": tool_input,
        }
    )
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    result = subprocess.run(
        ["python3", str(HOOK_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    return json.loads(result.stdout)


def _decision(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecision"]


def _reason(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecisionReason"]


def _future_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def _past_expiry() -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()


# T1: non-write/edit tool with absent gate file — must allow
def test_t1_non_write_tool_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Read", gate_path)
    assert _decision(output) == "allow"


# T2: Write with absent gate file — must deny with scope-gate message
def test_t2_write_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


# T3: Edit with absent gate file — must deny with scope-gate message
def test_t3_edit_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Edit", gate_path)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


# T4: Write, approved=false, future expiry — must deny
def test_t4_write_approved_false(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": False, "expires_at": _future_expiry()}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


# T5: Write, approved=true, expired — must deny
def test_t5_write_approved_expired(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": _past_expiry()}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


# T6: Write, approved=true, 1hr future expiry — must allow
def test_t6_write_approved_valid(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": _future_expiry()}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "allow"


# T7: Write, malformed JSON gate file — must deny with "malformed"
def test_t7_write_malformed_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text("this is not json {{{", encoding="utf-8")
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "malformed" in _reason(output)


# T8: Write, approved=true, expires_at is not a valid date — must deny
def test_t8_write_invalid_expires_at(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": "not-a-date"}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "deny"
    assert "invalid ISO 8601" in _reason(output)


# T9: Write, approved=true, future naive expires_at (no tz) — hook normalizes to UTC, must allow
def test_t9_write_naive_future_expires_at(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": "2099-12-31T23:59:59"}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "allow"


# T10: Write, approved=true, future expires_at with Z suffix — must allow
def test_t10_write_z_suffix_future_expires_at(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    gate_path.write_text(
        json.dumps({"approved": True, "expires_at": "2099-12-31T23:59:59Z"}),
        encoding="utf-8",
    )
    output = _run("Write", gate_path)
    assert _decision(output) == "allow"


# T11: Write with file_path == gate_path, gate absent — must allow (bootstrap exception)
def test_t11_write_to_gate_path_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Write", gate_path, file_path=str(gate_path))
    assert _decision(output) == "allow"


# T12: Edit with file_path == gate_path, gate absent — must allow (bootstrap exception)
def test_t12_edit_to_gate_path_gate_absent(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    output = _run("Edit", gate_path, file_path=str(gate_path))
    assert _decision(output) == "allow"

"""P5-002: entropy-check PreToolUse orchestrator (TRUST_CONTRACT §1)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ORCHESTRATOR = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "edit_pretooluse_orchestrator.py"
)
_HOOKS = Path(__file__).resolve().parent.parent / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from entropy_check import (  # noqa: E402
    PLACEHOLDER_LINES,
    estimate_lines_changed,
)
from entropy_state import EntropyState, reset_if_session_changed  # noqa: E402


def _future_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def _run_orchestrator(
    stdin_payload: str,
    *,
    gate_path: Path,
    pipeline_gate_path: Path | None = None,
) -> dict:
    workspace = gate_path.parent
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    if pipeline_gate_path is not None:
        env["AZOTH_PIPELINE_GATE_PATH"] = str(pipeline_gate_path)
    result = subprocess.run(
        ["python3", str(_ORCHESTRATOR)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _decision(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecision"]


def _reason(output: dict) -> str:
    return output["hookSpecificOutput"]["permissionDecisionReason"]


def test_a1_malformed_stdin_allow(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    workspace = gate_path.parent
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    result = subprocess.run(
        ["python3", str(_ORCHESTRATOR)],
        input="not valid json {{{",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert _decision(out) == "allow"


def test_a2_scope_deny_before_entropy_no_state_file(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    est_path = tmp_path / "entropy-state.json"
    assert not est_path.exists()
    payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(tmp_path / "x.txt")},
        }
    )
    out = _run_orchestrator(payload, gate_path=gate_path)
    assert _decision(out) == "deny"
    assert not est_path.exists()


def test_a3_yellow_zone_allow_with_advisory(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    est_path = tmp_path / "entropy-state.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-yellow",
            }
        ),
        encoding="utf-8",
    )
    est_path.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": "sess-yellow",
                "cumulative_entropy": 4.9,
                "modified_paths": [],
                "created_paths": [],
                "lines_total": 0,
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "new_file_yellow.txt"
    payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(target), "content": "a\n"},
        }
    )
    out = _run_orchestrator(payload, gate_path=gate_path)
    assert _decision(out) == "allow"
    r = _reason(out).lower()
    assert "[entropy-check]" in r
    assert "yellow" in r


def test_a4_red_zone_deny(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    est_path = tmp_path / "entropy-state.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-red",
            }
        ),
        encoding="utf-8",
    )
    est_path.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": "sess-red",
                "cumulative_entropy": 8.99,
                "modified_paths": [],
                "created_paths": [],
                "lines_total": 0,
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "new_file_red.txt"
    payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(target), "content": "a\n"},
        }
    )
    out = _run_orchestrator(payload, gate_path=gate_path)
    assert _decision(out) == "deny"
    r = _reason(out).lower()
    assert "[entropy-check]" in r
    assert "red" in r


def test_estimate_lines_placeholder_when_missing() -> None:
    assert estimate_lines_changed("Write", {}) == PLACEHOLDER_LINES
    assert estimate_lines_changed("Edit", {}) == PLACEHOLDER_LINES


def test_estimate_lines_write_content() -> None:
    n = estimate_lines_changed("Write", {"content": "a\nb\nc"})
    assert n == 3


def test_t14_settings_json_single_pretool_command() -> None:
    settings = Path(__file__).resolve().parent.parent / ".claude" / "settings.json"
    text = settings.read_text(encoding="utf-8")
    assert "edit_pretooluse_orchestrator.py" in text
    assert text.count("edit_pretooluse_orchestrator.py") >= 1


def test_reset_if_session_changed_clears_entropy() -> None:
    old = EntropyState(
        session_id="sess-a",
        cumulative_entropy=42.0,
        modified_paths=["/m1"],
        created_paths=["/c1"],
        lines_total=400,
    )
    new = reset_if_session_changed(old, "sess-b")
    assert new.session_id == "sess-b"
    assert new.cumulative_entropy == 0.0
    assert new.modified_paths == []
    assert new.created_paths == []
    assert new.lines_total == 0


def test_r1_created_files_cap_deny(tmp_path: Path) -> None:
    """11th new file in session exceeds created-path cap (10)."""
    gate_path = tmp_path / "scope-gate.json"
    est_path = tmp_path / "entropy-state.json"
    sid = "sess-created-cap"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": sid,
            }
        ),
        encoding="utf-8",
    )
    created = sorted(str((tmp_path / f"c{i}.txt").resolve()) for i in range(10))
    est_path.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": sid,
                "cumulative_entropy": 0.0,
                "modified_paths": [],
                "created_paths": created,
                "lines_total": 0,
            }
        ),
        encoding="utf-8",
    )
    eleventh = tmp_path / "c10.txt"
    payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(eleventh), "content": "x\n"},
        }
    )
    out = _run_orchestrator(payload, gate_path=gate_path)
    assert _decision(out) == "deny"
    assert "file count cap" in _reason(out).lower()


def test_r2_modified_files_cap_deny(tmp_path: Path) -> None:
    """11th distinct modified path in session exceeds modified-path cap (10)."""
    gate_path = tmp_path / "scope-gate.json"
    est_path = tmp_path / "entropy-state.json"
    sid = "sess-mod-cap"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": sid,
            }
        ),
        encoding="utf-8",
    )
    modified = sorted(str((tmp_path / f"m{i}.txt").resolve()) for i in range(10))
    m11 = tmp_path / "m10.txt"
    m11.write_text("exists\n", encoding="utf-8")
    est_path.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": sid,
                "cumulative_entropy": 0.0,
                "modified_paths": modified,
                "created_paths": [],
                "lines_total": 0,
            }
        ),
        encoding="utf-8",
    )
    payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(m11.resolve()), "content": "y\n"},
        }
    )
    out = _run_orchestrator(payload, gate_path=gate_path)
    assert _decision(out) == "deny"
    assert "file count cap" in _reason(out).lower()


def test_r3_lines_total_cap_deny(tmp_path: Path) -> None:
    """Session lines_total would exceed 500 after this Write."""
    gate_path = tmp_path / "scope-gate.json"
    est_path = tmp_path / "entropy-state.json"
    sid = "sess-lines"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": sid,
            }
        ),
        encoding="utf-8",
    )
    est_path.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": sid,
                "cumulative_entropy": 0.0,
                "modified_paths": [],
                "created_paths": [],
                "lines_total": 500,
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "one_more.txt"
    payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(target), "content": "a\n"},
        }
    )
    out = _run_orchestrator(payload, gate_path=gate_path)
    assert _decision(out) == "deny"
    assert "lines changed cap" in _reason(out).lower()


def test_r4_session_id_change_resets_entropy_state(tmp_path: Path) -> None:
    """New scope session_id must not inherit prior session cumulative entropy."""
    gate_path = tmp_path / "scope-gate.json"
    est_path = tmp_path / "entropy-state.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-new",
            }
        ),
        encoding="utf-8",
    )
    est_path.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": "sess-old",
                "cumulative_entropy": 99.0,
                "modified_paths": [],
                "created_paths": [],
                "lines_total": 0,
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "fresh.txt"
    payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(target), "content": "a\n"},
        }
    )
    out = _run_orchestrator(payload, gate_path=gate_path)
    assert _decision(out) == "allow"
    data = json.loads(est_path.read_text(encoding="utf-8"))
    assert data["session_id"] == "sess-new"
    assert data["cumulative_entropy"] < 5.0

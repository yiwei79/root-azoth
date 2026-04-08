from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ORCHESTRATOR_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "edit_pretooluse_orchestrator.py"
)

SCOPE_GATE_THIN_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "scope-gate.py"
)


def _run(
    tool_name: str,
    gate_path: Path,
    file_path: str | None = None,
    pipeline_gate_path: Path | None = None,
) -> dict:
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
    workspace = gate_path.parent
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    if pipeline_gate_path is not None:
        env["AZOTH_PIPELINE_GATE_PATH"] = str(pipeline_gate_path)
    result = subprocess.run(
        ["python3", str(ORCHESTRATOR_PATH)],
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


# T13–T16: governed scope + pipeline-gate.json (M1 / delivery_pipeline mechanical layer)


def test_t13_governed_scope_write_denied_without_pipeline_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-governed",
                "delivery_pipeline": "governed",
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "src.txt"
    output = _run("Write", gate_path, file_path=str(target), pipeline_gate_path=pg_path)
    assert _decision(output) == "deny"
    assert "pipeline-gate" in _reason(output).lower()


def test_t14_governed_scope_write_allowed_with_valid_pipeline_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-governed",
                "delivery_pipeline": "governed",
            }
        ),
        encoding="utf-8",
    )
    pg_path.write_text(
        json.dumps(
            {
                "approved": True,
                "session_id": "sess-governed",
                "expires_at": _future_expiry(),
                "pipeline": "deliver-full",
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "src.txt"
    output = _run("Write", gate_path, file_path=str(target), pipeline_gate_path=pg_path)
    assert _decision(output) == "allow"


def test_t15_governed_scope_write_to_pipeline_gate_path_allowed_without_prior_gate(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    output = _run("Write", gate_path, file_path=str(pg_path), pipeline_gate_path=pg_path)
    assert _decision(output) == "allow"


def test_t16_target_layer_m1_triggers_pipeline_gate(tmp_path: Path) -> None:
    gate_path = tmp_path / "scope-gate.json"
    pg_path = tmp_path / "pipeline-gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "approved": True,
                "expires_at": _future_expiry(),
                "session_id": "sess-m1",
                "target_layer": "M1",
                "delivery_pipeline": "standard",
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "x.txt"
    output = _run("Write", gate_path, file_path=str(target), pipeline_gate_path=pg_path)
    assert _decision(output) == "deny"


def test_t17_scope_gate_thin_cli_write_denied_without_gate(tmp_path: Path) -> None:
    """Regression: scope-gate.py thin CLI (scope-only) must run without NameError."""
    gate_path = tmp_path / "scope-gate.json"
    workspace = gate_path.parent
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    stdin_payload = json.dumps(
        {
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": str(tmp_path / "x.txt")},
        }
    )
    result = subprocess.run(
        ["python3", str(SCOPE_GATE_THIN_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert _decision(output) == "deny"
    assert "scope-gate" in _reason(output)


def test_t18_scope_gate_thin_malformed_stdin_allow(tmp_path: Path) -> None:
    """Parity with test_p5_002 test_a1: invalid JSON stdin must allow (fail-open)."""
    gate_path = tmp_path / "scope-gate.json"
    workspace = gate_path.parent
    env = {**os.environ, "AZOTH_SCOPE_GATE_PATH": str(gate_path)}
    env["AZOTH_ENTROPY_STATE_PATH"] = str(workspace / "entropy-state.json")
    result = subprocess.run(
        ["python3", str(SCOPE_GATE_THIN_PATH)],
        input="not valid json {{{",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert _decision(out) == "allow"

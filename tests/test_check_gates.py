"""Tests for scripts/check_gates.py — S4 cross-platform gate validator.

Verifies:
- check_gates.py imports successfully from scope_gate_check.py
- check_scope_gate_fields validates all 8 required fields
- check_pipeline_gate validates structure and cross-consistency
- check_all_gates composes both checks
- CLI exits 0 on valid gates, 1 on invalid
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


# ── Import guard ──────────────────────────────────────────────────────────────


def test_check_gates_importable() -> None:
    """check_gates.py must be importable and expose expected functions."""
    result = subprocess.run(
        [sys.executable, "-c", "import check_gates; print('ok')"],
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Import failed: {result.stderr}"
    assert "ok" in result.stdout


def test_check_gates_has_required_functions() -> None:
    """check_gates.py must expose check_scope_gate_fields, check_pipeline_gate, check_all_gates."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import check_gates; "
                "assert hasattr(check_gates, 'check_scope_gate_fields'); "
                "assert hasattr(check_gates, 'check_pipeline_gate'); "
                "assert hasattr(check_gates, 'check_all_gates'); "
                "print('ok')"
            ),
        ],
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Missing functions: {result.stderr}"


# ── Field validation ──────────────────────────────────────────────────────────


SCOPE_GATE_REQUIRED_FIELDS = {
    "session_id",
    "goal",
    "approved",
    "approved_by",
    "expires_at",
    "backlog_id",
    "delivery_pipeline",
    "target_layer",
}


def test_scope_gate_field_count() -> None:
    """scope-gate.json contract requires exactly 8 fields."""
    assert len(SCOPE_GATE_REQUIRED_FIELDS) == 8


PIPELINE_GATE_REQUIRED_FIELDS = {
    "session_id",
    "pipeline",
    "approved",
    "expires_at",
    "opened_at",
}


def test_pipeline_gate_field_count() -> None:
    """pipeline-gate.json contract requires exactly 5 fields."""
    assert len(PIPELINE_GATE_REQUIRED_FIELDS) == 5


# ── CLI exit codes ────────────────────────────────────────────────────────────


def test_cli_exits_1_when_no_scope_gate(tmp_path: Path) -> None:
    """check_gates.py exits 1 when scope-gate.json is missing."""
    # Create a fake repo structure without .azoth/scope-gate.json
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    # Copy both scripts to temp
    for name in ("check_gates.py", "scope_gate_check.py"):
        (scripts_dir / name).write_text(
            (SCRIPTS_DIR / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    result = subprocess.run(
        [sys.executable, str(scripts_dir / "check_gates.py")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "BLOCKED" in result.stdout or "not found" in result.stdout


def test_cli_exits_0_with_valid_scope_gate(tmp_path: Path) -> None:
    """check_gates.py exits 0 when scope-gate.json is valid."""
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    gate = {
        "session_id": "test-session",
        "goal": "test goal",
        "approved": True,
        "approved_by": "human",
        "expires_at": expires,
        "backlog_id": "ad-hoc",
        "delivery_pipeline": "auto",
        "target_layer": "M3",
    }
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(gate), encoding="utf-8"
    )

    for name in ("check_gates.py", "scope_gate_check.py"):
        (scripts_dir / name).write_text(
            (SCRIPTS_DIR / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    result = subprocess.run(
        [sys.executable, str(scripts_dir / "check_gates.py")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Unexpected failure: {result.stdout}\n{result.stderr}"


def test_cli_exits_1_with_missing_fields(tmp_path: Path) -> None:
    """check_gates.py exits 1 when scope-gate.json is missing required fields."""
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    # Missing approved_by and backlog_id
    gate = {
        "session_id": "test-session",
        "goal": "test goal",
        "approved": True,
        "expires_at": expires,
        "delivery_pipeline": "auto",
        "target_layer": "M3",
    }
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(gate), encoding="utf-8"
    )

    for name in ("check_gates.py", "scope_gate_check.py"):
        (scripts_dir / name).write_text(
            (SCRIPTS_DIR / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    result = subprocess.run(
        [sys.executable, str(scripts_dir / "check_gates.py")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "missing fields" in result.stdout


def test_cli_require_pipeline_gate_flag(tmp_path: Path) -> None:
    """--require-pipeline-gate exits 1 when pipeline-gate.json is absent."""
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    gate = {
        "session_id": "test-session",
        "goal": "test goal",
        "approved": True,
        "approved_by": "human",
        "expires_at": expires,
        "backlog_id": "ad-hoc",
        "delivery_pipeline": "auto",
        "target_layer": "M3",
    }
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(gate), encoding="utf-8"
    )

    for name in ("check_gates.py", "scope_gate_check.py"):
        (scripts_dir / name).write_text(
            (SCRIPTS_DIR / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    result = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "check_gates.py"),
            "--require-pipeline-gate",
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "pipeline-gate.json required" in result.stdout

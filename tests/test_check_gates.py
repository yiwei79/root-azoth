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
sys.path.insert(0, str(SCRIPTS_DIR))
import check_gates  # noqa: E402


def _future_iso(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _write_script_copies(tmp_path: Path) -> Path:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    for name in ("check_gates.py", "scope_gate_check.py"):
        (scripts_dir / name).write_text(
            (SCRIPTS_DIR / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return scripts_dir


def _write_scope_gate(
    azoth_dir: Path,
    *,
    session_id: str = "test-session",
    governance_mode: str = "standard",
    target_layer: str = "M3",
    delivery_pipeline: str | None = None,
    expires_at: str | None = None,
) -> None:
    gate = {
        "session_id": session_id,
        "goal": "test goal",
        "approved": True,
        "approved_by": "human",
        "expires_at": expires_at or _future_iso(),
        "backlog_id": "ad-hoc",
        "governance_mode": governance_mode,
        "target_layer": target_layer,
    }
    if delivery_pipeline is not None:
        gate["delivery_pipeline"] = delivery_pipeline
    (azoth_dir / "scope-gate.json").write_text(json.dumps(gate), encoding="utf-8")


def _write_pipeline_gate(
    azoth_dir: Path,
    *,
    session_id: str = "test-session",
    expires_at: str | None = None,
    pipeline: str = "deliver-full",
    research_required: bool = False,
    research_evidence: dict | None = None,
) -> None:
    gate = {
        "session_id": session_id,
        "pipeline_command": pipeline,
        "approved": True,
        "expires_at": expires_at or _future_iso(),
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "research_required": research_required,
    }
    if research_evidence is not None:
        gate["research_evidence"] = research_evidence
    (azoth_dir / "pipeline-gate.json").write_text(json.dumps(gate), encoding="utf-8")


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


def test_scope_gate_core_field_count() -> None:
    """scope-gate.json bridge keeps 7 core fields plus a mode field."""
    assert len(check_gates.SCOPE_GATE_CORE_REQUIRED_FIELDS) == 7


def test_scope_gate_requires_mode_bridge_field() -> None:
    assert check_gates.SCOPE_GATE_MODE_FIELDS == {"delivery_pipeline", "governance_mode"}


def test_pipeline_gate_core_field_count() -> None:
    """pipeline-gate.json bridge keeps 4 core fields plus a mode field."""
    assert len(check_gates.PIPELINE_GATE_CORE_REQUIRED_FIELDS) == 4


def test_pipeline_gate_requires_mode_bridge_field() -> None:
    assert check_gates.PIPELINE_GATE_MODE_FIELDS == {"pipeline", "pipeline_command"}


# ── CLI exit codes ────────────────────────────────────────────────────────────


def test_cli_exits_1_when_no_scope_gate(tmp_path: Path) -> None:
    """check_gates.py exits 1 when scope-gate.json is missing."""
    # Create a fake repo structure without .azoth/scope-gate.json
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    scripts_dir = _write_script_copies(tmp_path)

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
    scripts_dir = _write_script_copies(tmp_path)
    _write_scope_gate(azoth_dir)

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
    scripts_dir = _write_script_copies(tmp_path)
    expires = _future_iso()
    # Missing approved_by and backlog_id
    gate = {
        "session_id": "test-session",
        "goal": "test goal",
        "approved": True,
        "expires_at": expires,
        "target_layer": "M3",
    }
    (azoth_dir / "scope-gate.json").write_text(json.dumps(gate), encoding="utf-8")

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
    scripts_dir = _write_script_copies(tmp_path)
    _write_scope_gate(azoth_dir)

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


def test_cli_rejects_pipeline_gate_with_invalid_opened_at(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    scripts_dir = _write_script_copies(tmp_path)
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    pipeline_gate = {
        "session_id": "test-session",
        "pipeline_command": "deliver-full",
        "approved": True,
        "expires_at": expires,
        "opened_at": "not-a-date",
        "research_required": False,
    }
    (azoth_dir / "pipeline-gate.json").write_text(json.dumps(pipeline_gate), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(scripts_dir / "check_gates.py"), "--require-pipeline-gate"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "opened_at is invalid" in result.stdout


def test_check_pipeline_gate_allows_governed_local_only_path_when_research_not_required(
    tmp_path: Path,
) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(azoth_dir, expires_at=expires, research_required=False)

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is True
    assert "Pipeline gate valid" in message


def test_check_pipeline_gate_requires_top_level_research_required_boolean_for_governed_scope(
    tmp_path: Path,
) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    gate = {
        "session_id": "test-session",
        "pipeline_command": "deliver-full",
        "approved": True,
        "expires_at": expires,
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }
    (azoth_dir / "pipeline-gate.json").write_text(json.dumps(gate), encoding="utf-8")

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "research_required" in message


def test_check_pipeline_gate_rejects_non_boolean_research_required(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    gate = {
        "session_id": "test-session",
        "pipeline_command": "deliver-full",
        "approved": True,
        "expires_at": expires,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "research_required": "yes",
    }
    (azoth_dir / "pipeline-gate.json").write_text(json.dumps(gate), encoding="utf-8")

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "research_required" in message


def test_check_pipeline_gate_allows_same_session_repo_local_research_evidence(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(
        azoth_dir,
        expires_at=expires,
        research_required=True,
        research_evidence={
            "kind": "repo-local",
            "session_id": "test-session",
            "path": ".azoth/research/test-session.md",
        },
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is True
    assert "Pipeline gate valid" in message


def test_check_pipeline_gate_rejects_missing_research_evidence_when_required(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(azoth_dir, expires_at=expires, research_required=True)

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "research_evidence" in message


def test_check_pipeline_gate_rejects_malformed_research_evidence_object(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    gate = {
        "session_id": "test-session",
        "pipeline_command": "deliver-full",
        "approved": True,
        "expires_at": expires,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "research_required": True,
        "research_evidence": ["repo-local"],
    }
    (azoth_dir / "pipeline-gate.json").write_text(json.dumps(gate), encoding="utf-8")

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "research_evidence" in message


def test_check_pipeline_gate_rejects_research_evidence_missing_required_field(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(
        azoth_dir,
        expires_at=expires,
        research_required=True,
        research_evidence={
            "kind": "repo-local",
            "session_id": "test-session",
        },
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "research_evidence" in message
    assert "path" in message


def test_check_pipeline_gate_rejects_wrong_research_evidence_kind(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(
        azoth_dir,
        expires_at=expires,
        research_required=True,
        research_evidence={
            "kind": "web",
            "session_id": "test-session",
            "path": ".azoth/research/test-session.md",
        },
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "repo-local" in message


def test_check_pipeline_gate_rejects_research_evidence_session_mismatch(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(
        azoth_dir,
        expires_at=expires,
        research_required=True,
        research_evidence={
            "kind": "repo-local",
            "session_id": "other-session",
            "path": ".azoth/research/test-session.md",
        },
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "session_id" in message


def test_check_pipeline_gate_rejects_absolute_research_evidence_path(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(
        azoth_dir,
        expires_at=expires,
        research_required=True,
        research_evidence={
            "kind": "repo-local",
            "session_id": "test-session",
            "path": str((tmp_path / "evidence.md").resolve()),
        },
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "repo-relative" in message


def test_check_pipeline_gate_rejects_windows_drive_research_evidence_path(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(
        azoth_dir,
        expires_at=expires,
        research_required=True,
        research_evidence={
            "kind": "repo-local",
            "session_id": "test-session",
            "path": r"C:\evidence.md",
        },
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "repo-relative" in message


def test_check_pipeline_gate_rejects_parent_traversal_in_research_evidence_path(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(
        azoth_dir,
        expires_at=expires,
        research_required=True,
        research_evidence={
            "kind": "repo-local",
            "session_id": "test-session",
            "path": "../outside.md",
        },
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "repo-relative" in message


def test_check_pipeline_gate_rejects_uri_scheme_in_research_evidence_path(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(
        azoth_dir,
        expires_at=expires,
        research_required=True,
        research_evidence={
            "kind": "repo-local",
            "session_id": "test-session",
            "path": "file:///tmp/evidence.md",
        },
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "URI" in message


def test_check_pipeline_gate_rejects_non_file_uri_scheme_in_research_evidence_path(
    tmp_path: Path,
) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = _future_iso()
    _write_scope_gate(azoth_dir, governance_mode="governed", target_layer="M1", expires_at=expires)
    _write_pipeline_gate(
        azoth_dir,
        expires_at=expires,
        research_required=True,
        research_evidence={
            "kind": "repo-local",
            "session_id": "test-session",
            "path": "mailto:evidence",
        },
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)

    assert valid is False
    assert "URI" in message


def test_cli_rejects_expired_pipeline_gate(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    scope_gate = {
        "session_id": "test-session",
        "goal": "test goal",
        "approved": True,
        "approved_by": "human",
        "expires_at": expired,
        "backlog_id": "ad-hoc",
        "governance_mode": "governed",
        "target_layer": "M1",
    }
    pipeline_gate = {
        "session_id": "test-session",
        "pipeline_command": "deliver-full",
        "approved": True,
        "expires_at": expired,
        "opened_at": expires,
    }
    (azoth_dir / "scope-gate.json").write_text(json.dumps(scope_gate), encoding="utf-8")
    (azoth_dir / "pipeline-gate.json").write_text(json.dumps(pipeline_gate), encoding="utf-8")

    for name in ("check_gates.py", "scope_gate_check.py"):
        (scripts_dir / name).write_text(
            (SCRIPTS_DIR / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    result = subprocess.run(
        [sys.executable, str(scripts_dir / "check_gates.py"), "--require-pipeline-gate"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "pipeline-gate.json is expired" in result.stdout


def test_cli_accepts_valid_pipeline_gate_with_pipeline_command(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    opened = datetime.now(timezone.utc).isoformat()
    scope_gate = {
        "session_id": "test-session",
        "goal": "test goal",
        "approved": True,
        "approved_by": "human",
        "expires_at": expires,
        "backlog_id": "ad-hoc",
        "governance_mode": "governed",
        "pipeline_command": "deliver-full",
        "target_layer": "M1",
    }
    pipeline_gate = {
        "session_id": "test-session",
        "pipeline_command": "deliver-full",
        "approved": True,
        "expires_at": expires,
        "opened_at": opened,
        "research_required": False,
    }
    (azoth_dir / "scope-gate.json").write_text(json.dumps(scope_gate), encoding="utf-8")
    (azoth_dir / "pipeline-gate.json").write_text(json.dumps(pipeline_gate), encoding="utf-8")

    for name in ("check_gates.py", "scope_gate_check.py"):
        (scripts_dir / name).write_text(
            (SCRIPTS_DIR / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    result = subprocess.run(
        [sys.executable, str(scripts_dir / "check_gates.py"), "--require-pipeline-gate"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Unexpected failure: {result.stdout}\n{result.stderr}"


def test_check_pipeline_gate_rejects_invalid_pipeline_command(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    opened = datetime.now(timezone.utc).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "pipeline_command": "ship-it",
                "approved": True,
                "expires_at": expires,
                "opened_at": opened,
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(require=True, root=tmp_path)
    assert valid is False
    assert "must be one of" in message


def test_check_pipeline_gate_requires_file_for_governed_scope(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)
    assert valid is False
    assert "required but not found" in message


def test_check_pipeline_gate_rejects_opened_at_after_expires_at(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    opened = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "pipeline_command": "deliver-full",
                "approved": True,
                "expires_at": expires,
                "opened_at": opened,
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(require=True, root=tmp_path)
    assert valid is False
    assert "opened_at is after expires_at" in message


def test_check_pipeline_gate_rejects_unapproved_gate(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    opened = datetime.now(timezone.utc).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "pipeline_command": "deliver-full",
                "approved": False,
                "expires_at": expires,
                "opened_at": opened,
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)
    assert valid is False
    assert "not approved" in message


def test_check_pipeline_gate_rejects_invalid_expires_at(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    opened = datetime.now(timezone.utc).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": "2099-04-16T19:17:45+00:00",
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "pipeline_command": "deliver-full",
                "approved": True,
                "expires_at": "not-a-date",
                "opened_at": opened,
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)
    assert valid is False
    assert "expires_at is invalid" in message


def test_check_pipeline_gate_rejects_missing_mode_field(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    opened = datetime.now(timezone.utc).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "approved": True,
                "expires_at": expires,
                "opened_at": opened,
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)
    assert valid is False
    assert "missing mode field" in message


def test_check_pipeline_gate_rejects_malformed_json(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text("{not-json", encoding="utf-8")

    valid, message = check_gates.check_pipeline_gate(root=tmp_path)
    assert valid is False
    assert "malformed" in message


def test_check_pipeline_gate_rejects_session_mismatch(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    opened = datetime.now(timezone.utc).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "scope-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "pipeline-session",
                "pipeline_command": "deliver-full",
                "approved": True,
                "expires_at": expires,
                "opened_at": opened,
                "research_required": False,
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(require=True, root=tmp_path)
    assert valid is False
    assert "session_id mismatch" in message


def test_check_pipeline_gate_rejects_expires_at_mismatch(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    scope_expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    pipeline_expires = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    opened = datetime.now(timezone.utc).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": scope_expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "pipeline_command": "deliver-full",
                "approved": True,
                "expires_at": pipeline_expires,
                "opened_at": opened,
                "research_required": False,
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(require=True, root=tmp_path)
    assert valid is False
    assert "expires_at mismatch" in message


def test_check_pipeline_gate_rejects_selected_pipeline_mismatch(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    opened = datetime.now(timezone.utc).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "pipeline_command": "deliver-full",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "pipeline_command": "deliver",
                "approved": True,
                "expires_at": expires,
                "opened_at": opened,
                "research_required": False,
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(require=True, root=tmp_path)
    assert valid is False
    assert "does not match the selected pipeline" in message


def test_check_pipeline_gate_rejects_explicit_session_id_mismatch(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    opened = datetime.now(timezone.utc).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )
    (azoth_dir / "pipeline-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "pipeline_command": "deliver-full",
                "approved": True,
                "expires_at": expires,
                "opened_at": opened,
                "research_required": False,
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_pipeline_gate(
        session_id="other-session",
        root=tmp_path,
    )
    assert valid is False
    assert "session_id mismatch" in message


def test_check_scope_gate_rejects_missing_mode_field(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "target_layer": "M3",
            }
        ),
        encoding="utf-8",
    )

    valid, message = check_gates.check_scope_gate_fields(root=tmp_path)
    assert valid is False
    assert "missing mode field" in message


def test_check_all_gates_reports_composed_failures(tmp_path: Path) -> None:
    azoth_dir = tmp_path / ".azoth"
    azoth_dir.mkdir()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    (azoth_dir / "scope-gate.json").write_text(
        json.dumps(
            {
                "session_id": "test-session",
                "goal": "test goal",
                "approved": True,
                "approved_by": "human",
                "expires_at": expires,
                "backlog_id": "ad-hoc",
                "governance_mode": "governed",
                "target_layer": "M1",
            }
        ),
        encoding="utf-8",
    )

    valid, messages = check_gates.check_all_gates(root=tmp_path)
    assert valid is False
    assert len(messages) == 2
    assert any("Scope gate valid" in message for message in messages)
    assert any("pipeline-gate.json required but not found" in message for message in messages)

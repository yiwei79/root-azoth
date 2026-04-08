"""Tests for l2_evidence_append.py gate + append behavior."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APPEND = ROOT / "scripts" / "l2_evidence_append.py"


def _future_expires() -> str:
    t = datetime.now(timezone.utc) + timedelta(hours=2)
    return t.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _write_gates(
    azoth: Path,
    *,
    session_id: str,
    scope_approved: bool = True,
    pipeline_approved: bool = True,
    scope_expired: bool = False,
    pipeline_expired: bool = False,
    target_m1: bool = True,
) -> None:
    mem = azoth / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    exp = _future_expires()
    if scope_expired:
        exp = "2020-01-01T00:00:00+00:00"
    sg = {
        "approved": scope_approved,
        "expires_at": exp,
        "session_id": session_id,
        "delivery_pipeline": "governed",
        "target_layer": "M1" if target_m1 else "infrastructure",
    }
    (azoth / "scope-gate.json").write_text(json.dumps(sg), encoding="utf-8")
    pexp = _future_expires()
    if pipeline_expired:
        pexp = "2020-01-01T00:00:00+00:00"
    pg = {
        "session_id": session_id,
        "pipeline": "auto",
        "approved": pipeline_approved,
        "expires_at": pexp,
        "opened_at": "2026-04-08T12:00:00+00:00",
    }
    (azoth / "pipeline-gate.json").write_text(json.dumps(pg), encoding="utf-8")


def _minimal_record(session_id: str) -> dict:
    return {
        "record_schema_version": 1,
        "recorded_at": "2026-04-08T12:00:00+00:00",
        "session_id": session_id,
        "backlog_id": "P6-002",
        "source_pipeline": "auto",
        "source_stage_id": "auto_s4_evaluator",
        "source_agent": "evaluator",
        "evidence_kind": "eval_summary",
        "target_surfaces": ["skills/prompt-engineer/SKILL.md"],
        "summary": "test append",
        "payload": {},
    }


def _run_append(tmp: Path, session_id: str, record: dict, *, expect_ok: bool) -> subprocess.CompletedProcess:
    azoth = tmp / ".azoth"
    jsonl = azoth / "memory" / "l2-refinement-evidence.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(APPEND),
            "--session-id",
            session_id,
            "--azoth-dir",
            str(tmp),
            "--jsonl",
            str(jsonl),
            "--scope-gate",
            str(azoth / "scope-gate.json"),
            "--pipeline-gate",
            str(azoth / "pipeline-gate.json"),
        ],
        input=json.dumps(record),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
    )
    if expect_ok:
        assert proc.returncode == 0, proc.stderr
    else:
        assert proc.returncode != 0
    return proc


def test_append_rejects_without_scope_gate(tmp_path: Path):
    sid = "test-session-1"
    proc = subprocess.run(
        [
            sys.executable,
            str(APPEND),
            "--session-id",
            sid,
            "--azoth-dir",
            str(tmp_path),
        ],
        input=json.dumps(_minimal_record(sid)),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
    )
    assert proc.returncode != 0
    assert "missing" in proc.stderr.lower() or "scope" in proc.stderr.lower()


def test_append_rejects_session_mismatch(tmp_path: Path):
    azoth = tmp_path / ".azoth"
    _write_gates(azoth, session_id="scope-sid")
    proc = _run_append(tmp_path, "other-sid", _minimal_record("other-sid"), expect_ok=False)
    assert "mismatch" in proc.stderr.lower()


def test_append_rejects_expired_scope(tmp_path: Path):
    azoth = tmp_path / ".azoth"
    sid = "2026-04-08-p6-002"
    _write_gates(azoth, session_id=sid, scope_expired=True)
    proc = _run_append(tmp_path, sid, _minimal_record(sid), expect_ok=False)
    assert "expired" in proc.stderr.lower()


def test_append_rejects_unapproved_pipeline_for_m1(tmp_path: Path):
    azoth = tmp_path / ".azoth"
    sid = "2026-04-08-p6-002"
    _write_gates(azoth, session_id=sid, pipeline_approved=False)
    proc = _run_append(tmp_path, sid, _minimal_record(sid), expect_ok=False)
    assert "pipeline" in proc.stderr.lower()


def test_append_accepts_valid_gates(tmp_path: Path):
    azoth = tmp_path / ".azoth"
    sid = "2026-04-08-p6-002"
    _write_gates(azoth, session_id=sid)
    jsonl = azoth / "memory" / "l2-refinement-evidence.jsonl"
    rec = _minimal_record(sid)
    _run_append(tmp_path, sid, rec, expect_ok=True)
    lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["summary"] == "test append"


def test_standard_layer_skips_pipeline_gate(tmp_path: Path):
    azoth = tmp_path / ".azoth"
    sid = "std-layer-session"
    mem = azoth / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    sg = {
        "approved": True,
        "expires_at": _future_expires(),
        "session_id": sid,
        "delivery_pipeline": "standard",
        "target_layer": "infrastructure",
    }
    (azoth / "scope-gate.json").write_text(json.dumps(sg), encoding="utf-8")
    jsonl = azoth / "memory" / "l2-refinement-evidence.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(APPEND),
            "--session-id",
            sid,
            "--azoth-dir",
            str(tmp_path),
            "--jsonl",
            str(jsonl),
            "--scope-gate",
            str(azoth / "scope-gate.json"),
            "--pipeline-gate",
            str(azoth / "pipeline-gate.json"),
        ],
        input=json.dumps(_minimal_record(sid)),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert jsonl.is_file()

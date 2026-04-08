"""Tests for L2 evidence record validation (P6-002)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from l2_evidence_validate import (  # noqa: E402
    L2EvidenceValidationError,
    validate_l2_evidence_record,
)


def _minimal(**overrides):
    base = {
        "record_schema_version": 1,
        "recorded_at": "2026-04-08T12:00:00+00:00",
        "session_id": "2026-04-08-p6-002",
        "backlog_id": "P6-002",
        "source_pipeline": "auto",
        "source_stage_id": "auto_s4_evaluator",
        "source_agent": "evaluator",
        "evidence_kind": "eval_summary",
        "target_surfaces": ["skills/prompt-engineer/SKILL.md"],
        "summary": "PASS 0.89 vs threshold 0.85",
        "payload": {"overall_score": 0.89},
    }
    base.update(overrides)
    return base


def test_valid_minimal():
    validate_l2_evidence_record(_minimal())


def test_valid_z_suffix():
    doc = _minimal(recorded_at="2026-04-08T12:00:00Z")
    validate_l2_evidence_record(doc)


def test_missing_field():
    d = _minimal()
    del d["summary"]
    with pytest.raises(L2EvidenceValidationError, match="summary"):
        validate_l2_evidence_record(d)


def test_bad_schema_version():
    with pytest.raises(L2EvidenceValidationError, match="record_schema_version"):
        validate_l2_evidence_record(_minimal(record_schema_version=2))


def test_bad_pipeline():
    with pytest.raises(L2EvidenceValidationError, match="source_pipeline"):
        validate_l2_evidence_record(_minimal(source_pipeline="nope"))


def test_bad_agent():
    with pytest.raises(L2EvidenceValidationError, match="source_agent"):
        validate_l2_evidence_record(_minimal(source_agent="not-an-agent"))


def test_empty_target_surfaces():
    with pytest.raises(L2EvidenceValidationError, match="target_surfaces"):
        validate_l2_evidence_record(_minimal(target_surfaces=[]))


def test_summary_too_long():
    with pytest.raises(L2EvidenceValidationError, match="summary"):
        validate_l2_evidence_record(_minimal(summary="x" * 5000))


def test_payload_not_object():
    with pytest.raises(L2EvidenceValidationError, match="payload"):
        validate_l2_evidence_record(_minimal(payload=[]))


def test_extra_top_level_key():
    with pytest.raises(L2EvidenceValidationError, match="unknown top-level"):
        validate_l2_evidence_record(_minimal(extra="no"))


def test_jsonl_round_trip_line():
    doc = _minimal()
    line = json.dumps(doc)
    back = json.loads(line)
    validate_l2_evidence_record(back)

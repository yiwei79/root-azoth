"""Tests for architecture proposal validation (P6-003)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from architecture_proposal_validate import (  # noqa: E402
    ArchitectureProposalValidationError,
    _load_backlog_ids,
    _load_decision_ids,
    validate_architecture_proposal,
)


def _minimal(**overrides: object) -> dict:
    base = {
        "proposal_schema_version": 1,
        "created_at": "2026-04-08T12:00:00+00:00",
        "session_id": "2026-04-08-p6-003",
        "backlog_id": "P6-003",
        "title": "Test proposal",
        "summary": "Summary text for validation.",
        "status": "draft",
        "decision_refs": ["D1"],
        "scope_layers": ["docs"],
        "details": {},
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


def test_valid_minimal() -> None:
    validate_architecture_proposal(_minimal())


def test_example_file_round_trip() -> None:
    path = ROOT / "pipelines" / "examples" / "architecture-proposal.minimal.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_architecture_proposal(doc)


def test_valid_z_suffix() -> None:
    validate_architecture_proposal(_minimal(created_at="2026-04-08T12:00:00Z"))


def test_missing_field() -> None:
    d = _minimal()
    del d["summary"]
    with pytest.raises(ArchitectureProposalValidationError, match="summary"):
        validate_architecture_proposal(d)


def test_bad_schema_version() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="proposal_schema_version"):
        validate_architecture_proposal(_minimal(proposal_schema_version=2))


def test_bad_status() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="status"):
        validate_architecture_proposal(_minimal(status="published"))


def test_invalid_decision_ref_pattern() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="decision_refs\\[0\\]"):
        validate_architecture_proposal(_minimal(decision_refs=["D1a"]))


def test_empty_decision_refs() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="decision_refs"):
        validate_architecture_proposal(_minimal(decision_refs=[]))


def test_empty_scope_layers() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="scope_layers"):
        validate_architecture_proposal(_minimal(scope_layers=[]))


def test_invalid_scope_layer() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="scope_layers\\[1\\]"):
        validate_architecture_proposal(_minimal(scope_layers=["kernel", "unknown"]))


def test_summary_too_long() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="summary"):
        validate_architecture_proposal(_minimal(summary="x" * 9000))


def test_details_not_object() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="details"):
        validate_architecture_proposal(_minimal(details=[]))


def test_extra_top_level_key() -> None:
    d = _minimal()
    d["extra"] = "no"
    with pytest.raises(ArchitectureProposalValidationError, match="unknown top-level"):
        validate_architecture_proposal(d)


def test_root_not_dict() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="object"):
        validate_architecture_proposal([])


def test_jsonl_round_trip_line() -> None:
    doc = _minimal()
    line = json.dumps(doc)
    back = json.loads(line)
    validate_architecture_proposal(back)


def test_repo_aware_validation_accepts_live_backlog_and_decision_refs() -> None:
    validate_architecture_proposal(
        _minimal(backlog_id="T-010", decision_refs=["D21"]),
        backlog_ids=_load_backlog_ids(),
        decision_ids=_load_decision_ids(),
    )


def test_repo_aware_validation_rejects_unknown_backlog_id() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match="backlog_id"):
        validate_architecture_proposal(
            _minimal(backlog_id="NOT-REAL-001", decision_refs=["D21"]),
            backlog_ids=_load_backlog_ids(),
            decision_ids=_load_decision_ids(),
        )


def test_repo_aware_validation_rejects_unknown_decision_ref() -> None:
    with pytest.raises(ArchitectureProposalValidationError, match=r"decision_refs\[0\]"):
        validate_architecture_proposal(
            _minimal(backlog_id="T-010", decision_refs=["D9999"]),
            backlog_ids=_load_backlog_ids(),
            decision_ids=_load_decision_ids(),
        )


def test_cli_rejects_schema_valid_file_with_unknown_backlog_id(tmp_path: Path) -> None:
    path = tmp_path / "proposal.yaml"
    path.write_text(
        yaml.safe_dump(_minimal(backlog_id="NOT-REAL-001", decision_refs=["D21"])),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "architecture_proposal_validate.py"), str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "backlog_id" in result.stderr


def test_cli_rejects_schema_valid_file_with_unknown_decision_ref(tmp_path: Path) -> None:
    path = tmp_path / "proposal.yaml"
    path.write_text(
        yaml.safe_dump(_minimal(backlog_id="T-010", decision_refs=["D9999"])),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "architecture_proposal_validate.py"), str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "decision_refs[0]" in result.stderr

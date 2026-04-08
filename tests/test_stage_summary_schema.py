"""
Stage summary schema validation (BL-012).

Validates pipelines/stage-summary.schema.yaml structure and example documents.
Uses structural checks (no jsonschema dependency).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = REPO_ROOT / "pipelines" / "stage-summary.schema.yaml"
FIXTURE_FILE = REPO_ROOT / "tests" / "fixtures" / "stage_summary_valid.yaml"

_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from stage_summary_validate import (  # noqa: E402
    VALID_KINDS,
    StageSummaryValidationError,
    validate_stage_summary,
)


def test_schema_file_exists_and_loads() -> None:
    assert SCHEMA_FILE.is_file()
    raw = yaml.safe_load(SCHEMA_FILE.read_text(encoding="utf-8"))
    assert raw["$id"] == "azoth:stage-summary:v1"
    assert "required" in raw
    assert "properties" in raw


def test_fixture_examples_all_validate() -> None:
    text = FIXTURE_FILE.read_text(encoding="utf-8")
    docs = list(yaml.safe_load_all(text))
    assert len(docs) == 4
    kinds = []
    for i, doc in enumerate(docs):
        validate_stage_summary(doc, label=f"example[{i}]")
        kinds.append(doc["stage_kind"])
    assert set(kinds) == VALID_KINDS


def test_invalid_examples_rejected() -> None:
    bad = {"stage_summary_version": 1, "pipeline": "auto"}
    with pytest.raises(StageSummaryValidationError, match="missing"):
        validate_stage_summary(bad)

    bad2 = {
        "stage_summary_version": 1,
        "pipeline": "invalid",
        "stage_id": "x",
        "agent": "architect",
        "stage_kind": "research",
        "status": "complete",
        "entropy": "GREEN",
    }
    with pytest.raises(StageSummaryValidationError, match="pipeline"):
        validate_stage_summary(bad2)

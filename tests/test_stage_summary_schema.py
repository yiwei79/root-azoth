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

REPLAY_FIELDS = (
    "replay_iteration",
    "replay_target_stage",
    "finding_class",
    "threshold_limit",
    "lineage_artifacts",
)


def _base_summary() -> dict[str, object]:
    return {
        "stage_summary_version": 1,
        "pipeline": "deliver-full",
        "stage_id": "deliver_full_s6",
        "agent": "builder",
        "stage_kind": "build",
        "status": "complete",
        "entropy": "YELLOW",
    }


def _full_replay_bundle() -> dict[str, object]:
    return {
        "replay_iteration": 1,
        "replay_target_stage": "deliver_full_s2_architect",
        "finding_class": "test-strategy",
        "threshold_limit": 3,
        "lineage_artifacts": [
            ".azoth/handoffs/2026-04-22-bl-067-architecture-brief.md",
            ".azoth/handoffs/2026-04-22-bl-067-deliver_full_s5.yaml",
        ],
    }


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


def test_schema_requires_replay_fields_as_all_or_nothing_bundle() -> None:
    raw = yaml.safe_load(SCHEMA_FILE.read_text(encoding="utf-8"))

    dependent_required = raw.get("dependentRequired")
    assert isinstance(dependent_required, dict)
    assert set(dependent_required) == set(REPLAY_FIELDS)

    for field in REPLAY_FIELDS:
        assert set(dependent_required[field]) == (set(REPLAY_FIELDS) - {field})


def test_validate_stage_summary_accepts_no_replay_metadata() -> None:
    validate_stage_summary(_base_summary(), label="no_replay")


def test_validate_stage_summary_accepts_full_replay_bundle() -> None:
    validate_stage_summary(
        {**_base_summary(), **_full_replay_bundle()},
        label="full_bundle",
    )


@pytest.mark.parametrize(
    ("label", "partial_bundle"),
    [
        ("single_field", {"replay_iteration": 1}),
        (
            "leading_pair",
            {
                "replay_iteration": 1,
                "replay_target_stage": "deliver_full_s2_architect",
            },
        ),
        (
            "missing_lineage_artifacts",
            {
                "replay_iteration": 1,
                "replay_target_stage": "deliver_full_s2_architect",
                "finding_class": "test-strategy",
                "threshold_limit": 3,
            },
        ),
    ],
)
def test_validate_stage_summary_rejects_partial_replay_bundle(
    label: str,
    partial_bundle: dict[str, object],
) -> None:
    with pytest.raises(StageSummaryValidationError, match="replay"):
        validate_stage_summary({**_base_summary(), **partial_bundle}, label=label)

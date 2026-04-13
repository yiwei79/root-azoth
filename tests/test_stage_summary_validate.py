"""Unit tests for stage_summary_validate.py — BL-035.

Covers: valid/invalid YAML fixtures, every validation branch in
validate_stage_summary(), edge cases for array fields.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HOOKS = Path(__file__).resolve().parent.parent / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from stage_summary_validate import (  # noqa: E402
    StageSummaryValidationError,
    validate_stage_summary,
)


def _valid_doc(**overrides: object) -> dict:
    base = {
        "stage_summary_version": 1,
        "pipeline": "auto",
        "stage_id": "s1-architect",
        "agent": "architect",
        "stage_kind": "research",
        "status": "complete",
        "entropy": "GREEN",
    }
    base.update(overrides)
    return base


# --- Happy path ----------------------------------------------------------


class TestValidDocuments:
    def test_minimal_valid(self) -> None:
        validate_stage_summary(_valid_doc())

    def test_all_optional_fields(self) -> None:
        doc = _valid_doc(
            entropy_delta=5,
            gate_outcome="approved",
            session_id="2026-04-13-test",
            done=["item 1"],
            decisions=["decided X"],
            open=["question 1"],
            artifact_refs=["file.py"],
            next="continue to planner",
        )
        validate_stage_summary(doc)

    @pytest.mark.parametrize("pipeline", ["auto", "deliver", "deliver-full"])
    def test_all_valid_pipelines(self, pipeline: str) -> None:
        validate_stage_summary(_valid_doc(pipeline=pipeline))

    @pytest.mark.parametrize(
        "agent",
        [
            "architect",
            "planner",
            "builder",
            "reviewer",
            "researcher",
            "research-orchestrator",
            "evaluator",
            "prompt-engineer",
            "agent-crafter",
            "context-architect",
        ],
    )
    def test_all_valid_agents(self, agent: str) -> None:
        validate_stage_summary(_valid_doc(agent=agent))

    @pytest.mark.parametrize("kind", ["research", "build", "eval", "audit"])
    def test_all_valid_kinds(self, kind: str) -> None:
        validate_stage_summary(_valid_doc(stage_kind=kind))

    @pytest.mark.parametrize("status", ["complete", "blocked", "needs-input"])
    def test_all_valid_statuses(self, status: str) -> None:
        validate_stage_summary(_valid_doc(status=status))

    @pytest.mark.parametrize("entropy", ["GREEN", "YELLOW", "RED"])
    def test_all_valid_entropy_zones(self, entropy: str) -> None:
        validate_stage_summary(_valid_doc(entropy=entropy))


# --- Structural errors ----------------------------------------------------


class TestStructuralErrors:
    def test_non_dict_raises(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="must be a mapping"):
            validate_stage_summary("not a dict")

    def test_list_raises(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="must be a mapping"):
            validate_stage_summary([1, 2, 3])

    def test_none_raises(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="must be a mapping"):
            validate_stage_summary(None)


# --- Missing required fields ---------------------------------------------


class TestMissingFields:
    @pytest.mark.parametrize(
        "field",
        [
            "stage_summary_version",
            "pipeline",
            "stage_id",
            "agent",
            "stage_kind",
            "status",
            "entropy",
        ],
    )
    def test_missing_required_field(self, field: str) -> None:
        doc = _valid_doc()
        del doc[field]
        with pytest.raises(StageSummaryValidationError, match=f"missing required field '{field}'"):
            validate_stage_summary(doc)


# --- Invalid enum values --------------------------------------------------


class TestInvalidEnums:
    def test_invalid_version(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="stage_summary_version must be 1"):
            validate_stage_summary(_valid_doc(stage_summary_version=2))

    def test_invalid_pipeline(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="invalid pipeline"):
            validate_stage_summary(_valid_doc(pipeline="hotfix"))

    def test_invalid_agent(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="invalid agent"):
            validate_stage_summary(_valid_doc(agent="unknown-agent"))

    def test_invalid_stage_kind(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="invalid stage_kind"):
            validate_stage_summary(_valid_doc(stage_kind="deploy"))

    def test_invalid_status(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="invalid status"):
            validate_stage_summary(_valid_doc(status="running"))

    def test_invalid_entropy(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="invalid entropy"):
            validate_stage_summary(_valid_doc(entropy="green"))


# --- stage_id validation --------------------------------------------------


class TestStageId:
    def test_empty_string_rejected(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="stage_id must be str"):
            validate_stage_summary(_valid_doc(stage_id=""))

    def test_too_long_rejected(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="stage_id must be str"):
            validate_stage_summary(_valid_doc(stage_id="x" * 129))

    def test_max_length_accepted(self) -> None:
        validate_stage_summary(_valid_doc(stage_id="x" * 128))

    def test_non_string_rejected(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="stage_id must be str"):
            validate_stage_summary(_valid_doc(stage_id=42))


# --- Unknown keys ---------------------------------------------------------


class TestUnknownKeys:
    def test_unknown_key_rejected(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="unknown keys"):
            validate_stage_summary(_valid_doc(bogus_field="value"))

    def test_multiple_unknown_keys_listed(self) -> None:
        doc = _valid_doc(foo="a", bar="b")
        with pytest.raises(StageSummaryValidationError, match="unknown keys.*bar.*foo"):
            validate_stage_summary(doc)


# --- Array fields (done, decisions, open) ---------------------------------


class TestArrayFields:
    @pytest.mark.parametrize("field", ["done", "decisions", "open"])
    def test_non_list_rejected(self, field: str) -> None:
        with pytest.raises(StageSummaryValidationError, match=f"{field} must be a list"):
            validate_stage_summary(_valid_doc(**{field: "not a list"}))

    @pytest.mark.parametrize("field", ["done", "decisions", "open"])
    def test_too_many_items_rejected(self, field: str) -> None:
        with pytest.raises(StageSummaryValidationError, match=f"{field} max 5 items"):
            validate_stage_summary(_valid_doc(**{field: [f"item {i}" for i in range(6)]}))

    @pytest.mark.parametrize("field", ["done", "decisions", "open"])
    def test_five_items_accepted(self, field: str) -> None:
        validate_stage_summary(_valid_doc(**{field: [f"item {i}" for i in range(5)]}))

    @pytest.mark.parametrize("field", ["done", "decisions", "open"])
    def test_non_string_item_rejected(self, field: str) -> None:
        with pytest.raises(StageSummaryValidationError, match=f"{field}\\[0\\] must be string"):
            validate_stage_summary(_valid_doc(**{field: [123]}))

    @pytest.mark.parametrize("field", ["done", "decisions", "open"])
    def test_item_too_long_rejected(self, field: str) -> None:
        with pytest.raises(StageSummaryValidationError, match=f"{field}\\[0\\] exceeds 400 chars"):
            validate_stage_summary(_valid_doc(**{field: ["x" * 401]}))

    @pytest.mark.parametrize("field", ["done", "decisions", "open"])
    def test_item_at_400_chars_accepted(self, field: str) -> None:
        validate_stage_summary(_valid_doc(**{field: ["x" * 400]}))

    @pytest.mark.parametrize("field", ["done", "decisions", "open"])
    def test_empty_list_accepted(self, field: str) -> None:
        validate_stage_summary(_valid_doc(**{field: []}))


# --- Label parameter ------------------------------------------------------


class TestLabel:
    def test_custom_label_in_error(self) -> None:
        with pytest.raises(StageSummaryValidationError, match="my-doc"):
            validate_stage_summary("bad", label="my-doc")

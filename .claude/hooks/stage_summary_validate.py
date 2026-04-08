"""Structural validation for BL-012 pipeline stage summaries (hook + pytest reuse)."""

from __future__ import annotations

from typing import Any

VALID_PIPELINES = frozenset({"auto", "deliver", "deliver-full"})
VALID_KINDS = frozenset({"research", "build", "eval", "audit"})
VALID_STATUS = frozenset({"complete", "blocked", "needs-input"})
VALID_ENTROPY = frozenset({"GREEN", "YELLOW", "RED"})
VALID_AGENTS = frozenset(
    {
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
    }
)


class StageSummaryValidationError(Exception):
    pass


def validate_stage_summary(doc: Any, *, label: str = "document") -> None:
    if not isinstance(doc, dict):
        raise StageSummaryValidationError(f"{label}: must be a mapping")
    req = [
        "stage_summary_version",
        "pipeline",
        "stage_id",
        "agent",
        "stage_kind",
        "status",
        "entropy",
    ]
    for k in req:
        if k not in doc:
            raise StageSummaryValidationError(f"{label}: missing required field '{k}'")
    if doc["stage_summary_version"] != 1:
        raise StageSummaryValidationError(f"{label}: stage_summary_version must be 1")
    if doc["pipeline"] not in VALID_PIPELINES:
        raise StageSummaryValidationError(f"{label}: invalid pipeline {doc['pipeline']!r}")
    if doc["agent"] not in VALID_AGENTS:
        raise StageSummaryValidationError(f"{label}: invalid agent {doc['agent']!r}")
    if doc["stage_kind"] not in VALID_KINDS:
        raise StageSummaryValidationError(f"{label}: invalid stage_kind {doc['stage_kind']!r}")
    if doc["status"] not in VALID_STATUS:
        raise StageSummaryValidationError(f"{label}: invalid status {doc['status']!r}")
    if doc["entropy"] not in VALID_ENTROPY:
        raise StageSummaryValidationError(f"{label}: invalid entropy {doc['entropy']!r}")
    sid = doc["stage_id"]
    if not isinstance(sid, str) or not (1 <= len(sid) <= 128):
        raise StageSummaryValidationError(f"{label}: stage_id must be str length 1..128")
    extra = set(doc.keys()) - {
        "stage_summary_version",
        "pipeline",
        "stage_id",
        "agent",
        "stage_kind",
        "status",
        "entropy",
        "entropy_delta",
        "gate_outcome",
        "session_id",
        "done",
        "decisions",
        "open",
        "artifact_refs",
        "next",
    }
    if extra:
        raise StageSummaryValidationError(f"{label}: unknown keys {sorted(extra)}")
    for arr_key in ("done", "decisions", "open"):
        if arr_key in doc:
            v = doc[arr_key]
            if not isinstance(v, list):
                raise StageSummaryValidationError(f"{label}: {arr_key} must be a list")
            if len(v) > 5:
                raise StageSummaryValidationError(f"{label}: {arr_key} max 5 items")
            for i, item in enumerate(v):
                if not isinstance(item, str):
                    raise StageSummaryValidationError(f"{label}: {arr_key}[{i}] must be string")
                if len(item) > 400:
                    raise StageSummaryValidationError(f"{label}: {arr_key}[{i}] exceeds 400 chars")

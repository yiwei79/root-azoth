"""Structural validation for BL-012 pipeline stage summaries (hook + pytest reuse)."""

from __future__ import annotations

from typing import Any

VALID_PIPELINES = frozenset({"auto", "deliver", "deliver-full"})
VALID_KINDS = frozenset({"research", "build", "eval", "audit"})
VALID_STATUS = frozenset({"complete", "blocked", "needs-input"})
VALID_ENTROPY = frozenset({"GREEN", "YELLOW", "RED"})
VALID_FINDING_CLASSES = frozenset(
    {
        "architecture",
        "scope",
        "governance",
        "contract",
        "planning",
        "test-strategy",
        "handoff-completeness",
        "implementation",
        "failing-acceptance",
        "evidence-insufficient",
    }
)
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
REPLAY_FIELDS = frozenset(
    {
        "replay_iteration",
        "replay_target_stage",
        "finding_class",
        "threshold_limit",
        "lineage_artifacts",
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
        "replay_iteration",
        "replay_target_stage",
        "finding_class",
        "threshold_limit",
        "lineage_artifacts",
        "next",
    }
    if extra:
        raise StageSummaryValidationError(f"{label}: unknown keys {sorted(extra)}")
    replay_keys = REPLAY_FIELDS.intersection(doc)
    if replay_keys and replay_keys != REPLAY_FIELDS:
        missing_replay_keys = sorted(REPLAY_FIELDS - replay_keys)
        present_replay_keys = sorted(replay_keys)
        raise StageSummaryValidationError(
            f"{label}: replay metadata must include all five replay fields together; "
            f"present={present_replay_keys}, missing={missing_replay_keys}"
        )
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
    if "replay_iteration" in doc:
        value = doc["replay_iteration"]
        if not isinstance(value, int) or not (1 <= value <= 10):
            raise StageSummaryValidationError(f"{label}: replay_iteration must be int 1..10")
    if "threshold_limit" in doc:
        value = doc["threshold_limit"]
        if not isinstance(value, int) or not (1 <= value <= 10):
            raise StageSummaryValidationError(f"{label}: threshold_limit must be int 1..10")
    if "replay_target_stage" in doc:
        value = doc["replay_target_stage"]
        if not isinstance(value, str) or not (1 <= len(value) <= 128):
            raise StageSummaryValidationError(
                f"{label}: replay_target_stage must be str length 1..128"
            )
    if "finding_class" in doc and doc["finding_class"] not in VALID_FINDING_CLASSES:
        raise StageSummaryValidationError(
            f"{label}: invalid finding_class {doc['finding_class']!r}"
        )
    if "lineage_artifacts" in doc:
        value = doc["lineage_artifacts"]
        if not isinstance(value, list):
            raise StageSummaryValidationError(f"{label}: lineage_artifacts must be a list")
        if len(value) > 10:
            raise StageSummaryValidationError(f"{label}: lineage_artifacts max 10 items")
        for i, item in enumerate(value):
            if not isinstance(item, str):
                raise StageSummaryValidationError(f"{label}: lineage_artifacts[{i}] must be string")
            if len(item) > 512:
                raise StageSummaryValidationError(
                    f"{label}: lineage_artifacts[{i}] exceeds 512 chars"
                )

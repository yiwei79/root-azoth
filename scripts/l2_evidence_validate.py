"""Validate a single L2 evidence record dict (P6-002) before append."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

RECORD_SCHEMA_VERSION = 1
SUMMARY_MAX_LEN = 4096

VALID_PIPELINES = frozenset({"auto", "autonomous-auto", "deliver", "deliver-full"})
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
VALID_EVIDENCE_KINDS = frozenset({"eval_summary", "reviewer_gate", "episode_ref", "manual_eval"})

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


class L2EvidenceValidationError(Exception):
    pass


def validate_l2_evidence_record(doc: Any, *, label: str = "record") -> None:
    if not isinstance(doc, dict):
        raise L2EvidenceValidationError(f"{label}: must be a JSON object")
    req = [
        "record_schema_version",
        "recorded_at",
        "session_id",
        "backlog_id",
        "source_pipeline",
        "source_stage_id",
        "source_agent",
        "evidence_kind",
        "target_surfaces",
        "summary",
        "payload",
    ]
    for k in req:
        if k not in doc:
            raise L2EvidenceValidationError(f"{label}: missing required field {k!r}")
    if doc["record_schema_version"] != RECORD_SCHEMA_VERSION:
        raise L2EvidenceValidationError(
            f"{label}: record_schema_version must be {RECORD_SCHEMA_VERSION}"
        )
    ra = doc["recorded_at"]
    if not isinstance(ra, str) or not _ISO_RE.match(ra):
        raise L2EvidenceValidationError(f"{label}: recorded_at must be ISO-8601 UTC string")
    try:
        if ra.endswith("Z"):
            datetime.fromisoformat(ra.replace("Z", "+00:00"))
        else:
            datetime.fromisoformat(ra)
    except ValueError as e:
        raise L2EvidenceValidationError(f"{label}: invalid recorded_at datetime") from e

    for key, maxlen in (("session_id", 128), ("backlog_id", 64), ("source_stage_id", 128)):
        v = doc[key]
        if not isinstance(v, str) or not (1 <= len(v) <= maxlen):
            raise L2EvidenceValidationError(f"{label}: {key} must be non-empty str, max {maxlen}")

    if doc["source_pipeline"] not in VALID_PIPELINES:
        raise L2EvidenceValidationError(f"{label}: invalid source_pipeline")
    if doc["source_agent"] not in VALID_AGENTS:
        raise L2EvidenceValidationError(f"{label}: invalid source_agent")
    if doc["evidence_kind"] not in VALID_EVIDENCE_KINDS:
        raise L2EvidenceValidationError(f"{label}: invalid evidence_kind")

    ts = doc["target_surfaces"]
    if not isinstance(ts, list) or len(ts) < 1:
        raise L2EvidenceValidationError(f"{label}: target_surfaces must be non-empty array")
    for i, p in enumerate(ts):
        if not isinstance(p, str) or not (1 <= len(p) <= 512):
            raise L2EvidenceValidationError(
                f"{label}: target_surfaces[{i}] must be non-empty str, max 512 chars"
            )

    summary = doc["summary"]
    if not isinstance(summary, str) or not (1 <= len(summary) <= SUMMARY_MAX_LEN):
        raise L2EvidenceValidationError(f"{label}: summary must be str length 1..{SUMMARY_MAX_LEN}")

    if not isinstance(doc["payload"], dict):
        raise L2EvidenceValidationError(f"{label}: payload must be an object")

    extra = set(doc.keys()) - set(req)
    if extra:
        raise L2EvidenceValidationError(f"{label}: unknown top-level keys {sorted(extra)}")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

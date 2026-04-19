#!/usr/bin/env python3
"""Shared T-009 Phase 1 evaluator for repo-local research capsules."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Mapping
from urllib.parse import urlparse

RESEARCH_BANK_DIR = PurePosixPath(".azoth/research")
RESEARCH_EVIDENCE_KIND = "repo-local"
RESEARCH_EVIDENCE_REQUIRED_FIELDS = frozenset({"kind", "session_id", "path"})
CAPSULE_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "source_session_id",
        "goal",
        "captured_at",
        "volatility",
        "limitations",
        "questions",
    }
)
QUESTION_REQUIRED_FIELDS = frozenset(
    {"question_id", "question", "status", "answered_at", "fresh_until"}
)
QUESTION_ALLOWED_STATUSES = frozenset({"answered", "conflicting"})
WINDOWS_DRIVE_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def parse_iso(raw: object) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00") if text.endswith("Z") else text
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalized_rel_path(path_str: str) -> PurePosixPath | None:
    normalized = path_str.replace("\\", "/")
    parsed = urlparse(normalized)
    if not normalized:
        return None
    if Path(path_str).is_absolute() or WINDOWS_DRIVE_ABSOLUTE_RE.match(path_str):
        return None
    if parsed.scheme:
        return None
    parts = PurePosixPath(normalized).parts
    if not parts or ".." in parts:
        return None
    return PurePosixPath(*parts)


def _slugify(value: object, *, max_length: int) -> str:
    slug = NON_ALNUM_RE.sub("-", str(value or "").strip().lower()).strip("-")
    if len(slug) <= max_length:
        return slug
    return slug[:max_length].rstrip("-")


def derive_required_questions(goal: str | None, backlog_id: str | None) -> list[str]:
    """Derive Phase 1 required question ids from durable scope inputs only."""
    required = ["phase-1-reuse"]

    backlog_slug = _slugify(backlog_id, max_length=24)
    goal_slug = _slugify(goal, max_length=48)
    if backlog_slug == "ad-hoc":
        backlog_slug = ""

    derived_question_id = ""
    if backlog_slug and goal_slug:
        derived_question_id = f"phase-1-slice-{backlog_slug}-{goal_slug}"
    elif backlog_slug:
        derived_question_id = f"phase-1-slice-{backlog_slug}"
    elif goal_slug:
        derived_question_id = f"phase-1-goal-{goal_slug}"

    if derived_question_id and derived_question_id not in required:
        required.append(derived_question_id)

    return required


def validate_research_evidence_reference(gate: Mapping[str, object]) -> dict:
    """Validate top-level research metadata without enforcing capsule freshness."""
    research_required = gate.get("research_required")
    if not isinstance(research_required, bool):
        return {
            "ok": False,
            "evidence_path": None,
            "reasons": ["pipeline-gate.json research_required must be a boolean."],
        }
    if research_required is False:
        return {"ok": True, "evidence_path": None, "reasons": []}

    evidence = gate.get("research_evidence")
    if not isinstance(evidence, Mapping):
        return {
            "ok": False,
            "evidence_path": None,
            "reasons": [
                "pipeline-gate.json research_evidence must be an object when research_required "
                "is true."
            ],
        }

    missing = RESEARCH_EVIDENCE_REQUIRED_FIELDS - set(evidence.keys())
    if missing:
        return {
            "ok": False,
            "evidence_path": None,
            "reasons": [f"pipeline-gate.json research_evidence missing fields: {sorted(missing)}."],
        }

    kind = str(evidence.get("kind") or "").strip()
    if kind != RESEARCH_EVIDENCE_KIND:
        return {
            "ok": False,
            "evidence_path": None,
            "reasons": [
                f"pipeline-gate.json research_evidence.kind must equal {RESEARCH_EVIDENCE_KIND!r}."
            ],
        }

    evidence_session_id = str(evidence.get("session_id") or "").strip()
    if evidence_session_id != str(gate.get("session_id") or "").strip():
        return {
            "ok": False,
            "evidence_path": None,
            "reasons": [
                "pipeline-gate.json research_evidence.session_id must match "
                "pipeline-gate session_id."
            ],
        }

    evidence_path = str(evidence.get("path") or "").strip()
    if not evidence_path:
        return {
            "ok": False,
            "evidence_path": None,
            "reasons": ["pipeline-gate.json research_evidence.path must be a repo-relative path."],
        }
    if Path(evidence_path).is_absolute() or WINDOWS_DRIVE_ABSOLUTE_RE.match(evidence_path):
        return {
            "ok": False,
            "evidence_path": None,
            "reasons": ["pipeline-gate.json research_evidence.path must be repo-relative."],
        }

    normalized_path = _normalized_rel_path(evidence_path)
    if normalized_path is None:
        parsed_path = urlparse(evidence_path.replace("\\", "/"))
        if parsed_path.scheme:
            reason = "pipeline-gate.json research_evidence.path must not use a URI scheme."
        else:
            reason = "pipeline-gate.json research_evidence.path must be repo-relative."
        return {"ok": False, "evidence_path": None, "reasons": [reason]}

    return {"ok": True, "evidence_path": normalized_path.as_posix(), "reasons": []}


def evaluate_research_sufficiency(
    repo_root: Path,
    evidence_path: str,
    *,
    goal: str | None = None,
    backlog_id: str | None = None,
) -> dict:
    """Evaluate whether a repo-local research capsule is reusable for Phase 1."""
    normalized_path = _normalized_rel_path(str(evidence_path or "").strip())
    if normalized_path is None:
        return {
            "outcome": "research_missing",
            "reasons": ["Research evidence path must be repo-relative."],
        }

    if normalized_path.parent != RESEARCH_BANK_DIR:
        return {
            "outcome": "research_missing",
            "reasons": ["Research capsule must live under .azoth/research/ for Phase 1 reuse."],
        }

    if normalized_path.suffix != ".json":
        return {
            "outcome": "research_missing",
            "reasons": ["Research capsule must use the .json extension."],
        }

    capsule_path = repo_root / normalized_path
    if not capsule_path.is_file():
        return {
            "outcome": "research_missing",
            "reasons": [f"Research capsule is missing: {normalized_path.as_posix()}."],
        }

    try:
        capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "outcome": "research_missing",
            "reasons": [f"Research capsule is malformed: {exc}"],
        }

    if not isinstance(capsule, dict):
        return {
            "outcome": "research_missing",
            "reasons": ["Research capsule must be a JSON object."],
        }

    missing_capsule = CAPSULE_REQUIRED_FIELDS - set(capsule.keys())
    if missing_capsule:
        return {
            "outcome": "research_missing",
            "reasons": [f"Research capsule missing fields: {sorted(missing_capsule)}."],
        }

    if capsule.get("schema_version") != 1:
        return {
            "outcome": "research_missing",
            "reasons": ["Research capsule schema_version must equal 1."],
        }

    if not isinstance(capsule.get("limitations"), list):
        return {
            "outcome": "research_missing",
            "reasons": ["Research capsule limitations must be a list."],
        }

    questions = capsule.get("questions")
    if not isinstance(questions, list):
        return {
            "outcome": "research_missing",
            "reasons": ["Research capsule questions must be a list."],
        }
    if not questions:
        return {
            "outcome": "research_missing",
            "reasons": ["Research capsule must include at least one question."],
        }

    required_questions = derive_required_questions(goal=goal, backlog_id=backlog_id)
    now = datetime.now(timezone.utc)
    refresh_reasons: list[str] = []
    question_details: dict[str, dict[str, object]] = {}
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            return {
                "outcome": "research_missing",
                "reasons": [f"Research question #{index + 1} must be an object."],
            }

        missing_question = QUESTION_REQUIRED_FIELDS - set(question.keys())
        if missing_question:
            return {
                "outcome": "research_missing",
                "reasons": [f"Research question missing fields: {sorted(missing_question)}."],
            }

        question_id = str(question.get("question_id") or "").strip()
        if not question_id:
            return {
                "outcome": "research_missing",
                "reasons": ["Research question question_id must be a non-empty string."],
            }

        status = str(question.get("status") or "").strip()
        if status not in QUESTION_ALLOWED_STATUSES:
            return {
                "outcome": "research_missing",
                "reasons": [
                    f"Research question status must be one of {sorted(QUESTION_ALLOWED_STATUSES)}."
                ],
            }

        answered_at = parse_iso(question.get("answered_at"))
        if answered_at is None:
            return {
                "outcome": "research_missing",
                "reasons": ["Research question answered_at must be valid ISO 8601."],
            }

        fresh_until = parse_iso(question.get("fresh_until"))
        if fresh_until is None:
            return {
                "outcome": "research_missing",
                "reasons": ["Research question fresh_until must be valid ISO 8601."],
            }

        question_details[question_id] = {
            "status": status,
            "fresh_until": fresh_until,
        }

    missing_required_questions = [
        question_id for question_id in required_questions if question_id not in question_details
    ]
    if missing_required_questions:
        refresh_reasons.append(
            f"Research capsule missing required questions: {missing_required_questions}."
        )

    for question_id in required_questions:
        details = question_details.get(question_id)
        if details is None:
            continue
        status = str(details["status"])
        fresh_until = details["fresh_until"]
        if status == "conflicting":
            refresh_reasons.append(f"Research question {question_id} is conflicting.")
        elif isinstance(fresh_until, datetime) and fresh_until <= now:
            refresh_reasons.append(f"Research question {question_id} is stale.")

    if refresh_reasons:
        return {"outcome": "research_refresh_needed", "reasons": refresh_reasons}

    return {"outcome": "research_sufficient", "reasons": []}

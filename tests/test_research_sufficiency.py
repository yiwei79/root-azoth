from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _future_iso(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()


def _load_module():
    try:
        return importlib.import_module("research_sufficiency")
    except ModuleNotFoundError as exc:
        pytest.fail(
            "Expected scripts/research_sufficiency.py for the shared T-009 Phase 1 evaluator: "
            f"{exc}"
        )


def _evaluate(
    repo_root: Path,
    evidence_path: str,
    *,
    goal: str | None = None,
    backlog_id: str | None = None,
) -> dict:
    module = _load_module()
    evaluate = getattr(module, "evaluate_research_sufficiency", None)
    assert callable(
        evaluate
    ), "research_sufficiency.evaluate_research_sufficiency must exist for T-009 Phase 1"
    result = evaluate(
        repo_root=repo_root,
        evidence_path=evidence_path,
        goal=goal,
        backlog_id=backlog_id,
    )
    assert isinstance(result, dict)
    assert "outcome" in result
    assert "reasons" in result
    assert isinstance(result["reasons"], list)
    return result


def _reasons_text(result: dict) -> str:
    return " ".join(str(reason) for reason in result["reasons"]).lower()


def _derive_required_questions(goal: str, backlog_id: str) -> list[str]:
    module = _load_module()
    derive = getattr(module, "derive_required_questions", None)
    assert callable(derive), "research_sufficiency.derive_required_questions must exist"
    question_ids = derive(goal=goal, backlog_id=backlog_id)
    assert isinstance(question_ids, list)
    return question_ids


def _write_research_capsule(
    repo_root: Path,
    rel_path: str,
    *,
    source_session_id: str = "test-session",
    question_status: str = "answered",
    question_overrides: dict | None = None,
    capsule_overrides: dict | None = None,
    remove_question_keys: list[str] | None = None,
    remove_capsule_keys: list[str] | None = None,
) -> Path:
    capsule_path = repo_root / rel_path
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    question = {
        "question_id": "phase-1-reuse",
        "question": "Can this repo-local research capsule be reused?",
        "status": question_status,
        "answered_at": datetime.now(timezone.utc).isoformat(),
        "fresh_until": _future_iso(),
    }
    for key in remove_question_keys or []:
        question.pop(key, None)
    if question_overrides:
        question.update(question_overrides)
    capsule = {
        "schema_version": 1,
        "source_session_id": source_session_id,
        "goal": "T-009: Local research capsule bank + sufficiency checker",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "volatility": "bounded",
        "limitations": [],
        "questions": [question],
    }
    for key in remove_capsule_keys or []:
        capsule.pop(key, None)
    if capsule_overrides:
        capsule.update(capsule_overrides)
    capsule_path.write_text(json.dumps(capsule), encoding="utf-8")
    return capsule_path


@pytest.mark.parametrize(
    ("evidence_path", "expected_fragment"),
    [
        ("notes/test-session.json", ".azoth/research"),
        (".azoth/research/test-session.md", ".json"),
    ],
)
def test_evaluate_research_sufficiency_requires_json_capsules_under_repo_local_bank(
    tmp_path: Path,
    evidence_path: str,
    expected_fragment: str,
) -> None:
    result = _evaluate(tmp_path, evidence_path)

    assert result["outcome"] == "research_missing"
    assert expected_fragment in _reasons_text(result)


def test_evaluate_research_sufficiency_returns_missing_for_absent_capsule_file(
    tmp_path: Path,
) -> None:
    result = _evaluate(tmp_path, ".azoth/research/missing.json")

    assert result["outcome"] == "research_missing"
    assert "missing" in _reasons_text(result)


def test_evaluate_research_sufficiency_returns_missing_for_schema_invalid_capsule(
    tmp_path: Path,
) -> None:
    _write_research_capsule(
        tmp_path,
        ".azoth/research/test-session.json",
        remove_capsule_keys=["source_session_id"],
    )

    result = _evaluate(tmp_path, ".azoth/research/test-session.json")

    assert result["outcome"] == "research_missing"
    assert "source_session_id" in _reasons_text(result)


def test_evaluate_research_sufficiency_returns_missing_for_question_missing_required_field(
    tmp_path: Path,
) -> None:
    _write_research_capsule(
        tmp_path,
        ".azoth/research/test-session.json",
        remove_question_keys=["answered_at"],
    )

    result = _evaluate(tmp_path, ".azoth/research/test-session.json")

    assert result["outcome"] == "research_missing"
    assert "answered_at" in _reasons_text(result)


def test_evaluate_research_sufficiency_returns_missing_when_required_questions_are_absent(
    tmp_path: Path,
) -> None:
    _write_research_capsule(
        tmp_path,
        ".azoth/research/test-session.json",
        capsule_overrides={"questions": []},
    )

    result = _evaluate(tmp_path, ".azoth/research/test-session.json")

    assert result["outcome"] == "research_missing"
    assert "question" in _reasons_text(result)


def test_evaluate_research_sufficiency_returns_refresh_needed_for_stale_answer(
    tmp_path: Path,
) -> None:
    _write_research_capsule(
        tmp_path,
        ".azoth/research/test-session.json",
        question_overrides={"fresh_until": _past_iso()},
    )

    result = _evaluate(tmp_path, ".azoth/research/test-session.json")

    assert result["outcome"] == "research_refresh_needed"
    assert "fresh" in _reasons_text(result) or "stale" in _reasons_text(result)


def test_evaluate_research_sufficiency_returns_missing_for_invalid_question_status(
    tmp_path: Path,
) -> None:
    _write_research_capsule(
        tmp_path,
        ".azoth/research/test-session.json",
        question_overrides={"status": "partial"},
    )

    result = _evaluate(tmp_path, ".azoth/research/test-session.json")

    assert result["outcome"] == "research_missing"
    assert "status" in _reasons_text(result)


def test_evaluate_research_sufficiency_returns_refresh_needed_for_conflicting_question_status(
    tmp_path: Path,
) -> None:
    _write_research_capsule(
        tmp_path,
        ".azoth/research/test-session.json",
        question_overrides={"status": "conflicting"},
    )

    result = _evaluate(tmp_path, ".azoth/research/test-session.json")

    assert result["outcome"] == "research_refresh_needed"
    assert "conflict" in _reasons_text(result) or "conflicting" in _reasons_text(result)


def test_evaluate_research_sufficiency_returns_refresh_needed_when_slice_required_question_is_missing(
    tmp_path: Path,
) -> None:
    goal = "T-009: Local research capsule bank + sufficiency checker"
    backlog_id = "T-009"
    required_question_ids = _derive_required_questions(goal, backlog_id)
    _write_research_capsule(
        tmp_path,
        ".azoth/research/test-session.json",
        capsule_overrides={"goal": goal},
    )

    result = _evaluate(
        tmp_path,
        ".azoth/research/test-session.json",
        goal=goal,
        backlog_id=backlog_id,
    )

    assert result["outcome"] == "research_refresh_needed"
    assert required_question_ids[-1] in _reasons_text(result)


def test_evaluate_research_sufficiency_returns_sufficient_when_slice_required_questions_are_covered(
    tmp_path: Path,
) -> None:
    goal = "T-009: Local research capsule bank + sufficiency checker"
    backlog_id = "T-009"
    required_question_ids = _derive_required_questions(goal, backlog_id)
    now = datetime.now(timezone.utc).isoformat()
    _write_research_capsule(
        tmp_path,
        ".azoth/research/test-session.json",
        capsule_overrides={
            "goal": goal,
            "questions": [
                {
                    "question_id": question_id,
                    "question": f"Coverage for {question_id}",
                    "status": "answered",
                    "answered_at": now,
                    "fresh_until": _future_iso(),
                }
                for question_id in required_question_ids
            ],
        },
    )

    result = _evaluate(
        tmp_path,
        ".azoth/research/test-session.json",
        goal=goal,
        backlog_id=backlog_id,
    )

    assert result["outcome"] == "research_sufficient"
    assert result["reasons"] == []


def test_evaluate_research_sufficiency_returns_sufficient_for_reusable_capsule(
    tmp_path: Path,
) -> None:
    _write_research_capsule(tmp_path, ".azoth/research/test-session.json")

    result = _evaluate(tmp_path, ".azoth/research/test-session.json")

    assert result["outcome"] == "research_sufficient"
    assert result["reasons"] == []

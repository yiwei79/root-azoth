from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from personal_knowledge_validate import (  # noqa: E402
    PersonalKnowledgeValidationError,
    validate_card,
    validate_import_batch,
    validate_root,
)


def _write_yaml(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _valid_source_ref(**overrides: Any) -> dict[str, Any]:
    source_ref = {
        "repo": "root-azoth",
        "path": "docs/personal-control-plane/PERSONAL-KNOWLEDGE-ARCHITECTURE.md",
        "commit": "b0763a8",
    }
    source_ref.update(overrides)
    return source_ref


def _valid_card(**overrides: Any) -> dict[str, Any]:
    card = {
        "schema_version": 1,
        "id": "kb-root-azoth-001",
        "title": "Green campaign is not release readiness",
        "type": "operating_principle",
        "scope": ["azoth", "release"],
        "authority_home": "root-azoth",
        "privacy": "private",
        "status": "active",
        "confidence": "high",
        "freshness": {
            "reviewed_at": "2026-04-29",
            "review_after": "2026-05-29",
        },
        "source_refs": [_valid_source_ref()],
        "allowed_use": ["session_start_recall", "release_planning"],
        "forbidden_use": ["automatic_project_mutation", "public_release_claim"],
        "body": (
            "A completed autonomous campaign proves that campaign budget ended. "
            "Release readiness still requires packaging, deploy parity, validation, "
            "and clean state."
        ),
    }
    card.update(overrides)
    return card


def _valid_candidate(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "candidate_id": "candidate-001",
        "decision": "approved",
        "rationale": (
            "Candidate captures a small release-readiness lesson from approved root-side "
            "evidence without deploying it before operator review."
        ),
        "safety_classification": "approved_source_candidate",
        "authority_home": "root-azoth",
        "privacy": "private",
        "freshness": {
            "reviewed_at": "2026-04-29",
            "review_after": "2026-05-29",
        },
        "card_path": ".azoth/knowledge/cards/root-azoth/kb-root-azoth-001.yaml",
        "source_refs": [_valid_source_ref()],
        "proposed_card": _valid_card(),
    }
    candidate.update(overrides)
    return candidate


def _valid_batch(**overrides: Any) -> dict[str, Any]:
    batch = {
        "schema_version": 1,
        "id": "batch-000-root-azoth",
        "created_at": "2026-04-29T12:00:00Z",
        "source_plane": "root-azoth",
        "source_refs": [_valid_source_ref()],
        "candidates": [_valid_candidate()],
        "operator_review": {
            "approved": True,
            "approved_by": "operator",
            "approved_at": "2026-04-29T12:05:00Z",
        },
    }
    batch.update(overrides)
    return batch


def _write_empty_skeleton(root: Path) -> Path:
    knowledge = root / ".azoth" / "knowledge"
    (knowledge / "cards" / "root-azoth").mkdir(parents=True)
    (knowledge / "cards" / "projects").mkdir(parents=True)
    (knowledge / "cards" / "personal").mkdir(parents=True)
    (knowledge / "indexes").mkdir(parents=True)
    (knowledge / "imports" / "batches").mkdir(parents=True)
    (knowledge / "README.md").write_text("# Personal knowledge\n", encoding="utf-8")
    _write_yaml(
        knowledge / "policy.yaml",
        {
            "schema_version": 1,
            "policy": {
                "architecture": "federated_with_central_index",
                "bulk_imports_allowed": False,
                "silent_inbox_draining_allowed": False,
                "automatic_source_refresh_allowed": False,
                "project_writes_require_project_scope": True,
                "credentials_in_repo_allowed": False,
                "cards_require_source_refs": True,
                "cards_require_freshness": True,
                "import_batches_require_operator_approval": True,
            },
            "retrieval": {
                "max_cards_default": 5,
                "include_source_refs": True,
                "include_freshness_status": True,
            },
        },
    )
    _write_yaml(knowledge / "preferences.yaml", {"schema_version": 1, "preferences": []})
    _write_yaml(knowledge / "principles.yaml", {"schema_version": 1, "principles": []})
    _write_yaml(knowledge / "glossary.yaml", {"schema_version": 1, "terms": []})
    _write_yaml(knowledge / "indexes" / "topic-index.yaml", {"schema_version": 1, "topics": []})
    _write_yaml(
        knowledge / "indexes" / "authority-index.yaml",
        {"schema_version": 1, "authorities": []},
    )
    _write_yaml(knowledge / "imports" / "ledger.yaml", {"schema_version": 1, "imports": []})
    return knowledge


def test_schema_files_encode_personal_knowledge_contract() -> None:
    card_schema = yaml.safe_load(
        (ROOT / "schemas" / "personal-knowledge-card.schema.yaml").read_text(encoding="utf-8")
    )
    batch_schema = yaml.safe_load(
        (ROOT / "schemas" / "personal-knowledge-import-batch.schema.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert "source_refs" in card_schema["required"]
    assert card_schema["constraints"]["review_after_required_for_active"] is True
    assert card_schema["enums"]["type"] == [
        "operating_principle",
        "operator_preference",
        "project_summary",
        "source_note",
        "toolkit_lesson",
        "decision_context",
        "glossary_term",
    ]
    assert batch_schema["constraints"]["operator_review_required_before_deploy"] is True
    assert "rationale" in batch_schema["candidate_required"]
    assert "safety_classification" in batch_schema["candidate_required"]
    assert "privacy" in batch_schema["candidate_required"]
    assert "authority_home" in batch_schema["candidate_required"]
    assert "freshness" in batch_schema["candidate_required"]
    assert batch_schema["enums"]["safety_classification"] == [
        "approved_source_candidate",
        "manual_excerpt_required",
        "blocked_raw_bulk_import",
    ]
    assert batch_schema["enums"]["candidate_decision"] == [
        "approved",
        "rejected",
        "revise",
        "defer",
    ]


def test_valid_card_passes(tmp_path: Path) -> None:
    card_path = _write_yaml(tmp_path / "card.yaml", _valid_card())

    validate_card(card_path)


def test_card_required_fields_and_enums_fail_closed(tmp_path: Path) -> None:
    missing_path = _write_yaml(tmp_path / "missing.yaml", _valid_card(title=None))
    enum_path = _write_yaml(tmp_path / "enum.yaml", _valid_card(type="folk_wisdom"))

    with pytest.raises(PersonalKnowledgeValidationError, match="title"):
        validate_card(missing_path)
    with pytest.raises(PersonalKnowledgeValidationError, match="type"):
        validate_card(enum_path)


def test_card_requires_source_refs_and_safe_source_paths(tmp_path: Path) -> None:
    no_source_path = _write_yaml(tmp_path / "no-source.yaml", _valid_card(source_refs=[]))
    absolute_source_path = _write_yaml(
        tmp_path / "absolute-source.yaml",
        _valid_card(source_refs=[_valid_source_ref(path="/Users/yiwei/secret.txt")]),
    )
    traversal_source_path = _write_yaml(
        tmp_path / "traversal-source.yaml",
        _valid_card(source_refs=[_valid_source_ref(path="../secret.txt")]),
    )

    with pytest.raises(PersonalKnowledgeValidationError, match="source_refs"):
        validate_card(no_source_path)
    with pytest.raises(PersonalKnowledgeValidationError, match="safe relative"):
        validate_card(absolute_source_path)
    with pytest.raises(PersonalKnowledgeValidationError, match="safe relative"):
        validate_card(traversal_source_path)


def test_active_card_requires_review_after_and_body_bounds(tmp_path: Path) -> None:
    freshness = {"reviewed_at": "2026-04-29"}
    missing_review_after_path = _write_yaml(
        tmp_path / "missing-review-after.yaml",
        _valid_card(freshness=freshness),
    )
    short_body_path = _write_yaml(tmp_path / "short-body.yaml", _valid_card(body="too short"))

    with pytest.raises(PersonalKnowledgeValidationError, match="review_after"):
        validate_card(missing_review_after_path)
    with pytest.raises(PersonalKnowledgeValidationError, match="body"):
        validate_card(short_body_path)


def test_valid_import_batch_passes(tmp_path: Path) -> None:
    batch_path = _write_yaml(tmp_path / "batch.yaml", _valid_batch())

    validate_import_batch(batch_path)


def test_deferred_pre_deployment_batch_requires_review_metadata(tmp_path: Path) -> None:
    deferred = _valid_candidate(decision="defer")
    deferred.pop("card_path")
    batch_path = _write_yaml(
        tmp_path / "batch.yaml",
        _valid_batch(
            candidates=[deferred],
            operator_review={"approved": False, "reviewed_by": "operator"},
        ),
    )

    validate_import_batch(batch_path)


def test_batch_candidate_requires_rationale(tmp_path: Path) -> None:
    candidate = _valid_candidate(decision="defer")
    candidate.pop("card_path")
    candidate.pop("rationale")
    batch_path = _write_yaml(
        tmp_path / "batch.yaml",
        _valid_batch(
            candidates=[candidate],
            operator_review={"approved": False, "reviewed_by": "operator"},
        ),
    )

    with pytest.raises(PersonalKnowledgeValidationError, match="rationale"):
        validate_import_batch(batch_path)


def test_batch_candidate_invalid_safety_classification_fails_closed(tmp_path: Path) -> None:
    candidate = _valid_candidate(decision="defer", safety_classification="trust_me")
    candidate.pop("card_path")
    batch_path = _write_yaml(
        tmp_path / "batch.yaml",
        _valid_batch(
            candidates=[candidate],
            operator_review={"approved": False, "reviewed_by": "operator"},
        ),
    )

    with pytest.raises(PersonalKnowledgeValidationError, match="safety_classification"):
        validate_import_batch(batch_path)


@pytest.mark.parametrize(
    ("candidate_update", "expected_match"),
    [
        ({"privacy": "broadcast"}, "privacy"),
        ({"authority_home": ""}, "authority_home"),
        ({"freshness": {"review_after": "2026-05-29"}}, "freshness.reviewed_at"),
        ({"freshness": {"reviewed_at": "2026-04-29"}}, "freshness.review_after"),
        ({"freshness": {"reviewed_at": "soon", "review_after": "2026-05-29"}}, "freshness.reviewed_at"),
        ({"freshness": {"reviewed_at": "2026-04-29", "review_after": "later"}}, "freshness.review_after"),
    ],
)
def test_batch_candidate_review_metadata_fails_closed(
    tmp_path: Path,
    candidate_update: dict[str, Any],
    expected_match: str,
) -> None:
    candidate = _valid_candidate(decision="defer", **candidate_update)
    candidate.pop("card_path")
    batch_path = _write_yaml(
        tmp_path / "batch.yaml",
        _valid_batch(
            candidates=[candidate],
            operator_review={"approved": False, "reviewed_by": "operator"},
        ),
    )

    with pytest.raises(PersonalKnowledgeValidationError, match=expected_match):
        validate_import_batch(batch_path)


def test_batch_enums_fail_closed(tmp_path: Path) -> None:
    bad_plane_path = _write_yaml(
        tmp_path / "bad-plane.yaml",
        _valid_batch(source_plane="unbounded-memory"),
    )
    bad_decision_path = _write_yaml(
        tmp_path / "bad-decision.yaml",
        _valid_batch(candidates=[_valid_candidate(decision="ship_it")]),
    )

    with pytest.raises(PersonalKnowledgeValidationError, match="source_plane"):
        validate_import_batch(bad_plane_path)
    with pytest.raises(PersonalKnowledgeValidationError, match="decision"):
        validate_import_batch(bad_decision_path)


def test_batch_approved_candidate_requires_safe_card_path(tmp_path: Path) -> None:
    missing_path = _write_yaml(
        tmp_path / "missing-card-path.yaml",
        _valid_batch(candidates=[_valid_candidate(card_path=None)]),
    )
    unsafe_path = _write_yaml(
        tmp_path / "unsafe-card-path.yaml",
        _valid_batch(candidates=[_valid_candidate(card_path=".azoth/memory/raw.yaml")]),
    )
    traversal_path = _write_yaml(
        tmp_path / "traversal-card-path.yaml",
        _valid_batch(candidates=[_valid_candidate(card_path=".azoth/knowledge/cards/../raw.yaml")]),
    )

    with pytest.raises(PersonalKnowledgeValidationError, match="card_path"):
        validate_import_batch(missing_path)
    with pytest.raises(PersonalKnowledgeValidationError, match=".azoth/knowledge/cards"):
        validate_import_batch(unsafe_path)
    with pytest.raises(PersonalKnowledgeValidationError, match="safe relative"):
        validate_import_batch(traversal_path)


def test_batch_rejected_candidate_requires_reason(tmp_path: Path) -> None:
    rejected = _valid_candidate(decision="rejected")
    rejected.pop("card_path")
    rejected.pop("proposed_card")
    batch_path = _write_yaml(tmp_path / "batch.yaml", _valid_batch(candidates=[rejected]))

    with pytest.raises(PersonalKnowledgeValidationError, match="rejection_reason"):
        validate_import_batch(batch_path)


def test_batch_requires_operator_approval_before_deploy(tmp_path: Path) -> None:
    operator_review = {"approved": False, "reviewed_by": "operator"}
    batch_path = _write_yaml(
        tmp_path / "batch.yaml",
        _valid_batch(operator_review=operator_review),
    )

    with pytest.raises(PersonalKnowledgeValidationError, match="operator_review.approved"):
        validate_import_batch(batch_path)


def test_empty_skeleton_root_validation_passes_and_rejects_card_files(tmp_path: Path) -> None:
    knowledge = _write_empty_skeleton(tmp_path)

    validate_root(tmp_path, empty_skeleton=True)

    _write_yaml(knowledge / "cards" / "root-azoth" / "kb-root-azoth-001.yaml", _valid_card())

    with pytest.raises(PersonalKnowledgeValidationError, match="empty skeleton"):
        validate_root(tmp_path, empty_skeleton=True)


def test_empty_skeleton_root_validation_rejects_import_batch_files(tmp_path: Path) -> None:
    knowledge = _write_empty_skeleton(tmp_path)
    _write_yaml(knowledge / "imports" / "batches" / "batch-000-root-azoth.yaml", _valid_batch())

    with pytest.raises(PersonalKnowledgeValidationError, match="empty skeleton"):
        validate_root(tmp_path, empty_skeleton=True)


def test_root_validation_requires_skeleton_files_and_parseable_yaml(tmp_path: Path) -> None:
    knowledge = _write_empty_skeleton(tmp_path)
    (knowledge / "policy.yaml").write_text("policy: [unterminated\n", encoding="utf-8")

    with pytest.raises(PersonalKnowledgeValidationError, match="policy.yaml"):
        validate_root(tmp_path)


def test_cli_success_and_failure_messages(tmp_path: Path) -> None:
    valid_card_path = _write_yaml(tmp_path / "valid-card.yaml", _valid_card())
    invalid_card_path = _write_yaml(tmp_path / "invalid-card.yaml", _valid_card(source_refs=[]))

    ok = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "personal_knowledge_validate.py"),
            "--card",
            str(valid_card_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    failed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "personal_knowledge_validate.py"),
            "--card",
            str(invalid_card_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert ok.returncode == 0
    assert ok.stdout.strip() == "personal knowledge validation OK"
    assert failed.returncode == 1
    assert "personal knowledge validation failed:" in failed.stdout
    assert "- " in failed.stdout

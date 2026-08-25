from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
RECALL_SCRIPT = SCRIPTS_DIR / "personal_knowledge_recall.py"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


EXPECTED_OUTPUT_KEYS = {
    "card_id",
    "title",
    "type",
    "scope",
    "authority_home",
    "privacy",
    "status",
    "confidence",
    "freshness_status",
    "source_refs",
    "allowed_use",
    "forbidden_use",
    "match_reason",
    "advisory_authority",
}


def _write_yaml(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _card(card_id: str, **overrides: Any) -> dict[str, Any]:
    cards: dict[str, dict[str, Any]] = {
        "kb-root-azoth-001": {
            "title": "Green campaign completion is not release readiness",
            "type": "operating_principle",
            "scope": ["azoth", "release"],
            "confidence": "high",
            "source_path": ".azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PREFLIGHT-EVIDENCE.md",
            "allowed_use": ["session_start_recall", "release_planning"],
            "forbidden_use": ["automatic_project_mutation", "public_release_claim"],
        },
        "kb-root-azoth-002": {
            "title": "Memory needs read-back into action selection",
            "type": "toolkit_lesson",
            "scope": ["azoth", "memory", "operations"],
            "confidence": "high",
            "source_path": ".azoth/memory/patterns.yaml",
            "allowed_use": ["session_start_recall", "action_selection"],
            "forbidden_use": ["raw_memory_bulk_import", "governance_mutation"],
        },
        "kb-root-azoth-003": {
            "title": "No silent inbox draining or automatic intake decisions",
            "type": "operating_principle",
            "scope": ["azoth", "intake", "personal-root"],
            "confidence": "high",
            "source_path": ".azoth/roadmap-specs/v0.2.0/PERSONAL-ROOT-DEPLOYMENT-MODEL.md",
            "allowed_use": ["session_start_recall", "intake_planning"],
            "forbidden_use": ["silent_inbox_draining", "automatic_intake_decision"],
        },
        "kb-root-azoth-004": {
            "title": "Route-first workflows beat stale chat-memory continuation",
            "type": "toolkit_lesson",
            "scope": ["azoth", "routing", "autonomous-auto"],
            "confidence": "high",
            "source_path": ".azoth/memory/patterns.yaml",
            "allowed_use": ["session_start_recall", "route_selection"],
            "forbidden_use": ["bypass_scope_gate", "continue_from_chat_only_state"],
        },
        "kb-root-azoth-005": {
            "title": "Docs-first architecture slices should precede new implementation gaps",
            "type": "decision_context",
            "scope": ["azoth", "architecture", "planning"],
            "confidence": "medium",
            "source_path": ".azoth/roadmap-specs/v0.2.0/PERSONAL-ROOT-DEPLOYMENT-MODEL.md",
            "allowed_use": ["planning", "architecture_review"],
            "forbidden_use": ["skip_implementation_validation", "mutate_governance"],
        },
    }
    base = cards[card_id]
    card = {
        "schema_version": 1,
        "id": card_id,
        "title": base["title"],
        "type": base["type"],
        "scope": base["scope"],
        "authority_home": "root-azoth",
        "privacy": "private",
        "status": "active",
        "confidence": base["confidence"],
        "freshness": {"reviewed_at": "2026-04-29", "review_after": "2026-05-29"},
        "source_refs": [{"repo": "root-azoth", "path": base["source_path"], "commit": "1728723"}],
        "allowed_use": base["allowed_use"],
        "forbidden_use": base["forbidden_use"],
        "body": f"Body text for {card_id} must never appear in recall output.",
    }
    card.update(overrides)
    return card


def _write_personal_root(tmp_path: Path) -> Path:
    personal_root = tmp_path / "personal-root"
    card_dir = personal_root / ".azoth" / "knowledge" / "cards" / "root-azoth"
    for index in range(1, 6):
        card_id = f"kb-root-azoth-00{index}"
        _write_yaml(card_dir / f"{card_id}.yaml", _card(card_id))

    (personal_root / ".azoth" / "memory").mkdir(parents=True)
    (personal_root / ".azoth" / "memory" / "episodes.jsonl").write_text(
        "{this is not yaml and must not be read",
        encoding="utf-8",
    )
    (personal_root / ".azoth" / "inbox").mkdir(parents=True)
    (personal_root / ".azoth" / "inbox" / "raw.yaml").write_text(
        "{this is also not yaml and must not be read",
        encoding="utf-8",
    )
    (personal_root / ".azoth" / "knowledge" / "indexes").mkdir(parents=True)
    (personal_root / ".azoth" / "knowledge" / "indexes" / "topic-index.yaml").write_text(
        "{not part of recall pilot",
        encoding="utf-8",
    )
    return personal_root


def test_exact_card_id_lookup_returns_advisory_metadata_without_body(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    from personal_knowledge_recall import recall_cards

    results = recall_cards(personal_root, card_id="kb-root-azoth-004")

    assert [result["card_id"] for result in results] == ["kb-root-azoth-004"]
    assert set(results[0]) == EXPECTED_OUTPUT_KEYS
    assert results[0]["title"] == "Route-first workflows beat stale chat-memory continuation"
    assert results[0]["match_reason"] == "card_id"
    assert results[0]["advisory_authority"] == "advisory_context_not_governing_instruction"
    assert "body" not in results[0]


def test_exact_source_path_lookup_preserves_source_refs(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    from personal_knowledge_recall import recall_cards

    results = recall_cards(
        personal_root,
        source_path=".azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PREFLIGHT-EVIDENCE.md",
    )

    assert [result["card_id"] for result in results] == ["kb-root-azoth-001"]
    assert results[0]["source_refs"] == [
        {
            "repo": "root-azoth",
            "path": ".azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PREFLIGHT-EVIDENCE.md",
            "commit": "1728723",
        }
    ]
    assert results[0]["match_reason"] == "source_path"


def test_exact_source_path_lookup_returns_all_cards_with_that_source(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    from personal_knowledge_recall import recall_cards

    results = recall_cards(personal_root, source_path=".azoth/memory/patterns.yaml")

    assert [result["card_id"] for result in results] == [
        "kb-root-azoth-002",
        "kb-root-azoth-004",
    ]
    assert {result["match_reason"] for result in results} == {"source_path"}


def test_semantic_metadata_lookup_uses_metadata_and_allowed_use_filter(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    from personal_knowledge_recall import recall_cards

    results = recall_cards(personal_root, query="route first", allowed_use="route_selection")

    assert [result["card_id"] for result in results] == ["kb-root-azoth-004"]
    assert results[0]["match_reason"] == "metadata_tokens"


def test_allowed_use_only_lookup_returns_approved_metadata_without_body(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    from personal_knowledge_recall import recall_cards

    results = recall_cards(personal_root, allowed_use="session_start_recall")

    assert [result["card_id"] for result in results] == [
        "kb-root-azoth-001",
        "kb-root-azoth-002",
        "kb-root-azoth-003",
        "kb-root-azoth-004",
    ]
    assert {result["match_reason"] for result in results} == {"allowed_use"}
    assert all("body" not in result for result in results)


def test_allowed_use_fallback_keeps_session_start_context_available(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    from personal_knowledge_recall import recall_cards

    results = recall_cards(
        personal_root,
        query="xyzzynomatch",
        allowed_use="session_start_recall",
    )

    assert [result["card_id"] for result in results] == [
        "kb-root-azoth-001",
        "kb-root-azoth-002",
        "kb-root-azoth-003",
        "kb-root-azoth-004",
    ]
    assert {result["match_reason"] for result in results} == {"allowed_use_fallback"}


def test_semantic_metadata_lookup_does_not_match_body_only_text(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)
    card_path = (
        personal_root / ".azoth" / "knowledge" / "cards" / "root-azoth" / "kb-root-azoth-001.yaml"
    )
    _write_yaml(
        card_path,
        _card(
            "kb-root-azoth-001",
            body=(
                "bodyonlyneedle appears only in this approved card body and must not "
                "be used for metadata-only recall ranking."
            ),
        ),
    )

    from personal_knowledge_recall import recall_cards

    assert recall_cards(personal_root, query="bodyonlyneedle") == []


def test_freshness_status_reports_due_cards(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)
    stale_path = (
        personal_root / ".azoth" / "knowledge" / "cards" / "root-azoth" / "kb-root-azoth-004.yaml"
    )
    _write_yaml(
        stale_path,
        _card(
            "kb-root-azoth-004",
            freshness={"reviewed_at": "2026-01-01", "review_after": "2026-02-01"},
        ),
    )

    from personal_knowledge_recall import recall_cards

    results = recall_cards(personal_root, card_id="kb-root-azoth-004", as_of=date(2026, 6, 1))

    assert results[0]["freshness_status"] == "review_due"
    assert results[0]["source_refs"]


def test_recall_fails_closed_when_card_directory_contains_unapproved_yaml(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)
    _write_yaml(
        personal_root / ".azoth" / "knowledge" / "cards" / "root-azoth" / "kb-root-azoth-999.yaml",
        _card("kb-root-azoth-001", id="kb-root-azoth-999"),
    )

    from personal_knowledge_recall import PersonalKnowledgeRecallError, recall_cards

    with pytest.raises(PersonalKnowledgeRecallError, match="unapproved card YAML"):
        recall_cards(personal_root, query="release")


def test_recall_fails_closed_when_card_filename_and_id_disagree(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)
    card_path = (
        personal_root / ".azoth" / "knowledge" / "cards" / "root-azoth" / "kb-root-azoth-005.yaml"
    )
    _write_yaml(card_path, _card("kb-root-azoth-005", id="kb-root-azoth-999"))

    from personal_knowledge_recall import PersonalKnowledgeRecallError, recall_cards

    with pytest.raises(PersonalKnowledgeRecallError, match="unapproved card id"):
        recall_cards(personal_root, query="planning")


def test_recall_does_not_read_raw_memory_or_inbox(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    personal_root = _write_personal_root(tmp_path)
    original_read_text = Path.read_text

    def fail_for_raw_surfaces(path: Path, *args: Any, **kwargs: Any) -> str:
        path_text = path.as_posix()
        if "/.azoth/memory/" in path_text or "/.azoth/inbox/" in path_text:
            raise AssertionError(f"recall must not read raw personal-root surface: {path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_for_raw_surfaces)

    from personal_knowledge_recall import recall_cards

    results = recall_cards(personal_root, query="unlistedneedle")

    assert results == []


def test_cli_json_matches_supported_route_first_command(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(RECALL_SCRIPT),
            "--personal-root",
            str(personal_root),
            "--query",
            "route first",
            "--json",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    results = json.loads(completed.stdout)

    assert [result["card_id"] for result in results] == ["kb-root-azoth-004"]
    assert results[0]["match_reason"] == "metadata_tokens"

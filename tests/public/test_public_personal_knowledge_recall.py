from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    (ROOT / "kernel" / "templates" / "public-scripts").is_dir(),
    reason="public-script templates are exercised after product extraction",
)
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from personal_knowledge_recall import (  # noqa: E402
    PersonalKnowledgeRecallError,
    recall_cards,
)


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _card(card_id: str = "delivery-safety-001") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": card_id,
        "title": "Keep consequential delivery transitions explicit",
        "type": "operating_principle",
        "scope": ["delivery", "safety"],
        "authority_home": "operator",
        "privacy": "private",
        "status": "active",
        "confidence": "high",
        "freshness": {"review_after": "2030-01-01"},
        "source_refs": [{"path": "docs/delivery-notes.md"}],
        "allowed_use": ["session_start_recall"],
        "forbidden_use": ["automatic_mutation"],
        "body": "This body is deliberately absent from recall results.",
    }


def _approved_root(tmp_path: Path) -> Path:
    root = tmp_path / "operator root"
    card_rel = Path("cards/operator/delivery-safety-001.yaml")
    _write_yaml(root / ".azoth" / "knowledge" / card_rel, _card())
    _write_yaml(
        root / ".azoth" / "knowledge" / "approved-cards.yaml",
        {
            "schema_version": 1,
            "cards": [{"id": "delivery-safety-001", "path": card_rel.as_posix()}],
        },
    )
    return root


def test_manifest_approved_recall_is_metadata_only(tmp_path: Path) -> None:
    root = _approved_root(tmp_path)

    results = recall_cards(
        root,
        query="delivery safety",
        allowed_use="session_start_recall",
        as_of=date(2026, 8, 25),
    )

    assert [result["card_id"] for result in results] == ["delivery-safety-001"]
    assert results[0]["freshness_status"] == "current"
    assert results[0]["advisory_authority"] == "advisory_context_not_governing_instruction"
    assert "body" not in results[0]


@pytest.mark.parametrize(
    "manifest",
    (None, {"schema_version": 1, "cards": []}),
    ids=("missing", "empty"),
)
def test_recall_rejects_missing_or_empty_approval_manifest(
    tmp_path: Path,
    manifest: dict[str, Any] | None,
) -> None:
    root = tmp_path / "operator-root"
    root.mkdir()
    if manifest is not None:
        _write_yaml(root / ".azoth" / "knowledge" / "approved-cards.yaml", manifest)

    with pytest.raises(PersonalKnowledgeRecallError, match="manifest|non-empty"):
        recall_cards(root, query="delivery")


def test_recall_rejects_unlisted_card(tmp_path: Path) -> None:
    root = _approved_root(tmp_path)
    _write_yaml(
        root / ".azoth" / "knowledge" / "cards" / "operator" / "unlisted-001.yaml",
        _card("unlisted-001"),
    )

    with pytest.raises(PersonalKnowledgeRecallError, match="unlisted card YAML"):
        recall_cards(root, query="delivery")


def test_recall_rejects_traversal_and_symlink_escape(tmp_path: Path) -> None:
    root = _approved_root(tmp_path)
    manifest_path = root / ".azoth" / "knowledge" / "approved-cards.yaml"
    _write_yaml(
        manifest_path,
        {
            "schema_version": 1,
            "cards": [{"id": "delivery-safety-001", "path": "../outside.yaml"}],
        },
    )
    with pytest.raises(PersonalKnowledgeRecallError, match="safe relative path"):
        recall_cards(root, query="delivery")

    outside = tmp_path / "outside-card.yaml"
    _write_yaml(outside, _card())
    link = root / ".azoth" / "knowledge" / "cards" / "operator" / "delivery-safety-001.yaml"
    link.unlink()
    link.symlink_to(outside)
    _write_yaml(
        manifest_path,
        {
            "schema_version": 1,
            "cards": [
                {"id": "delivery-safety-001", "path": "cards/operator/delivery-safety-001.yaml"}
            ],
        },
    )
    with pytest.raises(PersonalKnowledgeRecallError, match="escapes the cards root"):
        recall_cards(root, query="delivery")

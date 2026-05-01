#!/usr/bin/env python3
"""Recall approved Batch 0 personal knowledge cards from metadata only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

try:
    from yaml_helpers import safe_load_yaml_path
except ModuleNotFoundError:  # pragma: no cover - defensive fallback for direct reuse.
    YAML_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

    def safe_load_yaml_path(path: Path) -> Any:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=YAML_SAFE_LOADER)


from personal_knowledge_validate import validate_card


APPROVED_CARD_IDS = {
    "kb-root-azoth-001",
    "kb-root-azoth-002",
    "kb-root-azoth-003",
    "kb-root-azoth-004",
    "kb-root-azoth-005",
}
CARD_DIR = Path(".azoth/knowledge/cards/root-azoth")
CARD_SUFFIXES = {".yaml", ".yml"}
ADVISORY_AUTHORITY = "advisory_context_not_governing_instruction"


class PersonalKnowledgeRecallError(Exception):
    """Fail-closed recall contract error."""


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = safe_load_yaml_path(path)
    except yaml.YAMLError as exc:
        raise PersonalKnowledgeRecallError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(loaded, dict):
        raise PersonalKnowledgeRecallError(f"{path}: root must be a mapping")
    return loaded


def _card_paths(personal_root: Path) -> list[Path]:
    card_dir = personal_root / CARD_DIR
    if not card_dir.is_dir():
        raise PersonalKnowledgeRecallError(f"card directory does not exist: {card_dir}")
    paths = sorted(
        path
        for path in card_dir.iterdir()
        if path.is_file() and path.suffix.lower() in CARD_SUFFIXES
    )
    filenames = {path.stem for path in paths}
    extra = sorted(filenames - APPROVED_CARD_IDS)
    missing = sorted(APPROVED_CARD_IDS - filenames)
    if extra:
        raise PersonalKnowledgeRecallError(f"unapproved card YAML: {', '.join(extra)}")
    if missing:
        raise PersonalKnowledgeRecallError(f"missing approved card YAML: {', '.join(missing)}")
    return paths


def _load_cards(personal_root: Path) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in _card_paths(personal_root):
        validate_card(path)
        card = _load_yaml_mapping(path)
        card_id = card.get("id")
        if card_id not in APPROVED_CARD_IDS:
            raise PersonalKnowledgeRecallError(f"{path}: unapproved card id {card_id!r}")
        if card_id in seen:
            raise PersonalKnowledgeRecallError(f"duplicate approved card id: {card_id}")
        seen.add(card_id)
        cards.append(card)
    return sorted(cards, key=lambda card: str(card["id"]))


def _date_from_value(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return date.fromisoformat(text)
    except ValueError:
        return None


def _freshness_status(card: dict[str, Any], *, as_of: date | None = None) -> str:
    if card.get("status") != "active":
        return "stale_for_use"
    freshness = card.get("freshness")
    if not isinstance(freshness, dict):
        return "unknown"
    review_after = _date_from_value(freshness.get("review_after"))
    if review_after is None:
        return "unknown"
    today = as_of or date.today()
    if review_after < today:
        return "review_due"
    return "current"


def _source_paths(card: dict[str, Any]) -> set[str]:
    source_refs = card.get("source_refs")
    if not isinstance(source_refs, list):
        return set()
    paths = set()
    for source_ref in source_refs:
        if isinstance(source_ref, dict) and isinstance(source_ref.get("path"), str):
            paths.add(source_ref["path"].strip())
    return paths


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _metadata_tokens(card: dict[str, Any]) -> set[str]:
    fields: list[str] = []
    for key in ("title", "type"):
        value = card.get(key)
        if isinstance(value, str):
            fields.append(value)
    for key in ("scope", "allowed_use", "forbidden_use"):
        value = card.get(key)
        if isinstance(value, list):
            fields.extend(item for item in value if isinstance(item, str))
    return _tokens(" ".join(fields))


def _as_result(
    card: dict[str, Any],
    *,
    match_reason: str,
    as_of: date | None = None,
) -> dict[str, Any]:
    return {
        "card_id": card["id"],
        "title": card.get("title"),
        "type": card.get("type"),
        "scope": card.get("scope", []),
        "authority_home": card.get("authority_home"),
        "privacy": card.get("privacy"),
        "status": card.get("status"),
        "confidence": card.get("confidence"),
        "freshness_status": _freshness_status(card, as_of=as_of),
        "source_refs": card.get("source_refs", []),
        "allowed_use": card.get("allowed_use", []),
        "forbidden_use": card.get("forbidden_use", []),
        "match_reason": match_reason,
        "advisory_authority": ADVISORY_AUTHORITY,
    }


def recall_cards(
    personal_root: Path,
    *,
    query: str | None = None,
    card_id: str | None = None,
    source_path: str | None = None,
    allowed_use: str | None = None,
    as_of: date | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic advisory recall results from approved card metadata."""
    if not personal_root.is_dir():
        raise PersonalKnowledgeRecallError(
            f"personal root does not exist or is not a directory: {personal_root}"
        )
    query_text = (query or "").strip()
    card_id_text = (card_id or "").strip()
    source_path_text = (source_path or "").strip()
    if not any((query_text, card_id_text, source_path_text)):
        raise PersonalKnowledgeRecallError("provide query, card_id, or source_path")

    cards = _load_cards(personal_root)
    if allowed_use:
        cards = [
            card
            for card in cards
            if allowed_use
            in [item for item in card.get("allowed_use", []) if isinstance(item, str)]
        ]

    exact_id = [card for card in cards if card.get("id") == card_id_text]
    if exact_id:
        return [_as_result(card, match_reason="card_id", as_of=as_of) for card in exact_id]

    source_matches = [card for card in cards if source_path_text in _source_paths(card)]
    if source_matches:
        return [
            _as_result(card, match_reason="source_path", as_of=as_of) for card in source_matches
        ]

    if not query_text:
        return []

    query_tokens = _tokens(query_text)
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for card in cards:
        score = len(query_tokens & _metadata_tokens(card))
        if score:
            scored.append((score, str(card["id"]), card))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if scored:
        best_score = scored[0][0]
        scored = [item for item in scored if item[0] == best_score]
    return [_as_result(card, match_reason="metadata_tokens", as_of=as_of) for _, _, card in scored]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recall approved Batch 0 personal knowledge cards from metadata only."
    )
    parser.add_argument("--personal-root", required=True, type=Path)
    parser.add_argument("--query")
    parser.add_argument("--card-id")
    parser.add_argument("--source-path")
    parser.add_argument("--allowed-use")
    parser.add_argument("--as-of")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.json:
        parser.error("personal knowledge recall requires --json")

    try:
        results = recall_cards(
            args.personal_root,
            query=args.query,
            card_id=args.card_id,
            source_path=args.source_path,
            allowed_use=args.allowed_use,
            as_of=_date_from_value(args.as_of) if args.as_of else None,
        )
    except PersonalKnowledgeRecallError as exc:
        print(f"personal knowledge recall failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

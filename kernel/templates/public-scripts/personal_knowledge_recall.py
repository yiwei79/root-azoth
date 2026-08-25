#!/usr/bin/env python3
"""Recall explicitly approved personal-knowledge card metadata without raw-body output."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


KNOWLEDGE_ROOT = Path(".azoth/knowledge")
APPROVAL_MANIFEST = KNOWLEDGE_ROOT / "approved-cards.yaml"
CARDS_ROOT = KNOWLEDGE_ROOT / "cards"
CARD_SUFFIXES = {".yaml", ".yml"}
ADVISORY_AUTHORITY = "advisory_context_not_governing_instruction"


class PersonalKnowledgeRecallError(Exception):
    """Fail-closed recall contract error."""


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PersonalKnowledgeRecallError(f"{path}: cannot load YAML: {exc}") from exc
    if not isinstance(loaded, dict):
        raise PersonalKnowledgeRecallError(f"{path}: root must be a mapping")
    return loaded


def _approved_card_paths(personal_root: Path) -> list[tuple[str, Path]]:
    knowledge_root = (personal_root / KNOWLEDGE_ROOT).resolve()
    cards_root = (personal_root / CARDS_ROOT).resolve()
    manifest_path = personal_root / APPROVAL_MANIFEST
    if not manifest_path.is_file():
        raise PersonalKnowledgeRecallError(f"approval manifest does not exist: {manifest_path}")
    manifest = _load_yaml_mapping(manifest_path)
    if manifest.get("schema_version") != 1:
        raise PersonalKnowledgeRecallError(f"{manifest_path}: schema_version must be 1")
    entries = manifest.get("cards")
    if not isinstance(entries, list) or not entries:
        raise PersonalKnowledgeRecallError(f"{manifest_path}: cards must be a non-empty list")

    approved: list[tuple[str, Path]] = []
    seen_ids: set[str] = set()
    seen_paths: set[Path] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise PersonalKnowledgeRecallError(f"{manifest_path}: cards[{index}] must be a mapping")
        card_id = str(entry.get("id") or "").strip()
        rel_text = str(entry.get("path") or "").strip()
        rel_path = Path(rel_text)
        if not card_id or not rel_text or rel_path.is_absolute() or ".." in rel_path.parts:
            raise PersonalKnowledgeRecallError(
                f"{manifest_path}: cards[{index}] requires id and a safe relative path"
            )
        candidate = (knowledge_root / rel_path).resolve()
        try:
            candidate.relative_to(cards_root)
        except ValueError as exc:
            raise PersonalKnowledgeRecallError(
                f"{manifest_path}: cards[{index}] path escapes the cards root"
            ) from exc
        if candidate.suffix.lower() not in CARD_SUFFIXES or not candidate.is_file():
            raise PersonalKnowledgeRecallError(
                f"{manifest_path}: approved card is missing or not YAML: {candidate}"
            )
        if card_id in seen_ids or candidate in seen_paths:
            raise PersonalKnowledgeRecallError(f"{manifest_path}: duplicate approved card entry")
        seen_ids.add(card_id)
        seen_paths.add(candidate)
        approved.append((card_id, candidate))

    discovered = {
        path.resolve()
        for path in cards_root.rglob("*")
        if path.is_file() and path.suffix.lower() in CARD_SUFFIXES
    }
    unlisted = sorted(str(path) for path in discovered - seen_paths)
    if unlisted:
        raise PersonalKnowledgeRecallError(
            "unlisted card YAML is present under the cards root: " + ", ".join(unlisted)
        )
    return sorted(approved, key=lambda item: item[0])


def _validate_card(card: dict[str, Any], *, card_id: str, path: Path) -> None:
    if card.get("schema_version") != 1:
        raise PersonalKnowledgeRecallError(f"{path}: schema_version must be 1")
    if card.get("id") != card_id or path.stem != card_id:
        raise PersonalKnowledgeRecallError(f"{path}: id must match manifest id and filename")
    for field in ("title", "type", "authority_home", "privacy", "status"):
        if not isinstance(card.get(field), str) or not str(card[field]).strip():
            raise PersonalKnowledgeRecallError(f"{path}: {field} must be a non-empty string")
    for field in ("scope", "source_refs", "allowed_use", "forbidden_use"):
        if not isinstance(card.get(field), list):
            raise PersonalKnowledgeRecallError(f"{path}: {field} must be a list")


def _load_cards(personal_root: Path) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for approved_id, path in _approved_card_paths(personal_root):
        card = _load_yaml_mapping(path)
        _validate_card(card, card_id=approved_id, path=path)
        cards.append(card)
    return cards


def _date_from_value(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        text = value.strip()
        return (
            datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            if "T" in text
            else date.fromisoformat(text)
        )
    except ValueError:
        return None


def _freshness_status(card: dict[str, Any], *, as_of: date | None = None) -> str:
    if card.get("status") != "active":
        return "stale_for_use"
    freshness = card.get("freshness")
    review_after = (
        _date_from_value(freshness.get("review_after")) if isinstance(freshness, dict) else None
    )
    if review_after is None:
        return "unknown"
    return "review_due" if review_after < (as_of or date.today()) else "current"


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _metadata_tokens(card: dict[str, Any]) -> set[str]:
    values = [str(card.get("title") or ""), str(card.get("type") or "")]
    for field in ("scope", "allowed_use", "forbidden_use"):
        items = card.get(field)
        if isinstance(items, list):
            values.extend(str(item) for item in items)
    return _tokens(" ".join(values))


def _source_paths(card: dict[str, Any]) -> set[str]:
    refs = card.get("source_refs")
    return (
        {
            str(ref.get("path") or "").strip()
            for ref in refs
            if isinstance(ref, dict) and str(ref.get("path") or "").strip()
        }
        if isinstance(refs, list)
        else set()
    )


def _as_result(card: dict[str, Any], *, match_reason: str, as_of: date | None) -> dict[str, Any]:
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
    """Return deterministic metadata from only the manifest-approved cards."""
    if not personal_root.is_dir():
        raise PersonalKnowledgeRecallError(f"personal root is not a directory: {personal_root}")
    if not any((query, card_id, source_path, allowed_use)):
        raise PersonalKnowledgeRecallError("provide query, card_id, source_path, or allowed_use")
    cards = _load_cards(personal_root)
    if allowed_use:
        cards = [card for card in cards if allowed_use in card.get("allowed_use", [])]
    if card_id:
        return [
            _as_result(card, match_reason="card_id", as_of=as_of)
            for card in cards
            if card.get("id") == card_id
        ]
    if source_path:
        return [
            _as_result(card, match_reason="source_path", as_of=as_of)
            for card in cards
            if source_path in _source_paths(card)
        ]
    query_tokens = _tokens(str(query or ""))
    scored = [(len(query_tokens & _metadata_tokens(card)), str(card["id"]), card) for card in cards]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[1]))
    if scored:
        best = scored[0][0]
        return [
            _as_result(card, match_reason="metadata_tokens", as_of=as_of)
            for score, _, card in scored
            if score == best
        ]
    if allowed_use:
        return [_as_result(card, match_reason="allowed_use", as_of=as_of) for card in cards]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
            as_of=_date_from_value(args.as_of),
        )
    except PersonalKnowledgeRecallError as exc:
        print(f"personal knowledge recall failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a no-write review packet for approved personal knowledge cards."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from personal_knowledge_recall import PersonalKnowledgeRecallError, recall_cards


DEFAULT_ALLOWED_USE = "session_start_recall"
REVIEW_DUE_STATUSES = {"review_due", "unknown", "stale_for_use"}
ADVISORY_AUTHORITY = "advisory_context_not_governing_instruction"


def build_review_packet(
    personal_root: Path,
    *,
    allowed_use: str = DEFAULT_ALLOWED_USE,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Return a deterministic metadata-only packet for personal knowledge review."""
    results = recall_cards(
        personal_root,
        allowed_use=allowed_use,
        as_of=as_of,
    )
    cards = [_review_item(result) for result in results]
    due_cards = [
        card for card in cards if card["freshness_status"] in REVIEW_DUE_STATUSES
    ]
    return {
        "schema_version": 1,
        "packet_type": "personal_knowledge_review",
        "personal_root": str(personal_root.resolve()),
        "allowed_use": allowed_use,
        "as_of": (as_of or date.today()).isoformat(),
        "summary": {
            "total_cards": len(cards),
            "current_cards": sum(1 for card in cards if card["freshness_status"] == "current"),
            "review_due_cards": len(due_cards),
            "requires_operator_review": bool(due_cards),
            "overall_status": "review_due" if due_cards else "current",
        },
        "cards": cards,
        "due_cards": due_cards,
        "next_safe_action": _next_safe_action(due_cards),
        "no_write_contract": {
            "writes_personal_root": False,
            "reads_raw_memory_or_inbox": False,
            "imports_unreviewed_sources": False,
        },
        "advisory_authority": ADVISORY_AUTHORITY,
    }


def _review_item(result: Mapping[str, Any]) -> dict[str, Any]:
    freshness_status = str(result.get("freshness_status") or "").strip()
    return {
        "card_id": str(result.get("card_id") or "").strip(),
        "title": str(result.get("title") or "").strip(),
        "freshness_status": freshness_status,
        "status": str(result.get("status") or "").strip(),
        "confidence": str(result.get("confidence") or "").strip(),
        "source_refs": result.get("source_refs", []),
        "allowed_use": result.get("allowed_use", []),
        "forbidden_use": result.get("forbidden_use", []),
        "review_reason": _review_reason(freshness_status),
    }


def _review_reason(freshness_status: str) -> str:
    if freshness_status == "current":
        return "card freshness window is current"
    if freshness_status == "review_due":
        return "card review_after date has passed"
    if freshness_status == "stale_for_use":
        return "card is not active and should not be treated as current context"
    return "card freshness metadata is missing or not actionable"


def _next_safe_action(due_cards: list[dict[str, Any]]) -> str:
    if not due_cards:
        return "continue daily harness use; no personal knowledge review is due"
    ids = ", ".join(card["card_id"] for card in due_cards)
    return (
        "review source refs for "
        f"{ids}; update card freshness only through an approved personal-knowledge review lane"
    )


def _date_from_value(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return date.fromisoformat(text)
    except ValueError as exc:
        raise PersonalKnowledgeRecallError(f"invalid --as-of date: {value}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personal-root", required=True, type=Path)
    parser.add_argument("--allowed-use", default=DEFAULT_ALLOWED_USE)
    parser.add_argument("--as-of")
    parser.add_argument("--fail-on-due", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.json:
        parser.error("personal knowledge review output requires --json")

    try:
        packet = build_review_packet(
            args.personal_root,
            allowed_use=args.allowed_use,
            as_of=_date_from_value(args.as_of),
        )
    except PersonalKnowledgeRecallError as exc:
        print(f"personal knowledge review failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(packet, indent=2, sort_keys=True))
    if args.fail_on_due and packet["summary"]["requires_operator_review"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

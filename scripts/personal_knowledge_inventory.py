#!/usr/bin/env python3
"""List root-side personal knowledge source candidates without reading contents."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SOURCE_PLANE = "root-azoth"
RAW_MEMORY_PATH = Path(".azoth/memory/episodes.jsonl")
INBOX_DIR = Path(".azoth/inbox")


@dataclass(frozen=True)
class InventoryRule:
    recommended_card_type: str
    risk: str
    risk_reason: str
    later_use_notes: str


APPROVED_SOURCE_RULES: dict[Path, InventoryRule] = {
    Path(".azoth/memory/patterns.yaml"): InventoryRule(
        recommended_card_type="toolkit_lesson",
        risk="approved_source_candidate",
        risk_reason="Approved M2 pattern source; review and excerpt before card drafting.",
        later_use_notes="May inform a future reviewed personal knowledge candidate batch.",
    ),
    Path(".azoth/roadmap-specs/v0.2.0/PERSONAL-ROOT-DEPLOYMENT-MODEL.md"): InventoryRule(
        recommended_card_type="decision_context",
        risk="approved_source_candidate",
        risk_reason="Root-side deployment model source; review and excerpt before card drafting.",
        later_use_notes="May anchor future personal-root authority and boundary cards.",
    ),
    Path(".azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PREFLIGHT-EVIDENCE.md"): InventoryRule(
        recommended_card_type="source_note",
        risk="approved_source_candidate",
        risk_reason="Stable preflight evidence source; review and excerpt before card drafting.",
        later_use_notes="May support future release-readiness or evidence-process cards.",
    ),
    Path(".azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PUBLICATION-EVIDENCE.md"): InventoryRule(
        recommended_card_type="source_note",
        risk="approved_source_candidate",
        risk_reason="Stable publication evidence source; review and excerpt before card drafting.",
        later_use_notes="May support future publication-process or release-boundary cards.",
    ),
}

RAW_MEMORY_RULE = InventoryRule(
    recommended_card_type="source_note",
    risk="raw_memory_bulk_import_forbidden",
    risk_reason="Raw memory episodes are not safe bulk import material; use manual excerpts only.",
    later_use_notes="May be referenced only through a future reviewed excerpt and candidate batch.",
)

INBOX_RULE = InventoryRule(
    recommended_card_type="source_note",
    risk="inbox_requires_intake_or_manual_excerpt",
    risk_reason="Inbox material requires intake or a manual excerpt before card drafting.",
    later_use_notes=(
        "May inform future candidates only after intake review selects a bounded excerpt."
    ),
)


class PersonalKnowledgeInventoryError(Exception):
    """Fail-closed inventory contract error."""


def _candidate_id(source_plane: str, source_path: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", source_path.lower()).strip("-")
    return f"{source_plane}-{slug}"


def _record(source_plane: str, rel_path: Path, rule: InventoryRule) -> dict[str, str]:
    source_path = rel_path.as_posix()
    return {
        "candidate_id": _candidate_id(source_plane, source_path),
        "source_plane": source_plane,
        "source_path": source_path,
        "recommended_card_type": rule.recommended_card_type,
        "provenance": f"{source_plane}:{source_path}",
        "risk": rule.risk,
        "risk_reason": rule.risk_reason,
        "later_use_notes": rule.later_use_notes,
    }


def _existing_inbox_files(source_root: Path) -> list[Path]:
    inbox = source_root / INBOX_DIR
    if not inbox.is_dir():
        return []
    return sorted(
        path.relative_to(source_root)
        for path in inbox.rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    )


def build_inventory(source_root: Path, *, source_plane: str) -> list[dict[str, str]]:
    """Return deterministic source candidate records using path existence only."""
    if source_plane != SUPPORTED_SOURCE_PLANE:
        raise PersonalKnowledgeInventoryError(
            f"unsupported source plane {source_plane!r}; T-041 supports only root-azoth"
        )
    if not source_root.is_dir():
        raise PersonalKnowledgeInventoryError(
            f"source root does not exist or is not a directory: {source_root}"
        )

    records: list[dict[str, str]] = []
    for rel_path, rule in APPROVED_SOURCE_RULES.items():
        if (source_root / rel_path).is_file():
            records.append(_record(source_plane, rel_path, rule))

    if (source_root / RAW_MEMORY_PATH).is_file():
        records.append(_record(source_plane, RAW_MEMORY_PATH, RAW_MEMORY_RULE))

    for rel_path in _existing_inbox_files(source_root):
        records.append(_record(source_plane, rel_path, INBOX_RULE))

    return sorted(records, key=lambda record: record["source_path"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List root-side personal knowledge source candidates without reading contents."
    )
    parser.add_argument(
        "--source-root",
        required=True,
        type=Path,
        help="Root source repository path.",
    )
    parser.add_argument(
        "--source-plane",
        required=True,
        help="Source plane name; only root-azoth is supported.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit deterministic JSON candidate records.",
    )
    args = parser.parse_args(argv)

    if not args.json:
        parser.error("T-041 inventory requires --json")
    if args.source_plane != SUPPORTED_SOURCE_PLANE:
        parser.error(
            f"unsupported --source-plane {args.source_plane!r}; T-041 supports only root-azoth"
        )

    try:
        records = build_inventory(args.source_root, source_plane=args.source_plane)
    except PersonalKnowledgeInventoryError as exc:
        print(f"personal knowledge inventory failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(records, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

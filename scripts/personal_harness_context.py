#!/usr/bin/env python3
"""Assemble a Personal Harness OS context packet for daily use."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from context_recall_quality import RecallQualityError, build_recall_packet
from context_view import build_context_view
from harness_profile import HarnessRequest, classify_harness_request

try:
    from personal_knowledge_recall import PersonalKnowledgeRecallError, recall_cards
except ModuleNotFoundError as exc:  # Optional root-only adapter is not public.
    if exc.name != "personal_knowledge_recall":
        raise
    PersonalKnowledgeRecallError = RuntimeError
    recall_cards = None


def build_personal_harness_context(
    *,
    goal: str,
    requested_actions: Sequence[str] = (),
    planned_paths: Sequence[str] = (),
    query_tags: Sequence[str] = (),
    repo_root: Path = Path("."),
    personal_root: Path | None = None,
    project_readback: Mapping[str, Any] | None = None,
    top_k: int = 3,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return one route-aware context packet for an operator goal."""
    root = repo_root.resolve()
    decision = classify_harness_request(
        HarnessRequest(
            goal=goal,
            requested_actions=tuple(requested_actions),
            planned_paths=tuple(planned_paths),
            trace_required=_trace_required(requested_actions),
        )
    )
    warnings: list[str] = []
    memory_recall = _memory_recall_packet(
        goal=goal,
        query_tags=query_tags,
        repo_root=root,
        top_k=top_k,
        as_of=as_of,
        warnings=warnings,
    )
    personal_results = _personal_recall_results(
        goal=goal,
        personal_root=personal_root,
        as_of=as_of,
        warnings=warnings,
    )
    context_view = build_context_view(
        goal=goal,
        harness_decision=decision,
        memory_results=_memory_context_items(memory_recall),
        personal_results=personal_results,
        project_receipt=project_readback,
        max_items=top_k,
    )
    return {
        "schema_version": 1,
        "packet_type": "personal_harness_context",
        "goal": goal,
        "context_view": context_view,
        "memory_recall": memory_recall,
        "warnings": warnings,
    }


def _trace_required(requested_actions: Sequence[str]) -> bool:
    normalized = {str(action).strip().lower().replace("-", "_") for action in requested_actions}
    return bool(normalized & {"focused_verification", "verify", "test", "focused_test"})


def _memory_recall_packet(
    *,
    goal: str,
    query_tags: Sequence[str],
    repo_root: Path,
    top_k: int,
    as_of: str | None,
    warnings: list[str],
) -> dict[str, Any]:
    episodes_path = repo_root / ".azoth" / "memory" / "episodes.jsonl"
    patterns_path = repo_root / ".azoth" / "memory" / "patterns.yaml"
    try:
        return build_recall_packet(
            query=goal,
            query_tags=[str(tag) for tag in query_tags if str(tag).strip()],
            top_k=top_k,
            as_of=as_of,
            episodes_path=episodes_path,
            patterns_path=patterns_path,
            episodes_source_ref=str(episodes_path),
            patterns_source_ref=str(patterns_path),
        )
    except (RecallQualityError, FileNotFoundError) as exc:
        warnings.append(f"memory recall skipped: {exc}")
        return {
            "schema_version": 1,
            "packet_type": "context_recall_quality_query",
            "query": goal,
            "query_tags": list(query_tags),
            "top_k": top_k,
            "results": [],
            "warnings": [str(exc)],
            "no_match": True,
            "advisory_authority": "advisory_context_not_governing_instruction",
        }


def _memory_context_items(memory_recall: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    results = memory_recall.get("results")
    if not isinstance(results, list):
        return items
    for result in results:
        if not isinstance(result, Mapping):
            continue
        summary = str(result.get("summary") or "").strip()
        if not summary:
            continue
        items.append(
            {
                "id": str(result.get("id") or "").strip(),
                "kind": str(result.get("source_type") or "").strip(),
                "summary": summary,
                "score": result.get("score_total"),
                "source_ref": str(result.get("source_ref") or "").strip(),
            }
        )
    return items


def _personal_recall_results(
    *,
    goal: str,
    personal_root: Path | None,
    as_of: str | None,
    warnings: list[str],
) -> list[dict[str, Any]]:
    if personal_root is None:
        return []
    if recall_cards is None:
        warnings.append(
            "personal knowledge recall skipped: optional personal adapter is not installed"
        )
        return []
    try:
        results = recall_cards(
            personal_root,
            allowed_use="session_start_recall",
            as_of=_as_of_date(as_of),
        )
    except PersonalKnowledgeRecallError as exc:
        warnings.append(f"personal knowledge recall skipped: {exc}")
        return []
    _append_personal_freshness_warning(results, warnings)
    return [_personal_context_item(result) for result in results]


def _as_of_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return date.fromisoformat(text)
    except ValueError:
        return None


def _append_personal_freshness_warning(
    results: Sequence[Mapping[str, Any]],
    warnings: list[str],
) -> None:
    due_ids = [
        str(result.get("card_id") or "").strip()
        for result in results
        if result.get("freshness_status") == "review_due" and result.get("card_id")
    ]
    if due_ids:
        warnings.append(f"personal knowledge review due: {', '.join(due_ids)}")


def _personal_context_item(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "card_id": str(result.get("card_id") or "").strip(),
        "title": str(result.get("title") or "").strip(),
        "summary": str(result.get("title") or "").strip(),
        "freshness": str(result.get("freshness_status") or "").strip(),
        "source_ref": _first_source_ref(result),
    }


def _first_source_ref(result: Mapping[str, Any]) -> str:
    refs = result.get("source_refs")
    if not isinstance(refs, list):
        return ""
    for item in refs:
        if isinstance(item, Mapping) and item.get("path"):
            return str(item["path"]).strip()
    return ""


def _project_readback_from_args(args: argparse.Namespace) -> dict[str, str] | None:
    if not any((args.project, args.selected_mode, args.freshness, args.receipt_ref)):
        return None
    return {
        "project": str(args.project or "").strip(),
        "selected_mode": str(args.selected_mode or "").strip(),
        "freshness": str(args.freshness or "").strip(),
        "receipt_ref": str(args.receipt_ref or "").strip(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--action", action="append", default=[])
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--personal-root", type=Path)
    parser.add_argument("--project")
    parser.add_argument("--selected-mode")
    parser.add_argument("--freshness")
    parser.add_argument("--receipt-ref")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--as-of")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.json:
        parser.error("personal harness context output requires --json")

    packet = build_personal_harness_context(
        goal=args.goal,
        requested_actions=args.action,
        planned_paths=args.path,
        query_tags=args.tag,
        repo_root=args.repo_root,
        personal_root=args.personal_root,
        project_readback=_project_readback_from_args(args),
        top_k=args.top_k,
        as_of=args.as_of,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

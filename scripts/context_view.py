#!/usr/bin/env python3
"""ContextView packet builder for Personal Harness OS.

The builder keeps context pull-based and advisory. It joins compact summaries
that were already approved or scored elsewhere; it does not read memory stores
or personal knowledge files on its own.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from harness_profile import HarnessDecision


def build_context_view(
    *,
    goal: str,
    harness_decision: HarnessDecision,
    memory_results: Sequence[Mapping[str, Any]] | None = None,
    personal_results: Sequence[Mapping[str, Any]] | None = None,
    project_receipt: Mapping[str, Any] | None = None,
    max_items: int = 3,
) -> dict[str, Any]:
    """Build a deterministic compact context packet for one route decision."""
    return {
        "schema_version": 1,
        "packet_type": "context_view",
        "advisory_authority": "advisory_only",
        "goal": goal,
        "harness_profile": harness_decision.profile,
        "operator_promise": harness_decision.operator_promise,
        "route_capsule": harness_decision.to_route_capsule(),
        "memory_context": _summarize_memory(memory_results or (), max_items),
        "personal_context": _summarize_personal(personal_results or (), max_items),
        "project_context": _summarize_project_receipt(project_receipt),
        "forbidden_actions": list(harness_decision.explicit_exclusions),
        "source_refs": list(harness_decision.source_refs),
    }


def _summarize_memory(
    results: Sequence[Mapping[str, Any]],
    max_items: int,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in results:
        if str(item.get("kind", "")).lower() == "raw":
            continue
        summary = str(item.get("summary", "")).strip()
        if not summary:
            continue
        summaries.append(
            {
                "id": str(item.get("id", "")).strip(),
                "kind": str(item.get("kind", "")).strip(),
                "summary": summary,
                "score": item.get("score"),
                "source_ref": str(item.get("source_ref", "")).strip(),
            }
        )
        if len(summaries) >= max_items:
            break
    return summaries


def _summarize_personal(
    results: Sequence[Mapping[str, Any]],
    max_items: int,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in results:
        summary = str(item.get("summary", "")).strip()
        if not summary:
            continue
        summaries.append(
            {
                "card_id": str(item.get("card_id", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "summary": summary,
                "freshness": str(item.get("freshness", "")).strip(),
                "source_ref": str(item.get("source_ref", "")).strip(),
            }
        )
        if len(summaries) >= max_items:
            break
    return summaries


def _summarize_project_receipt(
    receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not receipt:
        return {
            "project": "",
            "selected_mode": "",
            "freshness": "missing",
            "receipt_ref": "",
        }
    return {
        "project": str(receipt.get("project", "")).strip(),
        "selected_mode": str(receipt.get("selected_mode", "")).strip(),
        "freshness": str(receipt.get("freshness", "")).strip(),
        "receipt_ref": str(receipt.get("receipt_ref", "")).strip(),
    }

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from context_view import build_context_view  # noqa: E402
from harness_profile import HarnessRequest, classify_harness_request  # noqa: E402


def test_context_view_combines_route_memory_and_personal_context_without_raw_dump() -> None:
    decision = classify_harness_request(
        HarnessRequest(
            goal="Prepare thesis workspace with remembered preferences.",
            requested_actions=("focused_verification",),
            trace_required=True,
        )
    )

    view = build_context_view(
        goal=decision.request.goal,
        harness_decision=decision,
        memory_results=[
            {
                "id": "ep-463",
                "kind": "episode",
                "summary": "Run-ledger clobber taught fail-closed write claims.",
                "score": 0.91,
                "source_ref": ".azoth/memory/episodes.jsonl#ep-463",
            },
            {
                "id": "raw-hidden",
                "kind": "raw",
                "content": "This should not appear.",
                "score": 0.2,
                "source_ref": ".azoth/memory/raw.txt",
            },
        ],
        personal_results=[
            {
                "card_id": "pk-thesis-style",
                "title": "Thesis style preference",
                "summary": "Prefer concise synthesis before detail.",
                "freshness": "current",
                "source_ref": "personal_knowledge/cards/pk-thesis-style.yaml",
            }
        ],
        project_receipt={
            "project": "thesis",
            "selected_mode": "assisted",
            "freshness": "fresh",
            "receipt_ref": ".azoth/project-local-mode-receipt.yaml",
        },
    )

    assert view["schema_version"] == 1
    assert view["packet_type"] == "context_view"
    assert view["advisory_authority"] == "advisory_only"
    assert view["harness_profile"] == "assisted"
    assert view["route_capsule"]["route_state"] == "assist"
    assert view["memory_context"] == [
        {
            "id": "ep-463",
            "kind": "episode",
            "summary": "Run-ledger clobber taught fail-closed write claims.",
            "score": 0.91,
            "source_ref": ".azoth/memory/episodes.jsonl#ep-463",
        }
    ]
    assert view["personal_context"] == [
        {
            "card_id": "pk-thesis-style",
            "title": "Thesis style preference",
            "summary": "Prefer concise synthesis before detail.",
            "freshness": "current",
            "source_ref": "personal_knowledge/cards/pk-thesis-style.yaml",
        }
    ]
    assert "This should not appear." not in str(view)


def test_context_view_surfaces_authority_stop_for_managed_mode() -> None:
    decision = classify_harness_request(
        HarnessRequest(
            goal="Hydrate managed project state.",
            requested_actions=("update",),
            planned_paths=(".azoth/project-local-mode-receipt.yaml",),
        )
    )

    view = build_context_view(goal=decision.request.goal, harness_decision=decision)

    assert view["harness_profile"] == "managed"
    assert view["route_capsule"]["authority_required"] is True
    assert view["route_capsule"]["stop_reason"] == "fresh managed-mode authority required"
    assert view["source_refs"] == ["docs/PERSONAL_HARNESS_OS.md#mode-managed"]

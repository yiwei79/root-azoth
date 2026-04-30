"""Tests for read-only planning-bank routing summaries."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from planning_bank_surfacing import format_planning_bank_plain  # noqa: E402
from planning_bank_surfacing import load_planning_bank_summaries  # noqa: E402


def test_initiative_summary_surfaces_next_open_candidate_after_hydrated_slice(
    tmp_path: Path,
) -> None:
    bank_dir = tmp_path / ".azoth" / "initiative-banks"
    bank_dir.mkdir(parents=True)
    (bank_dir / "INI-PKB-001.yaml").write_text(
        "schema_version: 1\n"
        "bank_type: initiative\n"
        "initiative_id: INI-PKB-001\n"
        "title: Personal knowledge Batch 0 and deployment finalization\n"
        "status: planning_discovery_seed\n"
        "readiness:\n"
        "  readiness_status: ready_to_hydrate\n"
        "  human_decision: approved\n"
        "  candidate_first_slice: slice-pkb-001-a\n"
        "  hydration_recommendation: slice-pkb-001-a has been hydrated as T-042. Do not repeat hydration.\n"
        "candidate_slices:\n"
        "  - candidate_id: slice-pkb-001-a\n"
        "    proposed_task_id: T-042\n"
        "    title: Batch 0 candidate review artifact only\n"
        "    status: hydrated\n"
        "  - candidate_id: slice-pkb-001-b\n"
        "    proposed_task_id: T-PKB-B\n"
        "    title: Approved card deployment receipt and personal-root pointer index\n"
        "    status: candidate\n",
        encoding="utf-8",
    )

    summaries = load_planning_bank_summaries(tmp_path)
    bank = summaries["initiative_banks"][0]

    assert bank["readiness_candidate_id"] == "slice-pkb-001-a"
    assert bank["readiness_candidate_status"] == "hydrated"
    assert bank["candidate_id"] == "slice-pkb-001-b"
    assert bank["candidate_task_ref"] == "T-PKB-B"
    assert bank["candidate_status"] == "candidate"
    assert bank["ready_to_hydrate"] is False
    approval_boundary = (
        "Requires explicit approval before hydration, deployment, or personal-root mutation."
    )
    assert approval_boundary in bank["route_hint"]

    plain = "\n".join(format_planning_bank_plain(summaries))
    assert "candidate slice-pkb-001-b -> T-PKB-B (candidate)" in plain
    assert "slice-pkb-001-a has been hydrated" not in plain
    assert approval_boundary in plain


def test_initiative_summary_keeps_hydrated_slice_when_backlog_task_is_pending(
    tmp_path: Path,
) -> None:
    azoth_dir = tmp_path / ".azoth"
    bank_dir = azoth_dir / "initiative-banks"
    bank_dir.mkdir(parents=True)
    (azoth_dir / "backlog.yaml").write_text(
        "schema_version: 1\n"
        "items:\n"
        "  - id: T-044\n"
        "    status: pending\n",
        encoding="utf-8",
    )
    (bank_dir / "INI-PKB-001.yaml").write_text(
        "schema_version: 1\n"
        "bank_type: initiative\n"
        "initiative_id: INI-PKB-001\n"
        "title: Personal knowledge Batch 0 and deployment finalization\n"
        "status: planning_discovery_seed\n"
        "readiness:\n"
        "  readiness_status: ready_to_hydrate\n"
        "  human_decision: approved\n"
        "  candidate_first_slice: slice-pkb-001-b\n"
        "  hydration_recommendation: slice-pkb-001-b has been hydrated as T-044. Do not repeat hydration; personal-root mutation remains blocked.\n"
        "candidate_slices:\n"
        "  - candidate_id: slice-pkb-001-b\n"
        "    proposed_task_id: T-044\n"
        "    status: hydrated\n"
        "    hydration_plan:\n"
        "      hydrated_task_ref: T-044\n"
        "  - candidate_id: slice-pkb-001-c\n"
        "    proposed_task_id: T-PKB-C\n"
        "    title: Personal knowledge recall pilot and retrieval eval harness\n"
        "    status: candidate\n",
        encoding="utf-8",
    )

    summaries = load_planning_bank_summaries(tmp_path)
    bank = summaries["initiative_banks"][0]

    assert bank["candidate_id"] == "slice-pkb-001-b"
    assert bank["candidate_task_ref"] == "T-044"
    assert bank["candidate_status"] == "hydrated"
    assert "slice-pkb-001-b has been hydrated as T-044" in bank["route_hint"]
    approval_boundary = (
        "Requires explicit approval before hydration, deployment, or personal-root mutation."
    )
    assert approval_boundary in bank["route_hint"]

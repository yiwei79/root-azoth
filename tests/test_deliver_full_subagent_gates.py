"""Tests for .claude/commands/deliver-full.md — BL-006 / BL-008 / BL-011 (D21).

Enforces that each agent-gated stage (3–6) in /deliver-full mandates a
fresh-context subagent invocation, that Orchestration Constraints documents
isolation rules, and that BL-011 spawn minimization references the skill.

Governance anchor: D21 — subagent isolation for review gates.

All unit tests operate on file content read once at module level.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DELIVER_FULL_PATH = REPO_ROOT / ".claude" / "commands" / "deliver-full.md"
SUBAGENT_ROUTER = REPO_ROOT / "skills" / "subagent-router" / "SKILL.md"

# Read once; reused across all unit tests.
_CONTENT = DELIVER_FULL_PATH.read_text()
_ROUTER = SUBAGENT_ROUTER.read_text()


# ── BL-011 — spawn table + skill offload ──────────────────────────────────────


def test_spawn_invocation_section_present() -> None:
    """deliver-full must cite BL-011 minimal spawn and the subagent-router contract."""
    assert "## Spawn invocation (BL-011)" in _CONTENT
    assert "§Spawn Prompt Contract" in _CONTENT
    assert "§Stage briefs: deliver-full" in _CONTENT


def test_stage0_pipeline_gate_section_present() -> None:
    """Mechanical layer: Stage 0 must document pipeline-gate.json for governed scopes."""
    assert "## Stage 0 — Pipeline gate (mechanical)" in _CONTENT
    assert "pipeline-gate.json" in _CONTENT


def test_stage_ids_in_deliver_full_table() -> None:
    """Stages 3–6 must map to stable stage_id tokens for minimal spawns."""
    for sid in ("deliver_full_s3", "deliver_full_s4", "deliver_full_s5", "deliver_full_s6"):
        assert sid in _CONTENT


def test_canonical_d21_hints_live_in_subagent_router_skill() -> None:
    """Long-form D21 audit strings move to the skill; deliver-full stays thin."""
    for fragment in (
        "Agent(subagent_type=reviewer): Critique the brief for governance gaps",
        "Agent(subagent_type=planner): Convert approved design into deterministic tasks",
        "Agent(subagent_type=builder): Design tests from plan's test strategy",
        "Agent(subagent_type=builder): Implement against the approved plan",
    ):
        assert fragment in _ROUTER


# ── Stage 3 — Governance Review ───────────────────────────────────────────────


def test_stage3_trust_contract_escalation() -> None:
    """Stage 3 gate must reference architect disposition and Trust Contract §2."""
    assert "architect receives reviewer findings" in _CONTENT
    assert "Trust Contract §2" in _CONTENT


# ── Stage 4 — Planner ─────────────────────────────────────────────────────────


def test_stage4_gate_has_quality_completeness() -> None:
    """Stage 4 gate must mention architect review of quality and completeness."""
    assert "architect reviews plan quality and completeness" in _CONTENT


# ── Stage 5 — Test Builder ────────────────────────────────────────────────────


def test_stage5_gate_has_coverage_language() -> None:
    """Stage 5 gate must mention architect review of test coverage."""
    assert "architect reviews test coverage against plan" in _CONTENT


# ── Stage 6 — Builder ─────────────────────────────────────────────────────────


def test_stage6_gate_has_handoff_language() -> None:
    """Stage 6 gate must require all tests to pass before hand-off."""
    assert "all tests must pass before hand-off to architect review" in _CONTENT


# ── Orchestration Constraints section ────────────────────────────────────────


def test_orchestration_constraints_section_present() -> None:
    """deliver-full.md must contain an Orchestration Constraints section."""
    assert "## Orchestration Constraints" in _CONTENT


def test_orchestration_constraints_has_all_required_bullets() -> None:
    """The Orchestration Constraints section must contain all required bullets."""
    required = [
        "Policy source: `subagent-router` skill (trigger definitions and routing table)",
        "Each agent gate (stages 3\u20136) mandates a fresh-context subagent invocation via",
        "The Architect (orchestrator) remains the final speaker for all human gates",
        "Subagents return findings; Architect disposes and escalates to human if needed",
        "No review stage shall execute inline with the stage it reviews",
        "runtime enforcement will be added in Phase 5 (P5-001, D43)",
        "Isolation constraint applies to agent-gated review stages (3\u20136)",
    ]
    for bullet in required:
        assert bullet in _CONTENT, f"Missing orchestration constraint: {bullet!r}"


def test_version_bump_step_present() -> None:
    """Stage 7 must still call version-bump after human approval."""
    assert "python scripts/version-bump.py --patch" in _CONTENT


# ── Absence of old inline gate language ───────────────────────────────────────


def test_old_inline_gate_language_absent() -> None:
    """Old single-line gate strings that implied inline execution must be gone.

    Newline-termination prevents false positives when the old text appears as a
    prefix inside the new, richer gate descriptions.
    """
    assert "architect dispositions findings\n" not in _CONTENT, (
        "Old gate string 'architect dispositions findings' still present"
    )
    assert "Gate: agent (architect reviews plan)\n" not in _CONTENT, (
        "Old unqualified gate string 'Gate: agent (architect reviews plan)' still present"
    )
    assert "Gate: agent (auto-test pass)\n" not in _CONTENT, (
        "Old gate string 'Gate: agent (auto-test pass)' still present"
    )

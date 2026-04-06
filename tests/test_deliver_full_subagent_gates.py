"""Tests for .claude/commands/deliver-full.md — BL-006 (D21).

Enforces that each agent-gated stage (3–6) in /deliver-full mandates a
fresh-context subagent invocation and that an Orchestration Constraints
section documents the isolation rules.

All unit tests operate on file content read once at module level.
The integration test guards against collateral file modifications.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DELIVER_FULL_PATH = REPO_ROOT / ".claude" / "commands" / "deliver-full.md"

# Read once; reused across all unit tests.
_CONTENT = DELIVER_FULL_PATH.read_text()


# ── Stage 3 — Governance Review ───────────────────────────────────────────────


def test_stage3_bullet_has_agent_invocation() -> None:
    """Stage 3 must delegate to a fresh reviewer subagent (D21)."""
    assert (
        "Agent(subagent_type=reviewer): Critique the brief for governance gaps, entropy leakage, HITL misplacement"
        in _CONTENT
    )


def test_stage3_gate_has_escalation_language() -> None:
    """Stage 3 gate must reference architect disposition and Trust Contract §2."""
    assert "architect receives reviewer findings" in _CONTENT
    assert "Trust Contract §2" in _CONTENT


# ── Stage 4 — Planner ─────────────────────────────────────────────────────────


def test_stage4_bullet_has_agent_invocation() -> None:
    """Stage 4 must delegate to a fresh planner subagent (D21)."""
    assert (
        "Agent(subagent_type=planner): Convert approved design into deterministic tasks"
        in _CONTENT
    )


def test_stage4_gate_has_quality_completeness() -> None:
    """Stage 4 gate must mention architect review of quality and completeness."""
    assert "architect reviews plan quality and completeness" in _CONTENT


# ── Stage 5 — Test Builder ────────────────────────────────────────────────────


def test_stage5_bullet_has_agent_invocation() -> None:
    """Stage 5 must delegate to a fresh builder subagent (D21)."""
    assert (
        "Agent(subagent_type=builder): Design tests from plan's test strategy"
        in _CONTENT
    )


def test_stage5_gate_has_coverage_language() -> None:
    """Stage 5 gate must mention architect review of test coverage."""
    assert "architect reviews test coverage against plan" in _CONTENT


# ── Stage 6 — Builder ─────────────────────────────────────────────────────────


def test_stage6_bullet_has_agent_invocation() -> None:
    """Stage 6 must delegate to a fresh builder subagent (D21)."""
    assert (
        "Agent(subagent_type=builder): Implement against the approved plan"
        in _CONTENT
    )


def test_stage6_gate_has_handoff_language() -> None:
    """Stage 6 gate must require all tests to pass before hand-off."""
    assert "all tests must pass before hand-off to architect review" in _CONTENT


# ── Orchestration Constraints section ────────────────────────────────────────


def test_orchestration_constraints_section_present() -> None:
    """deliver-full.md must contain an Orchestration Constraints section."""
    assert "## Orchestration Constraints" in _CONTENT


def test_orchestration_constraints_has_all_six_bullets() -> None:
    """The Orchestration Constraints section must contain all six required bullets."""
    required = [
        "Each agent gate (stages 3\u20136) mandates a fresh-context subagent invocation via",
        "The Architect (orchestrator) remains the final speaker for all human gates",
        "Subagents return findings; Architect disposes and escalates to human if needed",
        "No review stage shall execute inline with the stage it reviews",
        "runtime enforcement will be added in Phase 5 (P5-001, D43)",
        "Isolation constraint applies to agent-gated review stages (3\u20136)",
    ]
    for bullet in required:
        assert bullet in _CONTENT, f"Missing orchestration constraint: {bullet!r}"


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


# ── Integration: no collateral file changes ───────────────────────────────────


def test_no_other_files_modified() -> None:
    """Guard: only deliver-full.md should be modified; no collateral changes allowed.

    This test passes both before implementation (no changes at all) and after
    (exactly one file changed: deliver-full.md).
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    changed_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

    # .azoth/scope-gate.json is updated by the pipeline harness at session open;
    # it is not a code file and its presence is not a collateral implementation change.
    allowed = {
        ".claude/commands/deliver-full.md",
        ".azoth/scope-gate.json",
    }
    unexpected = set(changed_files) - allowed
    assert not unexpected, (
        f"Unexpected files modified alongside deliver-full.md: {sorted(unexpected)}"
    )

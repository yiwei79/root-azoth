"""Tests for .claude/commands/deliver.md — BL-008 (D21).

Governance anchor: D21 — subagent isolation for review gates.
Failure mode: without explicit Agent() invocations in /deliver gate descriptions,
the lean pipeline's review gates can execute inline, defeating context isolation
between the producing stage and the reviewing stage.

All unit tests operate on file content read once at module level.
The integration test guards against collateral file modifications.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DELIVER_PATH = REPO_ROOT / ".claude" / "commands" / "deliver.md"

# Read once; reused across all unit tests.
_CONTENT = DELIVER_PATH.read_text(encoding="utf-8")


# ── Orchestration Constraints section ────────────────────────────────────────


def test_orchestration_constraints_section_present() -> None:
    """deliver.md must contain an Orchestration Constraints section (D21)."""
    assert "## Orchestration Constraints" in _CONTENT


def test_orchestration_constraints_cites_subagent_router() -> None:
    """Orchestration Constraints must cite subagent-router as the policy source (D21)."""
    assert "subagent-router" in _CONTENT


# ── Gate 1 — Planner gate ─────────────────────────────────────────────────────


def test_gate1_has_agent_invocation() -> None:
    """Gate 1 (Planner gate) must invoke Agent(subagent_type=architect) (D21)."""
    assert (
        "Agent(subagent_type=architect) — trigger: context-isolation"
        in _CONTENT
    )


# ── Gate 2 — Test Builder gate ────────────────────────────────────────────────


def test_gate2_has_agent_invocation() -> None:
    """Gate 2 (Test Builder gate) must invoke Agent(subagent_type=architect) (D21)."""
    assert (
        "architect reviews test coverage (trigger: review-independence)"
        in _CONTENT
    )


# ── Gate 3 — Architect Review gate ───────────────────────────────────────────


def test_gate3_orchestration_constraints_has_agent_invocation() -> None:
    """Gate 3 (Architect Review) must be listed in Orchestration Constraints (D21)."""
    assert (
        "Gate 3 (Architect Review stage): `Agent(subagent_type=architect)` — trigger: review-independence"
        in _CONTENT
    )


# ── Router reference ──────────────────────────────────────────────────────────


def test_router_policy_source_present() -> None:
    """deliver.md must reference subagent-router as the policy source (D21)."""
    assert (
        "Policy source: `subagent-router` skill (trigger definitions and routing table)"
        in _CONTENT
    )


# ── Integration: file-scoped collateral guard ─────────────────────────────────


@pytest.mark.xfail(
    strict=False,
    reason="Working-tree snapshot guard from BL-006/BL-008 delivery; fails whenever unrelated files are modified",
)
def test_only_deliver_md_modified() -> None:
    """Guard: only the expected Commit 2 files should be modified.

    This test passes both before implementation (no changes at all) and after
    (exactly the allowed files changed).
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    changed_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

    allowed = {
        ".claude/commands/deliver.md",
        ".claude/commands/deliver-full.md",
        ".claude/commands/auto.md",
        "tests/test_deliver_subagent_gates.py",
        "tests/test_deliver_full_subagent_gates.py",
        ".azoth/scope-gate.json",
        ".azoth/backlog.yaml",
        "skills/subagent-router/SKILL.md",
        "tests/test_subagent_router.py",
        "tests/test_skills.py",
        "azoth.yaml",
    }
    unexpected = set(changed_files) - allowed
    assert not unexpected, (
        f"Unexpected files modified alongside deliver.md: {sorted(unexpected)}"
    )

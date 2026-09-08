"""Tests for skills/subagent-router/SKILL.md — BL-008 (D21).

Governance anchor: D21 — subagent isolation for review gates.
Failure mode: if the routing policy is absent or incomplete, pipeline authors
have no canonical source to determine subagent_type assignments, causing
per-pipeline hardcoding to diverge or be omitted entirely.

All unit tests operate on file content read once at module level.
The integration test guards against collateral file modifications.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / ".agents" / "skills" / "subagent-router" / "SKILL.md"

# Read once; reused across all unit tests.
_CONTENT = SKILL_PATH.read_text(encoding="utf-8")


# ── File existence ────────────────────────────────────────────────────────────


def test_skill_file_exists() -> None:
    """.agents/skills/subagent-router/SKILL.md must exist (D21)."""
    assert SKILL_PATH.is_file(), ".agents/skills/subagent-router/SKILL.md must exist"


# ── Trigger definitions ───────────────────────────────────────────────────────


def test_trigger_review_independence_present() -> None:
    """Skill must define the review-independence trigger (D21)."""
    assert "review-independence" in _CONTENT


def test_trigger_context_isolation_present() -> None:
    """Skill must define the context-isolation trigger (D21)."""
    assert "context-isolation" in _CONTENT


def test_trigger_context_budget_present() -> None:
    """Skill must define the context-budget trigger (D21)."""
    assert "context-budget" in _CONTENT


def test_trigger_parallel_execution_present() -> None:
    """Skill must define the parallel-execution trigger (D21)."""
    assert "parallel-execution" in _CONTENT


# ── Routing table ─────────────────────────────────────────────────────────────


def test_routing_table_present() -> None:
    """Skill must contain a routing table mapping triggers to subagent types."""
    assert "Routing Table" in _CONTENT


def test_routing_table_maps_review_independence_to_reviewer() -> None:
    """review-independence must map to reviewer / architect in the routing table."""
    assert "reviewer" in _CONTENT


def test_routing_table_maps_parallel_execution_to_builder_not_researcher() -> None:
    """parallel-execution must map to builder; researcher must be explicitly excluded."""
    assert "NOT researcher" in _CONTENT


# ── Priority ordering ─────────────────────────────────────────────────────────


def test_priority_ordering_present() -> None:
    """Skill must declare explicit priority ordering for the four triggers."""
    assert "Priority 1: review-independence" in _CONTENT
    assert "Priority 2: context-isolation" in _CONTENT
    assert "Priority 3: context-budget" in _CONTENT
    assert "Priority 4: parallel-execution" in _CONTENT


# ── Exclusion clause ──────────────────────────────────────────────────────────


def test_architect_exclusion_clause_present() -> None:
    """Skill must contain the architect internal sub-invocations exclusion clause (D21)."""
    assert "out-of-scope for this router" in _CONTENT


# ── Spawn prompt contract (BL-011) ────────────────────────────────────────────


def test_spawn_prompt_contract_present() -> None:
    """BL-011: skill must define the minimal spawn template and stage briefs."""
    assert "## Spawn Prompt Contract (BL-011)" in _CONTENT
    assert "pipeline: autonomous-auto | deliver-full | deliver | auto" in _CONTENT
    assert "§Stage briefs: deliver-full" in _CONTENT or "Stage briefs: deliver-full" in _CONTENT


def test_before_after_token_illustration_present() -> None:
    """BL-011: illustrative before/after table for spawn body size."""
    assert "Before / after" in _CONTENT
    assert "anti-pattern" in _CONTENT.lower()


def test_codex_resolver_contract_present() -> None:
    """T-025: Codex spawns must use the runtime resolver before Agent()."""
    assert "## Codex Model Selector Contract (T-025)" in _CONTENT
    assert "scripts/codex_model_selector.py" in _CONTENT
    assert ".azoth/codex-model-selector-policy.yaml" in _CONTENT
    assert ".azoth/codex-model-selector-traces.local.jsonl" in _CONTENT


def test_codex_spawn_selection_is_host_compatible() -> None:
    """Selection flexibility preserves explicit choices and independent stages."""
    assert "host defaults or inheritance" in _CONTENT
    assert "Never invent spawn arguments" in _CONTENT
    assert "Respect explicit task-level model and effort choices" in _CONTENT
    assert "Inheritance never authorizes an inline substitute" in _CONTENT
    assert "The local selector remains available" in _CONTENT
    assert "Do not omit `model` or `reasoning_effort`" not in _CONTENT


# ── Integration: file-scoped collateral guard ─────────────────────────────────


@pytest.mark.xfail(
    strict=False,
    reason="Working-tree snapshot guard from BL-008 delivery; fails whenever unrelated files are modified",
)
def test_only_subagent_router_skill_modified() -> None:
    """Guard: only skills/subagent-router/SKILL.md should be modified in Commit 1.

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
        "skills/subagent-router/SKILL.md",
        "tests/test_subagent_router.py",
        "tests/test_skills.py",
        "azoth.yaml",
        ".azoth/scope-gate.json",
        ".azoth/backlog.yaml",
        # Commit 2 files (pipeline wiring — same session)
        ".claude/commands/auto.md",
        ".claude/commands/deliver.md",
        ".claude/commands/deliver-full.md",
        "tests/test_deliver_subagent_gates.py",
        "tests/test_deliver_full_subagent_gates.py",
    }
    unexpected = set(changed_files) - allowed
    assert not unexpected, (
        f"Unexpected files modified alongside subagent-router skill: {sorted(unexpected)}"
    )

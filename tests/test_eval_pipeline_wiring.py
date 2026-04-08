"""Drift: /eval escalation (E1–E6) stays wired into pipelines and command docs."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "marker",
    ["E1", "E2", "E3", "E4", "E5", "E6"],
    ids=lambda m: m,
)
def test_eval_md_defines_all_escalation_triggers(marker: str) -> None:
    text = _read(".claude/commands/eval.md")
    assert marker in text, f"eval.md must keep trigger {marker} for routing drift detection"


def test_eval_md_orchestrator_agent_wiring() -> None:
    text = _read(".claude/commands/eval.md")
    assert "Orchestrator (agents)" in text
    assert "/eval-swarm" in text
    assert "Intelligent routing" in text


def test_eval_swarm_cross_reference() -> None:
    text = _read(".claude/commands/eval-swarm.md")
    assert "eval.md" in text.lower() or "/eval`" in text


def test_auto_execution_eval_routing_section() -> None:
    text = _read(".claude/commands/auto.md")
    assert "E1–E6" in text or "E1-E6" in text
    assert "eval-swarm" in text.lower() or "/eval-swarm" in text
    assert "Evaluator stage" in text


def test_deliver_eval_routing_bullet() -> None:
    text = _read(".claude/commands/deliver.md")
    assert "Eval / swarm routing" in text
    assert "E1" in text and "E6" in text


def test_deliver_full_eval_routing_bullet() -> None:
    text = _read(".claude/commands/deliver-full.md")
    assert "Eval / swarm routing" in text
    assert "E1" in text and "E6" in text


def test_e2e_workflow_references_eval_commands() -> None:
    text = _read(".claude/workflows/enterprise/e2e-swarm-eval-loop.md")
    assert "/eval-swarm" in text
    assert "/eval" in text

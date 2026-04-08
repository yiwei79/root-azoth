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


def _copilot_prompt(stem: str) -> str:
    return f".github/prompts/{stem}.prompt.md"


def _opencode_cmd(stem: str) -> str:
    return f".opencode/commands/{stem}.md"


def _mirror_paths(stem: str) -> tuple[str, str]:
    return (_copilot_prompt(stem), _opencode_cmd(stem))


@pytest.mark.parametrize("stem", ["eval", "eval-swarm", "auto", "deliver", "deliver-full", "dynamic-full-auto"])
def test_deploy_mirrors_eval_pipeline_wiring(stem: str) -> None:
    """D46: Copilot + OpenCode deploy targets keep eval / eval-swarm routing (P1-010)."""
    copilot_rel, opencode_rel = _mirror_paths(stem)
    for rel in (copilot_rel, opencode_rel):
        assert (REPO / rel).is_file(), f"missing {rel} — run: python3 scripts/azoth-deploy.py"
        text = _read(rel)
        if stem == "eval":
            for marker in ("E1", "E2", "E3", "E4", "E5", "E6"):
                assert marker in text, f"{rel}: missing trigger {marker}"
            for needle in (
                "Orchestrator (agents)",
                "/eval-swarm",
                "Intelligent routing",
            ):
                assert needle in text, f"{rel}: missing {needle!r}"
        elif stem == "eval-swarm":
            assert (
                "eval.md" in text.lower() or "/eval`" in text
            ), f"{rel}: must reference eval.md for baseline routing"
        elif stem == "auto":
            assert "E1–E6" in text or "E1-E6" in text, f"{rel}: missing E1–E6 routing marker"
            assert (
                "eval-swarm" in text.lower() or "/eval-swarm" in text
            ), f"{rel}: missing eval-swarm reference"
            assert "Evaluator stage" in text, f"{rel}: missing Evaluator stage wiring"
        elif stem in ("deliver", "deliver-full"):
            assert "Eval / swarm routing" in text, f"{rel}: missing Eval / swarm routing bullet"
            assert "E1" in text and "E6" in text, f"{rel}: missing E1–E6 span in routing bullet"
        else:
            assert stem == "dynamic-full-auto"
            assert "E1–E6" in text or "E1-E6" in text, f"{rel}: missing E1–E6 (eval.md routing)"
            assert ".claude/commands/eval.md" in text, f"{rel}: missing normative eval.md pointer"
            assert (
                "eval-swarm" in text.lower() or "/eval-swarm" in text
            ), f"{rel}: missing eval-swarm reference"

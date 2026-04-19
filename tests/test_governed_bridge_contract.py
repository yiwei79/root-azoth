"""Bridge-contract regressions for governed scope signaling across pipeline docs."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_auto_pipeline_gate_bridge_wording() -> None:
    text = _read(".claude/commands/auto.md")
    assert "governance_mode == governed" in text
    assert "delivery_pipeline == governed" in text
    assert "delivery_pipeline == deliver-full" in text
    assert "target_layer == M1" in text


def test_orchestrator_bridge_wording_and_eval_trigger() -> None:
    text = _read("agents/tier1-core/orchestrator.agent.md")
    assert "governance_mode == governed" in text
    assert "delivery_pipeline == governed" in text
    assert "delivery_pipeline == deliver-full" in text
    assert "target_layer == M1" in text


def test_eval_e3_bridge_wording() -> None:
    text = _read(".claude/commands/eval.md")
    assert "governance_mode: governed" in text
    assert "delivery_pipeline: governed" in text
    assert "delivery_pipeline: deliver-full" in text
    assert "target_layer: M1" in text

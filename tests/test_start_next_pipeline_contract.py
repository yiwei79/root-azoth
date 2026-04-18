"""Drift guards for resume, scope approval, and pipeline selection contracts."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def _load_contract(rel: str) -> dict:
    return yaml.safe_load(_read(rel))


def test_start_resume_requires_pipeline_or_auto() -> None:
    rel = "commands/start/body.md"
    text = _read(rel)
    assert "/resume" in text, f"{rel}: missing /resume guidance"
    assert "pipeline_command" in text, f"{rel}: missing normalized pipeline_command guidance"
    assert "/auto" in text, f"{rel}: missing /auto default guidance"
    assert "Stage 0" in text, f"{rel}: missing Stage 0 guidance"
    assert (
        "without a second scope-approval wall" in text
        or "do not jump straight to implementation" in text
    ), f"{rel}: missing resume continuity guidance"


def test_next_scope_approval_requires_pipeline_selection() -> None:
    rel = "commands/next/body.md"
    text = _read(rel)
    for needle in (
        "Pipeline selection after scope approval (all scopes)",
        "does **not** authorize direct implementation",
        "/auto` is the default (D23)",
        "Stage 0 goal clarification",
        "For standard scopes, Stage 0 / pipeline selection still applies",
        "governance_mode",
        "pipeline_command",
    ):
        assert needle in text, f"{rel}: missing {needle!r}"


def test_next_refuses_to_overwrite_live_scope() -> None:
    rel = "commands/next/body.md"
    text = _read(rel)
    assert "route to `/resume`, `/park`, or `/session-closeout` instead" in text, (
        f"{rel}: missing active-scope hard stop guidance"
    )


def test_entrypoint_contracts_encode_normalized_runtime_bridge_fields() -> None:
    for rel in ("commands/start/command.yaml", "commands/next/command.yaml"):
        contract = _load_contract(rel)
        runtime = contract["runtime"]
        assert runtime["governance_mode"]["scope_gate_field"] == "governance_mode"
        assert runtime["governance_mode"]["legacy_scope_gate_field"] == "delivery_pipeline"
        assert runtime["pipeline_command"]["scope_gate_field"] == "pipeline_command"


def test_pipeline_command_contracts_require_durable_approval_consumption() -> None:
    expected = {
        "commands/auto/command.yaml": "auto",
        "commands/deliver/command.yaml": "deliver",
        "commands/deliver-full/command.yaml": "deliver-full",
    }
    for rel, command_value in expected.items():
        contract = _load_contract(rel)
        assert contract["execution"]["kind"] == "pipeline"
        assert contract["runtime"]["pipeline_command"]["command_value"] == command_value
        assert contract["runtime"]["pipeline_command"]["run_ledger_field"] == "pipeline_command"
        assert contract["runtime"]["pipeline_command"]["legacy_run_ledger_field"] == "mode"
        approval = contract["runtime"]["approval_consumption"]
        assert approval["helper"] == "scripts/run_ledger.py:consume_human_gate_approval"
        assert approval["durable"] is True
        assert approval["same_run_required"] is True

"""Tests for the Codex runtime model selector (T-025)."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from codex_model_selector import (  # noqa: E402
    ModelSelectionError,
    SelectionDecision,
    load_policy,
    main,
    resolve_codex_spawn,
    write_selector_trace,
)

POLICY_PATH = REPO_ROOT / ".azoth" / "codex-model-selector-policy.yaml"
TRACE_PATH = ".azoth/codex-model-selector-traces.local.jsonl"


def test_load_policy_exposes_runtime_contract() -> None:
    policy = load_policy(POLICY_PATH)

    assert policy["policy_ref"] == "codex-model-selector-policy@2026-04-29"
    assert policy["trace_path"] == TRACE_PATH
    assert policy["supported_reasoning_efforts"] == ["low", "medium", "high", "xhigh"]
    assert policy["default_model_tier"] == "standard"


def test_resolve_codex_spawn_prevents_parent_xhigh_leaf_leak() -> None:
    policy = load_policy(POLICY_PATH)

    decision = resolve_codex_spawn(
        {
            "stage_id": "autonomous_auto_s3_builder",
            "subagent_type": "builder",
            "model_tier": "standard",
            "parent_reasoning_effort": "xhigh",
            "mandatory_tools": ["apply_patch"],
        },
        policy=policy,
    )

    assert isinstance(decision, SelectionDecision)
    assert decision.model
    assert decision.reasoning_effort in {"low", "medium", "high"}
    assert decision.reasoning_effort != "xhigh"
    assert decision.to_spawn_kwargs()["model"] == decision.model
    assert decision.to_spawn_kwargs()["reasoning_effort"] == decision.reasoning_effort


def test_standard_tier_prefers_gpt55_and_medium_for_unsignaled_judgment_stages() -> None:
    policy = load_policy(POLICY_PATH)

    decision = resolve_codex_spawn(
        {
            "stage_id": "auto_s1_planner",
            "subagent_type": "planner",
            "model_tier": "standard",
        },
        policy=policy,
    )

    assert decision.model == "gpt-5.5"
    assert decision.reasoning_effort == "medium"
    assert decision.selection_rules == ("type_default",)


def test_standard_tier_escalates_judgment_work_from_task_signals() -> None:
    policy = load_policy(POLICY_PATH)

    decision = resolve_codex_spawn(
        {
            "stage_id": "auto_s1_planner",
            "subagent_type": "planner",
            "model_tier": "standard",
            "risk": "governance-change",
            "complexity": "cross-layer",
            "knowledge": "instruction-refinement",
            "target_layer": "M1",
        },
        policy=policy,
    )

    assert decision.model == "gpt-5.5"
    assert decision.reasoning_effort == "high"
    assert "risk_high" in decision.selection_rules
    assert "target_layer_m1" in decision.selection_rules
    assert "knowledge_high" in decision.selection_rules


def test_fast_read_only_scan_prefers_mini_low() -> None:
    policy = load_policy(POLICY_PATH)

    decision = resolve_codex_spawn(
        {
            "stage_id": "auto_s0_repo_search",
            "subagent_type": "researcher",
            "model_tier": "fast",
            "knowledge": "known-pattern",
        },
        policy=policy,
    )

    assert decision.model == "gpt-5.4-mini"
    assert decision.reasoning_effort == "low"
    assert "fast_read_only_low" in decision.selection_rules


def test_resolve_codex_spawn_falls_back_from_unavailable_policy_alias() -> None:
    policy = load_policy(POLICY_PATH)
    policy = copy.deepcopy(policy)
    preferred_alias = policy["tiers"]["standard"]["preferred_aliases"][0]
    policy["aliases"][preferred_alias]["availability_state"] = "unavailable"

    decision = resolve_codex_spawn(
        {
            "stage_id": "autonomous_auto_s3_builder",
            "subagent_type": "builder",
            "model_tier": "standard",
            "mandatory_tools": ["apply_patch"],
            "complexity": "multi-file",
            "triggers": ["failing-tests"],
        },
        policy=policy,
    )

    assert decision.alias != preferred_alias
    assert decision.fallback_reason is not None
    assert "unavailable" in decision.fallback_reason


def test_resolve_codex_spawn_fails_closed_for_deprecated_explicit_alias() -> None:
    policy = load_policy(POLICY_PATH)

    with pytest.raises(ModelSelectionError, match="deprecated"):
        resolve_codex_spawn(
            {
                "stage_id": "autonomous_auto_s3_builder",
                "subagent_type": "builder",
                "model_tier": "standard",
                "model_alias": "legacy-codex",
                "mandatory_tools": ["apply_patch"],
            },
            policy=policy,
        )


def test_resolve_codex_spawn_fails_closed_for_unavailable_explicit_alias() -> None:
    policy = load_policy(POLICY_PATH)
    policy = copy.deepcopy(policy)
    policy["aliases"]["gpt-5.4"]["availability_state"] = "unavailable"

    with pytest.raises(ModelSelectionError, match="unavailable"):
        resolve_codex_spawn(
            {
                "stage_id": "autonomous_auto_s3_builder",
                "subagent_type": "builder",
                "model_tier": "standard",
                "model_alias": "gpt-5.4",
                "mandatory_tools": ["apply_patch"],
            },
            policy=policy,
        )


def test_resolve_codex_spawn_fails_closed_for_unsupported_effort() -> None:
    policy = load_policy(POLICY_PATH)

    with pytest.raises(ModelSelectionError, match="reasoning_effort"):
        resolve_codex_spawn(
            {
                "stage_id": "autonomous_auto_s3_builder",
                "subagent_type": "builder",
                "model_tier": "standard",
                "model_alias": "gpt-5.3-codex",
                "reasoning_effort": "none",
                "mandatory_tools": ["apply_patch"],
            },
            policy=policy,
        )


def test_resolve_codex_spawn_requires_override_for_xhigh() -> None:
    policy = load_policy(POLICY_PATH)

    with pytest.raises(ModelSelectionError, match="xhigh requires"):
        resolve_codex_spawn(
            {
                "stage_id": "auto_s3_evaluator",
                "subagent_type": "evaluator",
                "model_tier": "premium",
                "reasoning_effort": "xhigh",
            },
            policy=policy,
        )


def test_resolve_codex_spawn_fails_closed_for_mandatory_tool_mismatch() -> None:
    policy = load_policy(POLICY_PATH)

    with pytest.raises(ModelSelectionError, match="mandatory_tools"):
        resolve_codex_spawn(
            {
                "stage_id": "autonomous_auto_s3_builder",
                "subagent_type": "builder",
                "model_tier": "fast",
                "model_alias": "gpt-5.4-nano",
                "mandatory_tools": ["apply_patch"],
            },
            policy=policy,
        )


def test_resolve_codex_spawn_requires_override_ref_and_reason_together() -> None:
    policy = load_policy(POLICY_PATH)

    with pytest.raises(ModelSelectionError, match="override_ref and override_reason"):
        resolve_codex_spawn(
            {
                "stage_id": "autonomous_auto_s3_builder",
                "subagent_type": "builder",
                "model_tier": "standard",
                "model_alias": "legacy-codex",
                "override_ref": "human-gate-123",
                "mandatory_tools": ["apply_patch"],
            },
            policy=policy,
        )


def test_resolve_codex_spawn_allows_explicit_override_and_trace(tmp_path: Path) -> None:
    policy = load_policy(POLICY_PATH)

    decision = resolve_codex_spawn(
        {
            "stage_id": "autonomous_auto_s3_builder",
            "subagent_type": "builder",
            "model_tier": "standard",
            "model_alias": "legacy-codex",
            "reasoning_effort": "medium",
            "override_ref": "human-gate-123",
            "override_reason": "bounded replay of deprecated alias behavior",
            "mandatory_tools": ["apply_patch"],
        },
        policy=policy,
    )
    trace_file = tmp_path / "selector.jsonl"

    write_selector_trace(decision, trace_path=trace_file)

    trace = json.loads(trace_file.read_text(encoding="utf-8").strip())
    assert decision.used_override is True
    assert trace["used_override"] is True
    assert trace["override_ref"] == "human-gate-123"
    assert trace["override_reason"] == "bounded replay of deprecated alias behavior"
    assert trace["alias"] == "legacy-codex"


def test_write_selector_trace_records_auditable_decision(tmp_path: Path) -> None:
    policy = load_policy(POLICY_PATH)
    decision = resolve_codex_spawn(
        {
            "stage_id": "autonomous_auto_s3_builder",
            "subagent_type": "builder",
            "model_tier": "standard",
            "mandatory_tools": ["apply_patch"],
            "complexity": "multi-file",
            "triggers": ["failing-tests"],
        },
        policy=policy,
    )

    trace_file = tmp_path / "selector.jsonl"
    write_selector_trace(decision, trace_path=trace_file)

    trace = json.loads(trace_file.read_text(encoding="utf-8").strip())
    assert trace["model"] == decision.model
    assert trace["reasoning_effort"] == decision.reasoning_effort
    assert trace["model_tier"] == "standard"
    assert trace["policy_ref"] == policy["policy_ref"]
    assert trace["source_observed_on"] == policy["source_observed_on"]
    assert trace["complexity"] == "multi-file"
    assert trace["selection_rules"] == [
        "type_default",
        "complexity_high",
        "trigger_high",
    ]
    assert "fallback_reason" in trace


def test_cli_resolve_outputs_spawn_fields_and_trace(tmp_path: Path) -> None:
    trace_file = tmp_path / "selector.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "codex_model_selector.py"),
            "resolve",
            "--stage-id",
            "auto_s2_builder",
            "--subagent-type",
            "builder",
            "--model-tier",
            "standard",
            "--mandatory-tool",
            "apply_patch",
            "--complexity",
            "complex",
            "--trigger",
            "bounded-replay",
            "--trace-path",
            str(trace_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["model"] == "gpt-5.5"
    assert payload["reasoning_effort"] == "high"
    assert payload["spawn_fields"] == {
        "model": "gpt-5.5",
        "reasoning_effort": "high",
    }
    assert payload["selection_rules"] == [
        "type_default",
        "complexity_high",
        "trigger_high",
    ]
    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    assert trace["stage_id"] == "auto_s2_builder"


def test_main_no_trace_mode_prints_json_without_trace(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    trace_file = tmp_path / "selector.jsonl"

    assert (
        main(
            [
                "resolve",
                "--stage-id",
                "auto_s1_planner",
                "--subagent-type",
                "planner",
                "--model-tier",
                "standard",
                "--trace-path",
                str(trace_file),
                "--no-trace",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["spawn_fields"]["model"] == "gpt-5.5"
    assert trace_file.exists() is False


def test_policy_does_not_prefer_deprecated_or_unavailable_aliases() -> None:
    policy = load_policy(POLICY_PATH)

    for tier in policy["tiers"].values():
        for alias in tier["preferred_aliases"]:
            alias_policy = policy["aliases"][alias]
            assert alias_policy["availability_state"] == "current"
            assert alias_policy.get("deprecated") is not True


def test_gitignore_excludes_local_selector_traces() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert TRACE_PATH in gitignore

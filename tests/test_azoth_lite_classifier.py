from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from azoth_lite import (  # noqa: E402
    SIDE_EFFECT_CLASSES,
    AzothLiteRequest,
    classify_request,
)


FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "azoth_lite_phase2_cases.json"


def _load_fixture_group(group: str) -> list[dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return list(payload[group])


@pytest.mark.parametrize("case", _load_fixture_group("phase1_cases"), ids=lambda case: case["id"])
def test_phase1_shadow_cases_classify_to_expected_profile(case: dict[str, object]) -> None:
    decision = classify_request(AzothLiteRequest.from_mapping(case))

    expected = case["expected"]
    assert decision.side_effect_class == expected["side_effect_class"]
    assert decision.selected_profile == expected["selected_profile"]
    assert decision.stop_state == expected["stop_state"]
    assert decision.escalate is expected["escalate"]


def test_fixture_set_represents_all_side_effect_classes() -> None:
    decisions = [
        classify_request(AzothLiteRequest.from_mapping(case))
        for case in _load_fixture_group("side_effect_cases")
    ]

    assert {decision.side_effect_class for decision in decisions} == set(SIDE_EFFECT_CLASSES)


@pytest.mark.parametrize("case", _load_fixture_group("side_effect_cases"), ids=lambda case: case["id"])
def test_side_effect_fixtures_classify_to_expected_profile(case: dict[str, object]) -> None:
    decision = classify_request(AzothLiteRequest.from_mapping(case))

    expected = case["expected"]
    assert decision.side_effect_class == expected["side_effect_class"]
    assert decision.selected_profile == expected["selected_profile"]
    assert decision.stop_state == expected["stop_state"]
    assert decision.escalate is expected["escalate"]


def test_escalation_decision_includes_advisory_handoff_packet() -> None:
    case = next(
        item
        for item in _load_fixture_group("phase1_cases")
        if item["id"] == "F4-governed-state-escalation"
    )

    decision = classify_request(AzothLiteRequest.from_mapping(case))

    assert decision.escalate is True
    assert decision.handoff_packet is not None
    assert decision.handoff_packet["goal"] == case["goal"]
    assert decision.handoff_packet["recommended_route"] == "azoth-full"
    assert decision.handoff_packet["stop_rule"] == "stop before mutation"
    assert "governed_state_change" in decision.escalation_reasons


def test_context_view_is_compact_and_advisory_for_local_edit() -> None:
    case = next(
        item
        for item in _load_fixture_group("phase1_cases")
        if item["id"] == "F3-ordinary-local-edit"
    )

    decision = classify_request(AzothLiteRequest.from_mapping(case))
    context_view = decision.to_context_view()

    assert context_view == {
        "goal": case["goal"],
        "success_criteria": [],
        "known_constraints": [],
        "dirty_worktree_summary": "",
        "side_effect_class": "local_edit",
        "allowed_actions": [
            "edit ordinary source, tests, docs, or research artifacts outside governed state",
            "run focused verification",
        ],
        "forbidden_actions": [
            "mutate .azoth state",
            "change kernel/governance",
            "package, release, deploy, merge, close out, or declare final delivery",
        ],
        "escalation_triggers": [],
        "selected_profile": "azoth-lite",
        "stop_rule": "complete the local task, then stop",
        "trace_required": True,
    }

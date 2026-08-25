from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from harness_profile import (  # noqa: E402
    HarnessRequest,
    classify_harness_request,
    route_capsule_for_profile,
)


FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "personal_harness_cases.yaml"


def _fixture_cases() -> list[dict[str, object]]:
    return list(yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))["cases"])


@pytest.mark.parametrize("case", _fixture_cases(), ids=lambda case: str(case["id"]))
def test_fixture_cases_classify_to_personal_harness_tiers(case: dict[str, object]) -> None:
    decision = classify_harness_request(HarnessRequest.from_mapping(case))

    expected = case["expected"]
    assert decision.profile == expected["profile"]
    assert decision.side_effect_class == expected["side_effect_class"]
    assert decision.route.route_state == expected["route_state"]
    assert decision.route.authority_required is expected["authority_required"]
    assert decision.route.authority_plane == expected["authority_plane"]


def test_guide_context_view_is_lightweight_and_user_facing() -> None:
    decision = classify_harness_request(
        HarnessRequest(goal="Help me decide what Azoth mode I need.", requested_actions=("read",))
    )

    context_view = decision.to_context_view()

    assert context_view["harness_profile"] == "guide"
    assert context_view["operator_promise"].startswith("Azoth is present as philosophy")
    assert context_view["route_capsule"]["route_state"] == "answer"
    assert context_view["route_capsule"]["next_safe_action"] == (
        "read orientation and decide whether to request assisted mode"
    )
    assert context_view["forbidden_actions"] == [
        "do not mutate project repos",
        "do not claim agents, planning state, or autonomy are installed",
        "do not open cross-repo writes",
    ]


def test_governed_autonomy_requires_budget_ledger_and_stop_conditions() -> None:
    decision = classify_harness_request(
        HarnessRequest(
            goal="Run autonomous loop for the next campaign slice.",
            requested_actions=("update",),
            planned_paths=(".azoth/run-ledger.yaml",),
        )
    )

    assert decision.profile == "governed_autonomy"
    assert decision.route.authority_required is True
    assert list(decision.route.required_inputs) == [
        "managed-mode readiness",
        "explicit autonomy budget",
        "write-claim policy",
        "stop/approval conditions",
    ]
    assert decision.route.stop_reason == "fresh governed-autonomy authority required"


def test_kernel_or_external_request_stops_without_disguising_as_daily_mode() -> None:
    decision = classify_harness_request(
        HarnessRequest(
            goal="Deploy Azoth and update kernel trust contract.",
            requested_actions=("deploy",),
            planned_paths=("kernel/TRUST_CONTRACT.md",),
        )
    )

    assert decision.profile == "governed_autonomy"
    assert decision.route.route_state == "stop"
    assert decision.route.authority_required is True
    assert decision.route.stop_reason == "protected or external action requires explicit human authority"


def test_route_capsule_is_deterministic_json_ready() -> None:
    decision = classify_harness_request(
        HarnessRequest(
            goal="Verify whether my personal cockpit can read this project.",
            requested_actions=("focused_verification",),
            trace_required=True,
        )
    )

    assert decision.to_route_capsule() == {
        "profile": "assisted",
        "side_effect_class": "read_only",
        "route_state": "assist",
        "authority_required": False,
        "authority_plane": "root_azoth",
        "required_inputs": [
            "guide-mode receipt",
            "installed skill/agent/command inventory",
            "explicit operator acceptance of assisted mode",
        ],
        "next_safe_action": "run read-only assisted checks or request managed-mode hydration",
        "stop_reason": "",
    }


def test_route_capsule_for_profile_exposes_cockpit_readback_without_reclassifying_goal() -> None:
    assert route_capsule_for_profile("assisted").to_json_dict() == {
        "profile": "assisted",
        "side_effect_class": "read_only",
        "route_state": "assist",
        "authority_required": False,
        "authority_plane": "root_azoth",
        "required_inputs": [
            "guide-mode receipt",
            "installed skill/agent/command inventory",
            "explicit operator acceptance of assisted mode",
        ],
        "next_safe_action": "run read-only assisted checks or request managed-mode hydration",
        "stop_reason": "",
    }

    governed = route_capsule_for_profile("governed_autonomy").to_json_dict()
    assert governed["route_state"] == "authority_required"
    assert governed["authority_required"] is True
    assert governed["stop_reason"] == "fresh governed-autonomy authority required"

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from autonomous_campaign_presets import (  # noqa: E402
    compile_autonomous_auto_init_packet,
    load_campaign_preset,
    validate_agentic_eval_packets,
)


def test_native_pm_preset_compiles_to_autonomous_auto_init_inputs() -> None:
    preset = load_campaign_preset(
        ROOT, "native-pm-campaign-architecture-discovery"
    )

    packet = compile_autonomous_auto_init_packet(
        preset,
        operator_goal="Find the next architecture discovery campaign.",
        loop_id="native-pm-test-loop",
    )

    assert packet["loop_id"] == "native-pm-test-loop"
    assert packet["objective"] == "Native PM Campaign Architecture Discovery"
    assert packet["max_iterations"] == 3
    assert packet["replay_threshold"] == 1
    assert packet["allowed_actions"] == [
        "research_initiative",
        "refine_proposal",
        "capture_self_improvement",
    ]
    assert packet["queue"][0]["action"] == "research_initiative"
    assert packet["queue"][0]["candidate_id"] == "native-pm-campaign-architecture-discovery"
    declaration = packet["vision_declaration"]
    assert declaration["selected_seed"] == "native-pm-campaign-architecture-discovery"
    assert declaration["campaign_owner"] == "PM orchestrator"
    assert declaration["agentic_eval"]["threshold"] == 0.90
    assert declaration["agentic_eval"]["max_iterations"] == 3
    assert declaration["agentic_eval"]["required_packet_fields"] == [
        "score",
        "threshold",
        "dimensions",
        "residual_risks",
        "iteration_history",
    ]
    assert declaration["expected_stages"] == [
        "architect",
        "researcher",
        "evaluator",
        "reviewer",
    ]
    assert "hydrate_task" in packet["blocked_actions"]
    assert "ship_task" in packet["blocked_actions"]
    assert "autonomous_loop.py remains the execution governor" in packet["approval_basis"]


def test_preset_compiler_does_not_emit_route_authority() -> None:
    preset = load_campaign_preset(
        ROOT, "native-pm-campaign-architecture-discovery"
    )

    packet = compile_autonomous_auto_init_packet(
        preset,
        operator_goal="Start the native PM preset.",
    )

    rendered = yaml.safe_dump(packet, sort_keys=True)
    assert "route_authority" not in rendered
    assert "strategy_preflight" not in rendered
    assert packet["route_boundary"]["authority"] == "existing_autonomous_auto_control_plane"
    assert packet["route_boundary"]["preset_role"] == "declaration_compiler_only"


def test_green_campaign_without_formal_eval_packets_is_incomplete() -> None:
    result = validate_agentic_eval_packets(
        [
            {
                "campaign_id": "pm-green-without-eval",
                "vision_band": "green",
                "summary": "Narrative-only green result.",
            }
        ]
    )

    assert result["complete"] is False
    assert result["blocking_reasons"] == [
        "formal agentic-eval packet 0 is missing score",
        "formal agentic-eval packet 0 is missing threshold",
        "formal agentic-eval packet 0 is missing dimensions",
        "formal agentic-eval packet 0 is missing residual_risks",
        "formal agentic-eval packet 0 is missing iteration_history",
    ]


def test_formal_eval_packet_passes_mechanical_acceptance() -> None:
    preset = load_campaign_preset(
        ROOT, "native-pm-campaign-architecture-discovery"
    )
    result = validate_agentic_eval_packets(
        [
            {
                "score": 0.91,
                "threshold": 0.90,
                "dimensions": {
                    "native_simplicity": 0.93,
                    "architectural_fit": 0.92,
                    "governance_safety": 0.92,
                    "pm_orchestration_quality": 0.92,
                    "iterative_quality": 0.91,
                    "bounded_implementation": 0.88,
                    "operator_ux": 0.94,
                },
                "residual_risks": [
                    "Preset compiler must not become route authority."
                ],
                "iteration_history": [
                    {
                        "iteration": 1,
                        "score": 0.88,
                        "critique": "Tighten evaluator packet mechanics.",
                        "refinement": "Require threshold, dimensions, risks, and history.",
                    },
                    {
                        "iteration": 2,
                        "score": 0.91,
                        "critique": "Passes strict bar.",
                        "refinement": "Stop.",
                    },
                ],
            }
        ],
        required_dimensions=preset["agentic_eval"]["dimensions"],
        minimum_threshold=preset["agentic_eval"]["threshold"],
    )

    assert result["complete"] is True
    assert result["overall_score"] == 0.91
    assert result["threshold"] == 0.90
    assert result["blocking_reasons"] == []


def test_eval_packet_below_threshold_blocks_acceptance() -> None:
    result = validate_agentic_eval_packets(
        [
            {
                "score": 0.84,
                "threshold": 0.85,
                "dimensions": {"native_simplicity": 0.90},
                "residual_risks": [],
                "iteration_history": [{"iteration": 1, "score": 0.84}],
            }
        ]
    )

    assert result["complete"] is False
    assert result["blocking_reasons"] == [
        "formal agentic-eval packet 0 score 0.84 is below threshold 0.85"
    ]


def test_eval_packet_missing_required_dimensions_blocks_acceptance() -> None:
    result = validate_agentic_eval_packets(
        [
            {
                "score": 0.91,
                "threshold": 0.90,
                "dimensions": {"native_simplicity": 0.93},
                "residual_risks": [],
                "iteration_history": [{"iteration": 1, "score": 0.91}],
            }
        ],
        required_dimensions=[
            "native_simplicity",
            "architectural_fit",
            "governance_safety",
        ],
        minimum_threshold=0.90,
    )

    assert result["complete"] is False
    assert result["blocking_reasons"] == [
        "formal agentic-eval packet 0 dimensions missing: architectural_fit, governance_safety"
    ]


def test_eval_packet_threshold_below_campaign_minimum_blocks_acceptance() -> None:
    result = validate_agentic_eval_packets(
        [
            {
                "score": 0.91,
                "threshold": 0.85,
                "dimensions": {"native_simplicity": 0.93},
                "residual_risks": [],
                "iteration_history": [{"iteration": 1, "score": 0.91}],
            }
        ],
        required_dimensions=["native_simplicity"],
        minimum_threshold=0.90,
    )

    assert result["complete"] is False
    assert result["blocking_reasons"] == [
        "formal agentic-eval packet 0 threshold 0.85 is below required minimum 0.90"
    ]


def test_eval_packet_non_numeric_score_blocks_acceptance() -> None:
    result = validate_agentic_eval_packets(
        [
            {
                "score": "excellent",
                "threshold": 0.90,
                "dimensions": {"native_simplicity": 0.93},
                "residual_risks": [],
                "iteration_history": [{"iteration": 1, "score": 0.91}],
            }
        ],
        required_dimensions=["native_simplicity"],
        minimum_threshold=0.90,
    )

    assert result["complete"] is False
    assert result["blocking_reasons"] == [
        "formal agentic-eval packet 0 score and threshold must be numeric"
    ]


def test_unknown_preset_fails_closed() -> None:
    with pytest.raises(FileNotFoundError):
        load_campaign_preset(ROOT, "missing-preset")


@pytest.mark.parametrize("preset_id", ["../secret", "nested/preset", r"nested\\preset", ""])
def test_path_like_preset_ids_fail_closed(preset_id: str) -> None:
    with pytest.raises(ValueError):
        load_campaign_preset(ROOT, preset_id)

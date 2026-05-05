#!/usr/bin/env python3
"""Compile native autonomous-auto campaign presets into loop-init inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yaml_helpers import safe_load_yaml_path


ROOT = Path(__file__).resolve().parent.parent
PRESET_DIR = ".azoth/campaign-presets"
REQUIRED_EVAL_FIELDS = (
    "score",
    "threshold",
    "dimensions",
    "residual_risks",
    "iteration_history",
)


def _validate_preset_id(preset_id: str) -> str:
    clean_id = preset_id.strip()
    if not clean_id:
        raise ValueError("preset_id is required")
    if "/" in clean_id or "\\" in clean_id or ".." in clean_id:
        raise ValueError("preset_id must be a registry id, not a path")
    return clean_id


def load_campaign_preset(repo_root: Path, preset_id: str) -> dict[str, Any]:
    """Load a named campaign preset from the repo-native preset registry."""
    clean_id = _validate_preset_id(preset_id)
    path = repo_root / PRESET_DIR / f"{clean_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(path)
    preset = safe_load_yaml_path(path) or {}
    if not isinstance(preset, dict):
        raise ValueError(f"preset {clean_id!r} must be a YAML mapping")
    if str(preset.get("id") or "").strip() != clean_id:
        raise ValueError(f"preset id mismatch for {path}")
    return preset


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _approval_basis(preset: dict[str, Any], *, operator_goal: str) -> str:
    blocked = ", ".join(_string_list(preset.get("blocked_actions")))
    allowed = ", ".join(_string_list(preset.get("allowed_actions")))
    return (
        f"Operator requested: {operator_goal.strip() or preset['objective']}. "
        f"Preset {preset['id']} compiles a native PM campaign declaration; "
        "autonomous_loop.py remains the execution governor. "
        f"Allowed actions: {allowed}. Blocked actions: {blocked}. "
        f"Stop condition: {preset['stop_condition']}"
    )


def compile_autonomous_auto_init_packet(
    preset: dict[str, Any],
    *,
    operator_goal: str,
    loop_id: str | None = None,
) -> dict[str, Any]:
    """Render a preset into existing autonomous-auto init/open inputs.

    The packet is intentionally not route authority. It is a deterministic
    declaration compiler that feeds the existing loop governor.
    """
    preset_id = str(preset.get("id") or "").strip()
    if not preset_id:
        raise ValueError("preset id is required")
    allowed_actions = _string_list(preset.get("allowed_actions"))
    if not allowed_actions:
        raise ValueError(f"preset {preset_id!r} must define allowed_actions")
    blocked_actions = _string_list(preset.get("blocked_actions"))
    stages = _string_list(preset.get("expected_stages"))
    agentic_eval = preset.get("agentic_eval")
    if not isinstance(agentic_eval, dict):
        raise ValueError(f"preset {preset_id!r} must define agentic_eval")
    queue_seed = preset.get("queue_seed")
    if not isinstance(queue_seed, dict):
        raise ValueError(f"preset {preset_id!r} must define queue_seed")

    declaration = {
        "status": "approved",
        "summary": str(preset.get("summary") or preset.get("objective") or "").strip(),
        "selected_seed": str(queue_seed.get("candidate_id") or preset_id).strip(),
        "selected_seed_type": str(preset.get("selected_seed_type") or "preset").strip(),
        "scope_notes": str(preset.get("scope_notes") or "").strip(),
        "campaign_owner": str(preset.get("campaign_owner") or "PM orchestrator").strip(),
        "expected_stages": stages,
        "agentic_eval": {
            "pattern": str(agentic_eval.get("pattern") or "evaluator-optimizer"),
            "threshold": float(agentic_eval.get("threshold", 0.85)),
            "max_iterations": int(agentic_eval.get("max_iterations", 3)),
            "dimensions": _string_list(agentic_eval.get("dimensions")),
            "required_packet_fields": list(REQUIRED_EVAL_FIELDS),
        },
        "stop_condition": str(preset.get("stop_condition") or "").strip(),
    }

    return {
        "schema_version": 1,
        "packet_type": "autonomous_auto_campaign_preset_init",
        "preset_id": preset_id,
        "loop_id": loop_id or str(preset.get("default_loop_id") or preset_id).strip(),
        "objective": str(preset.get("objective") or "").strip(),
        "max_iterations": int(preset.get("max_iterations", 3)),
        "replay_threshold": int(preset.get("replay_threshold", 1)),
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
        "queue": [dict(queue_seed)],
        "vision_declaration": declaration,
        "approval_basis": _approval_basis(preset, operator_goal=operator_goal),
        "route_boundary": {
            "preset_role": "declaration_compiler_only",
            "authority": "existing_autonomous_auto_control_plane",
            "non_goals": [
                "No lifecycle-route replacement.",
                "No autonomous_loop.py strategy-preflight replacement.",
                "No hidden approval for blocked actions.",
            ],
        },
    }


def validate_agentic_eval_packets(
    packets: list[dict[str, Any]],
    *,
    required_dimensions: list[str] | None = None,
    minimum_threshold: float | None = None,
) -> dict[str, Any]:
    """Mechanically validate formal agentic-eval packets for campaign acceptance."""
    blocking_reasons: list[str] = []
    scores: list[float] = []
    thresholds: list[float] = []
    required_dimension_set = {
        str(item).strip() for item in (required_dimensions or []) if str(item).strip()
    }
    for index, packet in enumerate(packets):
        if not isinstance(packet, dict):
            blocking_reasons.append(f"formal agentic-eval packet {index} must be a mapping")
            continue
        missing = [field for field in REQUIRED_EVAL_FIELDS if field not in packet]
        for field in missing:
            blocking_reasons.append(f"formal agentic-eval packet {index} is missing {field}")
        if missing:
            continue
        try:
            score = float(packet["score"])
            threshold = float(packet["threshold"])
        except (TypeError, ValueError):
            blocking_reasons.append(
                f"formal agentic-eval packet {index} score and threshold must be numeric"
            )
            continue
        scores.append(score)
        thresholds.append(threshold)
        dimensions = packet["dimensions"]
        if not isinstance(dimensions, dict) or not dimensions:
            blocking_reasons.append(
                f"formal agentic-eval packet {index} dimensions must be a non-empty mapping"
            )
        elif required_dimension_set:
            missing_dimensions = sorted(required_dimension_set - set(dimensions))
            if missing_dimensions:
                blocking_reasons.append(
                    f"formal agentic-eval packet {index} dimensions missing: "
                    f"{', '.join(missing_dimensions)}"
                )
        if not isinstance(packet["residual_risks"], list):
            blocking_reasons.append(
                f"formal agentic-eval packet {index} residual_risks must be a list"
            )
        if not isinstance(packet["iteration_history"], list) or not packet["iteration_history"]:
            blocking_reasons.append(
                f"formal agentic-eval packet {index} iteration_history must be a non-empty list"
            )
        if minimum_threshold is not None and threshold < float(minimum_threshold):
            blocking_reasons.append(
                f"formal agentic-eval packet {index} threshold {threshold:.2f} "
                f"is below required minimum {float(minimum_threshold):.2f}"
            )
        if score < threshold:
            blocking_reasons.append(
                f"formal agentic-eval packet {index} score {score:.2f} "
                f"is below threshold {threshold:.2f}"
            )

    return {
        "complete": bool(packets) and not blocking_reasons,
        "packet_count": len(packets),
        "overall_score": min(scores) if scores else None,
        "threshold": max(thresholds) if thresholds else None,
        "blocking_reasons": blocking_reasons,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preset_id")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--operator-goal", default="")
    parser.add_argument("--loop-id", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = args.repo_root.resolve()
    preset = load_campaign_preset(repo_root, args.preset_id)
    packet = compile_autonomous_auto_init_packet(
        preset,
        operator_goal=args.operator_goal,
        loop_id=args.loop_id,
    )
    print(json.dumps(packet, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Resolve Codex subagent model and reasoning effort from a local policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from yaml_helpers import safe_load_yaml_path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY_PATH = REPO_ROOT / ".azoth" / "codex-model-selector-policy.yaml"


class ModelSelectionError(ValueError):
    """Raised when a Codex spawn request cannot be resolved safely."""


@dataclass(frozen=True)
class SelectionDecision:
    """Concrete Codex spawn fields plus audit metadata."""

    alias: str
    model: str
    reasoning_effort: str
    model_tier: str
    policy_ref: str
    confidence: float
    fallback_reason: str | None
    source_observed_on: str
    stage_id: str | None
    subagent_type: str | None
    used_override: bool = False
    override_ref: str | None = None
    override_reason: str | None = None

    def to_spawn_kwargs(self) -> dict[str, str]:
        """Return the explicit fields required by the active Codex spawn API."""
        return {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
        }


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    """Load and validate the Codex model selector policy."""
    policy_path = Path(path)
    policy = safe_load_yaml_path(policy_path)
    if not isinstance(policy, dict):
        raise ModelSelectionError(f"Policy at {policy_path} must be a YAML mapping")

    for key in (
        "policy_ref",
        "source_observed_on",
        "trace_path",
        "default_model_tier",
        "supported_reasoning_efforts",
        "tiers",
        "aliases",
    ):
        if key not in policy:
            raise ModelSelectionError(f"Policy missing required key: {key}")

    supported_efforts = policy["supported_reasoning_efforts"]
    if supported_efforts != ["low", "medium", "high", "xhigh"]:
        raise ModelSelectionError(
            "Policy supported_reasoning_efforts must be low/medium/high/xhigh"
        )

    tiers = policy["tiers"]
    aliases = policy["aliases"]
    default_tier = policy["default_model_tier"]
    if default_tier not in tiers:
        raise ModelSelectionError(f"Unknown default_model_tier: {default_tier}")

    for tier_name, tier_policy in tiers.items():
        preferred_aliases = tier_policy.get("preferred_aliases")
        if not isinstance(preferred_aliases, list) or not preferred_aliases:
            raise ModelSelectionError(f"Tier {tier_name} must define preferred_aliases")
        default_effort = tier_policy.get("default_reasoning_effort")
        if default_effort not in supported_efforts:
            raise ModelSelectionError(
                f"Tier {tier_name} default_reasoning_effort is unsupported"
            )
        for alias in preferred_aliases:
            if alias not in aliases:
                raise ModelSelectionError(
                    f"Tier {tier_name} references unknown alias {alias}"
                )
            alias_policy = aliases[alias]
            if alias_policy.get("availability_state") != "current":
                raise ModelSelectionError(
                    f"Tier {tier_name} prefers non-current alias {alias}"
                )
            if alias_policy.get("deprecated") is True:
                raise ModelSelectionError(
                    f"Tier {tier_name} prefers deprecated alias {alias}"
                )

    return policy


def resolve_codex_spawn(
    spawn_request: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
    policy_path: Path | str = DEFAULT_POLICY_PATH,
) -> SelectionDecision:
    """Resolve a subagent spawn request to explicit Codex model fields."""
    active_policy = dict(policy) if policy is not None else load_policy(policy_path)
    supported_efforts = active_policy["supported_reasoning_efforts"]
    tier_name = str(
        spawn_request.get("model_tier") or active_policy["default_model_tier"]
    )
    tiers = active_policy["tiers"]
    aliases = active_policy["aliases"]

    if tier_name not in tiers:
        raise ModelSelectionError(f"Unknown model_tier: {tier_name}")

    tier_policy = tiers[tier_name]
    subagent_type = _optional_str(spawn_request.get("subagent_type"))
    requested_effort = spawn_request.get("reasoning_effort")
    if requested_effort is None:
        requested_effort = _default_effort(tier_policy, subagent_type)
    requested_effort = str(requested_effort)
    if requested_effort not in supported_efforts:
        raise ModelSelectionError(
            "reasoning_effort must be one of low, medium, high, or xhigh"
        )

    explicit_alias = _optional_str(
        spawn_request.get("model_alias") or spawn_request.get("alias")
    )
    candidates = [explicit_alias] if explicit_alias else list(tier_policy["preferred_aliases"])
    mandatory_tools = tuple(_string_list(spawn_request.get("mandatory_tools", [])))
    override_ref = _optional_str(spawn_request.get("override_ref"))
    override_reason = _optional_str(spawn_request.get("override_reason"))
    has_override = bool(override_ref and override_reason)
    if (override_ref or override_reason) and not has_override:
        raise ModelSelectionError(
            "override_ref and override_reason are both required for selector override"
        )

    rejected: list[str] = []
    for alias in candidates:
        reason = _rejection_reason(
            alias=alias,
            alias_policy=aliases.get(alias),
            reasoning_effort=requested_effort,
            mandatory_tools=mandatory_tools,
        )
        if reason and explicit_alias and not has_override:
            raise ModelSelectionError(reason)
        if reason and not has_override:
            rejected.append(f"{alias}: {reason}")
            continue

        alias_policy = aliases.get(alias)
        if not isinstance(alias_policy, Mapping):
            raise ModelSelectionError(f"Unknown model alias: {alias}")
        confidence = _confidence(fallback=bool(rejected), override=has_override)
        return SelectionDecision(
            alias=alias,
            model=str(alias_policy["model"]),
            reasoning_effort=requested_effort,
            model_tier=tier_name,
            policy_ref=str(active_policy["policy_ref"]),
            confidence=confidence,
            fallback_reason="; ".join(rejected) if rejected else None,
            source_observed_on=str(active_policy["source_observed_on"]),
            stage_id=_optional_str(spawn_request.get("stage_id")),
            subagent_type=subagent_type,
            used_override=has_override,
            override_ref=override_ref,
            override_reason=override_reason,
        )

    raise ModelSelectionError(
        "No policy alias satisfies the Codex spawn request: " + "; ".join(rejected)
    )


def write_selector_trace(
    decision: SelectionDecision,
    *,
    trace_path: Path | str | None = None,
    policy: Mapping[str, Any] | None = None,
) -> Path:
    """Append a selector decision to the local JSONL trace artifact."""
    if trace_path is None:
        active_policy = policy if policy is not None else load_policy()
        trace_path = active_policy["trace_path"]

    path = Path(trace_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    record = asdict(decision)
    record["spawn_fields"] = decision.to_spawn_kwargs()
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def _default_effort(tier_policy: Mapping[str, Any], subagent_type: str | None) -> str:
    by_type = tier_policy.get("reasoning_effort_by_subagent_type", {})
    if isinstance(by_type, Mapping) and subagent_type in by_type:
        return str(by_type[subagent_type])
    return str(tier_policy["default_reasoning_effort"])


def _rejection_reason(
    *,
    alias: str,
    alias_policy: Any,
    reasoning_effort: str,
    mandatory_tools: Sequence[str],
) -> str | None:
    if not isinstance(alias_policy, Mapping):
        return f"Unknown model alias: {alias}"
    availability_state = alias_policy.get("availability_state")
    if availability_state != "current":
        return f"alias {alias} availability_state is {availability_state}"
    if alias_policy.get("deprecated") is True:
        return f"alias {alias} is deprecated"
    if reasoning_effort not in alias_policy.get("reasoning_efforts", []):
        return f"alias {alias} does not support reasoning_effort {reasoning_effort}"
    supported_tools = set(_string_list(alias_policy.get("supported_tools", [])))
    missing_tools = [tool for tool in mandatory_tools if tool not in supported_tools]
    if missing_tools:
        return f"alias {alias} missing mandatory_tools: {', '.join(missing_tools)}"
    return None


def _confidence(*, fallback: bool, override: bool) -> float:
    if override:
        return 0.35
    if fallback:
        return 0.65
    return 0.95


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ModelSelectionError("Expected a list of strings")
    return [str(item) for item in value]

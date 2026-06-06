#!/usr/bin/env python3
"""Personal Harness OS mode router.

This module translates the lower-level azoth-lite side-effect classifier into
the operator-facing mode ladder from the deployment readiness contract:
guide, assisted, managed, and governed_autonomy. It is advisory and pure by
default; callers decide whether to act on the returned route capsule.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from azoth_lite import AzothLiteRequest, classify_request


HARNESS_PROFILES = ("guide", "assisted", "managed", "governed_autonomy")


@dataclass(frozen=True)
class HarnessRequest:
    """Input to the personal harness router."""

    goal: str
    requested_actions: tuple[str, ...] = ()
    planned_paths: tuple[str, ...] = ()
    trace_required: bool = False
    dirty_worktree: bool = False
    dirty_worktree_summary: str = ""
    success_criteria: tuple[str, ...] = ()
    known_constraints: tuple[str, ...] = ()
    allow_stock_lite: bool = True

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "HarnessRequest":
        """Build a request from JSON/YAML-compatible fixture data."""
        return cls(
            goal=str(payload.get("goal", "")).strip(),
            requested_actions=tuple(_string_list(payload.get("requested_actions", ()))),
            planned_paths=tuple(_string_list(payload.get("planned_paths", ()))),
            trace_required=bool(payload.get("trace_required", False)),
            dirty_worktree=bool(payload.get("dirty_worktree", False)),
            dirty_worktree_summary=str(payload.get("dirty_worktree_summary", "")).strip(),
            success_criteria=tuple(_string_list(payload.get("success_criteria", ()))),
            known_constraints=tuple(_string_list(payload.get("known_constraints", ()))),
            allow_stock_lite=bool(payload.get("allow_stock_lite", True)),
        )

    def to_azoth_lite_request(self) -> AzothLiteRequest:
        """Return the lower-level classifier request."""
        return AzothLiteRequest(
            goal=self.goal,
            requested_actions=self.requested_actions,
            planned_paths=self.planned_paths,
            trace_required=self.trace_required,
            dirty_worktree=self.dirty_worktree,
            dirty_worktree_summary=self.dirty_worktree_summary,
            success_criteria=self.success_criteria,
            known_constraints=self.known_constraints,
            allow_stock_lite=self.allow_stock_lite,
        )


@dataclass(frozen=True)
class RouteCapsule:
    """Compact route state for user-facing harness decisions."""

    profile: str
    side_effect_class: str
    route_state: str
    authority_required: bool
    authority_plane: str
    required_inputs: tuple[str, ...]
    next_safe_action: str
    stop_reason: str = ""

    def to_json_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_inputs"] = list(self.required_inputs)
        return payload


@dataclass(frozen=True)
class HarnessDecision:
    """Advisory personal harness decision."""

    request: HarnessRequest
    profile: str
    side_effect_class: str
    route: RouteCapsule
    operator_promise: str
    explicit_exclusions: tuple[str, ...]
    source_refs: tuple[str, ...]
    azoth_lite_profile: str
    escalation_reasons: tuple[str, ...] = ()

    def to_route_capsule(self) -> dict[str, Any]:
        """Return a deterministic JSON-friendly route capsule."""
        return self.route.to_json_dict()

    def to_context_view(self) -> dict[str, Any]:
        """Return a compact context view for callers that do not need memory joins."""
        return {
            "schema_version": 1,
            "packet_type": "harness_context_view",
            "goal": self.request.goal,
            "harness_profile": self.profile,
            "azoth_lite_profile": self.azoth_lite_profile,
            "side_effect_class": self.side_effect_class,
            "operator_promise": self.operator_promise,
            "route_capsule": self.to_route_capsule(),
            "success_criteria": list(self.request.success_criteria),
            "known_constraints": list(self.request.known_constraints),
            "forbidden_actions": list(self.explicit_exclusions),
            "escalation_triggers": list(self.escalation_reasons),
            "source_refs": list(self.source_refs),
        }


def classify_harness_request(request: HarnessRequest | Mapping[str, Any]) -> HarnessDecision:
    """Classify a request into an operator-facing personal harness mode."""
    active_request = request if isinstance(request, HarnessRequest) else HarnessRequest.from_mapping(request)
    lite_decision = classify_request(active_request.to_azoth_lite_request())
    profile = _profile_for_lite_decision(lite_decision.selected_profile, lite_decision.side_effect_class, lite_decision.escalation_reasons)
    route = _route_for_profile(profile, lite_decision.side_effect_class, lite_decision.escalation_reasons)
    mode = _MODE_CONTRACTS[profile]

    return HarnessDecision(
        request=active_request,
        profile=profile,
        side_effect_class=lite_decision.side_effect_class,
        route=route,
        operator_promise=mode["operator_promise"],
        explicit_exclusions=tuple(mode["explicit_exclusions"]),
        source_refs=(f".azoth/research/t-059-deployment-readiness-mode-matrix.yaml#mode_matrix.{profile}",),
        azoth_lite_profile=lite_decision.selected_profile,
        escalation_reasons=lite_decision.escalation_reasons,
    )


def _profile_for_lite_decision(
    lite_profile: str,
    side_effect_class: str,
    escalation_reasons: Sequence[str],
) -> str:
    if side_effect_class in {"kernel_or_governance", "external_or_destructive"}:
        return "governed_autonomy"
    if "autonomous_continuation_requested" in escalation_reasons:
        return "governed_autonomy"
    if side_effect_class == "governed_state":
        return "managed"
    if lite_profile == "stock-lite":
        return "guide"
    return "assisted"


def _route_for_profile(
    profile: str,
    side_effect_class: str,
    escalation_reasons: Sequence[str],
) -> RouteCapsule:
    mode = _MODE_CONTRACTS[profile]
    route_state = str(mode["route_state"])
    stop_reason = str(mode["stop_reason"])

    if side_effect_class in {"kernel_or_governance", "external_or_destructive"}:
        route_state = "stop"
        stop_reason = "protected or external action requires explicit human authority"

    return RouteCapsule(
        profile=profile,
        side_effect_class=side_effect_class,
        route_state=route_state,
        authority_required=bool(mode["authority_required"]),
        authority_plane=str(mode["authority_plane"]),
        required_inputs=tuple(mode["required_inputs"]),
        next_safe_action=str(mode["next_safe_action"]),
        stop_reason=stop_reason,
    )


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


_MODE_CONTRACTS: dict[str, dict[str, Any]] = {
    "guide": {
        "operator_promise": "Azoth is present as philosophy, trust posture, orientation, and prompts only.",
        "route_state": "answer",
        "authority_required": False,
        "authority_plane": "personal_cockpit",
        "required_inputs": (
            "selected project pointer or current repository",
            "source/profile receipt",
        ),
        "next_safe_action": "read orientation and decide whether to request assisted mode",
        "stop_reason": "",
        "explicit_exclusions": (
            "do not mutate project repos",
            "do not claim agents, planning state, or autonomy are installed",
            "do not open cross-repo writes",
        ),
    },
    "assisted": {
        "operator_promise": (
            "Azoth can help with instructions, skills, wrappers, and selected agents, "
            "but does not own project-management state."
        ),
        "route_state": "assist",
        "authority_required": False,
        "authority_plane": "root_azoth",
        "required_inputs": (
            "guide-mode receipt",
            "installed skill/agent/command inventory",
            "explicit operator acceptance of assisted mode",
        ),
        "next_safe_action": "run read-only assisted checks or request managed-mode hydration",
        "stop_reason": "",
        "explicit_exclusions": (
            "do not hydrate roadmap, backlog, or planning-bank state",
            "do not run no-human-gate autonomy",
            "do not mutate a project repo without local approval",
        ),
    },
    "managed": {
        "operator_promise": "Azoth provides a project-management substrate after explicit local approval.",
        "route_state": "authority_required",
        "authority_required": True,
        "authority_plane": "project_local",
        "required_inputs": (
            "assisted-mode readiness",
            "human approval for project-management state",
            "project-local target path and receipt owner",
        ),
        "next_safe_action": "hydrate or repair project-local planning state under a fresh gate",
        "stop_reason": "fresh managed-mode authority required",
        "explicit_exclusions": (
            "do not run branch-local no-human-gate autonomy",
            "do not hydrate hidden state",
            "do not let cockpit drive writes without project-local approval",
        ),
    },
    "governed_autonomy": {
        "operator_promise": (
            "Azoth may run campaign-bounded supervised autonomy only after managed-mode "
            "receipts, ledger proof, and explicit stop conditions exist."
        ),
        "route_state": "authority_required",
        "authority_required": True,
        "authority_plane": "root_azoth",
        "required_inputs": (
            "managed-mode readiness",
            "explicit autonomy budget",
            "write-claim policy",
            "stop/approval conditions",
        ),
        "next_safe_action": "open a bounded governed-autonomy campaign only with fresh authority",
        "stop_reason": "fresh governed-autonomy authority required",
        "explicit_exclusions": (
            "do not leak root self-development authority into consumer projects",
            "do not run open-ended loops",
            "do not continue stale campaign state",
        ),
    },
}

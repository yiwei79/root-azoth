#!/usr/bin/env python3
"""Advisory azoth-lite profile classifier.

This helper is used by the Codex control-plane router as a default-posture
advisory classifier. It does not mutate runtime state on its own.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SIDE_EFFECT_CLASSES = (
    "read_only",
    "local_edit",
    "governed_state",
    "kernel_or_governance",
    "external_or_destructive",
)

READ_ONLY_ACTIONS = {
    "inspect",
    "read",
    "search",
    "status",
    "summarize",
}
FOCUSED_VERIFICATION_ACTIONS = {
    "focused_test",
    "focused_verification",
    "test",
    "verify",
}
LOCAL_EDIT_ACTIONS = {
    "add",
    "create",
    "edit",
    "fix",
    "implement",
    "migrate",
    "patch",
    "refactor",
    "update",
    "wire",
    "write",
}
EXTERNAL_OR_DESTRUCTIVE_ACTIONS = {
    "add_dependency",
    "clean",
    "closeout",
    "commit",
    "delete",
    "deploy",
    "external_service",
    "final_delivery",
    "finalize",
    "install_dependency",
    "merge",
    "package",
    "publish",
    "push",
    "release",
    "reset",
    "send_message",
    "stage",
}

GOVERNED_PATH_PREFIXES = (
    ".azoth/",
    ".agents/rules/",
    ".agents/skills/",
    ".agents/workflows/",
    ".claude/agents/",
    ".claude/commands/",
    ".claude/skills/",
    ".codex/agents/",
    ".gemini/commands/",
    ".gemini/agents/",
    ".github/agents/",
    ".github/prompts/",
    ".github/skills/",
    ".opencode/agents/",
    ".opencode/commands/",
    ".opencode/skills/",
    "agents/",
    "commands/",
    "pipelines/",
    "skills/",
)
KERNEL_OR_GOVERNANCE_PATH_PREFIXES = (
    ".claude/hooks/",
    ".cursor/rules/",
    ".codex/hooks.json",
    ".codex/config.toml",
    ".codex/rules/",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "kernel/",
)
GOVERNED_GOAL_TERMS = (
    "backlog",
    "handoff",
    "initiative",
    "memory",
    "pipeline gate",
    "pipeline-gate",
    "roadmap",
    "run ledger",
    "run-ledger",
    "scope gate",
    "scope-gate",
)
KERNEL_OR_GOVERNANCE_GOAL_TERMS = (
    "governance",
    "hook",
    "permission",
    "trust contract",
)
FINALITY_GOAL_TERMS = (
    "clean final delivery",
    "close out",
    "closeout",
    "commit",
    "deploy",
    "final delivery",
    "finalize",
    "merge",
    "package",
    "publish",
    "release",
)
MUTATION_GOAL_TERMS = (
    "append",
    "change",
    "create",
    "edit",
    "fix",
    "implement",
    "mutate",
    "refactor",
    "update",
    "write",
)


@dataclass(frozen=True)
class AzothLiteRequest:
    """Input to the advisory classifier."""

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
    def from_mapping(cls, payload: Mapping[str, Any]) -> "AzothLiteRequest":
        """Build a request from JSON-compatible fixture data."""
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


@dataclass(frozen=True)
class AzothLiteDecision:
    """Advisory profile decision plus compact context-view fields."""

    request: AzothLiteRequest
    side_effect_class: str
    selected_profile: str
    stop_state: str
    escalate: bool
    escalation_reasons: tuple[str, ...] = ()
    handoff_packet: dict[str, Any] | None = None

    def to_context_view(self) -> dict[str, Any]:
        """Return the compact manual context view from the Phase 1 trial pack."""
        return {
            "goal": self.request.goal,
            "success_criteria": list(self.request.success_criteria),
            "known_constraints": list(self.request.known_constraints),
            "dirty_worktree_summary": self.request.dirty_worktree_summary,
            "side_effect_class": self.side_effect_class,
            "allowed_actions": _allowed_actions(self.side_effect_class),
            "forbidden_actions": _forbidden_actions(),
            "escalation_triggers": list(self.escalation_reasons),
            "selected_profile": self.selected_profile,
            "stop_rule": _stop_rule(self),
            "trace_required": self.request.trace_required,
        }

    def to_json_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-friendly decision payload."""
        payload = asdict(self)
        payload["context_view"] = self.to_context_view()
        return payload


def classify_request(request: AzothLiteRequest | Mapping[str, Any]) -> AzothLiteDecision:
    """Classify a task into a profile suggestion without changing runtime behavior."""
    active_request = (
        request if isinstance(request, AzothLiteRequest) else AzothLiteRequest.from_mapping(request)
    )
    side_effect_class, class_reasons = _classify_side_effect(active_request)
    escalation_reasons = list(class_reasons)

    if active_request.dirty_worktree and _finality_requested(active_request):
        _append_once(escalation_reasons, "dirty_state_blocks_finality")

    escalate = side_effect_class in {
        "governed_state",
        "kernel_or_governance",
        "external_or_destructive",
    }
    selected_profile = _selected_profile(active_request, side_effect_class, escalate)
    stop_state = "escalate" if escalate else "done"
    reasons = tuple(escalation_reasons)

    return AzothLiteDecision(
        request=active_request,
        side_effect_class=side_effect_class,
        selected_profile=selected_profile,
        stop_state=stop_state,
        escalate=escalate,
        escalation_reasons=reasons,
        handoff_packet=_handoff_packet(active_request, side_effect_class, reasons)
        if escalate
        else None,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Print a JSON decision for an explicit fixture/request file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_json", type=Path, help="Path to an azoth-lite request JSON file")
    args = parser.parse_args(argv)

    request = AzothLiteRequest.from_mapping(
        json.loads(args.request_json.read_text(encoding="utf-8"))
    )
    decision = classify_request(request)
    print(json.dumps(decision.to_json_dict(), indent=2, sort_keys=True))
    return 0


def _classify_side_effect(request: AzothLiteRequest) -> tuple[str, tuple[str, ...]]:
    actions = {_normalize_token(action) for action in request.requested_actions}
    paths = tuple(_normalize_path(path) for path in request.planned_paths)
    goal = request.goal.lower()
    mutation_requested = _mutation_requested(request)
    reasons: list[str] = []

    if (
        actions & EXTERNAL_OR_DESTRUCTIVE_ACTIONS
        or _starts_with_any(goal, FINALITY_GOAL_TERMS)
        or (mutation_requested and _contains_any(goal, FINALITY_GOAL_TERMS))
    ):
        reasons.append("external_or_destructive_action")
        if _finality_requested(request):
            reasons.append("finality_or_packaging_requested")
        return "external_or_destructive", tuple(reasons)

    if mutation_requested and (
        any(_matches_prefix(path, KERNEL_OR_GOVERNANCE_PATH_PREFIXES) for path in paths)
        or _contains_any(goal, KERNEL_OR_GOVERNANCE_GOAL_TERMS)
    ):
        return "kernel_or_governance", ("kernel_or_governance_change",)

    if mutation_requested and (
        any(_matches_prefix(path, GOVERNED_PATH_PREFIXES) for path in paths)
        or _contains_any(goal, GOVERNED_GOAL_TERMS)
    ):
        return "governed_state", ("governed_state_change",)

    if mutation_requested:
        return "local_edit", ()

    return "read_only", ()


def _selected_profile(
    request: AzothLiteRequest,
    side_effect_class: str,
    escalate: bool,
) -> str:
    if escalate:
        return "azoth-full"
    if side_effect_class == "read_only" and _can_use_stock_lite(request):
        return "stock-lite"
    return "azoth-lite"


def _can_use_stock_lite(request: AzothLiteRequest) -> bool:
    actions = {_normalize_token(action) for action in request.requested_actions}
    if not request.allow_stock_lite or request.trace_required:
        return False
    if actions & FOCUSED_VERIFICATION_ACTIONS:
        return False
    return actions <= READ_ONLY_ACTIONS or not actions


def _finality_requested(request: AzothLiteRequest) -> bool:
    actions = {_normalize_token(action) for action in request.requested_actions}
    return bool(actions & EXTERNAL_OR_DESTRUCTIVE_ACTIONS) or _contains_any(
        request.goal.lower(), FINALITY_GOAL_TERMS
    )


def _mutation_requested(request: AzothLiteRequest) -> bool:
    actions = {_normalize_token(action) for action in request.requested_actions}
    return bool(actions & LOCAL_EDIT_ACTIONS) or _contains_any(
        request.goal.lower(), MUTATION_GOAL_TERMS
    )


def _handoff_packet(
    request: AzothLiteRequest,
    side_effect_class: str,
    reasons: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "goal": request.goal,
        "side_effect_class": side_effect_class,
        "escalation_reasons": list(reasons),
        "dirty_worktree_summary": request.dirty_worktree_summary,
        "planned_paths": list(request.planned_paths),
        "verification_already_run": [],
        "recommended_route": "azoth-full",
        "stop_rule": "stop before mutation",
    }


def _allowed_actions(side_effect_class: str) -> list[str]:
    if side_effect_class == "read_only":
        return [
            "read files",
            "inspect status",
            "run focused verification",
        ]
    if side_effect_class == "local_edit":
        return [
            "edit ordinary source, tests, docs, or research artifacts outside governed state",
            "run focused verification",
        ]
    return [
        "prepare an advisory handoff packet",
    ]


def _forbidden_actions() -> list[str]:
    return [
        "mutate .azoth state",
        "change kernel/governance",
        "package, release, deploy, merge, close out, or declare final delivery",
    ]


def _stop_rule(decision: AzothLiteDecision) -> str:
    if decision.escalate:
        return "stop before mutation"
    if decision.side_effect_class == "read_only":
        return "answer or report verification, then stop"
    return "complete the local task, then stop"


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _matches_prefix(path: str, prefixes: Sequence[str]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def _contains_any(text: str, terms: Sequence[str]) -> bool:
    return any(term in text for term in terms)


def _starts_with_any(text: str, terms: Sequence[str]) -> bool:
    stripped = text.strip()
    return any(stripped.startswith(f"{term} ") or stripped.startswith(f"{term}:") for term in terms)


def _append_once(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


if __name__ == "__main__":
    raise SystemExit(main())

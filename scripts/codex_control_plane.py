#!/usr/bin/env python3
"""Codex calm-flow prompt normalization for Azoth compatibility routes."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from session_gate import (
    classify_goal_intent,
    ensure_exploratory_session,
    matching_exploratory_session,
)
from session_continuity import resolve_transition

PIPELINE_COMMANDS = {"auto", "autonomous-auto", "dynamic-full-auto", "deliver", "deliver-full"}
LEADING_COMMAND_RE = re.compile(r"^\s*/([a-z][a-z0-9-]*)\b(.*)$", re.DOTALL)
SKILL_COMMAND_RE = re.compile(r"^\s*\$azoth-([a-z][a-z0-9-]*)\b(.*)$", re.DOTALL)
NONLEADING_COMMAND_MENTION_RE = re.compile(r"(?<!\S)/([a-z][a-z0-9-]*)\b")
PIPELINE_OVERRIDE_RE = re.compile(
    r"^\s*pipeline_command=(autonomous-auto|dynamic-full-auto|deliver-full|deliver|auto)\b(.*)$",
    re.DOTALL,
)

_ACTIONABLE_PREFIXES = (
    "continue",
    "resume",
    "keep going",
    "let's continue",
    "lets continue",
    "start a new goal",
    "start new goal",
    "new goal",
    "start ",
    "work on",
    "implement",
    "fix",
    "add",
    "update",
    "refactor",
    "change",
    "patch",
    "wire",
    "migrate",
    "edit",
    "explore",
    "research",
    "brainstorm",
    "plan",
    "explain",
    "diagnose",
    "compare",
    "think through",
    "let's think through",
    "lets think through",
    "walk through",
)
_CONTINUE_PREFIXES = ("continue", "resume", "keep going", "let's continue", "lets continue")
_NEW_GOAL_PREFIXES = ("start a new goal", "start new goal", "new goal", "start ")


@dataclass(frozen=True)
class ParsedPrompt:
    raw_prompt: str
    source_command: str = ""
    raw_arguments: str = ""
    canonical_input: str = ""
    effective_route_name: str = ""
    effective_pipeline_command: str = ""
    prompt_goal: str = ""
    requested_session_id: str = ""
    is_freeform: bool = False


@dataclass(frozen=True)
class PromptDirective:
    additional_context: str
    updated_input: str = ""

    def to_hook_payload(self) -> dict[str, Any]:
        hook_output: dict[str, Any] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": self.additional_context,
        }
        if self.updated_input:
            hook_output["updatedInput"] = self.updated_input
        return {"hookSpecificOutput": hook_output}


def _command_contract(root: Path, name: str) -> Path | None:
    command_path = root / "commands" / name / "command.yaml"
    if command_path.is_file():
        return command_path
    legacy_path = root / ".claude" / "commands" / f"{name}.md"
    if legacy_path.is_file():
        return legacy_path
    return None


def _read_payload(raw: str) -> str:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    prompt = payload.get("prompt")
    return prompt if isinstance(prompt, str) else ""


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload))


def _looks_like_actionable_freeform(prompt: str) -> bool:
    stripped = prompt.strip().lower()
    return any(stripped.startswith(prefix) for prefix in _ACTIONABLE_PREFIXES)


def _mentions_command_token_only(prompt: str) -> bool:
    stripped = prompt.strip()
    return bool(stripped) and not stripped.startswith("/") and bool(
        NONLEADING_COMMAND_MENTION_RE.search(stripped)
    )


def _extract_session_id(arguments: str) -> tuple[str, str]:
    stripped = arguments.strip()
    if not stripped:
        return "", ""
    match = re.match(r"^session_id=([A-Za-z0-9._:-]+)\b(.*)$", stripped, re.DOTALL)
    if not match:
        return "", stripped
    return match.group(1), match.group(2).strip()


def _start_argument_parts(arguments: str) -> tuple[str, str, str, str]:
    stripped = arguments.strip()
    if not stripped:
        return "", "", "", ""
    override_match = PIPELINE_OVERRIDE_RE.match(stripped)
    if override_match:
        pipeline = override_match.group(1)
        session_id, goal = _extract_session_id(override_match.group(2))
        return pipeline, "", goal, session_id
    token, _, remainder = stripped.partition(" ")
    if token in {"next", "resume", "closeout"}:
        session_id, goal = _extract_session_id(remainder)
        return "", token, goal, session_id
    session_id, goal = _extract_session_id(stripped)
    return "", "", goal, session_id


def _canonical_start_input(
    *,
    pipeline_command: str = "",
    keyword: str = "",
    goal: str = "",
    session_id: str = "",
) -> str:
    if keyword == "closeout":
        return "$azoth-session-closeout"
    parts = ["$azoth-start"]
    if pipeline_command:
        parts.append(f"pipeline_command={pipeline_command}")
    elif keyword:
        parts.append(keyword)
    if session_id:
        parts.append(f"session_id={session_id}")
    if goal:
        parts.append(goal)
    return " ".join(parts).strip()


def _skill_path(root: Path, name: str) -> Path:
    return root / ".agents" / "skills" / f"azoth-{name}" / "SKILL.md"


def _parsed_command_prompt(
    root: Path, prompt: str, *, name: str, arguments: str
) -> ParsedPrompt | None:
    if name in PIPELINE_COMMANDS:
        goal = arguments.strip()
        return ParsedPrompt(
            raw_prompt=prompt,
            source_command=name,
            raw_arguments=arguments.strip(),
            canonical_input=_canonical_start_input(pipeline_command=name, goal=goal),
            effective_route_name="start",
            effective_pipeline_command=name,
            prompt_goal=goal,
        )
    if name == "next":
        return ParsedPrompt(
            raw_prompt=prompt,
            source_command=name,
            raw_arguments=arguments.strip(),
            canonical_input=_canonical_start_input(keyword="next", goal=arguments.strip()),
            effective_route_name="start",
            prompt_goal=arguments.strip(),
        )
    if name == "session-closeout":
        return ParsedPrompt(
            raw_prompt=prompt,
            source_command=name,
            raw_arguments=arguments.strip(),
            canonical_input="$azoth-session-closeout",
            effective_route_name="session-closeout",
        )
    if name == "start":
        pipeline_command, keyword, goal, session_id = _start_argument_parts(arguments)
        effective_route_name = "session-closeout" if keyword == "closeout" else "start"
        return ParsedPrompt(
            raw_prompt=prompt,
            source_command=name,
            raw_arguments=arguments.strip(),
            canonical_input=_canonical_start_input(
                pipeline_command=pipeline_command,
                keyword=keyword,
                goal=goal,
                session_id=session_id,
            ),
            effective_route_name=effective_route_name,
            effective_pipeline_command=pipeline_command,
            prompt_goal=goal,
            requested_session_id=session_id,
        )
    if _command_contract(root, name) is None:
        return None
    return ParsedPrompt(
        raw_prompt=prompt,
        source_command=name,
        raw_arguments=arguments.strip(),
        canonical_input=f"$azoth-{name}" + (f" {arguments.strip()}" if arguments.strip() else ""),
        effective_route_name=name,
        prompt_goal=arguments.strip(),
    )


def parse_prompt(root: Path, prompt: str) -> ParsedPrompt | None:
    stripped = prompt.strip()
    if not stripped:
        return None

    match = LEADING_COMMAND_RE.match(stripped)
    if match:
        return _parsed_command_prompt(root, prompt, name=match.group(1), arguments=match.group(2))

    match = SKILL_COMMAND_RE.match(stripped)
    if match:
        return _parsed_command_prompt(root, prompt, name=match.group(1), arguments=match.group(2))

    if _mentions_command_token_only(prompt):
        return None

    if not _looks_like_actionable_freeform(prompt):
        return None

    return ParsedPrompt(
        raw_prompt=prompt,
        canonical_input="",
        prompt_goal=prompt.strip(),
        is_freeform=True,
    )


def _freeform_transition_inputs(prompt: str) -> tuple[str, str]:
    stripped = prompt.strip()
    lowered = stripped.lower()
    if any(lowered.startswith(prefix) for prefix in _CONTINUE_PREFIXES):
        return "resume", ""
    if any(lowered.startswith(prefix) for prefix in _NEW_GOAL_PREFIXES):
        normalized = re.sub(
            r"^\s*(start a new goal|start new goal|new goal)\s*:?\s*", "", stripped, flags=re.I
        )
        return "", normalized or stripped
    return "", stripped


def _transition_guidance(
    root: Path,
    parsed: ParsedPrompt,
) -> str:
    if parsed.is_freeform:
        command_name, prompt_goal = _freeform_transition_inputs(parsed.raw_prompt)
        decision = resolve_transition(
            root,
            command_name=command_name,
            prompt_goal=prompt_goal,
        )
    else:
        decision = resolve_transition(
            root,
            command_name=parsed.source_command,
            command_args=parsed.prompt_goal or parsed.raw_arguments,
            prompt_goal=parsed.prompt_goal,
            requested_session_id=parsed.requested_session_id or None,
        )

    if not decision.active_session_id or decision.action == "new":
        return ""
    if decision.action == "resume":
        return (
            f"Active scope `{decision.active_session_id}` matches this request. "
            "Treat it as a resume/continue decision, not as a brand-new scope."
        )
    if decision.action == "extend":
        return (
            f"Active scope `{decision.active_session_id}` is still the right session but TTL is low. "
            "Offer extend/checkpoint/abort rather than reopening scope from scratch."
        )
    if decision.action == "replace":
        return (
            f"Active scope `{decision.active_session_id}` is live for "
            f"`{decision.active_goal or 'the current goal'}`. "
            "Treat this request as a replace decision: park or close the current scope before opening a new one."
        )
    if decision.action == "conflict":
        return (
            f"A different live scope `{decision.active_session_id}` already exists. "
            "Do not silently retarget it."
        )
    return ""


def _governed_write_reminder() -> str:
    return (
        "Continuity guidance classifies the session transition only; it does not authorize writes. "
        "Governed edits still require a valid scope-gate and, when applicable, pipeline-gate."
    )


def staged_delegation_available(root: Path) -> bool:
    agents_dir = root / ".codex" / "agents"
    required = ("orchestrator.toml", "builder.toml", "reviewer.toml")
    return agents_dir.is_dir() and all((agents_dir / name).is_file() for name in required)


def _pipeline_guidance(root: Path, parsed: ParsedPrompt) -> list[str]:
    pipeline = parsed.effective_pipeline_command
    guidance = [
        f"Codex compatibility route detected for `/{parsed.source_command}`.",
        f"Normalize this request to `{parsed.canonical_input}` so the effective `pipeline_command={pipeline}` stays durable.",
        "Use `$azoth-start` as the canonical Codex daily entry surface; raw slash tokens and compatibility wrappers are fallback surfaces.",
        f"Read `{(root / 'commands' / 'start' / 'command.yaml').relative_to(root).as_posix()}` and `{(root / 'commands' / 'start' / 'body.md').relative_to(root).as_posix()}` as the Codex control-plane contract.",
        f"Then follow `{(root / 'commands' / pipeline / 'command.yaml').relative_to(root).as_posix()}` for the pipeline contract.",
    ]

    skill_path = _skill_path(root, "start")
    if skill_path.is_file():
        guidance.append(
            f"The explicit Codex skill surface is `{skill_path.relative_to(root).as_posix()}`."
        )

    guidance.extend(
        [
            "Keep the orchestrator in the main thread.",
            "This is a request for staged pipeline execution and staged delegation, not permission to improvise the work inline.",
            "Record every subagent spawn and typed summary in `.azoth/run-ledger.local.yaml`; before protected downstream stages, run `scripts/run_ledger.py require-stage-evidence` and fail closed on missing, mismatched, blocked, or needs-input evidence.",
        ]
    )
    if pipeline in {"auto", "autonomous-auto", "dynamic-full-auto"}:
        guidance.append(
            "Within an approved `/auto`, `dynamic-full-auto`, or `autonomous-auto` run, the orchestrator may keep a bounded slice inline only when it explicitly justifies why inline is more beneficial than spawning and no required fresh-context, review-independence, or human gate is being bypassed."
        )
    if pipeline == "autonomous-auto":
        guidance.extend(
            [
                "Autonomous Auto Mode is a standalone adaptive pipeline, not a submode of `dynamic-full-auto`.",
                "Use `alignment_mode: async`; classify later operator messages as alignment packets and apply them at the next safe checkpoint unless they are `async_stop`.",
                "Persist `approval_basis` beside any branch-local autonomous approval fields.",
            ]
        )
    if pipeline == "deliver-full":
        guidance.extend(
            [
                "For governed `/deliver-full`, the next legal stage is spawned `deliver_full_s2_architect`.",
                "For governed `/deliver-full`, inline architecture prose does not satisfy Stage 2.",
                "For governed `/deliver-full`, a Declaration, gate write, or status card does not count as Stage 2 execution.",
            ]
        )
    if not staged_delegation_available(root):
        guidance.append(
            "Staged delegation is unavailable in this runtime. STOP after the Declaration and ask the human whether to authorize delegation, adjust the pipeline, or switch platforms."
        )
    else:
        guidance.append(
            "If staged delegation becomes unavailable at runtime, STOP after the Declaration and ask the human before continuing."
        )
    guidance.append(
        "For write-enabled or governed stages, follow the gate procedure before editing."
    )
    exploratory_gate = matching_exploratory_session(root, parsed.prompt_goal)
    if (
        exploratory_gate
        and (
            not parsed.prompt_goal
            or str(exploratory_gate.get("goal") or "").strip() == parsed.prompt_goal.strip()
        )
    ):
        guidance.append(
            "A matching exploratory session is already active. Reuse its `session_id` when "
            "the delivery flow writes `.azoth/scope-gate.json` so exploration → delivery stays one session."
        )
    return guidance


def _closeout_guidance(root: Path, parsed: ParsedPrompt) -> list[str]:
    guidance = [
        f"Codex closeout route detected for `/{parsed.source_command}`.",
        "Keep closeout explicit: use `$azoth-session-closeout` or `$azoth-start closeout` as the canonical Codex path.",
        "During closeout, treat W1/W2/W4 under `.azoth/` as authoritative.",
        "Refresh `.azoth/session-state.md` as the repo-local W2 handoff artifact.",
        "Attempt W3 Claude memory mirroring, and log `W3 deferred` if it is blocked.",
        "Closeout output must report the W3 disposition and the next operator action.",
    ]
    return guidance


def _start_guidance(root: Path, parsed: ParsedPrompt) -> list[str]:
    guidance = [
        "Codex start route detected.",
        "Use `$azoth-start` as the canonical daily entry surface in Codex.",
        f"Read `{(root / 'commands' / 'start' / 'command.yaml').relative_to(root).as_posix()}` and `{(root / 'commands' / 'start' / 'body.md').relative_to(root).as_posix()}` before routing.",
        "Honor the existing `.azoth/` scope, pipeline, and continuity state before proposing new work.",
    ]
    if parsed.effective_pipeline_command:
        guidance.extend(_pipeline_guidance(root, parsed)[1:])
    return guidance


def _command_guidance(root: Path, parsed: ParsedPrompt) -> list[str]:
    command_contract = _command_contract(root, parsed.source_command)
    if command_contract is None:
        return []
    guidance = [
        f"Azoth compatibility workflow detected: `/{parsed.source_command}`.",
        f"Read `{command_contract.relative_to(root).as_posix()}` and follow that repository contract instead of improvising.",
    ]
    skill_path = _skill_path(root, parsed.source_command)
    if skill_path.is_file():
        guidance.append(
            f"The generated Codex wrapper skill is `{skill_path.relative_to(root).as_posix()}`."
        )
    return guidance


def directive_for_prompt(root: Path, prompt: str) -> PromptDirective | None:
    parsed = parse_prompt(root, prompt)
    if parsed is None:
        return None

    if parsed.is_freeform:
        command_name, prompt_goal = _freeform_transition_inputs(parsed.raw_prompt)
        decision = resolve_transition(
            root,
            command_name=command_name,
            prompt_goal=prompt_goal,
        )
        transition = _transition_guidance(root, parsed)
        if decision.action in {"replace", "conflict", "extend"}:
            guidance = [transition, _governed_write_reminder()] if transition else []
            return PromptDirective(additional_context=" ".join(guidance))
        if command_name == "resume":
            guidance = [transition] if transition else []
            if guidance:
                return PromptDirective(additional_context=" ".join(guidance))
            return None

        goal = prompt_goal or parsed.raw_prompt.strip()
        if not goal:
            return None

        intent = classify_goal_intent(goal)
        if intent == "exploratory":
            gate = ensure_exploratory_session(root, goal=goal)
            guidance = [
                f"Exploratory intent detected for `{goal}`.",
                f"Opened `.azoth/session-gate.json` for session `{gate['session_id']}`.",
                "Treat this as a real no-scope session: memory capture and light closeout are allowed, "
                "but ordinary repo edits must stop and escalate into `/auto` first.",
                "Normalize this request through `$azoth-start` so the Codex control plane stays start-centered.",
            ]
            if transition:
                guidance.append(transition)
            return PromptDirective(
                additional_context=" ".join(guidance),
                updated_input=_canonical_start_input(goal=goal),
            )

        guidance = [
            f"Delivery intent detected for `{goal}`.",
            "Normalize this request through `$azoth-start pipeline_command=auto ...` so the default delivery path remains explicit.",
        ]
        exploratory_gate = matching_exploratory_session(root, goal)
        session_id = ""
        if exploratory_gate:
            session_id = str(exploratory_gate.get("session_id") or "").strip()
            guidance.append(
                "A matching exploratory session is already active. Carry its `session_id` forward "
                "in the routed input and write `.azoth/scope-gate.json` with that same session."
            )
        if transition:
            guidance.append(transition)
            guidance.append(_governed_write_reminder())
        return PromptDirective(
            additional_context=" ".join(guidance),
            updated_input=_canonical_start_input(
                pipeline_command="auto",
                goal=goal,
                session_id=session_id,
            ),
        )

    if parsed.effective_route_name == "session-closeout":
        guidance = _closeout_guidance(root, parsed)
    elif parsed.effective_pipeline_command:
        guidance = _pipeline_guidance(root, parsed)
    elif parsed.effective_route_name == "start":
        guidance = _start_guidance(root, parsed)
    else:
        guidance = _command_guidance(root, parsed)

    transition = _transition_guidance(root, parsed)
    if transition:
        guidance.append(transition)
        guidance.append(_governed_write_reminder())

    return PromptDirective(
        additional_context=" ".join(guidance),
        updated_input=parsed.canonical_input,
    )


def main() -> int:
    prompt = _read_payload(sys.stdin.read())
    if not prompt.strip():
        return 0

    root = Path(__file__).resolve().parent.parent
    directive = directive_for_prompt(root, prompt)
    if directive is None:
        return 0
    _emit_json(directive.to_hook_payload())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

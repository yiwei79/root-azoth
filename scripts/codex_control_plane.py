#!/usr/bin/env python3
"""Codex prompt-entry control plane for Azoth calm flow."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    import tomli as tomllib

from session_continuity import _route_start_selection, resolve_transition

ROOT = Path(__file__).resolve().parent.parent
PIPELINE_COMMANDS = {"auto", "dynamic-full-auto", "deliver", "deliver-full"}
START_ROUTED_COMMANDS = PIPELINE_COMMANDS | {"next"}
COMMAND_DIR = Path(".claude/commands")
SKILLS_DIR = Path(".agents/skills")
LEADING_COMMAND_RE = re.compile(r"^\s*/([a-z][a-z0-9-]*)\b(.*)$", re.DOTALL)
LEADING_SKILL_RE = re.compile(r"^\s*\$azoth-([a-z][a-z0-9-]*)\b(.*)$", re.DOTALL)
PIPELINE_OVERRIDE_RE = re.compile(
    r"^\s*pipeline_command\s*(?:=|:)\s*"
    r"(auto|dynamic-full-auto|deliver|deliver-full)\b(?:\s+(.*))?$",
    re.DOTALL,
)


@dataclass(frozen=True)
class PromptDirective:
    """Structured UserPromptSubmit result."""

    additional_context: str = ""
    updated_input: str = ""
    decision: str = ""

    def as_hook_output(self) -> dict[str, object]:
        hook_specific: dict[str, object] = {"hookEventName": "UserPromptSubmit"}
        if self.additional_context:
            hook_specific["additionalContext"] = self.additional_context
        if self.updated_input:
            hook_specific["updatedInput"] = self.updated_input
        if self.decision:
            hook_specific["decision"] = self.decision
        return {"hookSpecificOutput": hook_specific}


@dataclass(frozen=True)
class ParsedPrompt:
    """Normalized leading Azoth command prompt."""

    source: str
    name: str
    args: str
    command_path: Path
    skill_path: Path

    @property
    def canonical_name(self) -> str:
        if self.name == "start" or self.name in START_ROUTED_COMMANDS:
            return "start"
        return self.name

    @property
    def explicit_pipeline_command(self) -> str | None:
        if self.name in PIPELINE_COMMANDS:
            return self.name
        if self.name == "start":
            pipeline_command, _ = _split_pipeline_override(self.args)
            return pipeline_command
        return None

    @property
    def start_selection(self) -> str:
        if self.name == "next":
            return "next"
        if self.name in PIPELINE_COMMANDS:
            return self.args or "resume"
        if self.name == "start":
            pipeline_command, selection = _split_pipeline_override(self.args)
            if pipeline_command and not selection:
                return "resume"
            return selection
        return self.args

    @property
    def routed_start_selection(self) -> tuple[str, str, str | None]:
        return _route_start_selection(self.start_selection)

    @property
    def effective_route_name(self) -> str:
        if self.name in PIPELINE_COMMANDS:
            return self.name
        if self.name == "start":
            routed_name, _, _ = self.routed_start_selection
            if self.explicit_pipeline_command and routed_name in PIPELINE_COMMANDS | {"resume"}:
                return self.explicit_pipeline_command
            return routed_name
        return self.name

    @property
    def effective_pipeline_command(self) -> str | None:
        if self.name in PIPELINE_COMMANDS:
            return self.name
        if self.name != "start":
            return None
        routed_name, _, _ = self.routed_start_selection
        if routed_name in PIPELINE_COMMANDS:
            return self.explicit_pipeline_command or routed_name
        if routed_name == "resume":
            return self.explicit_pipeline_command
        return None

    @property
    def transition_command_args(self) -> str:
        if self.name == "start":
            return self.start_selection
        return self.args

    @property
    def canonical_args(self) -> str:
        if self.name == "next":
            return "next"
        if self.name in PIPELINE_COMMANDS:
            return _format_start_args(self.start_selection, pipeline_command=self.name)
        if self.name == "start":
            return _format_start_args(
                self.start_selection,
                pipeline_command=self.explicit_pipeline_command,
            )
        return self.args

    @property
    def canonical_input(self) -> str:
        token = canonical_skill_token(self.canonical_name)
        return f"{token} {self.canonical_args}".strip()


def canonical_skill_name(command_name: str) -> str:
    return f"azoth-{command_name}"


def canonical_skill_token(command_name: str) -> str:
    return f"${canonical_skill_name(command_name)}"


def command_path(root: Path, command_name: str) -> Path:
    return root / COMMAND_DIR / f"{command_name}.md"


def skill_path(root: Path, command_name: str) -> Path:
    return root / SKILLS_DIR / canonical_skill_name(command_name) / "SKILL.md"


def _split_pipeline_override(args: str) -> tuple[str | None, str]:
    stripped = args.strip()
    match = PIPELINE_OVERRIDE_RE.match(stripped)
    if match is None:
        return None, stripped
    return match.group(1), (match.group(2) or "").strip()


def _format_start_args(selection: str, *, pipeline_command: str | None = None) -> str:
    normalized_selection = selection.strip()
    if not pipeline_command:
        return normalized_selection
    if not normalized_selection:
        return f"pipeline_command={pipeline_command}"
    return f"pipeline_command={pipeline_command} {normalized_selection}"


def parse_prompt(root: Path, prompt: str) -> ParsedPrompt | None:
    for source, pattern in (("slash", LEADING_COMMAND_RE), ("skill", LEADING_SKILL_RE)):
        match = pattern.match(prompt)
        if match is None:
            continue
        name = match.group(1)
        cmd_path = command_path(root, name)
        canonical_name = "start" if name == "start" or name in START_ROUTED_COMMANDS else name
        skl_path = skill_path(root, canonical_name)
        if not cmd_path.is_file() and not skl_path.is_file():
            return None
        return ParsedPrompt(
            source=source,
            name=name,
            args=match.group(2).strip(),
            command_path=cmd_path,
            skill_path=skl_path,
        )
    return None


def _looks_like_actionable_freeform(prompt: str) -> bool:
    stripped = prompt.strip().lower()
    prefixes = (
        "continue",
        "resume",
        "keep going",
        "let's continue",
        "start",
        "begin",
        "new goal",
        "work on",
        "implement",
        "fix",
        "add",
        "update",
        "refactor",
        "change",
    )
    return stripped.startswith(prefixes)


def _freeform_transition_inputs(prompt: str) -> tuple[str, str]:
    stripped = prompt.strip().lower()
    if stripped.startswith(("continue", "resume", "keep going", "let's continue")):
        return "resume", ""
    return "", ""


def _transition_guidance(
    root: Path,
    prompt: str,
    *,
    command_name: str = "",
    command_args: str = "",
) -> str:
    decision = resolve_transition(
        root,
        command_name=command_name,
        command_args=command_args,
        prompt_goal="" if command_name else prompt,
    )
    if not decision.active_session_id or decision.action in {"new", "noop"}:
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


def _command_context(root: Path, parsed: ParsedPrompt) -> list[str]:
    context: list[str] = []
    effective_pipeline_command = parsed.effective_pipeline_command
    if parsed.source == "slash":
        context.append(
            f"Normalized literal `/{parsed.name}` to `{parsed.canonical_input}` so Codex uses the canonical calm-flow skill path."
        )

    context.append(
        f"Read `{parsed.command_path.relative_to(root).as_posix()}` and follow that repository workflow contract."
    )

    if parsed.name == "start":
        context.append(
            "`$azoth-start` is the Codex calm-flow entrypoint: use it to refresh orientation and route to resume/next/closeout/intake/plan or a custom goal without relying on a default SessionStart hook."
        )
        if effective_pipeline_command:
            context.append(
                f"This routed `$azoth-start` request resolves to the `{effective_pipeline_command}` pipeline; keep that `pipeline_command` value in the fused Declaration and any scope/pipeline gate writes."
            )
    elif parsed.name in START_ROUTED_COMMANDS:
        context.extend(
            [
                f"In Codex calm mode, `/{parsed.name}` is a compatibility shim over `{parsed.canonical_input}`, not an independent daily path.",
                (
                    f"The normalized `$azoth-start` input already carries `pipeline_command={effective_pipeline_command}`; preserve that value in the fused Declaration and any scope/pipeline gate writes."
                    if effective_pipeline_command
                    else "Keep next-task selection inside the same calm-flow `$azoth-start` route instead of splitting it into `/start -> /next -> /auto`."
                ),
            ]
        )
    elif parsed.name == "session-closeout":
        context.append(
            "During closeout, treat W1/W2/W4 under `.azoth/` as authoritative, refresh `.azoth/session-state.md` as the W2 repo-local handoff artifact, attempt W3, and log `W3 deferred` if blocked."
        )
        context.append("Closeout output must report W3 disposition and the next operator action.")

    if effective_pipeline_command:
        context.extend(
            [
                "Keep the orchestrator in the main thread and use staged subagents when the command or `skills/subagent-router/SKILL.md` requires isolation.",
                f"The effective pipeline route is `{effective_pipeline_command}`; staged pipeline execution and staged delegation still apply even when Codex normalizes through `$azoth-start`.",
                "That route is not permission to improvise the work inline.",
                "A Declaration, gate write, or status card does not count as stage execution.",
                "If staged delegation is unavailable or you cannot actually execute the required staged handoffs, STOP after the Declaration and ask the human whether to authorize delegation, adjust the pipeline, or switch platforms.",
            ]
        )

    transition = _transition_guidance(
        root,
        parsed.canonical_input,
        command_name=parsed.name,
        command_args=parsed.transition_command_args,
    )
    if transition:
        context.append(transition)
        context.append(_governed_write_reminder())

    return context


def _load_codex_config(root: Path) -> dict[str, object]:
    config_path = root / ".codex" / "config.toml"
    if not config_path.is_file():
        return {}
    try:
        return tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def staged_delegation_ready(root: Path) -> tuple[bool, str]:
    config = _load_codex_config(root)
    features = config.get("features")
    if not isinstance(features, dict) or features.get("multi_agent") is not True:
        return False, "Codex multi-agent staging is not enabled in `.codex/config.toml`."

    orchestrator_path = root / ".codex" / "agents" / "orchestrator.toml"
    if not orchestrator_path.is_file():
        return False, "missing `.codex/agents/orchestrator.toml`."

    return True, ""


def _block_missing_skill(root: Path, parsed: ParsedPrompt) -> PromptDirective:
    requested = "/" + parsed.name if parsed.source == "slash" else f"$azoth-{parsed.name}"
    return PromptDirective(
        additional_context=(
            f"Blocked `{requested}` because Codex calm flow requires the generated skill wrapper "
            f"`{parsed.skill_path.relative_to(root).as_posix()}`. "
            "Run `python3 scripts/azoth-deploy.py --platforms codex` to restore the canonical command surface, then retry."
        ),
        decision="block",
    )


def _block_missing_delegation(parsed: ParsedPrompt, reason: str) -> PromptDirective:
    return PromptDirective(
        additional_context=(
            f"Blocked `{parsed.canonical_input}` because staged delegation is not ready in this Codex worktree ({reason}) "
            "and governed pipeline entry must stop rather than continue inline without the required staged handoffs."
        ),
        decision="block",
    )


def directive_for_prompt(root: Path, prompt: str) -> PromptDirective | None:
    parsed = parse_prompt(root, prompt)
    if parsed is None:
        if not _looks_like_actionable_freeform(prompt):
            return None
        freeform_command_name, freeform_command_args = _freeform_transition_inputs(prompt)
        transition = _transition_guidance(
            root,
            prompt,
            command_name=freeform_command_name,
            command_args=freeform_command_args,
        )
        if not transition:
            return None
        return PromptDirective(additional_context=transition)

    if not parsed.skill_path.is_file():
        return _block_missing_skill(root, parsed)

    if parsed.effective_pipeline_command:
        ready, reason = staged_delegation_ready(root)
        if not ready:
            return _block_missing_delegation(parsed, reason)

    additional_context = " ".join(_command_context(root, parsed))
    if parsed.source == "slash" or (
        parsed.source == "skill" and parsed.canonical_input != prompt.strip()
    ):
        return PromptDirective(
            additional_context=additional_context,
            updated_input=parsed.canonical_input,
        )
    if additional_context:
        return PromptDirective(additional_context=additional_context)
    return None


def normalize_token(
    root: Path,
    *,
    command_name: str,
    command_args: list[str] | None = None,
) -> dict[str, object]:
    name = command_name.strip().lower()
    args = " ".join(command_args or []).strip()
    parsed = ParsedPrompt(
        source="slash",
        name=name,
        args=args,
        command_path=command_path(root, name),
        skill_path=skill_path(root, "start" if name == "start" or name in START_ROUTED_COMMANDS else name),
    )
    if name == "session-closeout":
        return {
            "route": "pass-through",
            "canonical_skill": "$azoth-session-closeout",
            "summary": "Closeout remains an explicit Codex command.",
        }
    if name == "start" and not args:
        return {
            "route": "orientation",
            "canonical_skill": "$azoth-start",
            "summary": "Codex calm mode uses `$azoth-start` as the canonical daily entry surface.",
        }
    payload: dict[str, object] = {
        "route": "redirect" if name in START_ROUTED_COMMANDS else "pass-through",
        "canonical_skill": parsed.canonical_input,
        "source_contract": parsed.command_path.as_posix(),
    }
    if parsed.effective_pipeline_command:
        payload["pipeline_command"] = parsed.effective_pipeline_command
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex calm-flow control plane.")
    parser.add_argument("--root", type=Path, default=ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize-token")
    normalize.add_argument("token")
    normalize.add_argument("token_args", nargs="*")

    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "normalize-token":
        print(
            json.dumps(
                normalize_token(root, command_name=args.token, command_args=args.token_args),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    raise AssertionError(f"Unhandled command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())

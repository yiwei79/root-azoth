---
name: azoth-context-architect
description: Explicit Codex entrypoint for Azoth's `/context-architect` workflow.
  Use when the user wants to run `/context-architect` in Codex via `/skills` or `$azoth-context-architect`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/context-architect` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-context-architect`.
This skill is the explicit Codex-native equivalent of typing `/context-architect`.

Execution contract:
- Read `.claude/commands/context-architect.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-context-architect` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: read` contract.
- If the user typed literal `/context-architect` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/context-architect.md`
- Description: Map dependencies, blast radius, and change sequencing before implementation

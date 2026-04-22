---
name: azoth-promote
description: Explicit Codex entrypoint for Azoth's `/promote` workflow. Use when the
  user wants to run `/promote` in Codex via `/skills` or `$azoth-promote`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/promote` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-promote`.
This skill is the explicit Codex-native equivalent of typing `/promote`.

Execution contract:
- Read `.claude/commands/promote.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-promote` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: mixed` contract.
- If the user typed literal `/promote` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/promote.md`
- Description: Review promotion candidates from M3 episodes to M2 patterns

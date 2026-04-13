---
name: azoth-plan
description: Explicit Codex entrypoint for Azoth's `/plan` workflow. Use when the
  user wants to run `/plan` in Codex via `/skills` or `$azoth-plan`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/plan` workflow.

Codex does not register repository-defined slash commands in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of typing `/plan`.

Execution contract:
- Read `.claude/commands/plan.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-plan` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: read` contract.
- If the user typed literal `/plan` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/plan.md`
- Description: Structured planning without execution

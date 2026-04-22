---
name: azoth-auto
description: Explicit Codex entrypoint for Azoth's `/auto` workflow. Use when the
  user wants to run `/auto` in Codex via `/skills` or `$azoth-auto`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/auto` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-auto`.
This skill is the explicit Codex-native equivalent of typing `/auto`.

Execution contract:
- Read `commands/auto/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/auto.md`.
- Treat the rest of the user's prompt after `$azoth-auto` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/auto` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/auto/command.yaml`
- Body source path: `.claude/commands/auto.md`
- Description: Auto-compose and execute a pipeline based on goal classification

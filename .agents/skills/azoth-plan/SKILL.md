---
name: azoth-plan
description: Explicit Codex entrypoint for Azoth's `/plan` workflow. Use when the
  user wants to run `/plan` in Codex via `/skills` or `$azoth-plan`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/plan` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-plan`.
This skill is the explicit Codex-native equivalent of typing `/plan`.

Execution contract:
- Read `commands/plan/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/plan.md`.
- Treat the rest of the user's prompt after `$azoth-plan` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: read` contract.
- If the user typed literal `/plan` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/plan/command.yaml`
- Body source path: `.claude/commands/plan.md`
- Description: Structured planning without execution

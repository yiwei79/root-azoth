---
name: azoth-deliver-full
description: Explicit Codex entrypoint for Azoth's `/deliver-full` workflow. Use when
  the user wants to run `/deliver-full` in Codex via `/skills` or `$azoth-deliver-full`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/deliver-full` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-deliver-full`.
This skill is the explicit Codex-native equivalent of typing `/deliver-full`.

Execution contract:
- Read `commands/deliver-full/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/deliver-full.md`.
- Treat the rest of the user's prompt after `$azoth-deliver-full` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/deliver-full` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/deliver-full/command.yaml`
- Body source path: `.claude/commands/deliver-full.md`
- Description: Full pipeline with governance gates — for kernel, governance, or breaking changes

---
name: azoth-next
description: Explicit Codex entrypoint for Azoth's `/next` workflow. Use when the
  user wants to run `/next` in Codex via `/skills` or `$azoth-next`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/next` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-next`.
This skill is the explicit Codex-native equivalent of typing `/next`.

Execution contract:
- Read `commands/next/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `commands/next/body.md`.
- Treat the rest of the user's prompt after `$azoth-next` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: mixed` contract.
- If the user typed literal `/next` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/next/command.yaml`
- Body source path: `commands/next/body.md`
- Description: Show the next priority task from the roadmap and suggest how to proceed

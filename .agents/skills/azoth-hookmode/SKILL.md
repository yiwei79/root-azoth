---
name: azoth-hookmode
description: Explicit Codex entrypoint for Azoth's `/hookmode` workflow. Use when
  the user wants to run `/hookmode` in Codex via `/skills` or `$azoth-hookmode`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/hookmode` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-hookmode`.
This skill is the explicit Codex-native equivalent of typing `/hookmode`.

Execution contract:
- Read `commands/hookmode/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/hookmode.md`.
- Treat the rest of the user's prompt after `$azoth-hookmode` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/hookmode` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/hookmode/command.yaml`
- Body source path: `.claude/commands/hookmode.md`
- Description: Inspect or switch the local Codex operating mode

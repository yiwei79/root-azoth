---
name: azoth-test
description: Explicit Codex entrypoint for Azoth's `/test` workflow. Use when the
  user wants to run `/test` in Codex via `/skills` or `$azoth-test`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/test` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-test`.
This skill is the explicit Codex-native equivalent of typing `/test`.

Execution contract:
- Read `commands/test/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/test.md`.
- Treat the rest of the user's prompt after `$azoth-test` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/test` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/test/command.yaml`
- Body source path: `.claude/commands/test.md`
- Description: Generate unit tests for specified code

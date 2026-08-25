---
name: azoth-sync
description: Explicit Codex entrypoint for Azoth's `/sync` workflow. Use when the
  user wants to run `/sync` in Codex via `/skills` or `$azoth-sync`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/sync` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-sync`.
This skill is the explicit Codex-native equivalent of typing `/sync`.

Execution contract:
- Read `commands/sync/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/sync.md`.
- Treat the rest of the user's prompt after `$azoth-sync` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/sync` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/sync/command.yaml`
- Body source path: `.claude/commands/sync.md`
- Description: Extract patterns from a source framework into Azoth

---
name: azoth-autonomous-auto
description: Explicit Codex entrypoint for Azoth's `/autonomous-auto` workflow. Use
  when the user wants to run `/autonomous-auto` in Codex via `/skills` or `$azoth-autonomous-auto`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/autonomous-auto` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-autonomous-auto`.
This skill is the explicit Codex-native equivalent of typing `/autonomous-auto`.

Execution contract:
- Read `commands/autonomous-auto/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/autonomous-auto.md`.
- Treat the rest of the user's prompt after `$azoth-autonomous-auto` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/autonomous-auto` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/autonomous-auto/command.yaml`
- Body source path: `.claude/commands/autonomous-auto.md`
- Description: Autonomous Auto Mode: standalone adaptive pipeline for branch-local Azoth self-development with alignment_mode: async, alignment packets, and approval_basis persistence

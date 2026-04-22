---
name: azoth-roadmap
description: Explicit Codex entrypoint for Azoth's `/roadmap` workflow. Use when the
  user wants to run `/roadmap` in Codex via `/skills` or `$azoth-roadmap`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/roadmap` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-roadmap`.
This skill is the explicit Codex-native equivalent of typing `/roadmap`.

Execution contract:
- Read `commands/roadmap/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/roadmap.md`.
- Treat the rest of the user's prompt after `$azoth-roadmap` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: read` contract.
- If the user typed literal `/roadmap` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/roadmap/command.yaml`
- Body source path: `.claude/commands/roadmap.md`
- Description: Roadmap dashboard — versioned phases (D48) and upcoming work

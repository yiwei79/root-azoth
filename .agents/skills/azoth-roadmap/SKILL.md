---
name: azoth-roadmap
description: Explicit Codex entrypoint for Azoth's `/roadmap` workflow. Use when the
  user wants to run `/roadmap` in Codex via `/skills` or `$azoth-roadmap`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/roadmap` workflow.

Codex does not register repository-defined slash commands in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of typing `/roadmap`.

Execution contract:
- Read `.claude/commands/roadmap.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-roadmap` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: read` contract.
- If the user typed literal `/roadmap` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/roadmap.md`
- Description: Roadmap dashboard — versioned phases (D48) and upcoming work

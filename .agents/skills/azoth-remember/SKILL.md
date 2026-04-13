---
name: azoth-remember
description: Explicit Codex entrypoint for Azoth's `/remember` workflow. Use when
  the user wants to run `/remember` in Codex via `/skills` or `$azoth-remember`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/remember` workflow.

Codex does not register repository-defined slash commands in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of typing `/remember`.

Execution contract:
- Read `.claude/commands/remember.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-remember` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/remember` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/remember.md`
- Description: Capture a cross-session learning as a structured episode

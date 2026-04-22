---
name: azoth-park
description: Explicit Codex entrypoint for Azoth's `/park` workflow. Use when the
  user wants to run `/park` in Codex via `/skills` or `$azoth-park`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/park` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-park`.
This skill is the explicit Codex-native equivalent of typing `/park`.

Execution contract:
- Read `.claude/commands/park.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-park` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/park` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/park.md`
- Description: Park the current session for later resumption

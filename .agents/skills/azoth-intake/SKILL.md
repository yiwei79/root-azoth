---
name: azoth-intake
description: Explicit Codex entrypoint for Azoth's `/intake` workflow. Use when the
  user wants to run `/intake` in Codex via `/skills` or `$azoth-intake`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/intake` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-intake`.
This skill is the explicit Codex-native equivalent of typing `/intake`.

Execution contract:
- Read `.claude/commands/intake.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-intake` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/intake` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/intake.md`
- Description: Process queued insights from .azoth/inbox/ through the governed intake protocol

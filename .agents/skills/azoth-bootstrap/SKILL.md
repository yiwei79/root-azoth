---
name: azoth-bootstrap
description: Explicit Codex entrypoint for Azoth's `/bootstrap` workflow. Use when
  the user wants to run `/bootstrap` in Codex via `/skills` or `$azoth-bootstrap`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/bootstrap` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-bootstrap`.
This skill is the explicit Codex-native equivalent of typing `/bootstrap`.

Execution contract:
- Read `.claude/commands/bootstrap.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-bootstrap` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/bootstrap` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/bootstrap.md`
- Description: Day 0 bootstrap — create the Azoth kernel from the architecture plan

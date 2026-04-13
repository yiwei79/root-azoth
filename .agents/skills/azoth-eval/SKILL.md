---
name: azoth-eval
description: Explicit Codex entrypoint for Azoth's `/eval` workflow. Use when the
  user wants to run `/eval` in Codex via `/skills` or `$azoth-eval`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/eval` workflow.

Codex does not register repository-defined slash commands in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of typing `/eval`.

Execution contract:
- Read `.claude/commands/eval.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-eval` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: read` contract.
- If the user typed literal `/eval` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/eval.md`
- Description: Governance quality gate — evaluate artifacts; auto-escalates to swarm eval when warranted

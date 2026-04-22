---
name: azoth-eval
description: Explicit Codex entrypoint for Azoth's `/eval` workflow. Use when the
  user wants to run `/eval` in Codex via `/skills` or `$azoth-eval`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/eval` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-eval`.
This skill is the explicit Codex-native equivalent of typing `/eval`.

Execution contract:
- Read `commands/eval/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/eval.md`.
- Treat the rest of the user's prompt after `$azoth-eval` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: read` contract.
- If the user typed literal `/eval` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/eval/command.yaml`
- Body source path: `.claude/commands/eval.md`
- Description: Governance quality gate — evaluate artifacts; auto-escalates to swarm eval when warranted

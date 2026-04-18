---
name: azoth-eval-swarm
description: Explicit Codex entrypoint for Azoth's `/eval-swarm` workflow. Use when
  the user wants to run `/eval-swarm` in Codex via `/skills` or `$azoth-eval-swarm`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/eval-swarm` workflow.

Codex does not register repository-defined slash commands in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of typing `/eval-swarm`.

Execution contract:
- Read `.claude/commands/eval-swarm.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-eval-swarm` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: mixed` contract.
- If the user typed literal `/eval-swarm` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/eval-swarm.md`
- Description: Strict swarm evaluation — 0.90 bar, isolated evaluators, multi-wave iteration

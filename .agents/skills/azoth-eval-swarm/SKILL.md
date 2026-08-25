---
name: azoth-eval-swarm
description: Explicit Codex entrypoint for Azoth's `/eval-swarm` workflow. Use when
  the user wants to run `/eval-swarm` in Codex via `/skills` or `$azoth-eval-swarm`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/eval-swarm` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-eval-swarm`.
This skill is the explicit Codex-native equivalent of typing `/eval-swarm`.

Execution contract:
- Read `commands/eval-swarm/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/eval-swarm.md`.
- Treat the rest of the user's prompt after `$azoth-eval-swarm` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: mixed` contract.
- If the user typed literal `/eval-swarm` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/eval-swarm/command.yaml`
- Body source path: `.claude/commands/eval-swarm.md`
- Description: Strict swarm evaluation — 0.90 bar, isolated evaluators, multi-wave iteration

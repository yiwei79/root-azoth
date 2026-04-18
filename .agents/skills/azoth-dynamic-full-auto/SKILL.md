---
name: azoth-dynamic-full-auto
description: Explicit Codex entrypoint for Azoth's `/dynamic-full-auto` workflow.
  Use when the user wants to run `/dynamic-full-auto` in Codex via `/skills` or `$azoth-dynamic-full-auto`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/dynamic-full-auto` workflow.

Codex does not register repository-defined slash commands in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of typing `/dynamic-full-auto`.

Execution contract:
- Read `.claude/commands/dynamic-full-auto.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-dynamic-full-auto` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/dynamic-full-auto` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/dynamic-full-auto.md`
- Description: DYNAMIC-FULL-AUTO+ session: adaptive research/explore swarms, digest, Checkpoint Γ, optional eval-swarm, then /auto-style delivery

Codex calm-flow rules:
- In Codex, `$azoth-dynamic-full-auto` is a compatibility shim over `$azoth-start ...`, not an independent daily entry path.
- Normalize this request through `scripts/codex_control_plane.py` and preserve `pipeline_command: dynamic-full-auto`.
- If Codex cannot normalize the request into the canonical calm-flow path, stop with a short redirect instead of continuing inline.

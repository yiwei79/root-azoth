---
name: azoth-deliver
description: Explicit Codex entrypoint for Azoth's `/deliver` workflow. Use when the
  user wants to run `/deliver` in Codex via `/skills` or `$azoth-deliver`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/deliver` workflow.

Codex does not register repository-defined slash commands in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of typing `/deliver`.

Execution contract:
- Read `commands/deliver/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `.claude/commands/deliver.md`.
- Treat the rest of the user's prompt after `$azoth-deliver` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/deliver` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/deliver/command.yaml`
- Body source path: `.claude/commands/deliver.md`
- Description: Lean pipeline for pre-approved, additive work

Codex calm-flow rules:
- In Codex, `$azoth-deliver` is a compatibility shim over `$azoth-start ...`, not an independent daily entry path.
- Normalize this request through `scripts/codex_control_plane.py` and preserve `pipeline_command: deliver`.
- If Codex cannot normalize the request into the canonical calm-flow path, stop with a short redirect instead of continuing inline.

---
name: azoth-resume
description: Explicit Codex entrypoint for Azoth's `/resume` workflow. Use when the
  user wants to run `/resume` in Codex via `/skills` or `$azoth-resume`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/resume` workflow.

Codex does not register repository-defined slash commands in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of typing `/resume`.

Execution contract:
- Read `commands/resume/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `commands/resume/body.md`.
- Treat the rest of the user's prompt after `$azoth-resume` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/resume` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/resume/command.yaml`
- Body source path: `commands/resume/body.md`
- Description: Resume the current active scope or reopen a parked session

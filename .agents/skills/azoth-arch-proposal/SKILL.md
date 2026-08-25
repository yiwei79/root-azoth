---
name: azoth-arch-proposal
description: Explicit Codex entrypoint for Azoth's `/arch-proposal` workflow. Use
  when the user wants to run `/arch-proposal` in Codex via `/skills` or `$azoth-arch-proposal`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/arch-proposal` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-arch-proposal`.
This skill is the explicit Codex-native equivalent of typing `/arch-proposal`.

Execution contract:
- Read `.claude/commands/arch-proposal.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-arch-proposal` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: mixed` contract.
- If the user typed literal `/arch-proposal` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/arch-proposal.md`
- Description: L3 human-gated architecture proposal artifact — structured YAML under .azoth/proposals/

---
name: azoth-worktree-sync
description: Explicit Codex entrypoint for Azoth's `/worktree-sync` workflow. Use
  when the user wants to run `/worktree-sync` in Codex via `/skills` or `$azoth-worktree-sync`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/worktree-sync` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-worktree-sync`.
This skill is the explicit Codex-native equivalent of typing `/worktree-sync`.

Execution contract:
- Read `.claude/commands/worktree-sync.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-worktree-sync` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/worktree-sync` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/worktree-sync.md`
- Description: Protocol-aware worktree sync for producer handoffs and integrate runs

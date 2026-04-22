---
name: azoth-review-insights
description: Explicit Codex entrypoint for Azoth's `/review-insights` workflow. Use
  when the user wants to run `/review-insights` in Codex via `/skills` or `$azoth-review-insights`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/review-insights` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-review-insights`.
This skill is the explicit Codex-native equivalent of typing `/review-insights`.

Execution contract:
- Read `.claude/commands/review-insights.md` and follow it as the source of truth.
- Treat the rest of the user's prompt after `$azoth-review-insights` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/review-insights` in prompt text instead, apply the same workflow contract.

Command metadata:
- Source path: `.claude/commands/review-insights.md`
- Description: Run Cursor-oriented blindspot review and write D32 insights to .azoth/inbox/

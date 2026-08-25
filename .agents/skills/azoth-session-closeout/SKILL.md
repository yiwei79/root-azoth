---
name: azoth-session-closeout
description: Explicit Codex entrypoint for Azoth's `/session-closeout` workflow. Use
  when the user wants to run `/session-closeout` in Codex via `/skills` or `$azoth-session-closeout`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/session-closeout` workflow.

Codex uses skills as the custom command surface for Azoth workflows.
In the Codex app, enabled skills may appear in the slash command list.
In Codex CLI/IDE, use `/skills` or `$azoth-session-closeout`.
This skill is the explicit Codex-native equivalent of typing `/session-closeout`.

Execution contract:
- Read `commands/session-closeout/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `commands/session-closeout/body.md`.
- Treat the rest of the user's prompt after `$azoth-session-closeout` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: write` contract.
- If the user typed literal `/session-closeout` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/session-closeout/command.yaml`
- Body source path: `commands/session-closeout/body.md`
- Description: Unified eval + close + sync — run at the end of every session

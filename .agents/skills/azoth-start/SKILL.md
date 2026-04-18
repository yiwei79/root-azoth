---
name: azoth-start
description: Explicit Codex entrypoint for Azoth's `/start` workflow. Use when the
  user wants to run `/start` in Codex via `/skills` or `$azoth-start`.
---

Use this skill as the Codex-visible entrypoint for Azoth's `/start` workflow.

Codex does not register repository-defined slash commands in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of typing `/start`.

Execution contract:
- Read `commands/start/command.yaml` and treat it as the source of truth.
- Read the body source referenced by that contract: `commands/start/body.md`.
- Treat the rest of the user's prompt after `$azoth-start` as `$ARGUMENTS`.
- Preserve the command's stage structure, gate rules, evaluation rules, and referenced skills/agents.
- Preserve the command's `agent: orchestrator` binding.
- Respect the command's `azoth_effect: read` contract.
- If the user typed literal `/start` in prompt text instead, apply the same workflow contract.

Command metadata:
- Contract path: `commands/start/command.yaml`
- Body source path: `commands/start/body.md`
- Description: Session welcome dashboard — orient, then route to your next action

Codex calm-flow rules:
- Treat `$azoth-start` as the canonical daily control surface in Codex.
- Route `resume`, `next`, `closeout`, and custom goals through the same calm-flow controller in `scripts/codex_control_plane.py`.
- In Codex, do not split the daily path into `/start -> /next -> /auto`; `next` and custom goals both resolve to the same fused declaration path.
- If the request carries an explicit pipeline override, preserve it as `pipeline_command` while staying inside the `$azoth-start ...` route.

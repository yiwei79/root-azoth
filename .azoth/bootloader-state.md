# Azoth Bootloader State

## Current Phase
v0.1.2.2 · Phase 2 — v0.2.0 · declarative swarm depth · memory hardening · active_version: v0.2.0-p2 · patch 2

## Last Session
- **Session**: 2026-04-18-codex-hook-ux-fix
- **Platform**: Codex
- **Delivered**: Codex hook UX regression fix + restored `azoth-*` command wrapper generation
- **Pipeline**: auto (approved infrastructure closeout)
- **Eval**: targeted Codex parity checks green (`tests/test_codex_adapter_templates.py`, `tests/test_azoth_deploy.py -k codex`)
- **Episodes**: ep-163
- **Version bump**: 0.1.2.1 → 0.1.2.2

## Key Changes This Session
1. `.codex/hooks/user_prompt_submit_router.py` and the Codex adapter template now resolve repo paths from the hook location, only route leading workflow tokens, and add active-scope continuity guidance with a governed-write reminder.
2. `.codex/config.toml` / `.codex/hooks.json` and their templates now use calmer Codex parity wording and hook copy consistent with this branch's real command surface.
3. `scripts/azoth-deploy.py` again generates `.agents/skills/azoth-*` command wrappers plus `agents/openai.yaml`, restoring the discoverable Codex command surface after deploy.
4. `tests/test_codex_adapter_templates.py` now covers non-root cwd routing, additional command coverage, mention-only token suppression, and active-scope resume guidance.
5. `.claude/agents/orchestrator.md` now describes the actual Codex command entry surface on this branch instead of promising undeployed behavior.

## Open Decisions
- No blocking decisions. Codex remains hook-soft: Bash hook enforcement exists, but non-Bash write gating is still behavioral.

## Next Action
- Re-open `/skills` in Codex to confirm the regenerated `azoth-*` command wrappers appear, then run `/next` for the next v0.2.0-p2 task.

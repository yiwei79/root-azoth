# Azoth Bootloader State

## Current Phase
v0.1.1.43 · Phase 1 — v0.2.0 · swarm · memory · UX (milestone phase 1) · active_version: v0.2.0-p1

## Last Session
- **Session**: 2026-04-12-bl-027
- **Platform**: GitHub Copilot CLI (GPT-5.4)
- **Delivered**: BL-027 — fix `eval-swarm.md` `azoth_effect: read` → `mixed`
- **Pipeline**: auto (governed M1)
- **Eval**: eval-swarm pass; average score 0.926; final architect review approved
- **Episodes**: ep-157
- **Version bump**: 0.1.1.42 → 0.1.1.43

## Key Changes This Session
1. `.claude/commands/eval-swarm.md`: corrected frontmatter to `azoth_effect: mixed` to match the command's governed write-capable path.
2. Governed `/auto` delivery confirmed the blast radius was one source command file and one line; no kernel or additional command surfaces changed.
3. `scripts/azoth-deploy.py` transform inspection confirmed `azoth_effect` is stripped from command mirrors, so deploy regeneration was intentionally skipped for this fix.

## Open Decisions
- Optional follow-up: clarify `eval-swarm.md` body wording around "read-only for repo files" so it reads more cleanly beside the `mixed` frontmatter.
- BL-028 is now the top backlog item and remains unscopeed.

## Next Action
- Run `/next` to scope BL-028: exclude `kernel/templates/` from product extraction (infrastructure, standard).

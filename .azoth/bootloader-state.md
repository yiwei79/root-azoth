# Azoth Bootloader State

## Current Phase
v0.1.2.9 · Phase 2 — v0.2.0 · memory hardening · declarative swarm · platform parity (milestone phase 2) · active_version: v0.2.0-p2

## Last Session
- **Session**: 2026-04-13-codex-eval-hardening
- **Platform**: Codex
- **Delivered**: Codex parity hardening follow-up — fallback router now resolves repo-root command docs, fires only for intentional leading slash invocations, and handoff/orientation surfaces now describe `/skills` and `$azoth-*` as the primary Codex entry.
- **Pipeline**: ad-hoc repair loop from `/eval-swarm` findings, then `/session-closeout`
- **Episodes**: ep-177, ep-178, ep-179
- **Version bump**: 0.1.2.8 → 0.1.2.9

## Key Changes This Session
1. Fixed the Codex fallback router at `kernel/templates/platform-adapters/codex/user_prompt_submit_router.py.template` so it resolves `.claude/commands/*.md` from the repository root rather than the process `cwd`. This removes the broken-below-subdirectory behavior seen in the swarm audit.
2. Narrowed fallback routing to intentional leading slash commands only. Mention-only prose like “Explain the difference between /auto and /deliver” no longer hijacks into workflow execution context. Added regression coverage for both bugs in `tests/test_codex_adapter_templates.py`.
3. Refreshed cross-IDE parity surfaces so Codex is explicit and current in the opening architecture framing, W3 closeout contract, welcome/orientation text, README quickstart, and the live session handoff capsule.
4. Prepared split commits so canonical sources, deployed mirrors, and closeout/version artifacts can land as separate reviewable units.

## Open Decisions
- If Codex later adds documented repo-defined command registration, replace the current wrapper-skill-first guidance with the official native path and simplify the fallback router accordingly.

## Next Action
- In Codex, use `/skills` or `$azoth-next` / `$azoth-auto` as the primary entry. When Codex adapter files or command wrappers change, rerun `python3 scripts/azoth-deploy.py` and the Codex router parity tests before claiming compatibility.

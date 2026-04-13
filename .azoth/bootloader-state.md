# Azoth Bootloader State

## Current Phase
v0.1.2.8 · Phase 2 — v0.2.0 · memory hardening · declarative swarm · platform parity (milestone phase 2) · active_version: v0.2.0-p2

## Last Session
- **Session**: 2026-04-13-bl-037
- **Platform**: GitHub Copilot (Claude Opus 4.6)
- **Delivered**: BL-037 (governed: align TRUST_CONTRACT §1 'per turn' → 'per session' across 7 source files + 145 deployed surfaces)
- **Pipeline**: auto-full (S0-S6, governed, evaluator 0.94)
- **Episodes**: ep-176
- **Version bump**: 0.1.2.6 → 0.1.2.8

## Key Changes This Session
1. BL-037 (M1/governed): Changed 'per turn' → 'per session' in kernel/TRUST_CONTRACT.md §1 (header, narrative, table cells). Fixed 'withoIut' typo. Fixed 500→1000 mismatch in reviewer/builder agents.
2. Updated docs/AZOTH_ARCHITECTURE.md (3 locations), agents (reviewer + builder), skills/entropy-guard, .claude/hooks/entropy_check.py docstring, scripts/azoth-deploy.py template string.
3. Ran azoth-deploy.py to regenerate 145 deployed surfaces across .claude/, .github/, .opencode/, .codex/, AGENTS.md.
4. Added M2 pattern: pipeline-declaration-before-execution (user preference for upfront pipeline declaration).
5. Test suite: 1337 pass, 0 regressions.

## Open Decisions
- None blocking.

## Next Action
- `/next` to pick next v0.2.0-p2 deliverable or check backlog for new active items.

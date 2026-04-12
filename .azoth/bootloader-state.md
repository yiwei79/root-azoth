# Azoth Bootloader State

## Current Phase
v0.1.1.45 · Phase 1 — v0.2.0 · swarm · memory · UX (milestone phase 1) · active_version: v0.2.0-p1

## Last Session
- **Session**: 2026-04-12-bl-031
- **Platform**: GitHub Copilot (Claude Opus 4.6)
- **Delivered**: BL-031, BL-032, BL-033 — Copilot adapter fallback, dry-run test, AZOTH_VERSION coupling
- **Pipeline**: auto (infrastructure, standard)
- **Eval**: agentic-eval pass; weighted score 0.94
- **Episodes**: ep-161
- **Version bump**: 0.1.1.44 → 0.1.1.45

## Key Changes This Session
1. `.claude/commands/eval.md` + `eval-swarm.md`: added fallback guidance line for installs without `.claude/commands/` (BL-031).
2. `scripts/azoth_extract_product.py`: added `_read_azoth_version()` and `_build_claude_substitutions()` to read AZOTH_VERSION from `azoth.yaml` at extract time instead of hardcoded `"0.1.0"` (BL-033).
3. `tests/test_azoth_extract_product.py`: added `test_dry_run_banner_states_step1_only` (BL-032) and `test_azoth_version_coupled_to_azoth_yaml` (BL-033).
4. `azoth-deploy.py` mirrors regenerated for eval/eval-swarm across all platforms.
5. Backlog: BL-031/032/033 marked complete; no active items remain.

## Open Decisions
- None — backlog queue is empty. Next session should run `/intake` or add new items.

## Next Action
- Run `/next` to populate new backlog items or `/intake` if insights arrive.

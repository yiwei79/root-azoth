# Azoth Bootloader State

## Current Phase
v0.1.2.13 · Phase 2 — v0.2.0 · memory hardening · declarative swarm · platform parity (milestone phase 2) · active_version: v0.2.0-p2

## Last Session
- **Session**: 2026-04-14-codex-fix-design
- **Platform**: GitHub Copilot (VS Code, orchestrator mode)
- **Delivered**: Codex audit + design + build (S1–S4) + readiness scorecard (9.26/10) + standalone platform guide (`docs/platform-guides/codex-guide.md`). DFA+ pipeline: audit → architect synthesis → 4 fixes shipped (approval_policy, Trust Contract inline, DFA+ Codex happy path, kernel-integrity Stop hook) + eval 0.92 PASS.
- **Pipeline**: /dynamic-full-auto → /eval → readiness audit → platform guide
- **Episodes**: ep-199
- **Version bump**: 0.1.2.12 → 0.1.2.13

## Key Changes This Session
1. `kernel/templates/platform-adapters/codex/config.toml.template`: approval_policy "on-request" → "auto-edit"; added 4-line Trust Contract boundaries in developer_instructions.
2. `kernel/templates/platform-adapters/codex/hooks.json.template`: added kernel-integrity.py as Stop hook.
3. `skills/dynamic-full-auto/SKILL.md`: added "Happy path — Codex" section (6 items: hook-soft, network disabled, scope-gate contract, Stop hook).
4. `docs/platform-guides/codex-guide.md`: new standalone Codex platform guide consolidating all scattered content.
5. All deployed surfaces regenerated via azoth-deploy.py (176 files in sync).

## Open Decisions
- BL-047: human must verify network_access=true intent on phase/v0.2.0-p2 before next merge (priority 2).
- 6 M2 candidates from prior intake (ep-184, ep-188, ep-190, ep-193, ep-194, ep-196) — surface via /promote when evidence matures.

## Next Action
- BL-047 (verify network_access=true on phase branch) — priority 2, do first.
- BL-042 (sync-config.yaml kernel/templates/ exclusion) — priority 3, standard delivery.
- BL-048 (entropy split-brain: canonical archetypes) — priority 4, straightforward sync.

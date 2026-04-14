# Azoth Bootloader State

## Current Phase
v0.1.2.14 · Phase 2 — v0.2.0 · memory hardening · declarative swarm · platform parity (milestone phase 2) · active_version: v0.2.0-p2

## Last Session
- **Session**: 2026-04-14-codex-fix-design (continued — post-closeout bug fixes + hardening)
- **Platform**: GitHub Copilot (VS Code, orchestrator mode)
- **Delivered**: Fixed 3 sequential Codex runtime crashes (approval_policy enum, PreToolUse permissionDecision incompatibility, Stop hook JSON stdout). Hardened hook compatibility layer with `lint_codex_hooks()` in `azoth-deploy.py` (mechanical prevention) + 5 protocol rules in platform guide + architecture doc hook protocol table. Episodes ep-200, ep-201, ep-202.
- **Pipeline**: ad-hoc bug fixes → systematic hardening
- **Episodes**: ep-200 (failure), ep-201 (failure), ep-202 (pattern)
- **Version bump**: 0.1.2.13 → 0.1.2.14

## Key Changes This Session
1. `kernel/templates/.../config.toml.template`: reverted approval_policy from "auto-edit" to "on-request" (runtime-verified valid enum).
2. `kernel/templates/.../hooks.json.template`: removed PreToolUse hook (permissionDecision incompatible with Codex); added `--quiet` to notify.py Stop hook (JSON stdout requirement).
3. `scripts/azoth-deploy.py`: added `lint_codex_hooks()` (~90 LOC) — mechanical lint catching 3 violation classes on every deploy/check.
4. `docs/platform-guides/codex-guide.md`: added 5 hook protocol rules, compatibility matrix, new-hook checklist.
5. `docs/AZOTH_ARCHITECTURE.md`: Codex parity section expanded with hook protocol table + 4 enforcement rules.
6. `.azoth/memory/episodes.jsonl`: ep-200 (failure: approval_policy + PreToolUse), ep-201 (failure: notify stdout + wishful thinking), ep-202 (pattern: systematic hardening).
7. All deployed surfaces regenerated (176 files in sync). 1351 tests pass.

## Open Decisions
- BL-047: human must verify network_access=true intent on phase/v0.2.0-p2 before next merge (priority 2).
- BL-049: version-bump.py doesn't update settings.json AZOTH_VERSION env var (test_settings_env_matches_azoth_manifest failing).
- 6 M2 candidates from prior intake (ep-184, ep-188, ep-190, ep-193, ep-194, ep-196) — surface via /promote when evidence matures.

## Next Action
- BL-047 (verify network_access=true on phase branch) — priority 2, do first.
- BL-049 (version-bump.py settings.json coverage) — fix pre-existing test failure.
- BL-042 (sync-config.yaml kernel/templates/ exclusion) — priority 3, standard delivery.

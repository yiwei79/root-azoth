# Azoth Bootloader State

## Current Phase
v0.1.2.10 · Phase 2 — v0.2.0 · memory hardening · declarative swarm · platform parity (milestone phase 2) · active_version: v0.2.0-p2

## Last Session
- **Session**: 2026-04-13-promote-session
- **Platform**: GitHub Copilot (VS Code)
- **Delivered**: /promote pass — 6 M2 patterns promoted from M3 (patterns.yaml 11→17), BL-042 added for D42 sync-config.yaml kernel/templates/ gap.
- **Pipeline**: /start → /intake (empty) → /promote → /session-closeout
- **Episodes**: ep-181
- **Version bump**: 0.1.2.9 → 0.1.2.10

## Key Changes This Session
1. Promoted 6 M3 episodes to M2 patterns: blast-radius-includes-all-downstream-surfaces, status-enum-defensive-set-check, adaptive-stage-skip-three-condition-rule, scaffold-only-paths-require-explicit-product-exclusion, backlog-status-update-is-mandatory-at-closeout, w3-mirror-required-from-all-platforms.
2. Added BL-042 to backlog.yaml: kernel/templates/ missing from sync-config.yaml exclude_paths is a D42 governance gap that must be fixed before public product extraction (D35/D38).
3. Deferred ep-173 (tool-availability-check-before-write-protocols) — single evidence point, fails Promotion Rubric D (3+ sessions). Keep m2_candidate for next reinforcement.
4. Codex parity changes from prior sessions (session-closeout.md, test_azoth_deploy.py) batched into this commit.

## Open Decisions
- ep-173 (tool-availability check) held at not-yet — revisit after 2 more reinforcements.
- BL-042 ready for standard delivery session when scope allows.
- If Codex later adds documented repo-defined command registration, replace wrapper-skill-first guidance with the official native path.

## Next Action
- BL-041 (INI-MEM-004: harden memory-loop parity for promote + closeout) is the top active backlog item — standard delivery via /deliver, aligned to P1-017 exact-id reinforcement automation.
- BL-042 (sync-config.yaml kernel/templates/ exclusion) is priority 3 — standard delivery.

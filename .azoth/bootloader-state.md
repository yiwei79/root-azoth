# Azoth Bootloader State

## Current Phase
v0.1.2.1 · Phase 2 — v0.2.0 · declarative swarm depth · memory hardening · active_version: v0.2.0-p2 · patch 1

## Last Session
- **Session**: 2026-04-13-ini-rst-001
- **Platform**: Claude Code
- **Delivered**: BL-034 — Declarative swarm / eval-wave specification depth pass (INI-RST-001)
- **Pipeline**: deliver-full (governed, M1, 7-stage)
- **Eval**: agentic-eval pass; all 90 new + pre-existing tests green
- **Episodes**: ep-162
- **Version bump**: 0.1.2.0 → 0.1.2.1

## Key Changes This Session
1. `pipelines/run-ledger.schema.yaml`: added optional `stage_id` (string, pattern-validated) + `wave_label` (enum [A,B,C,D], advisory) to `wave_entry.$defs`; added cross-reference design comment linking to `swarm-eval-wave.schema.yaml` (T1, BL-034).
2. `pipelines/swarm-build-review.example.yaml`: new 2-wave (A=builder, B=reviewer) example; validates against swarm-eval-wave.schema.yaml; Iron Law compliant (max_parallel:5) (T2, BL-034).
3. `.claude/workflows/enterprise/e2e-swarm-eval-loop.md`: added reference bullet for `swarm-build-review.example.yaml` in References section (T5, BL-034).
4. `tests/test_swarm_wave_schema.py`: `TestBuildReviewExample` class with 4 tests; all green.
5. `tests/test_run_ledger.py`: 3 new tests for optional wave_entry fields + `import pytest` fix.
6. `.azoth/backlog.yaml`: BL-034 added and complete.

## Open Decisions
- None blocking. INI-RST-001 delivered. BL-034 complete.

## Next Action
- Run `/next` to schedule next v0.2.0-p2 task (P1-017 reinforcement_count automation, P1-020 verbatim-first M3, P1-021 memory parity).

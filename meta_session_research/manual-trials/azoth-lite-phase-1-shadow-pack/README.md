# Azoth-Lite Phase 1 Shadow Trial Pack

Date: 2026-05-01

Status: manual/shadow Phase 1 artifact. No runtime behavior change.

## Approval Boundary

The profile split is accepted as architecture direction, not as an implemented
default posture.

This pack is deliberately outside `.azoth/`. It does not create roadmap state,
validators, hooks, command contracts, adapter output, run-ledger entries, memory
entries, or closeout artifacts.

## Purpose

Use the smallest `azoth-lite` surface as a manual runbook and run it against the
five Phase 1 proof cases:

- one read-only/status task;
- one focused verification task;
- one ordinary local edit task;
- one governed-state escalation task;
- one finality/packaging escalation task.

## Artifacts

- [trial-pack.md](trial-pack.md): the manual `azoth-lite` context view,
  classifier, escalation checklist, and trace template.
- [fixture-matrix.md](fixture-matrix.md): the Phase 1 fixture set and expected
  outcomes.
- [run-log.md](run-log.md): concrete execution trace for the first five-case
  shadow run.

## Stop Rule

Stop Phase 1 after the manual pack and first five-case run are recorded. Do not
open Phase 2 helper implementation or route integration in this session.

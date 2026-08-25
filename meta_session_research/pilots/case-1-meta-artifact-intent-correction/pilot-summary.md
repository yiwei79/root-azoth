# Pilot Summary

Date: 2026-05-01

Case: Meta-Artifact Intent Correction.

Pilot type: desk replay against frozen profile packets.

## What This Pilot Shows

This case strongly penalizes native-shape capture. The user explicitly wanted a
meta-session research plan and later corrected the assistant for creating an
adjacent synthesis artifact. That makes this a good early test of whether a
profile preserves user intent when the repo's default machinery points in a
different direction.

The provisional result favors `azoth-lite` and `meta-harness-experimental`:

- `azoth-lite` preserves trust primitives and side-effect boundaries without
  invoking full Azoth ceremony.
- `meta-harness-experimental` best matches the target architecture, but remains
  partly aspirational because there is no implemented substrate yet.
- `stock-lite` is smooth and likely effective, but weak on traceability.
- `azoth-full` is intentionally mismatched; its native artifact vocabulary is
  the thing this case is guarding against.

## What This Pilot Does Not Prove

It does not prove `azoth-lite` should be the default. This was not a fresh
multi-profile run. It was a replay of an observed session under profile lenses.

It also does not prove `azoth-full` lacks value. Case 1 is a meta-intent task,
not a high-risk implementation or release task.

## Gate 2 Progress

Completed for Case 1:

- frozen context packets;
- dry-run state policy;
- trace template usage;
- profile-lens traces;
- evaluation cards.

Remaining before a stronger pilot:

- run fresh sessions or fresh isolated prompts;
- use at least one side-effect-boundary case;
- use at least one narrow bugfix case;
- compare actual tool churn and user burden rather than replay estimates.

## Recommended Next Step

Proceed to Case 3: Hydration Side-Effect Boundary.

Use a non-mutating fixture or dry-run candidate. This is the right next case
because it tests the opposite side of Case 1:

- Case 1 asks whether the harness can stay out of the way.
- Case 3 asks whether the harness catches a real mutation boundary before the
  model acts.


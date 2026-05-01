# Pilot Summary

Date: 2026-05-01

Case: Hydration Side-Effect Boundary.

Pilot type: dry-run boundary evaluation.

## What This Pilot Shows

This case is the counterweight to Case 1. Case 1 showed the cost of native-shape
capture. Case 3 shows why deterministic safety boundaries exist.

The historical bypass was real: hydration was performed after continuation
wording and mutated roadmap/backlog/spec state without a live approved scope.
The current repo now contains a direct guard and tests for that failure mode.

This is strong evidence that some Azoth machinery is not mere ceremony. For
planning-state mutation, a profile needs explicit permission boundaries.

## Profile Implication

`stock-lite` is under-gated for this case.

`azoth-lite` can work if the context view explicitly classifies hydration as a
mutating action and requires read-only checks first.

`azoth-full` works well here because the current guard, scope gate, and tests are
directly relevant.

`meta-harness-experimental` is the best target shape: retain the safety
property, but express it as permissioned hands and event logs rather than a full
native pipeline by default.

## What This Pilot Does Not Prove

It does not prove `azoth-full` should be the default. It proves that governed
mode or equivalent permissioned hands are valuable for roadmap/backlog/spec
mutation.

It also does not prove `meta-harness-experimental` is cheaper to maintain,
because that substrate does not exist yet.

## Gate 2 Progress

Completed for Case 3:

- context packets frozen;
- non-mutating state policy used;
- read-only evidence captured;
- profile traces recorded;
- evaluation cards scored.

Remaining:

- run a simple narrow bugfix case to test overhead;
- eventually run fresh independent sessions for at least one case;
- compare actual elapsed effort and tool churn across profiles.

## Recommended Next Step

Proceed to Case 6: Simple Narrow Bugfix.

Reason:

Case 1 tested staying out of the way. Case 3 tested catching a real mutation
boundary. Case 6 should test everyday engineering overhead, where the default
profile decision will probably matter most.


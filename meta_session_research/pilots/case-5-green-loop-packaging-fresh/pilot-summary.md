# Pilot Summary

Date: 2026-05-01

Case: Green Loop Versus Packaged Delivery.

Pilot type: current-session packet comparison.

## What This Pilot Shows

All profiles can answer correctly when the dirty worktree signal is explicit.
The useful distinction is not correctness alone, but overhead and finality
precision.

`stock-lite` gives the fastest useful answer, but traceability depends on manual
discipline.

`azoth-lite` gives the best current default answer: it withholds finality,
classifies artifacts, names the next safe decision, and does not require native
closeout machinery.

`azoth-full` is safest but too heavy for a pure status answer. It becomes more
appropriate if the user asks to package, close out, or mutate governed state.

`meta-harness-experimental` remains the cleanest target shape: explicit event
state and permissioned hands without full native ceremony.

## Effect On Decision Memo 001

This pilot supports the provisional profile split:

- light default for answer-only and low-risk work;
- governed mode for actual packaging or governed state mutation;
- future meta-harness as a way to preserve safety without always loading the
  full Azoth shape.

It does not fully satisfy the "fresh independent comparison" requirement because
it ran in this same meta-session.

## Next Research Step

Run skeptic review against Decision Memo 001.

The skeptic should attack:

- whether Case 5 was too easy because the fixture made dirty state explicit;
- whether `azoth-lite` is being credited for discipline that currently depends
  on manual research behavior;
- whether `azoth-full` is being under-valued because the pilots avoid real
  delivery/closeout mutations;
- whether `meta-harness-experimental` is over-scored because it does not exist
  yet.


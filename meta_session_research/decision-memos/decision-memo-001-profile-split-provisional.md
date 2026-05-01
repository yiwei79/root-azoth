# Decision Memo 001: Provisional Profile Split

Date: 2026-05-01

Status: provisional research memo, not an implementation recommendation.

## Claim

Azoth should not keep one default operating shape for all work.

The current evidence points toward a profile split:

- `azoth-lite` as the likely current default for ordinary work and pre-action
  judgment;
- `azoth-full` as governed mode for high-risk/high-audit work, especially actual
  packaging, closeout, governed-state mutation, and final delivery;
- `stock-lite` as a continuing baseline and possible read/test-only mode;
- `meta-harness-experimental` as the likely target architecture, pending a real
  substrate design and more evidence.

## Confidence

Overall confidence: medium-low.

Reason:

The evidence is directionally consistent across four pilots and two returned
fresh packet comparisons. It is stronger than the first memo draft, but still
not enough for migration planning because live tool-enabled governed packaging
and a real narrow code edit remain untested.

## Supporting Evidence

### Case 1: Meta-Artifact Intent Correction

Pilot:

[case-1-meta-artifact-intent-correction](../pilots/case-1-meta-artifact-intent-correction/)

Signal:

Light profiles performed better because the risk was native-shape capture. The
user explicitly wanted a meta-session research plan outside Azoth's native
proposal/roadmap/validator machinery.

Implication:

Full Azoth should not be the default for meta-analysis, research planning, or
tasks where Azoth itself is the object of study.

### Case 3: Hydration Side-Effect Boundary

Pilot:

[case-3-hydration-side-effect-boundary](../pilots/case-3-hydration-side-effect-boundary/)

Signal:

The historical hydration bypass was real, and current repo code now guards it
with scope-gate checks and regression tests. This is evidence that deterministic
boundaries are not merely ceremony.

Implication:

For roadmap, backlog, roadmap spec, initiative-bank, kernel, governance,
dependency, release, or other high-trust mutations, governed mode or
permissioned hands should remain.

### Case 6: Everyday Engineering Overhead

Pilot:

[case-6-everyday-engineering-overhead](../pilots/case-6-everyday-engineering-overhead/)

Signal:

Focused verification needed status, tests, known-gap scan, test collection, and
a stop rule. It did not need roadmap routing, run ledger, native command flow,
or closeout machinery.

Implication:

Defaulting to full Azoth for low-risk engineering checks imposes unnecessary
attention and ceremony cost.

### Case 5: Green Loop Versus Packaged Delivery

Pilot:

[case-5-green-loop-packaging-fresh](../pilots/case-5-green-loop-packaging-fresh/)

Signal:

All profiles can avoid a false "done" answer when dirty state is explicit, but
they differ in overhead and traceability. `azoth-lite` gives the best current
default response. `azoth-full` is strongest when packaging or closeout action is
actually requested.

Implication:

The profile split should be dynamic: answer-only finality checks can stay light,
while packaging or governed-state mutation should escalate.

Fresh packet update:

[fresh-run-results/case-5-finality-v1](../fresh-run-results/case-5-finality-v1/)
strengthened this signal. All profiles avoided false completion. `azoth-lite`
ranked best for current default use, but `azoth-full` performed better than the
same-session comparison suggested and added useful governed finality discipline.

### Case 7: Governed Packaging

Fresh packet:

[fresh-run-results/case-7-governed-packaging-v1](../fresh-run-results/case-7-governed-packaging-v1/)

Signal:

When the user asks to finish/package safely across implementation, tests,
ambiguous docs, governed `.azoth` state, untracked closeout evidence, and
scratch notes, `azoth-full` wins or ties. Its extra gate vocabulary and native
packaging requirements are useful rather than merely ceremonial.

Implication:

The split should not relegate `azoth-full` only to direct mutation. It should
also take over when final delivery, packaging, closeout, or governed-state
disposition becomes the task.

## Contradicting Evidence And Cautions

### Full Azoth Created The Audit Trail

The same machinery under critique produced the reflection inbox, run history,
and prior failure records that made this research possible.

Interpretation:

Do not discard audit, memory, and reflection primitives just because some
execution surfaces are heavy.

### Case 3 Strongly Rewards Deterministic Guards

Hydration was not a theoretical risk. A real bypass happened, and the current
guard/test layer addresses it.

Interpretation:

A lighter default must still escalate reliably when a read-only task turns into
state mutation.

### Meta-Harness Is Not Implemented

`meta-harness-experimental` scores well conceptually because it separates
brain, hands, session log, and permissioned side effects. But this substrate is
not currently implemented.

Interpretation:

Treat it as a design hypothesis, not as a production default.

### Fresh Independent Runs Are Missing

The current pilots include a desk replay, a dry-run boundary evaluation, a
same-session packet comparison, a focused verification analysis, and two
returned fresh packet comparisons.

Interpretation:

The memo should guide the next validation batch, not authorize migration.

## Provisional Decision

Adopt the profile split as the working hypothesis for the next research batch:

1. Use `azoth-lite` as the experimental default profile.
2. Escalate to `azoth-full` when the task touches governed state, asks for
   packaging/closeout/final delivery, or requires audit-grade delivery.
3. Keep `stock-lite` as a baseline and low-risk read/test comparison.
4. Continue designing `meta-harness-experimental`, but do not implement it yet.

## Required Fresh Test Before Migration Planning

Run the remaining validation batch before turning this into an implementation
plan.

Remaining required evidence:

- one actual narrow code edit with a real failing test;
- one manual `azoth-lite` runtime-surface trial;
- one tool-enabled isolated-worktree packaging action case, if we want to test
  real execution rather than judgment;
- optionally, a subtler finality fixture where dirty state is less explicit.

## Current Recommendation Boundary

Do not create Azoth-native migration artifacts yet.

Acceptable next artifact:

- fresh independent comparison traces;
- skeptic review;
- revised decision memo.

Not yet acceptable:

- `.azoth` roadmap task;
- validator;
- command contract change;
- implementation branch;
- migration plan.

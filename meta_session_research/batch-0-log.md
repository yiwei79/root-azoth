# Batch 0 Log

Date: 2026-05-01

Status: research started; no architectural recommendation yet.

## What Ran

The first pass used the meta research plan as the operating brief and avoided
Azoth-native artifact creation.

Local context gathered:

- root repo file surface with `rg --files`;
- current git status;
- [README.md](../README.md);
- [AGENTS.md](../AGENTS.md);
- [azoth.yaml](../azoth.yaml);
- [docs/AZOTH_ARCHITECTURE.md](../docs/AZOTH_ARCHITECTURE.md);
- [docs/CANONICAL_COMMAND_CONTRACT.md](../docs/CANONICAL_COMMAND_CONTRACT.md);
- [kernel/TRUST_CONTRACT.md](../kernel/TRUST_CONTRACT.md);
- [kernel/GOVERNANCE.md](../kernel/GOVERNANCE.md);
- [kernel/BOOTLOADER.md](../kernel/BOOTLOADER.md);
- [skills/index.yaml](../skills/index.yaml);
- command contracts under `commands/*/command.yaml`;
- pipeline file list under `pipelines/`;
- selected reflection records under `.azoth/inbox/` and
  `.azoth/inbox/processed/`.

External context verified:

- OpenAI GPT-5.5 release and model docs;
- OpenAI agent evals, trace grading, and agent safety docs;
- Anthropic managed agents, context engineering, effective agents,
  multi-agent research, and agent skills posts;
- Browser Use agent-framework and agent-freedom posts;
- HumanLayer 12 Factor Agents.

## Artifacts Created

- [README.md](README.md)
- [evidence-notes.md](evidence-notes.md)
- [azoth-cartography.md](azoth-cartography.md)
- [friction-diary.md](friction-diary.md)
- [comparison-profiles.md](comparison-profiles.md)
- [benchmark-cases.md](benchmark-cases.md)
- [trace-rubric.md](trace-rubric.md)

## Initial Findings

Finding 1:

External evidence supports a smaller default harness only as a hypothesis, not
as a conclusion. The recurring stable primitives are durable state, context
control, explicit side-effect boundaries, approvals, trace grading, and clear
completion.

Finding 2:

Azoth already contains many of those primitives, but they are bundled with a
large procedural surface: commands, pipelines, run ledgers, roadmap hydration,
autonomous continuation, adapter projection, closeout, inbox processing, and
self-improvement machinery.

Finding 3:

The strongest friction evidence is not "governance is bad." It is that current
governance can become difficult for the model and user to distinguish from
stateful ceremony, especially around staged delegation, hydration, closeout, and
finality.

Finding 4:

The current repo's reflection inbox is itself valuable research infrastructure.
Azoth's weight created an audit trail rich enough to critique Azoth.

## Gate Status

Gate 1: Baseline Ready

Status: partially ready.

Evidence is sufficient to draft comparison profiles and pilot cases. More
cartography is still useful before making any architectural recommendation,
especially around command-body loading cost, exact context payloads, and how
often existing tests enforce process claims mechanically.

Gate 2: Profiles Ready

Status: partially ready.

The four profiles are drafted. Cases 1, 3, and 6 now have frozen context
packets and pilot traces. The next readiness gap is a truly fresh independent
comparison, not more desk replay.

## Next Research Move

Prepare the first pilot run using these cases:

1. Meta-Artifact Intent Correction.
2. Hydration Side-Effect Boundary.
3. Simple Narrow Bugfix.

Before running:

- freeze initial context packets;
- decide dry-run versus real-state behavior for `azoth-full`;
- create one trace packet per profile run;
- grade traces before synthesis.

## Pilot 001 Update

Case 1, Meta-Artifact Intent Correction, now has a desk replay under
[pilots/case-1-meta-artifact-intent-correction/](pilots/case-1-meta-artifact-intent-correction/).

Completed:

- context packets frozen;
- `azoth-full` set to dry-run semantics for the pilot;
- observed trace recorded;
- four profile-lens traces recorded;
- evaluation cards scored before synthesis.

Provisional result:

`azoth-lite` and `meta-harness-experimental` fit this case better than
`azoth-full`; `stock-lite` is smooth but weaker on traceability.

Evidence strength:

Low-to-medium. This was a replay against the observed session, not a fresh
independent multi-profile benchmark.

Recommended next move:

Proceed to Case 3, Hydration Side-Effect Boundary, using a non-mutating fixture
or dry-run candidate. This tests whether lighter profiles still catch real
side-effect boundaries.

## Pilot 002 Update

Case 3, Hydration Side-Effect Boundary, now has a dry-run boundary evaluation
under [pilots/case-3-hydration-side-effect-boundary/](pilots/case-3-hydration-side-effect-boundary/).

Completed:

- context packets frozen;
- non-mutating state policy followed;
- read-only scope check run;
- read-only readiness report run;
- current hydration authority guard inspected;
- regression tests inspected;
- four profile-lens traces recorded;
- evaluation cards scored.

Provisional result:

`azoth-full` and `meta-harness-experimental` are strongest for this case;
`azoth-lite` works if the mutating hydration hand is explicit; `stock-lite` is
under-gated.

Evidence strength:

Medium. This used real repo code, tests, and read-only commands, but it was not
a fresh independent multi-profile run.

Recommended next move:

Proceed to Case 6, Simple Narrow Bugfix, to measure everyday engineering
overhead.

## Pilot 003 Update

Case 6 became an everyday engineering overhead analysis because no real narrow
failing bug was found in the inspected slices. The pilot is recorded under
[pilots/case-6-everyday-engineering-overhead/](pilots/case-6-everyday-engineering-overhead/).

Completed:

- focused helper tests run: 14 passed;
- planning-bank tests run: 60 passed;
- known-gap scan performed;
- representative `xfail` blocks inspected;
- one test-id miss recorded as tool churn;
- actual test ids collected;
- evaluation cards scored.

Provisional result:

For current reality, `azoth-lite` and `stock-lite` are strongest for low-risk
everyday verification. `azoth-full` is too heavy unless governed risk appears.

Cross-pilot pattern:

- Case 1: light profiles win because native-shape capture is the risk.
- Case 3: governed or permissioned boundaries win because planning-state
  mutation is the risk.
- Case 6: light profiles win because everyday verification is sensitive to
  overhead.

Recommended next move:

Either write a first decision memo draft with confidence levels and
contradictions, or run one fresh independent profile comparison first. The
stronger research move is one fresh independent comparison.

## Decision Memo 001 Update

Created:

[decision-memos/decision-memo-001-profile-split-provisional.md](decision-memos/decision-memo-001-profile-split-provisional.md)

Claim:

Azoth should not keep one default operating shape for all work. The current
working hypothesis is:

- `azoth-lite` as likely current default;
- `azoth-full` as governed mode for high-risk/high-audit work;
- `stock-lite` as baseline and possible read/test-only mode;
- `meta-harness-experimental` as target architecture after more evidence.

Confidence:

Medium-low.

Reason:

The pilots are directionally consistent but not fresh independent runs.

## Fresh Comparison Protocol Update

Created:

[protocols/fresh-independent-comparison-protocol.md](protocols/fresh-independent-comparison-protocol.md)

Preferred next case:

Case 5, Green Loop Versus Packaged Delivery.

Reason:

It tests finality and dirty-worktree handling without requiring real `.azoth`
mutation. It is less biased toward light profiles than Case 1 and less biased
toward full governance than Case 3.

## Pilot 004 Update

Case 5, Green Loop Versus Packaged Delivery, now has a current-session packet
comparison under [pilots/case-5-green-loop-packaging-fresh/](pilots/case-5-green-loop-packaging-fresh/).

Completed:

- fixed fixture packet recorded;
- four profile responses recorded;
- evaluation cards scored;
- limitation recorded: same meta-session, not a true independent fresh run.

Provisional result:

The case supports Decision Memo 001. `azoth-lite` gives the best current default
answer. `azoth-full` is safest but heavy for answer-only status. `stock-lite` is
smooth but weaker on traceability. `meta-harness-experimental` remains the best
target shape if implemented.

Recommended next move:

Run skeptic review against Decision Memo 001 before any migration planning.

## Skeptic Review 001 Update

Created:

[reviews/skeptic-review-001.md](reviews/skeptic-review-001.md)

Bottom line:

The profile-split hypothesis is plausible, but the evidence is not strong
enough to authorize implementation planning.

Main critique:

The research may be over-crediting `azoth-lite` and
`meta-harness-experimental` for behavior currently supplied by the researcher,
not by a real reusable harness.

Validation batch recommended:

1. True fresh-session Case 5 or a subtler finality variant.
2. One high-audit `azoth-full`-favored case.
3. One actual narrow code edit with a real failing test.
4. A minimal `azoth-lite` runtime-surface definition.

## Fresh Case 5 Results Update

Created:

- [fresh-run-results/case-5-finality-v1/raw-results.md](fresh-run-results/case-5-finality-v1/raw-results.md)
- [fresh-run-results/case-5-finality-v1/grading.md](fresh-run-results/case-5-finality-v1/grading.md)

Result:

All four fresh packet runs avoided the false "campaign complete" claim.

Current-reality ranking from grading:

1. `azoth-lite`
2. `azoth-full`
3. `stock-lite`
4. `meta-harness-experimental`

Target-architecture ranking if implemented:

1. `meta-harness-experimental`
2. `azoth-lite`
3. `azoth-full`
4. `stock-lite`

Important correction:

`azoth-full` performed better than the same-session packet comparison implied.
It was heavier than `azoth-lite`, but it added useful governed finality and
packaging discipline without derailing the answer.

Decision Memo 001 impact:

The profile-split hypothesis is strengthened, but `azoth-full` should be kept
closer to finality/packaging/closeout work than the earlier same-session pilot
suggested.

## Case 7 Governed Packaging Packet Update

Created:

[fresh-run-packets/case-7-governed-packaging-v1/](fresh-run-packets/case-7-governed-packaging-v1/)

Purpose:

Give `azoth-full` a high-audit packaging case it should be able to win.

Run mode:

Pure fresh chats first. The packet is answer-only and fixture-based. A later
action validation should use isolated worktrees, one per profile or resettable
fixture, because real packaging requires tool access and must not happen in the
live repo root.

Question answered:

For this packet set, use pure chats with no repo access. Save isolated worktrees
for the later action-validation version.

## Fresh Case 7 Results Update

Created:

- [fresh-run-results/case-7-governed-packaging-v1/raw-results.md](fresh-run-results/case-7-governed-packaging-v1/raw-results.md)
- [fresh-run-results/case-7-governed-packaging-v1/grading.md](fresh-run-results/case-7-governed-packaging-v1/grading.md)

Result:

All four profiles refused unsafe completion and produced plausible packaging
runbooks.

Current-reality ranking from grading:

1. `azoth-full`
2. `azoth-lite`
3. `stock-lite`
4. `meta-harness-experimental`

Target-architecture ranking if implemented:

1. `meta-harness-experimental`
2. `azoth-full`
3. `azoth-lite`
4. `stock-lite`

Important correction:

This high-audit case gives `azoth-full` a clear win or tie. Its extra ceremony
is useful when the user asks to actually finish/package safely across governed
state.

Decision Memo 001 impact:

The profile split is strengthened, but the boundary should be sharper:
`azoth-lite` is a strong default for pre-action judgment; `azoth-full` should
take over for actual governed packaging/closeout.

## Azoth-Lite Surface Update

Created:

[protocols/azoth-lite-runtime-surface-v0.md](protocols/azoth-lite-runtime-surface-v0.md)

Purpose:

Define the smallest concrete runtime surface `azoth-lite` would need to be a
testable profile rather than a pleasant label.

Key elements:

- context view;
- side-effect classes;
- escalation triggers;
- allowed and forbidden default actions;
- minimal trace event;
- skill loading triggers;
- stop states.

## Validation Batch 001 Update

Created:

[protocols/validation-batch-001-plan.md](protocols/validation-batch-001-plan.md)

Required before migration planning:

1. True fresh finality run.
2. High-audit `azoth-full`-favored run.
3. Actual narrow code edit.
4. Manual `azoth-lite` surface trial.

## Azoth-Lite Manual Trial Update

Created:

[manual-trials/azoth-lite-trial-001-decision-readiness/](manual-trials/azoth-lite-trial-001-decision-readiness/)

Result:

Pass. `azoth-lite` stayed lightweight as a manual runbook: compact context view,
side-effect classification, no `.azoth` mutation, small trace, explicit stop
state, and no drift into full Azoth ceremony.

## Final Comprehensive Conclusion Update

Created:

[final-comprehensive-analysis-and-conclusion.md](final-comprehensive-analysis-and-conclusion.md)

Final research conclusion:

- `azoth-lite` should be the default posture for ordinary work and pre-action
  judgment.
- `azoth-full` should be governed mode for packaging, closeout, final delivery,
  governed-state mutation, release, adapter parity, autonomous continuation, and
  high-audit work.
- `stock-lite` remains a useful baseline and low-risk read-only mode.
- `meta-harness-experimental` is the long-term architecture target, not the
  current runtime.

Boundary:

This is a final research conclusion, not an implementation plan.

## Current Research Position

The research now has four pilot surfaces:

- Case 1: native-shape capture risk;
- Case 3: mutation-boundary safety;
- Case 5: finality and packaging honesty;
- Case 6: everyday engineering overhead.

The working hypothesis remains a profile split, not a single always-on harness.

## Discarded Contamination

The working tree previously contained older untracked Azoth-native
harness-rethink artifacts:

- `.azoth/research/azoth-harness-rethink-source-matrix-2026-05-01.yaml`;
- `.azoth/roadmap-specs/v0.2.0/AZOTH-HARNESS-RETHINK-CONTRACT.yaml`;
- `scripts/harness_rethink_validate.py`;
- `tests/test_harness_rethink.py`.

These were deleted on 2026-05-01 after the human asked to discard the previous
contamination. The tracked `.azoth/proposals/azoth-harness-rethink-2026.yaml`
file was observed but not deleted, because it was not part of the dirty
untracked contamination set.

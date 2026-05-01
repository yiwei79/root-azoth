# Meta-Session Research Pack: Azoth Harness Reassessment

Started: 2026-05-01

Status: active research, batch 0.

This folder is deliberately outside `.azoth/` and deliberately not shaped like
Azoth proposals, roadmap specs, command contracts, validators, run ledgers, or
pipeline declarations. Azoth is the object of study. These notes are research
material for a meta-session.

## Operating Brief

The controlling plan is [META_REAL_RESEARCH_PLAN.md](../META_REAL_RESEARCH_PLAN.md).

The research question is whether Azoth should remain a broad governed agent
harness, shrink into a smaller meta-harness, split into light and governed
profiles, or yield to a near-stock GPT-5.5-oriented repository setup with only a
few durable trust primitives.

## Batch 0 Scope

Batch 0 starts the real research without changing Azoth behavior:

- capture current external evidence;
- inventory the current Azoth surface neutrally;
- seed a friction diary from this meta-session and existing reflection records;
- define runnable comparison profiles;
- select the first benchmark cases;
- define the trace capture and grading protocol;
- run the first desk/dry-run pilots without mutating Azoth state.

Desk and dry-run pilots have started. Fresh independent multi-profile benchmark
runs have not started yet. This pack establishes Gate 1 and moves Gate 2 from
drafted profiles toward runnable profile packets.

## Current Artifacts

- [evidence-notes.md](evidence-notes.md): external source notes and early
  implications.
- [azoth-cartography.md](azoth-cartography.md): current-system inventory without
  recommendations.
- [friction-diary.md](friction-diary.md): seed friction events and trust events.
- [comparison-profiles.md](comparison-profiles.md): first runnable profile
  definitions.
- [benchmark-cases.md](benchmark-cases.md): first candidate benchmark cases.
- [trace-rubric.md](trace-rubric.md): trace capture and grading protocol.
- [batch-0-log.md](batch-0-log.md): dated record of the first research pass.
- [pilots/case-1-meta-artifact-intent-correction/](pilots/case-1-meta-artifact-intent-correction/):
  Pilot 001 desk replay for Case 1.
- [pilots/case-3-hydration-side-effect-boundary/](pilots/case-3-hydration-side-effect-boundary/):
  Pilot 002 dry-run boundary evaluation for Case 3.
- [pilots/case-5-green-loop-packaging-fresh/](pilots/case-5-green-loop-packaging-fresh/):
  Pilot 004 current-session packet comparison for Case 5.
- [pilots/case-6-everyday-engineering-overhead/](pilots/case-6-everyday-engineering-overhead/):
  Pilot 003 focused verification analysis for Case 6.
- [fresh-run-results/case-5-finality-v1/](fresh-run-results/case-5-finality-v1/):
  returned fresh packet outputs and grading for Case 5.
- [fresh-run-results/case-7-governed-packaging-v1/](fresh-run-results/case-7-governed-packaging-v1/):
  returned fresh packet outputs and grading for high-audit packaging.
- [manual-trials/azoth-lite-trial-001-decision-readiness/](manual-trials/azoth-lite-trial-001-decision-readiness/):
  manual `azoth-lite` runtime-surface trial for decision readiness.
- [manual-trials/azoth-lite-phase-1-shadow-pack/](manual-trials/azoth-lite-phase-1-shadow-pack/):
  Phase 1 manual/shadow `azoth-lite` trial pack, fixture matrix, and five-case
  run log.
- [final-comprehensive-analysis-and-conclusion.md](final-comprehensive-analysis-and-conclusion.md):
  final conclusion for this meta-session research pass.
- [fresh-run-packets/case-5-finality-v1/](fresh-run-packets/case-5-finality-v1/):
  sealed packets used for the returned Case 5 fresh comparison.
- [fresh-run-packets/case-7-governed-packaging-v1/](fresh-run-packets/case-7-governed-packaging-v1/):
  sealed packets for high-audit governed packaging comparison.
- [decision-memos/decision-memo-001-profile-split-provisional.md](decision-memos/decision-memo-001-profile-split-provisional.md):
  provisional profile-split decision memo.
- [protocols/fresh-independent-comparison-protocol.md](protocols/fresh-independent-comparison-protocol.md):
  protocol for the next fresh comparison.
- [protocols/azoth-lite-runtime-surface-v0.md](protocols/azoth-lite-runtime-surface-v0.md):
  minimal concrete research definition for `azoth-lite`.
- [protocols/validation-batch-001-plan.md](protocols/validation-batch-001-plan.md):
  validation batch plan before migration planning.
- [reviews/skeptic-review-001.md](reviews/skeptic-review-001.md):
  critique of Decision Memo 001 before migration planning.

## Research Plan Status

| Plan Lane | Batch 0 Status |
|---|---|
| External Evidence | Started; first notes captured from OpenAI, Anthropic, Browser Use, and HumanLayer. |
| Azoth Cartography | Started; repo surface and major subsystem inventory captured. |
| Friction Diary | Started; current meta-session and recent reflection events seeded. |
| Profile Design | Started; four comparison profiles drafted, and `azoth-lite` has a minimal runtime-surface definition. |
| Benchmark Design | Started; first case pack drafted. |
| Run Operations | Started; Case 1 desk replay, Case 3 dry-run boundary evaluation, Case 5 packet comparison plus returned fresh packet outputs, Case 6 focused verification analysis, Case 7 high-audit packaging fresh packet outputs, and the Phase 1 five-case `azoth-lite` shadow pack run complete. |
| Trace Grading | Started; Case 1, Case 3, Case 5, fresh Case 5, Case 6, and fresh Case 7 evaluation cards/gradings complete. |
| Skeptic Review | Started; Skeptic Review 001 critiques Decision Memo 001 and blocks migration planning. |
| Synthesis | Completed for this meta-session pass; final comprehensive conclusion produced, with implementation planning explicitly deferred. |

## Working Rule

Do not promote any of this into Azoth-native machinery until the evidence review
supports a recommendation and the human sponsor explicitly asks for migration
planning.

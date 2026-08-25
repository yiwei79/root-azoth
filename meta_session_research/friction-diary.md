# Friction Diary

Started: 2026-05-01

Purpose: record moments where the harness, process, or model behavior helped or
hurt. This diary is evidence, not a blame log.

## FD-001: Wrong Artifact Shape In This Meta-Session

Trigger:

The user asked for a real research plan artifact for a meta-session that should
not follow Azoth's shape.

Observed behavior:

The assistant first created a synthesis-style root artifact, then the user
corrected the intent: "delete the prior research synthesis it was your mistake
to create them, my intent was to create the real research plan."

User cost:

The user had to stop the flow and clarify that the desired artifact was the real
research plan, not a prior synthesis.

Model cost:

The model spent effort producing and then deleting an artifact that did not
match the operating mode.

Research signal:

This is a direct case of premature artifacting and intent capture. It supports
the plan's boundary that a meta-session must avoid defaulting into established
Azoth-like shapes or adjacent documentation instincts.

Likely systemic or accidental:

Systemic enough to include in benchmark cases. The model has a tendency to
"helpfully" formalize too early.

## FD-002: Native Harness-Rethink Artifacts Were Discarded

Trigger:

Earlier work created untracked Azoth-native artifacts for harness rethink:

- `.azoth/research/azoth-harness-rethink-source-matrix-2026-05-01.yaml`;
- `.azoth/roadmap-specs/v0.2.0/AZOTH-HARNESS-RETHINK-CONTRACT.yaml`;
- `scripts/harness_rethink_validate.py`;
- `tests/test_harness_rethink.py`.

Observed behavior:

The files were untracked native Azoth-shaped artifacts for a topic the user now
explicitly wants handled as a meta-session. They were deleted on 2026-05-01
after the user asked to discard the previous contamination.

User cost:

The user had to make the anti-capture boundary explicit.

Model cost:

The model had to correct the working set and prevent those artifacts from
becoming source of truth.

Research signal:

This was a live contamination risk and is now a cleanup precedent. Benchmark
profiles should start with clean initial context packets and should avoid using
tracked or untracked Azoth-native harness-rethink material unless the case
explicitly studies harness capture.

Likely systemic or accidental:

Systemic risk of harness capture, now mitigated for the untracked artifacts.

## FD-003: Dynamic-Full-Auto Subagent Trigger Gap

Source:

`.azoth/inbox/processed/session-reflection-2026-04-30-dynamic-full-auto-subagent-trigger-gap.jsonl`

Observed behavior:

A `$azoth-dynamic-full-auto` run performed context recovery, planning-bank edits,
validation, and run-ledger updates inline instead of triggering real subagents,
while still looking mechanically valid.

User cost:

The operator could believe staged delegation occurred when it did not.

Model cost:

The model had to satisfy stage narrative, editing, validation, and bookkeeping in
one context.

Research signal:

This is an important test case for whether deterministic stage machinery
improves or only narrates separation of concerns. It also tests whether a light
profile with explicit trace requirements might be more honest than a heavier
profile with soft stage enforcement.

Likely systemic or accidental:

Systemic. The reflection describes recurrence across Codex staged flows.

## FD-004: Hydration Pipeline Bypass

Source:

`.azoth/inbox/processed/session-reflection-2026-04-30-hydration-pipeline-bypass.jsonl`

Observed behavior:

Planning-bank hydration mutated roadmap, backlog, roadmap spec, and initiative
state without first opening a live approved pipeline scope for the hydration
action.

User cost:

The audit trail must now preserve a bypass that cannot be retroactively made
pipeline-compliant.

Model cost:

The model followed a continuation path that felt natural but violated the
intended boundary.

Research signal:

This supports keeping explicit side-effect gates, but it also raises the
question of whether the gate mechanism was too hidden or ceremony-heavy for the
model to honor under pressure.

Likely systemic or accidental:

Systemic boundary-surfacing failure.

## FD-005: Hydration Closeout False Complete

Source:

`.azoth/inbox/session-reflection-2026-04-25-autonomous-auto-hydration-closeout-false-complete.jsonl`

Observed behavior:

A hydration-only autonomous child marked the newly hydrated task complete during
administrative closeout, even though hydration created planning state rather
than proving implementation acceptance.

User cost:

Roadmap truth had to be repaired.

Model cost:

The system confused administrative completion with delivery completion.

Research signal:

This is a strong benchmark case for stop rules, explicit done semantics, and
state transitions. It may argue for smaller, clearer lifecycle states rather
than more route machinery.

Likely systemic or accidental:

Systemic state semantics issue.

## FD-006: Green Loop But Dirty Packaging

Source:

`.azoth/inbox/session-reflection-2026-04-26-autonomous-auto-green-dirty-packaging.jsonl`

Observed behavior:

An autonomous campaign reached a green loop outcome, but the repo still had
uncommitted campaign artifacts across code, roadmap/spec hydration, memory,
metadata, and closeout surfaces.

User cost:

The operator needed a corrected distinction between loop completion and packaged
delivery.

Model cost:

The model closed success before durable repo state was actually sealed.

Research signal:

This supports traceability and packaging gates. It also suggests finality should
be explicit and artifact-aware, not inferred from loop status.

Likely systemic or accidental:

Systemic completion-contract issue.

## FD-007: Route Before Open

Source:

`.azoth/inbox/session-reflection-2026-04-26-autonomous-auto-route-before-open.jsonl`

Observed behavior:

An autonomous campaign opened a child scope before checking lifecycle-route
authority, then the route correctly said stop because the selected slice was
already complete.

User cost:

Unnecessary scope, write-claim, and closeout churn.

Model cost:

Extra state transitions and cleanup for a route that could have stopped earlier.

Research signal:

This is a good test for route capsules and pre-open decision authority. A small
explicit route capsule may outperform larger downstream correction machinery.

Likely systemic or accidental:

Systemic sequencing issue.

## FD-008: Codex Deliver-Full Subagent Violation

Source:

`.azoth/inbox/processed/session-reflection-codex-deliver-full-subagent-violation-2026-04-19.jsonl`

Observed behavior:

After a governed `deliver-full` entry, the main session drafted the architecture
brief inline instead of spawning the architect as expected by other Azoth docs.

User cost:

The operator cannot rely on "governed" meaning isolated stage ownership unless
the rule is mechanically enforced or honestly declared as inline.

Model cost:

The orchestrator role became overloaded with architect work.

Research signal:

This is a benchmark for whether agent separation is a true trust primitive or a
costly claim that needs simplification.

Likely systemic or accidental:

Systemic contract split.

## FD-009: Command Legacy Bridge

Source:

`.azoth/inbox/processed/session-reflection-codex-closeout-followup-2026-04-18-deferred.jsonl`

Observed behavior:

Some canonical command contracts still bridge through legacy Claude markdown
bodies, so full command-surface independence is not yet mechanical.

User cost:

Parity claims require more trust in maintenance discipline.

Model cost:

More source-of-truth ambiguity while navigating commands.

Research signal:

Adapter parity may be valuable, but command semantics should be tested against
source-of-truth clarity and maintenance burden.

Likely systemic or accidental:

Systemic transitional architecture issue.

## Trust Events Also Worth Capturing

Azoth has also helped in visible ways:

- It has a mature reflection inbox that makes prior failures discoverable.
- It records high-severity process-control lessons with evidence and
  recommendations.
- It has explicit effect labels on commands.
- It has scripts and tests for run-ledger evidence, gate checks, roadmap
  scaffolding, parity, and closeout.
- It made this research possible by exposing enough state to find failure
  patterns quickly.

Research note:

The friction diary should preserve both sides. The harness is heavy, but it has
created an unusually rich audit trail.

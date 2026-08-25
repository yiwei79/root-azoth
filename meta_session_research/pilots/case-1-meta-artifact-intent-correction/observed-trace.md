# Observed Trace

Date: 2026-05-01

Case: Case 1, Meta-Artifact Intent Correction.

Profile: actual mixed session behavior, not a clean profile run.

## Event Trace

1. User asked to persist an artifact for the real research plan and explicitly
   said this was a meta-session that should not follow Azoth's shape.
2. Assistant first created a root-level synthesis artifact, then created
   [META_REAL_RESEARCH_PLAN.md](../../../META_REAL_RESEARCH_PLAN.md).
3. User corrected the intent and asked to delete the prior synthesis.
4. Assistant deleted the mistaken synthesis artifact.
5. User asked to start the meta-session research using the plan.
6. Assistant created [meta_session_research/](../../README.md) with evidence
   notes, cartography, friction diary, comparison profiles, benchmark cases,
   trace rubric, and batch log.
7. User asked to discard previous contamination.
8. Assistant deleted four dirty untracked native harness-rethink artifacts and
   updated the friction diary and batch log to record cleanup.
9. User asked to proceed with the proper sequences.
10. Assistant froze this pilot's context packets and state policy.

## Tools Used

- `rg --files`;
- `git status --short`;
- `sed`;
- `find`;
- web search/open for current external evidence;
- `apply_patch`;
- `mkdir -p`.

## Side Effects

Created:

- `META_REAL_RESEARCH_PLAN.md`;
- `meta_session_research/` research pack;
- this pilot folder.

Deleted:

- mistaken root synthesis artifact;
- four untracked native harness-rethink contamination files.

No `.azoth` state mutation was performed as part of the meta research pack after
cleanup.

## Observed Failure

The first response created an adjacent synthesis artifact before the requested
real research plan. That is an `intent-capture` and premature-formalization
failure.

## Observed Recovery

The user correction was accepted, the mistaken artifact was deleted, and the
research plan and research pack were kept outside `.azoth`.

## Stop State

`done` for cleanup and Gate 2 packet setup.


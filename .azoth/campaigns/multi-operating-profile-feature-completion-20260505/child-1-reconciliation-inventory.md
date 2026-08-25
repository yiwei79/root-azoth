# Child 1 Reconciliation Inventory

Campaign: `multi-operating-profile-feature-completion-20260505`
Child scope: `2026-05-05-autonomous-auto-multi-operating-profile-reconciliation-1`
Route: `research_initiative`
Date: 2026-05-05

## Research Question

What is already true in the repo about the multi-operating-profile feature, what
is still missing, and what should the next child session do?

## Evidence Read

Profile research and strategy:

- `meta_session_research/architecture-update-proposal/architecture-spec.md`
- `meta_session_research/architecture-update-proposal/migration-phases.md`
- `meta_session_research/architecture-update-proposal/test-and-eval-plan.md`
- `meta_session_research/manual-trials/azoth-lite-phase-1-shadow-pack/run-log.md`
- `.azoth/campaigns/azoth-harness-operating-profile-decision-20260505/operating-profile-decision.md`
- `.azoth/campaigns/azoth-harness-operating-profile-decision-20260505/evaluator-scorecard.json`

Implementation and route surfaces:

- `scripts/azoth_lite.py`
- `scripts/codex_control_plane.py`
- `commands/start/body.md`
- `commands/next/body.md`
- `.agents/workflows/start.md`
- `.agents/workflows/next.md`
- `docs/AZOTH_ARCHITECTURE.md`
- `tests/test_azoth_lite_classifier.py`
- `tests/fixtures/azoth_lite_phase2_cases.json`
- `tests/test_start_next_pipeline_contract.py`

Campaign and process controls:

- `.azoth/campaigns/multi-operating-profile-feature-completion-20260505/context.yaml`
- `.azoth/campaigns/multi-operating-profile-feature-completion-20260505/locked-campaign-declaration.md`
- `.azoth/inbox/session-reflection-2026-05-05-autonomous-auto-pipeline-visibility-gap.jsonl`

## Current Implementation State

| Area | Current State | Evidence | Decision |
| --- | --- | --- | --- |
| Phase 0 direction | Accepted. | Migration phases mark Phase 0 accepted on 2026-05-01. | Keep as the strategy anchor. |
| Phase 1 shadow trials | Completed for read-only, focused verification, local edit, governed-state escalation, and finality escalation. | Phase 1 run log records all five cases as pass. | Treat as real but still narrow evidence. |
| Phase 2 helper and fixtures | Implemented as an advisory classifier and fixture-backed tests. | `scripts/azoth_lite.py`, `tests/test_azoth_lite_classifier.py`, and `tests/fixtures/azoth_lite_phase2_cases.json`. | Treat as live opt-in machinery, not default authority. |
| Phase 3 advisory routing | Partially implemented. | `scripts/codex_control_plane.py` emits profile advisories and routes escalation to `$azoth-start pipeline_command=auto`; start/next docs mention lite default. | Needs contract reconciliation before further hardening. |
| Phase 4 default switch | Not safely complete. | Architecture docs mention ordinary work starts in lite, but the campaign blocks public release and protected/generated broad changes. | Do not broaden defaults in this child. |
| Meta-harness experimental | Research track only. | Prior operating-profile decision keeps it long-term. | Keep out of production defaults. |

## Boundary Findings

The profile split is no longer only a proposal. The repo already has:

- a manual shadow pack;
- an advisory classifier;
- profile fixtures covering all side-effect classes;
- Codex calm-flow advisory routing;
- start/next command text that says ordinary work defaults to `azoth-lite`;
- docs stating `/auto` is governed delivery when explicitly invoked or when
  lite escalates.

The missing artifact is the canonical source contract that ties these surfaces
together. Without it, agents can read the pieces in different orders and
over-conclude either that Phase 4 is complete or that the feature is still only
research.

## Selected Gaps

1. The canonical profile contract is not durable in one place.
2. The trace rule is still spread across the architecture spec, Phase 1 trial
   pack, and classifier context view.
3. The handoff packet fields in the architecture spec are richer than the
   current helper's `handoff_packet`.
4. `stock-lite` versus `azoth-lite` read-only selection is implemented, but the
   operator-facing contract should explain when trace-required read-only work
   becomes `azoth-lite`.
5. Autonomous continuation correctly belongs to `azoth-full`, but the current
   fixture set lacks a named autonomous-continuation case.
6. Public release/sync/freshness must remain blocked by default and on-demand
   only, because prior campaign evidence shows it was a tempting wrong lane.

## Rejected Next Moves

| Candidate | Decision | Reason |
| --- | --- | --- |
| Implement a broad default switch now | Reject | The campaign requires proof first, and Phase 4 is not the smallest safe move. |
| Hydrate roadmap/backlog/spec tasks | Reject | Blocked by campaign declaration. |
| Public release/readiness/freshness lane | Reject | Operator explicitly marked public release on-demand only. |
| Treat Phase 1 as sufficient final proof | Reject | Phase 1 itself says classifier and routing behavior were not proven then. |
| Skip to meta-harness experimental | Reject | It remains a separate research track and would blur current profile boundaries. |

## Recommended Child 2

Open a `refine_proposal` child to lock the canonical internal profile contract.

The contract should define:

- profile definitions and precedence;
- side-effect classes;
- read-only `stock-lite` versus traced/focused `azoth-lite` selection;
- context-view fields and target size;
- conditional trace rule;
- escalation trigger list;
- handoff packet schema;
- implementation source mapping from contract to helper, docs, and tests;
- proof plan for the next smallest implementation slice.

Child 2 should stop with a concrete implementation/test/doc gap, or with a
decision to skip implementation if the contract proves the current repo is
already coherent enough.

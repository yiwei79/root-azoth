# Azoth Harness Operating Profile Decision

## Executive Decision

Keep the **profile split** as the internal operating model:

- `stock-lite`: simple read-only/status baseline.
- `azoth-lite`: ordinary repo work, focused verification, local non-governed edits, and pre-action judgment.
- `azoth-full`: governed state, autonomous continuation, finality, closeout, packaging, kernel/governance, high-audit delivery, and protected boundaries.
- `meta-harness-experimental`: long-term research track only.

Do **not** simplify Azoth by deleting governed machinery now.
Do **not** switch additional defaults or public-facing product behavior now.
Do **not** treat public release work as an autonomous default campaign.

## What Stays Full Governed Harness

These surfaces remain `azoth-full`:

- `.azoth/` roadmap, backlog, initiative, design-bank, memory, handoff, run-ledger, scope-gate, and pipeline-gate state.
- `kernel/`, trust, governance, permission, hook, command-contract, and generated adapter behavior.
- Autonomous continuation, campaign loop state, child scopes, write claims, stage evidence, bounded replay, and closeout.
- Packaging, final delivery, commits, pushes, merge, release, publish, deployment, dependency changes, credentials, backups, and destructive operations.
- Any task where independent review, fresh-context isolation, or high-audit traceability is materially needed.

## What Becomes Lighter Operator UX

These surfaces should default lighter when no escalation trigger fires:

- Read-only status and file inspection.
- Focused verification without state mutation.
- Ordinary local edits outside governed Azoth state.
- Non-governed research notes and local docs/source/test work.
- Pre-action profile judgment and compact handoff packets.

The current `scripts/azoth_lite.py` classifier and tests show this already
exists as an advisory layer. It should remain advisory until the proof gaps are
closed.

## What Remains Experimental

The `meta-harness` direction is valuable but not ready for production defaults.
It needs trace evidence, benchmark cases, and a clear event/session substrate
before it can replace or reshape governed Azoth flows.

## Key Rejected Alternatives

| Alternative | Decision | Reason |
| --- | --- | --- |
| Direct harness simplification now | Reject | Source matrix, contract artifact, benchmark evidence, and harness-specific validator are absent. |
| Defer Harness Rethink entirely | Reject | Profile split already has accepted direction and visible implementation/test evidence. |
| Make `azoth-lite` authoritative for governed state | Reject | Governed-state and finality fixtures correctly escalate to `azoth-full`. |
| Continue public release/freshness lane | Reject | Operator clarified public release is on-demand only and never an automatic campaign. |
| Hydrate a roadmap task now | Reject | PM mobility reports zero safe hydration candidates and this budget blocks hydration. |
| Implement code now | Reject | The approved campaign blocks implementation, commits, and pushes. |

## Residual Risks

- `azoth-lite` could become a second full pipeline if trace requirements grow too large.
- `azoth-lite` could under-gate governed state if new governed paths are added without fixture updates.
- Existing docs and router behavior may already be ahead of the missing Harness Rethink contract artifact.
- The absent source matrix and contract artifact make it harder for future agents to reconstruct why the profile split is safe.
- Public release must remain on-demand only; future route boards should mark it blocked/deferred by default.

## Selected Next Internal Campaign

**Azoth-Lite Profile Evidence Reconciliation And Shadow Trial Plan**

Route: `refine_proposal`

Goal: reconcile the accepted profile-split research pack with the implemented
`azoth-lite` classifier, docs, fixtures, and Codex routing; then produce a
small internal plan for the next proof step without changing runtime defaults.

Recommended scope:

- inventory what profile-split phase is actually implemented
- identify missing source/contract/validator artifacts
- decide whether the next proof should be source-matrix recovery, shadow trials, fixture expansion, or advisory-routing hardening
- preserve `azoth-full` as the governed route for autonomous continuation, finality, packaging, `.azoth` state, kernel/governance, and protected boundaries
- keep public release/sync/freshness work out of the candidate set unless explicitly requested

Acceptance:

- one evaluator-scored reconciliation packet
- ranked next-proof options
- no roadmap/backlog/spec hydration
- no implementation
- no public/cockpit/project mutation
- no commit or push

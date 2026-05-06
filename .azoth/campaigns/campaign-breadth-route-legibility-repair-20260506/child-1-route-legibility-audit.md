# Child 1 Route Legibility Audit

Campaign: `campaign-breadth-route-legibility-repair-20260506`
Child scope: `2026-05-06-autonomous-auto-campaign-breadth-route-legibility-audit-1`
Action: `research_initiative`
Status: evaluator-pass

## Executive Read

Child 1 confirms that the narrowness problem is not that autonomous-auto uses
narrow child scopes. That part is healthy. The campaign envelope is broad,
approved, and explicitly blocks public release/sync/freshness, hydration,
cockpit/project mutation, credentials, destructive actions, protected gates, and
commits unless separately requested.

The unhealthy part is route legibility. Current route truth exists in the scope
gate and loop history, but the operator read can show `Route authority:
not-evaluated` while an active child blocks continuation. Campaign report also
mixes current active-loop truth with historical completed-Green handoff context,
which makes stale archive evidence feel like live authority.

## Audit Matrix

| Audit row | Healthy narrowness | Legibility gap |
| --- | --- | --- |
| Campaign envelope vs child edge | The campaign has four allowed action classes and a broad repair goal. Child 1 is intentionally research-only. | Operator-facing surfaces can make the active child look like the whole campaign. |
| Route authority | Scope gate and loop history carry `research_initiative:discovery_active`. | `status --operator-read` reports `Route authority: not-evaluated` while blocked by `active_scope_present`. |
| Historical noise | Completed Green handoffs are useful archive context. | `campaign-report --json` includes April 25 handoff observations beside active-loop truth without enough current-vs-historical separation. |
| Stage evidence visibility | The child uses real architect, researcher, and evaluator subagent sessions with run-ledger evidence. | Prior reflection shows stage evidence was not visible early enough after `open-next`, making the pipeline look fake. |
| Roadmap/dashboard route surface | Planning-bank routes correctly stop repeat hydration for hydrated or complete lanes. | Dashboard truth is healthy now, but campaign/report readbacks need the same stale/complete/current distinction. |
| Residual-risk taxonomy | The campaign declares a need to classify risks. | Current surfaces mostly flatten residuals into raw strings instead of live, stale, superseded, packaging-only, and protected classes. |

## Evidence

- `.azoth/campaigns/campaign-breadth-route-legibility-repair-20260506/context.yaml`
- `.azoth/scope-gate.json`
- `.azoth/autonomous-loop-state.local.yaml`
- `scripts/autonomous_loop.py status --operator-read`
- `scripts/autonomous_loop.py campaign-report --json`
- `scripts/autonomous_loop.py campaign-audit --loop-id campaign-breadth-route-legibility-repair-20260506 --json`
- `scripts/run_ledger.py status`
- `scripts/roadmap_dashboard.py`
- `.azoth/inbox/session-reflection-2026-05-05-autonomous-auto-pipeline-visibility-gap.jsonl`
- `.azoth/inbox/session-reflection-2026-05-03-autonomous-auto-inline-stage-exception.jsonl`
- `.azoth/campaigns/native-pm-campaign-architecture-discovery-20260505/`
- `.azoth/campaigns/post-green-route-truth-repair-20260505/`

## Rejected Alternatives

- Continue the April 25 Green handoff: rejected because completed-loop truth is
  archive context, not fresh authority.
- Hydrate roadmap/backlog/spec work: rejected by the campaign boundary.
- Public release, public sync, or public freshness work: protected and explicitly
  blocked.
- Cockpit/project/private-root writes, credentials, dependencies/network,
  destructive actions, kernel/governance/M1: protected.
- Backfill fake subagent evidence: rejected. Only real spawn evidence or explicit
  inline exceptions count.
- Jump straight to implementation: rejected by evaluator. The right next move is
  a proposal/refinement contract before a focused ship child.

## Residual Risks

| Class | Risk |
| --- | --- |
| Live | Operator read hides route authority during `active_scope_present` even though scope/loop history has `research_initiative:discovery_active`. |
| Live | Campaign report mixes active loop truth with historical completed Green handoff observations. |
| Live | Residual risks need structured taxonomy in operator-facing surfaces. |
| Stale | April 25 handoff residuals and recommendations are archive context, not current route authority. |
| Superseded | Completed T-032/T-033 learning-harvester and campaign-evaluation proposal signals should remain stale or rejected. |
| Packaging-only | Branch ahead and campaign artifacts should be separated before any later commit request. |
Protected boundaries remain blocked and are recorded as campaign boundaries, not
as live residual risks that should trigger autonomous self-heal. They include
public release/sync/freshness, hydration, cockpit/project mutation,
network/dependencies, credentials/backups, destructive actions, and
kernel/governance/M1.

## Evaluator Decision

Score: `0.92`
Threshold: `0.90`
Disposition: pass.

Iteration history:

| Iteration | Score | Result |
| --- | --- | --- |
| 0 | 0.84 | Pre-evaluator campaign audit correctly found missing evaluator evidence and recommended `repair_evidence`. |
| 1 | 0.92 | Architect, researcher, and evaluator evidence now support continuing without bounded replay. |

## Recommended Next Child

Open child 2 as `refine_proposal`:
`campaign-breadth-route-legibility-contract`.

Goal: define a bounded internal repair contract for operator-read route
authority, campaign-report current-vs-historical separation, stage-evidence
visibility, and residual-risk taxonomy. Do not public release/sync/freshness,
hydrate roadmap/backlog/specs, mutate cockpit/project repos, or commit unless the
operator separately requests packaging.

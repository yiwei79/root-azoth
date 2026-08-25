# Child 2 Repair Contract

Campaign: `campaign-breadth-route-legibility-repair-20260506`
Child scope: `2026-05-06-autonomous-auto-campaign-breadth-route-legibility-contract-2`
Action: `refine_proposal`
Status: evaluator-pass after one bounded replay

## Executive Read

Child 2 converts the child-1 audit into a deterministic internal repair
contract. The repair must improve operator route legibility without broadening
scope into public release/sync/freshness, roadmap/backlog/spec hydration,
cockpit/project mutation, dependency/network expansion, credentials, destructive
actions, kernel/governance/M1, or commits.

The selected implementation shape is additive: preserve existing campaign-report
schema version and raw fields, then add current route authority, historical
handoff authority, stage-evidence states, and structured residual-risk fields.

## Required Fields

Preserve:

- `report_schema_version: 1`
- `current_loop`
- `handoff_campaign`
- `learning_harvester`
- `next_campaign_recommendation`
- `observation`
- raw `residual_risks` wherever already present

Add:

- `current_route_authority`
- `stage_evidence_states`
- `structured_residual_risks`
- `historical_handoff`
- `historical_handoff_authority`

## Current Route Authority

Source priority:

1. Active `.azoth/scope-gate.json` `loop_decision.strategy_preflight.route_authority`
   when the scope session is active/current.
2. Latest matching `.azoth/autonomous-loop-state.local.yaml` history entry
   `strategy_preflight.route_authority`.
3. Live decision or lifecycle packet route authority.
4. `unavailable_fail_closed`.

Completed or stale handoffs, protected-boundary notes, and historical residuals
must never become current authority.

Shape:

```yaml
current_route_authority:
  status: selected | conflict | unavailable_fail_closed
  route_authority: refine_proposal:candidate_ready_for_review
  selected_action: refine_proposal
  route_state: candidate_ready_for_review
  source_priority_rank: 1
  source_kind: active_scope_strategy_preflight
  source_ref: .azoth/scope-gate.json
  stale_or_blocked_sources: []
  historical_handoff_authority_ref: historical_handoff_authority
```

## Historical Handoff

Historical handoff data is archive/display evidence only. It may be useful for
context, but it must not authorize the current loop, `auto_self_heal_now`, or
`next_safe_action`.

```yaml
historical_handoff_authority:
  authority_role: historical_handoff_authority
  may_authorize_current_loop: false
  may_authorize_auto_self_heal_now: false
  may_authorize_next_safe_action: false
  display_states:
    - historical
    - blocked
    - stale
    - completed
```

## Stage Evidence States

Derive stage states from:

- latest run-ledger `stage_spawns` by `spawned_at`
- latest run-ledger `stage_summaries` by `summary_recorded_at`
- completion evidence from `stages_completed` plus `require-completion-evidence`
  semantics
- active run status and `pending_stage_ids`

Allowed states:

- `not_started`
- `in_progress_pending_summary`
- `summary_blocking`
- `summary_mismatch_or_stale`
- `complete_with_paired_evidence`
- `complete_with_allowed_inline_exception`
- `completion_unverified`
- `unavailable_missing_run`

Rules:

- Spawn without a matching latest summary is `in_progress_pending_summary`, never
  completion.
- Summary counts only when timestamp is at or after the latest spawn and metadata
  matches the latest spawn.
- Blocking dispositions such as `request-changes` remain `summary_blocking`.
- A stage is complete only when paired evidence passes `require-stage-evidence`,
  or inline exception is allowed by policy and completion rules.
- For `spawn_required` stages, inline exception is audit-only and cannot satisfy
  completion.

## Structured Residual Risks

Add `structured_residual_risks` while preserving raw residual strings.

Allowed classes:

- `live`
- `stale`
- `superseded`
- `packaging_only`
- `protected`
- `historical`

Each structured row should include:

```yaml
- class: live
  risk: Operator read hides active route authority.
  source_ref: campaign-audit
  selectable_as_auto_self_heal_now: true
  selectable_as_next_safe_action: false
```

Protected and historical rows are display/block evidence only.

## Later Child 3 Implementation Scope

Action: `ship_task`

Target files:

- `scripts/autonomous_loop.py`
- `tests/test_autonomous_loop.py`

Expansion beyond these files requires a narrow evaluator-justified reason. No
roadmap/backlog/spec hydration, public release/sync/freshness, cockpit/project
mutation, schema version bump, generated platform sweep, or commit packaging is
authorized by this contract.

Required tests:

- active scope strategy preflight wins over loop history and handoff
- latest matching loop-history strategy preflight is fallback
- live decision/lifecycle packet is third fallback
- missing authority fails closed
- completed/stale handoff appears only as historical handoff authority
- spawn-only stage is `in_progress_pending_summary`
- blocking latest summary remains `summary_blocking`
- paired latest spawn/summary plus completion evidence becomes complete
- `report_schema_version` remains `1`
- existing raw fields remain present
- protected and historical risks cannot become `auto_self_heal_now`,
  `next_safe_action`, or current authority

## Evaluator Result

Score: `0.94`
Threshold: `0.90`
Disposition: pass.

Iteration history:

| Iteration | Gate | Score | Result |
| --- | --- | --- | --- |
| 0 | initial reviewer | 0.86 | Request changes. Contract needed deterministic priority, stage-state derivation, additive schema rules, and protected/historical isolation. |
| 1 | bounded replay architect | n/a | Accepted reviewer findings and pinned deterministic contract fields. |
| 2 | replay reviewer | 0.94 | Approved revised contract. |
| 3 | evaluator | 0.94 | Pass. Child 2 can complete and queue child 3. |

## Rejected Alternatives

- Reuse April 25 completed Green handoff as current authority.
- Let protected or historical evidence become `auto_self_heal_now`,
  `next_safe_action`, or loop authority.
- Treat evaluator spawn as completion.
- Broaden child 3 into audit/helper work by default.
- Hydrate roadmap/backlog/specs, public sync/release/freshness, or mutate
  cockpit/project repos.

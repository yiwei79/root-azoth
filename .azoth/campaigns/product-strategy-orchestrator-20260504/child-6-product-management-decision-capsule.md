# Product Management Decision Capsule

Date: 2026-05-04
Campaign: `product-strategy-orchestrator-20260504`
Child scope: `2026-05-04-autonomous-auto-product-management-decision-capsule-6`
Action: `ship_task`
Status: executive product strategy capsule

## Executive Decision

The Product Strategy Orchestrator should use **Initiative Discovery PM Lane** as
its practical product-management spine, with **Harness Rethink** as the
strategic constraint layer.

This means:

- compare initiatives before choosing work
- research assumption-heavy opportunities
- refine proposals when the lane is promising but not executable
- ship strategy capsules when the decision needs to be durable
- stop for human approval before hydration, delivery, public release, cockpit or
  project writes, commits, pushes, or any protected boundary

## What We Decided

| Decision | Outcome |
| --- | --- |
| Strategic frame | Harness Rethink is the right north star, but not an implementation lane yet. |
| Practical PM workflow | Initiative Discovery is the best current lane for smart product-management choices. |
| Routing substrate | Autonomous Initiative Lifecycle supplies useful route verbs and fail-closed transitions. |
| Near-term product move | Validate this strategy once, then stop at a human gate for any hydration/delivery/packaging choice. |
| Authority boundary | Campaign artifacts recommend; `.azoth/roadmap.yaml` and `.azoth/backlog.yaml` remain authoritative. |

## Why This Beats The Alternatives

| Alternative | Rejected Because |
| --- | --- |
| Public Release Root Feature Parity | High product value, but too close to public sync/release and checkout mutation gates. |
| INI-MEM-003 Recall Quality | Useful quality lane, but narrower than the requested product strategy capability. |
| Direct Harness Simplification | Harness proposal is draft and referenced evidence artifacts are absent in this checkout. |
| Hydrate A Roadmap Task Now | Explicitly blocked without a fresh human gate naming candidate and write path. |
| Package/Commit Now | Explicitly blocked unless the operator approves packaging/commit work. |

## Operating Rule

The orchestrator should choose the next route by state:

- `raw_or_ambiguous` -> research
- `discovery_active` -> research or proposal refinement
- `candidate_ready_for_review` -> proposal refinement and plan-only handoff
- `approved_for_hydration` -> stop for explicit hydration gate
- `delivery_ready` -> stop for explicit delivery campaign gate
- `fulfilled_or_stale` -> stop or research a fresh distinct seed

## Current Campaign Evidence

- Child 1: portfolio inventory and scorecard complete.
- Child 2: product strategy operating model complete.
- Child 3: decision surface and route table complete.
- Child 4: Harness Rethink deep dive complete; strategic constraint selected.
- Child 5: Initiative Discovery PM state machine complete.

## Next Safe Internal Move

Run one validation/replay-readiness child before marking the campaign Green:

Action: `research_initiative`

Candidate id: `product-strategy-validation-and-replay-readiness`

Purpose:

- confirm the strategy still matches live roadmap/backlog/planning-bank state
- confirm no hidden protected gate was crossed
- confirm the route table and state machine are enough for an operator-level
  product-management read
- decide whether the campaign should close Green or use bounded replay

## Next Product Move After Campaign

After validation, the likely next real product move requires human choice:

1. Approve packaging/commit of completed campaign artifacts.
2. Approve a hydration-specific campaign for one exact Initiative Discovery
   slice.
3. Approve a public-release strategy campaign with explicit public boundary
   gates.
4. Defer delivery and keep the strategy artifacts as advisory context.

Until then, no roadmap/backlog/spec writes, public sync/release, cockpit/project
writes, dependency/network/credential work, destructive actions, kernel or
governance mutation, commit, or push are authorized.

## Residual Risk

The strategy is coherent and useful, but it is not executable authority. Its
main residual risk is future agents treating the capsule as a task generator
instead of a product-management decision aid. The validation child should check
that this warning is visible enough.

# Initiative Discovery PM Lane

Date: 2026-05-04
Campaign: `product-strategy-orchestrator-20260504`
Child scope: `2026-05-04-autonomous-auto-initiative-discovery-pm-lane-5`
Action: `refine_proposal`
Status: active campaign-local PM lane

## Purpose

This refinement turns Initiative Discovery into the practical operating lane for
the Product Strategy Orchestrator. Harness Rethink supplies the strategic
constraints; Initiative Discovery supplies the repeatable product-management
workflow.

This artifact is not authoritative roadmap/backlog state. It is a campaign-local
strategy refinement.

## Key Source Judgment

The Initiative Discovery proposal is strong enough to become the campaign's PM
spine because it already defines:

- initiatives as durable goal containers, not delivery scopes
- proposals as design/challenge surfaces
- initiative banks as readiness and evidence state
- readiness reports before hydration
- candidate slices with acceptance criteria and non-goals
- explicit human approval before roadmap/backlog/spec writes
- stop/defer/reject as valid discovery outcomes
- replay scenarios for historical-only, discovery-active, and ready-after-gate
  initiative shapes

The planning-bank design bank and INI-EVI-002 bank add an important current-state
constraint: do not reopen completed planning-bank helper or T-046 lanes. The PM
lane must choose fresh distinct seeds, not rehydrate fulfilled work.

## Harness Rethink Constraints Folded In

Initiative Discovery should operate with these harness-shape constraints:

- One campaign brain owns product choice and route explanation.
- Execution hands are used only when parallelism, independent review, or
  mechanically separated ownership is real.
- Each child emits a compact route capsule: question, evidence, selected route,
  rejected alternatives, protected gates, next safe action.
- Context views should be generated from proposal, bank, roadmap, and campaign
  surfaces instead of asking the operator to restate known state.
- The lane prefers strategy/report artifacts until readiness and human gates
  justify canonical writes.
- Evals and validators are evidence; they do not replace human approval for
  hydration or protected boundaries.

## PM State Machine

| State | Evidence | Safe Route | Output | Blocked |
| --- | --- | --- | --- | --- |
| `raw_or_ambiguous` | Operator goal or initiative id exists, but no durable evidence surface owns it | `research_initiative` | campaign research brief or proposal seed recommendation | hydration, delivery |
| `discovery_active` | Proposal/bank exists with open questions, candidate slices, assumptions, or contradictions | `research_initiative` or `refine_proposal` | updated readiness synthesis or challenge/refinement artifact | roadmap/backlog/spec writes |
| `candidate_ready_for_review` | First slice has scope, non-goals, acceptance, target layer, and evidence refs | `refine_proposal` | plan-only hydration handoff recommendation | scaffold execution |
| `approved_for_hydration` | Readiness is green and human approval names exact candidate and scaffold path | `stop_for_human_gate` in this campaign | ask for explicit hydration approval | all writes until approved |
| `delivery_ready` | Roadmap/backlog/spec task exists after approved hydration | `stop_for_human_gate` in this campaign | ask whether to open delivery campaign | direct delivery from strategy lane |
| `fulfilled_or_stale` | The apparent next seed duplicates completed task or lacks fresh distinct evidence | `stop` or `research_initiative` for a fresh seed | stop reason or fresh-seed research | repeat hydration |

## Readiness Review Rule

The orchestrator may recommend hydration only when all of these are true:

- the initiative goal is stable
- at least one first slice is smaller than the initiative
- target layer and delivery pipeline are clear
- acceptance criteria and non-goals are explicit
- source evidence is fresh enough for the slice
- contradictions are adjudicated or consciously deferred
- protected boundaries are named
- the candidate is not duplicating completed work
- the human gate can name the exact candidate and scaffold/write path

If any item is missing, the next route is research or refinement, not hydration.

## Product-Management Operating Loop

1. **Frame**

   Name the product question and expected decision.

2. **Inventory**

   Read proposals, initiative/design banks, roadmap/backlog truth, campaign
   reports, and recent lessons.

3. **Challenge**

   Ask what would make this not worth building, what is too broad, what is
   already fulfilled, and what protected boundary the next move would cross.

4. **Route**

   Choose `research_initiative`, `refine_proposal`, `ship_task`, or
   `stop_for_human_gate` from readiness evidence.

5. **Capsule**

   Emit a small decision capsule with selected lane, rejected alternatives,
   evidence, next safe action, and packaging truth.

## Current Campaign Decision

The orchestrator now has:

- portfolio inventory
- operating model
- decision surface
- Harness Rethink strategic constraint
- Initiative Discovery PM lane

The next useful move is not more research. It is to ship an auditable product
strategy decision capsule that summarizes the selected lane, rejected
alternatives, current stop gates, and next safe action.

## Next Child Recommendation

Action: `ship_task`

Candidate id: `product-management-decision-capsule`

Title: `Product Management Decision Capsule`

Expected output:

- A campaign-local executive capsule with the selected product strategy lane.
- A clear "what we decided / what we rejected / what happens next" table.
- Explicit note that hydration, delivery, release, and commits remain blocked
  without fresh human approval.
- No roadmap/backlog/spec writes.

# Locked Campaign Declaration

## Name

Multi-Operating Profile Feature Completion

## Mode

`autonomous-auto`

## Goal

Complete the internal multi-operating-profile feature for Azoth end-to-end:
reconcile accepted profile-split research with implemented classifier, routing,
docs, and tests; define the canonical profile contract; implement the smallest
safe internal slice if route evidence proves one is needed; run shadow-trial and
eval cases; and stop with evaluator-scored proof that `stock-lite`,
`azoth-lite`, `azoth-full`, and `meta-harness-experimental` are coherent and
escalation-safe.

## Design Intent

This campaign should achieve the feature goal, not merely describe it.

The campaign is allowed to progress from research to refinement to a bounded
internal implementation slice when the earlier child scopes prove the needed
gap and the work stays within the declared boundaries. It should not hydrate
roadmap/backlog/spec state, mutate public/cockpit/project repos, or treat public
release as an automatic candidate.

## Budget

- Up to 6 child scopes.
- 1 bounded replay per child.
- Alignment mode: async.

## Allowed Actions

- `research_initiative`
- `refine_proposal`
- `ship_task`
- `capture_self_improvement`

## Blocked Without Fresh Explicit Gate

- `hydrate_task`
- roadmap/backlog/spec hydration
- public `azoth` mutation
- public release, public sync, tags, public freshness, or public checkout work
- cockpit or controlled project repo writes
- network or dependency expansion
- credential or backup work
- kernel/governance/M1 mutation
- destructive actions
- commits and pushes

## Child Scope Design

| Child | Route | Purpose | Stop/Proceed Rule |
| ---: | --- | --- | --- |
| 1 | `research_initiative` | Reconcile accepted profile-split research, previous campaign decision, live classifier/docs/tests/routing, and dirty-state packaging truth. | Proceed only if the gap is internal and non-protected. |
| 2 | `refine_proposal` | Lock canonical profile contract: side-effect classes, context view, trace rule, escalation handoff, and profile boundaries. | Proceed only if a concrete implementation/test/doc gap is named. |
| 3 | `ship_task` | Implement the smallest safe internal slice needed for coherence. | Stop if the slice touches protected gates, public release, dependencies, or broad generated surfaces beyond budget. |
| 4 | `research_initiative` | Run shadow-trial/eval cases across read-only, focused verification, local edit, governed escalation, finality escalation, and autonomous continuation. | Use bounded replay only for a concrete failed profile/eval finding. |
| 5 | `ship_task` | Harden integration/docs/tests if eval exposes a bounded gap. | Skip if child 4 is Green without changes. |
| 6 | `refine_proposal` | Produce final evaluator packet, residual risks, rejected alternatives, and next campaign recommendation. | Close Green only when proof and operator-read are coherent. |

## Child Session Contract

Each child is its own autonomous-auto session, not a section inside one
continuous informal analysis pass.

Every child must:

- open through `autonomous_loop.py open-next`
- acquire its own scope gate and write claim
- expose its `delegation_plan` before substantive work
- record stage evidence immediately after open, using either real subagent
  spawn evidence or an explicit inline exception when host policy prevents
  spawning
- complete the declared orchestration stages with run-ledger summaries
- run `require-completion-evidence`
- record evaluator score and replay accounting
- close out and release its write claim before the next child opens

No later child may start while an earlier child has an active write claim or
unverified completion evidence.

## Orchestration Pipeline Pattern

Each child uses the orchestration pattern appropriate to its route:

- `research_initiative`: architect question framing, researcher evidence
  gathering, evaluator completeness scoring
- `refine_proposal`: architect contract framing, reviewer boundary critique,
  evaluator scorecard and replay decision
- `ship_task`: architect implementation slice, builder-owned change, evaluator
  verification, with reviewer inserted when blast radius or independence risk
  warrants it
- `capture_self_improvement`: architect/root-cause framing, capture artifact,
  evaluator acceptance against mistake-to-artifact criteria

The orchestrator may keep work inline only with an explicit run-ledger inline
exception that explains why host policy or scope makes spawning inappropriate.
It may not silently collapse a child into chat-only reasoning.

## Evaluator Iterative Improvement Pattern

Every child evaluator packet must include:

- `score`
- `threshold`
- scored `dimensions`
- `iteration_history`
- bounded replay count
- rejected alternatives
- residual risks
- final disposition: `pass`, `conditional`, or `fail`

If the first evaluator score is below threshold and the finding is inside the
child budget, the child must run one bounded replay through the narrowest
affected stage. If the replay still misses threshold or crosses a protected
boundary, the child stops with residual risks instead of broadening silently.

## Acceptance Criteria

- `stock-lite`, `azoth-lite`, `azoth-full`, and `meta-harness-experimental` have a canonical internal contract.
- `azoth-lite` stays light and does not become a second full pipeline.
- Governed `.azoth` state, command contracts, generated surfaces, finality, closeout, autonomous continuation, kernel/governance, and protected boundaries route to `azoth-full`.
- Public release/sync/freshness is blocked by default and on-demand only.
- Shadow/eval cases prove lightness preservation and escalation precision.
- Existing `azoth-lite` classifier tests and relevant Codex/start routing tests pass.
- `azoth-deploy.py --check` remains green if generated surfaces are touched.
- Run-ledger stage evidence is visible immediately after every child opens.
- Each child closes as its own session before the next child opens.
- Each child includes an evaluator iterative-improvement packet with
  `iteration_history` and bounded replay accounting.

## Initial Queue

Start with `multi-operating-profile-reconciliation`, a research child that maps
what is already implemented, what is missing, and what concrete next child
should do.

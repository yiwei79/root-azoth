---
description: 'Autonomous Auto Mode: standalone adaptive pipeline for branch-local
  Azoth self-development with alignment_mode: async, alignment packets, and approval_basis
  persistence'
agent: orchestrator
---

# /autonomous-auto $ARGUMENTS

**Primary specification:** `Read` **`.agents/skills/autonomous-auto/SKILL.md`** and execute it
end-to-end for the goal in `$ARGUMENTS`. This command is the slash entry for Autonomous Auto
Mode; do not treat it as a submode of `dynamic-full-auto`.

## Autonomous Auto Mode

Use `autonomous-auto` when the operator grants a branch-local autonomy budget for Azoth
self-development and wants alignment to arrive asynchronously. The session must route through
the delivery control plane as `pipeline_command=autonomous-auto`.

Before execution, declare:

- goal
- selected mode = `autonomous-auto`
- `alignment_mode: async`
- branch-local autonomy budget
- `approval_basis`
- adaptive pipeline stages expected now
- replay threshold and stop conditions
- protected human-gate boundaries

## Vision Declaration

For realistic use, the operator should be able to start with a short prompt such as
"start the next autonomous campaign." Do not require a long structured budget prompt.
Instead, begin with a Vision Declaration phase:

1. Inspect current repo state plus initiative, proposal, roadmap, and backlog surfaces.
2. Propose a concise campaign declaration: objective, selected seed or initiative,
   allowed action classes, iteration budget, replay threshold, stop conditions, and
   protected boundaries.
3. Discuss and revise the declaration with the operator in the same session.
4. After explicit approval, initialize the loop and persist the locked declaration under
   `.azoth/autonomous-loop-state.local.yaml` `vision.declaration`.

Autonomous self-development starts after that approval. The declaration's `approval_basis`
may satisfy branch-local routine approval fields, but protected human gates still stop.

## Async Alignment

Operator lines are not sequential gates. Treat later human messages as alignment packets,
classify them as `async_advisory`, `async_override`, `async_stop`, or `approval_basis`, and
apply them at the next safe checkpoint while non-blocked work continues.

## Pipeline Discipline

Autonomous auto must still deliver with an adaptive pipeline:

- Stage 0 classification and `skills/auto-router/SKILL.md` composition are required.
- When autonomous-mode behavior is in scope, read
  `.azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md`; architect stages emit
  `UX Anchor Fit` and evaluator stages emit `UX Anchor Scorecard` using Green/Yellow/Red
  alignment bands.
- Research/explore waves are inserted when the goal is not ready to hydrate or deliver.
- Hydration and implementation stay separate artifact-class stages when both are needed.
- Each opened child scope carries a compact `delegation_plan` in `.azoth/scope-gate.json`.
  Treat it as a deterministic reminder and audit scaffold, not a full scheduler: the
  orchestrator still uses architect judgment, but may not silently replace required
  context-isolation, review-independence, context-budget, or protected gates with inline work.
- Each child scope starts with an active `.azoth/run-ledger.local.yaml` run entry. Delegated
  stages must record `stage_spawns` and `stage_summaries`; inline exceptions must be explicit
  and justified against the `delegation_plan.inline_policy`.
- E1–E6 from `.claude/commands/eval.md` decide whether `/eval-swarm` is inserted.
- Bounded replay handles failed review/eval findings; stop at the replay threshold.
- Scope/pipeline gates, write claims, run-ledger evidence, and closeout remain mechanical.

## Loop Governor

When the operator grants a continuing self-development budget, run `autonomous-auto` as a
bounded loop of normal Azoth sessions:

1. Finish the current adaptive pipeline and close out. Treat that closeout as a checkpoint,
   not a terminal stop, unless the UX vision score is Green or a real stop condition fires.
2. Reflect on mistakes, failed assumptions, missing workflow affordances, and closeout drift.
3. Make an architect judgment for exactly one next action: `ship_task`, `hydrate_task`,
   `research_initiative`, `refine_proposal`, `capture_self_improvement`, or `stop`.
4. If loop state is missing and the current operator message grants an explicit branch-local
   autonomy budget, use `scripts/autonomous_loop.py init --approval-basis <text>` to create
   `.azoth/autonomous-loop-state.local.yaml`; include `--vision-declaration-json` once the
   operator has approved the campaign declaration. Otherwise stop at `missing_loop_state`.
5. Use `scripts/autonomous_loop.py decide-next --json` to emit the next decision.
6. If the decision is not `stop`, use `scripts/autonomous_loop.py open-next --decision <path>`
   to open the next `pipeline_command=autonomous-auto` scope, persist its `delegation_plan`,
   create the child run-ledger entry, and acquire the write claim.
7. Use `scripts/autonomous_loop.py status --operator-read` for concise operator alignment
   packets including live write-claim drift, `record-alignment` / `apply-alignment` for async
   packet state, and `record-vision-score` / `materialize-self-capture` for vision scoring and
   inbox-first mistake capture.

Local loop state lives in `.azoth/autonomous-loop-state.local.yaml`; the tracked
`.azoth/autonomous-loop-state.local.yaml.example` documents its shape. The loop governor
must stop when state is missing, budget is exhausted, another scope is active, a protected
gate is required, or no safe candidate is discoverable. Do not stop after a child closeout
while the UX vision is still below target and safe work remains in budget.

Non-stop loop decisions carry an architect decision capsule with selected candidate,
rejected alternatives where visible, readiness/risk/value scoring, and alignment checkpoint
summary. Opened scope gates should persist the autonomy budget and decision capsule.

For durable self-development over time, prefer a Codex automation or cron-style wakeup that
runs one bounded iteration per wakeup. A single long interactive thread is acceptable for
calibration experiments, but not the durable default.

## Gates

`autonomous-auto` does not skip protected human gates. Stop for kernel, governance, M1,
destructive, credential, or unverified network expansion, or for any explicit `async_stop`
packet. For governed or M1 work, `.azoth/pipeline-gate.json` must use
`"pipeline_command": "autonomous-auto"`.

## Arguments

Goal / session intent: **$ARGUMENTS**

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

## Async Alignment

Operator lines are not sequential gates. Treat later human messages as alignment packets,
classify them as `async_advisory`, `async_override`, `async_stop`, or `approval_basis`, and
apply them at the next safe checkpoint while non-blocked work continues.

## Pipeline Discipline

Autonomous auto must still deliver with an adaptive pipeline:

- Stage 0 classification and `skills/auto-router/SKILL.md` composition are required.
- Research/explore waves are inserted when the goal is not ready to hydrate or deliver.
- Hydration and implementation stay separate artifact-class stages when both are needed.
- E1–E6 from `.claude/commands/eval.md` decide whether `/eval-swarm` is inserted.
- Bounded replay handles failed review/eval findings; stop at the replay threshold.
- Scope/pipeline gates, write claims, run-ledger evidence, and closeout remain mechanical.

## Loop Governor

When the operator grants a continuing self-development budget, run `autonomous-auto` as a
bounded loop of normal Azoth sessions:

1. Finish the current adaptive pipeline and close out.
2. Reflect on mistakes, failed assumptions, missing workflow affordances, and closeout drift.
3. Make an architect judgment for exactly one next action: `ship_task`, `hydrate_task`,
   `research_initiative`, `refine_proposal`, `capture_self_improvement`, or `stop`.
4. Use `scripts/autonomous_loop.py decide-next --json` to emit the next decision.
5. If the decision is not `stop`, use `scripts/autonomous_loop.py open-next --decision <path>`
   to open the next `pipeline_command=autonomous-auto` scope and acquire the write claim.

Local loop state lives in `.azoth/autonomous-loop-state.local.yaml`; the tracked
`.azoth/autonomous-loop-state.local.yaml.example` documents its shape. The loop governor
must stop when state is missing, budget is exhausted, another scope is active, a protected
gate is required, or no safe candidate is discoverable.

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

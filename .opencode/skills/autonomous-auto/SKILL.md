---
name: autonomous-auto
description: |
  Autonomous Auto Mode: a standalone adaptive pipeline for branch-local Azoth
  self-development with async operator alignment packets, explicit approval_basis
  fields, bounded replay, and normal scope/pipeline gate enforcement.
---

# Autonomous Auto Mode

## Autonomous Auto Mode

`autonomous-auto` is a standalone mode for fully autonomous Azoth self-development.
It is not a submode of `dynamic-full-auto`. Use it when the operator grants a
branch-local autonomy budget for Azoth to refine initiatives, hydrate tasks, implement,
evaluate, replay bounded fixes, and close out while human alignment can arrive
asynchronously.

## Autonomy Budget

At session start, declare:

- goal
- selected mode = `autonomous-auto`
- `pipeline_command=autonomous-auto`
- `alignment_mode: async`
- branch-local autonomy budget and `approval_basis`
- adaptive pipeline stages that are expected now
- replay threshold and recomposition stop conditions
- protected human-gate boundaries that still stop the run

Use `.azoth/scope-gate.json` with `pipeline_command: autonomous-auto` and
`alignment_mode: async`. If governed delivery, M1, or a protected gate is involved, also
write `.azoth/pipeline-gate.json` with `pipeline_command: autonomous-auto`.

## Async Alignment

When the budget declares `alignment_mode: async`, operator lines are not sequential gates.
Treat later human messages as **alignment packets** that can arrive while non-blocked work
continues. The orchestrator polls for them at stage boundaries, after research/explore
waves, before first write in a new artifact class, before bounded replay, and before
closeout. Apply each packet at the next safe checkpoint; do not rewind completed work unless
the packet invalidates scope, acceptance, or safety.

Classify each alignment packet before acting:

- `async_advisory` — preference, emphasis, or ranking signal. Record the disposition in the
  stage summary or artifact note and continue.
- `async_override` — changes scope, acceptance, non-goals, branch target, or task priority.
  Apply at the next safe checkpoint; if it conflicts with completed work, open a bounded
  replay or split a follow-on scope.
- `async_stop` — explicit stop/abort/no, kernel/M1/governance expansion, destructive action,
  network or credential blocker, or any protected human gate. Stop before the affected edge
  and ask for a fresh decision.
- `approval_basis` — the packet supplies or updates the branch-local autonomy basis. Persist
  it beside any `human_decision: approved` or gate field it supports.

## Adaptive Pipeline

Autonomous auto must still deliver with pipeline discipline. At Checkpoint Γ, run the same
Stage 0 classification and `skills/auto-router/SKILL.md` composition used by `/auto`, then
adapt the stage list to the actual scope:

- Use research/explore waves before hydration when knowledge is incomplete.
- Hydrate planning artifacts only when readiness and `approval_basis` are explicit.
- Open implementation as a separate delivery stage when the hydrated task is ready.
- Insert `/eval-swarm` when `.claude/commands/eval.md` E1–E6 triggers fire.
- Use bounded replay for failed review/eval findings; stop at the threshold.
- Close out through the normal session lifecycle and record the autonomous approval basis.

The adaptive pipeline may be short for known-pattern edits or longer for planning-bank,
roadmap, command, skill, or generated-surface work. It may continue under the same
branch-local autonomy budget while async alignment is pending. It does not skip mechanical
scope/pipeline gates, write claims, run-ledger evidence, final safety checks, or
kernel/governance/M1 approvals.

## Loop Governor

When the operator grants a continuing self-development budget, `autonomous-auto` may run as
a loop rather than a single delivery. Each iteration is still a normal scoped Azoth session:

1. Execute the current adaptive pipeline.
2. Close out through the normal session lifecycle.
3. Reflect on mistakes, failed assumptions, missing workflow affordances, and closeout drift.
4. Make an architect judgment for the next move.
5. Capture self-improvement signals as repo-native inbox, proposal, initiative, or backlog
   candidates when they should change future behavior.
6. Select exactly one next action: `ship_task`, `hydrate_task`, `research_initiative`,
   `refine_proposal`, `capture_self_improvement`, or `stop`.
7. Open the next `autonomous-auto` scope only when the loop state, autonomy budget, gates,
   and write claim allow it.

Use `.azoth/autonomous-loop-state.local.yaml` for local loop state. The tracked
`.azoth/autonomous-loop-state.local.yaml.example` documents the expected fields. The loop
state records `loop_id`, branch, `autonomy_budget.approval_basis`, max iterations,
iteration count, last session, queued work, history, stop reason, and automation hints.

Use `scripts/autonomous_loop.py` for deterministic continuation decisions:

- `status` reports loop state and whether a live scope blocks continuation.
- `decide-next --json` emits the next architect decision.
- `open-next --decision <path>` writes the next scope gate and acquires a write claim.
- `stop --reason <reason>` records a terminal local stop.

`decide-next` must stop, not improvise, when loop state is missing, the iteration budget is
exhausted, another live scope is active, a protected gate is required, or no safe candidate
is discoverable.

For durable self-building over time, prefer a Codex automation or cron-style wakeup that
runs one bounded iteration per wakeup. A single long interactive thread may be used for
experiments and calibration, but it is not the durable default. Heartbeat continuation is
only appropriate for short same-thread runs where the operator is still actively observing.

## Stop Conditions

Stop before the affected edge when:

- an `async_stop` packet arrives,
- kernel, governance, M1, destructive, credential, or network expansion appears,
- the autonomy budget no longer covers the next artifact class,
- eval/review replay exceeds the threshold,
- scope/pipeline gates or write claims are invalid,
- external freshness is material and cannot be verified.

## Relation to Other Modes

`/auto` is the default composed delivery path. `dynamic-full-auto` is the high-autonomy
one-session adaptive delivery pipeline with discovery/research insertion. `autonomous-auto`
is the branch-local self-development mode with async alignment, explicit `approval_basis`
persistence, and an optional loop governor for continuing from one proposal, initiative,
or task to the next.

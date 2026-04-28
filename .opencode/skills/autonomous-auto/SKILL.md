---
name: autonomous-auto
description: |
  Autonomous Auto Mode: a standalone adaptive pipeline for branch-local Azoth
  self-development with async operator alignment packets, explicit approval_basis
  fields, bounded replay, and normal scope/pipeline gate enforcement.
---

# Autonomous Auto Mode

## Overview

This skill defines the canonical branch-local autonomous self-development mode
for Azoth. It keeps autonomous campaigns auditable through vision declarations,
async alignment handling, bounded replay, and normal gate enforcement.

## Autonomous Auto Mode

`autonomous-auto` is a standalone mode for fully autonomous Azoth self-development.
It is not a submode of `dynamic-full-auto`. Use it when the operator grants a
branch-local autonomy budget for Azoth to refine initiatives, hydrate tasks, implement,
evaluate, replay bounded fixes, and close out while human alignment can arrive
asynchronously.

## When to Use

Use `autonomous-auto` when Azoth is developing Azoth itself under a branch-local
autonomy budget, especially for initiative refinement, task hydration, governed
implementation, bounded replay, self-heal routing, and campaign closeout where the
operator wants async alignment packets instead of sequential human gates.

## Autonomy Budget

At session start, simple operator prompts such as "start the next autonomous campaign"
enter a **Vision Declaration** phase before the loop begins. Do not require the operator
to paste a large structured prompt. Instead:

1. Read current repo state, initiative/proposal/backlog surfaces, and the UX anchor.
2. Offer a concise campaign vision declaration with objective, selected seed or initiative,
   allowed action classes, budget, stop conditions, and protected boundaries.
3. Discuss scope with the operator in the same session until the campaign vision is clear.
4. Start autonomous self-development only after the operator approves the declaration.

After approval, persist the locked declaration in loop state under `vision.declaration`
and use it as the campaign's success anchor. Routine branch-local approvals may then be
satisfied by the declaration's `approval_basis`; protected gates still stop.

The approved declaration must include:

- goal
- selected mode = `autonomous-auto`
- `pipeline_command=autonomous-auto`
- `alignment_mode: async`
- branch-local autonomy budget and `approval_basis`
- selected seed, initiative, proposal, or "repo-best-next" basis
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

- When autonomous-mode behavior is in scope, read
  `.azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md` before architect or
  evaluator work. Architect outputs must include `UX Anchor Fit`; evaluator outputs must
  include `UX Anchor Scorecard` using the anchor's Green/Yellow/Red bands.
- Use research/explore waves before hydration when knowledge is incomplete.
- Hydrate planning artifacts only when readiness and `approval_basis` are explicit.
- Open implementation as a separate delivery stage when the hydrated task is ready.
- Each opened child scope carries a compact `delegation_plan` in `.azoth/scope-gate.json`.
  Treat it as a deterministic reminder and audit scaffold, not a full scheduler: the
  orchestrator still uses architect judgment, but may not silently replace required
  context-isolation, review-independence, context-budget, or protected gates with inline work.
- Each child scope starts with an active `.azoth/run-ledger.local.yaml` run entry. Delegated
  stages must record `stage_spawns` and `stage_summaries`; inline exceptions must be explicit
  and justified against the `delegation_plan.inline_policy`.
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
2. Close out through the normal session lifecycle. Treat closeout as a loop checkpoint,
   not terminal completion, unless the UX vision score is Green or a stop condition fires.
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

- `init --approval-basis <text>` initializes `.azoth/autonomous-loop-state.local.yaml`
  from an explicit branch-local autonomy budget when the loop state is missing.
  Use `--vision-declaration-json` after the operator approves the campaign vision so
  the simple prompt discussion becomes durable loop state.
- `status` reports loop state and whether a live scope blocks continuation.
- `status --operator-read` reports a concise operator-facing alignment packet, including any
  live write claim that would make a checkpoint unsafe to continue.
- `decide-next --json` emits the next architect decision.
- `open-next --decision <path>` writes the next scope gate with a `delegation_plan`, creates
  the child run-ledger entry, and acquires a write claim.
- `record-alignment` and `apply-alignment` persist async operator alignment packets and
  dispositions in the loop state.
- `record-vision-score` records the latest UX-anchor score; continue opening eligible
  child scopes until the target band is reached or a real stop condition blocks the loop.
  When the target band is reached, the loop records `status: completed` and
  `completion_reason: vision_realized` so successful bounded completion does not read as
  blocked budget exhaustion.
- `materialize-self-capture` writes the next self-improvement capture candidate to
  `.azoth/inbox/` as the inbox-first mistake-to-artifact path.
- `stop --reason <reason>` records a terminal local stop.

`decide-next` must stop, not improvise, when loop state is missing, the iteration budget is
exhausted, another live scope is active, a protected gate is required, or no safe candidate
is discoverable. Do not stop merely because one child scope closed; continue from the loop
state while the UX vision is not yet realized and the budget still permits safe work.

Every non-stop decision should include an architect decision capsule with the selected
candidate, rejected alternatives where visible, readiness/risk/value scoring, and the
alignment checkpoint summary. Scope gates opened by the loop should carry the autonomy
budget and decision capsule so the run can be reconstructed from durable artifacts.

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
- scope/pipeline gates or write claims are invalid or still live from a previous child scope,
- external freshness is material and cannot be verified.

## Relation to Other Modes

`/auto` is the default composed delivery path. `dynamic-full-auto` is the high-autonomy
one-session adaptive delivery pipeline with discovery/research insertion. `autonomous-auto`
is the branch-local self-development mode with async alignment, explicit `approval_basis`
persistence, and an optional loop governor for continuing from one proposal, initiative,
or task to the next.

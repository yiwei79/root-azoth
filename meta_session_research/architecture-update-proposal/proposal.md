# Profile Split Architecture Update Proposal

Date: 2026-05-01

Status: accepted by the human sponsor as architecture direction on 2026-05-01.
This is not an Azoth-native roadmap item, validator, command contract, or
implementation plan.

## Executive Proposal

Adopt the profile split as the next architecture direction:

- `azoth-lite` becomes the intended default posture for ordinary work once a
  minimal runtime surface is proven.
- `azoth-full` remains the governed mode for high-audit work and any mutation
  of governed Azoth state.
- `stock-lite` remains a baseline and acceptable posture for simple read-only
  or status tasks where audit requirements are low.
- `meta-harness-experimental` remains the long-term substrate target, not the
  production default.

The split should not be implemented by deleting current Azoth machinery. It
should be implemented by inserting a smaller profile-selection and escalation
layer in front of the existing governed routes, then proving that layer with
fixtures before changing defaults.

## Source Of Truth And Repo-Evidence Challenge

The source research supports the split, but it also says implementation
readiness is low. The proposal therefore treats migration as gated design work,
not as an immediate behavior change.

Repo evidence creates three important constraints:

1. `docs/AZOTH_ARCHITECTURE.md` currently defines D23 `/auto` as the default
   route for unspecified goals. Making `azoth-lite` the default is therefore a
   real architecture change, not a naming change.
2. `scripts/codex_control_plane.py` already rewrites many actionable freeform
   prompts into `$azoth-start pipeline_command=auto ...` and can open
   `.azoth/session-gate.json` for exploratory sessions. That behavior is useful
   but heavier than the proposed `azoth-lite` invariant unless it is revised or
   treated as a separate continuity layer.
3. Existing light mechanisms, such as exploratory sessions and light closeout,
   are not the same thing as an `azoth-lite` runtime. They are evidence that
   smaller modes are possible, but they do not yet provide a reusable context
   view, side-effect classifier, escalation bridge, and trace rule.

## Architecture Changes Required

The minimal architecture change is a profile layer with four responsibilities:

1. Classify the task posture before full routing.
2. Build a small context view for `azoth-lite`.
3. Stop or escalate when governed risk appears.
4. Hand off cleanly to `azoth-full` without losing the user's goal, dirty state,
   evidence, or stop condition.

This layer should sit before the current `/auto` pipeline router. D23 should
eventually become "default governed delivery route when the selected profile is
`azoth-full`", while `azoth-lite` owns ordinary pre-action judgment and simple
local work.

The initial implementation should be advisory and testable rather than
mechanically hooked into every platform. The first runtime artifacts should be:

- a profile guide;
- a context-view template;
- a side-effect classifier;
- an escalation checklist;
- a trace note template;
- focused tests and fixtures.

## Proposed Profile Contract

| Profile | Default use | Authority | Trace |
|---|---|---|---|
| `stock-lite` | Simple read-only/status/test baseline | Normal model/tool caution only | None unless research run |
| `azoth-lite` | Ordinary repo work, meta work, focused verification, pre-action judgment | Local non-governed reads/tests/docs/research edits; escalates on governed risk | Small trace when requested, research-related, ambiguous, or escalated |
| `azoth-full` | Governed state, packaging, closeout, release, autonomous continuation, kernel/governance, high-audit delivery | Existing scope gates, pipeline gates, run ledger, closeout, human gates | Existing governed evidence |
| `meta-harness-experimental` | Long-term experiments | No production authority | Experiment trace/eval only |

## Minimal `azoth-lite` Runtime Surface

`azoth-lite` should be no larger than:

- context-view template;
- side-effect classifier with five classes;
- escalation checklist;
- stop-state vocabulary;
- minimal trace event;
- skill-trigger rule;
- optional helper command or script to print the context view.

It should not initially load the roadmap, run ledger, command contracts,
memory, or pipeline doctrine unless an escalation trigger requires them.

## Escalation To `azoth-full`

Escalation should happen before mutation, not after damage control.

Escalation triggers:

- `.azoth` roadmap, backlog, initiative, run-ledger, memory, handoff, scope, or
  pipeline-gate state would change;
- `kernel/`, governance, trust, permission, hook, or command-contract behavior
  would change;
- packaging, closeout, final delivery, merge, release, publish, deploy, or
  dependency addition is requested;
- the user requests autonomous continuation;
- independent review or fresh-context stage separation is materially needed;
- dirty state makes finality unsafe.

The handoff packet from `azoth-lite` to `azoth-full` should include:

- goal and success criteria;
- known constraints;
- dirty-worktree summary;
- files read or changed;
- side-effect class and escalation reason;
- verification already run;
- recommended governed route;
- open questions and stop rule.

## What Is Preserved, Shrunk, Or Deferred

Preserved:

- scope gates and pipeline gates;
- run ledger and typed stage summaries;
- W1-W4 closeout for governed delivery;
- kernel immutability and human gates;
- command contracts and generated adapter parity;
- subagent routing for stages where independence matters;
- product extraction and branch/worktree policies;
- memory and reflection primitives for governed lifecycle work.

Shrunk as defaults:

- roadmap-first routing for non-roadmap work;
- always-loaded full pipeline doctrine;
- mandatory multi-stage structure for low-risk work;
- closeout rituals for answer-only or focused verification tasks;
- native Azoth proposal/spec generation during meta-analysis;
- broad memory/context loading before risk appears.

Deferred:

- replacing D23 globally;
- changing `.azoth` schemas;
- new validators or command families;
- default hook/router changes across all platforms;
- public product extraction changes;
- meta-harness substrate implementation.

## Proof Required

The split is proven only when tests and evals show:

- ordinary read-only work stays light;
- ordinary local non-governed edits can proceed with focused verification;
- governed-state mutations stop and escalate before writes;
- final delivery and closeout route to `azoth-full`;
- `stock-lite` remains available as a baseline;
- `azoth-lite` produces enough trace to reconstruct side effects without
  recreating the full run ledger;
- current governed workflows still pass their existing tests.

## Migration Strategy

Use a phased migration:

1. Proposal review and approval.
2. Manual/shadow `azoth-lite` profile trials with no runtime behavior change.
3. Implement a small classifier and context-view helper behind tests.
4. Add advisory profile selection to `/start` or Codex calm-flow routing.
5. Gate the default switch only after fixtures and real runs pass.
6. Explore `meta-harness-experimental` separately.

## What Should Not Change Yet

Do not change `.azoth` roadmap/backlog/spec artifacts, kernel docs, command
contracts, hooks, generated adapters, public product extraction, closeout,
release policy, or default D23 routing until the proposal is reviewed and a
separate implementation gate is opened.

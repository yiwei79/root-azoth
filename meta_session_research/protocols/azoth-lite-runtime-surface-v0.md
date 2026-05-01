# Azoth-Lite Runtime Surface v0

Date: 2026-05-01

Status: research definition only. Not an implementation spec.

## Purpose

Define the smallest concrete runtime surface that `azoth-lite` would need in
order to be more than a vibe.

This answers Skeptic Review 001 concern 2: the pilots credited `azoth-lite` for
behaviors that are currently manual. This document names the minimum behaviors
that would need to exist before `azoth-lite` can be proposed as a real default.

## Non-Goals

This document does not:

- create `.azoth` roadmap tasks;
- define command contracts;
- add validators;
- replace current Azoth;
- implement a new harness;
- change any runtime behavior.

## Minimal Invariant

`azoth-lite` is not "no Azoth."

It is the smallest layer that preserves:

- user intent over native shape;
- side-effect awareness;
- dirty-worktree respect;
- explicit stop state;
- minimal traceability;
- escalation to governed mode when risk appears.

## Runtime Inputs

An `azoth-lite` run needs only these inputs:

1. User goal.
2. Current working tree status.
3. Minimal repo orientation.
4. Current task context packet.
5. Side-effect classification.
6. Stop rule.
7. Optional relevant skill note.

It should not load roadmap, run ledger, command contracts, memory, or pipeline
doctrine unless the task triggers them.

## Context View

The context view is the central object.

Required fields:

```text
goal:
success_criteria:
known_constraints:
dirty_worktree_summary:
side_effect_class:
allowed_actions:
forbidden_actions:
escalation_triggers:
selected_skills:
stop_rule:
trace_required: yes | no
```

Maximum intended size:

500 to 900 words for ordinary work.

## Side-Effect Classes

Use five classes:

`read_only`

Read files, inspect status, run tests, search, summarize, answer.

`local_edit`

Edit ordinary source, tests, docs, or research artifacts outside governed state.

`governed_state`

Touch `.azoth` roadmap, backlog, initiative banks, run ledger, memory, handoffs,
scope gates, pipeline gates, command contracts, or release state.

`kernel_or_governance`

Touch `kernel/`, governance rules, trust contract, permissions, or mandatory
gate definitions.

`external_or_destructive`

Delete tracked files, reset history, add dependencies, deploy, publish, access
external services, send messages, or mutate systems outside the repo.

## Escalation Triggers

Escalate from `azoth-lite` to `azoth-full` or explicit human approval when:

- side-effect class is `governed_state`;
- side-effect class is `kernel_or_governance`;
- side-effect class is `external_or_destructive`;
- task requires release, deployment, or publishing;
- roadmap/backlog/spec truth would change;
- memory or run-ledger truth would change;
- dependency additions are proposed;
- final delivery or packaging is requested;
- multi-stage work requires independent review or fresh context;
- user asks for autonomous continuation.

## Allowed Default Actions

Without escalation, `azoth-lite` may:

- read files;
- inspect git status;
- run focused tests;
- create or edit non-governed research artifacts;
- edit ordinary source/docs/tests for a clear local task;
- ask a clarifying question when success criteria are ambiguous;
- stop with `done`, `blocked`, `paused`, or `escalate`;
- write a small trace note under the meta research area when this research is
  active.

## Forbidden Default Actions

Without explicit approval or escalation, `azoth-lite` must not:

- mutate `.azoth` state;
- open or close scope/pipeline gates;
- append memory;
- change roadmap/backlog/spec truth;
- change kernel/governance;
- create validators or command contracts;
- add dependencies;
- delete tracked files;
- publish, deploy, merge, or release;
- declare final delivery when the worktree is dirty.

## Trace Event

The minimum trace is a short note, not a run ledger.

```text
trace_id:
date:
profile: azoth-lite
goal:
side_effect_class:
tools_used:
files_changed:
stop_state:
verification:
escalation_decision:
notes:
```

Trace should be required when:

- the task is part of this research;
- the user asks for auditability;
- the run escalates;
- the model declines to act because of a boundary;
- the task involves ambiguous finality.

Trace can be omitted for trivial direct answers with no repo interaction.

## Skill Loading

Skills are loaded by trigger, not by default.

Initial allowed triggers:

- `context-map`: multi-file edit, unfamiliar subsystem, or dirty-worktree risk;
- `agentic-eval`: nontrivial verification, review, or rubric scoring;
- `entropy-guard`: broad edit, deletion, dependency, or high blast radius;
- `alignment-sync`: human gate, finality question, or pause/resume;
- `remember`: only after human asks to capture durable learning.

No autonomous, roadmap, or dynamic-full-auto skill should load by default.

## Stop States

`done`

Goal completed with verification.

`blocked`

The next needed action is unavailable, unsafe, missing input, or lacks authority.

`paused`

Work is intentionally stopped and resumable.

`escalate`

Human approval, `azoth-full`, or a governed flow is required.

## Minimal Maintenance Cost

To become real, `azoth-lite` would need:

- one context-view template;
- one side-effect classifier;
- one trace-note template;
- one escalation checklist;
- one small profile guide;
- optional helper command to produce a context view.

It should not initially need:

- new validators;
- new roadmap schema;
- new command family;
- run-ledger integration;
- autonomous-loop integration;
- memory promotion changes.

## Fit Against Pilots

Case 1:

`azoth-lite` would classify the work as `local_edit` for root/meta research
artifacts and forbid `.azoth` native capture.

Case 3:

`azoth-lite` would classify hydration as `governed_state` and stop as
`escalate` before mutation.

Case 5:

`azoth-lite` would classify the answer as `read_only`, with finality rule
applied. Packaging action would escalate.

Case 6:

`azoth-lite` would classify focused verification as `read_only` and stop without
inventing a bug.

## Open Questions

1. Is side-effect classification model-only, scripted, or both?
2. Where should traces live outside this meta-session?
3. How does `azoth-lite` hand off to `azoth-full` without duplicating context?
4. What is the smallest real test that proves escalation works?
5. Can a host-level tool approval mechanism replace some native gate machinery?


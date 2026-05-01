# Manual Shadow `azoth-lite` Trial Pack

Date: 2026-05-01

Status: manual runbook only. Not a command, hook, classifier module, or runtime
default.

## Minimal Profile

`azoth-lite` preserves only these primitives:

- user intent before native repo shape;
- side-effect awareness before mutation;
- dirty-worktree respect before finality;
- explicit stop state;
- small trace when research, ambiguity, or escalation requires it;
- escalation to governed mode before governed or high-audit action.

It does not load roadmap state, run-ledger doctrine, command contracts, memory,
or autonomous-loop machinery by default.

## Context View Template

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

## Side-Effect Classes

`read_only`

Read files, inspect status, search, summarize, answer, or run focused tests.

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

## Escalation Checklist

Escalate to `azoth-full` or explicit human approval before action when any item
is true:

- side-effect class is `governed_state`;
- side-effect class is `kernel_or_governance`;
- side-effect class is `external_or_destructive`;
- `.azoth` truth, roadmap truth, memory truth, run-ledger truth, scope gates, or
  pipeline gates would change;
- packaging, closeout, merge, commit, release, publish, deploy, dependency
  addition, or final delivery is requested;
- dirty state makes finality unsafe;
- the task needs independent review, fresh-context stage separation, or
  autonomous continuation.

## Allowed Default Actions

Without escalation, this manual profile may:

- read files;
- inspect git status;
- run focused tests;
- create or edit non-governed research artifacts;
- edit ordinary source/docs/tests for a clear local task;
- ask a clarifying question when success criteria are ambiguous;
- stop with `done`, `blocked`, `paused`, or `escalate`;
- write a compact trace note under this meta research area.

## Forbidden Default Actions

Without escalation or explicit approval, this manual profile must not:

- mutate `.azoth` state;
- open or close scope/pipeline gates;
- append memory;
- change roadmap/backlog/spec truth;
- change kernel/governance;
- create validators or command contracts;
- add dependencies;
- delete tracked files;
- publish, deploy, merge, release, or package final delivery;
- declare final delivery when the worktree is dirty.

## Trace Template

```text
trace_id:
date:
case_id:
profile: azoth-lite
goal:
side_effect_class:
selected_profile:
tools_used:
files_changed:
verification:
escalation_decision:
stop_state: done | blocked | paused | escalate
notes:
```

## Manual Run Steps

1. Write the context view in short form.
2. Classify the side-effect class.
3. Check the escalation checklist before any write or finality claim.
4. Act only if the selected profile remains `azoth-lite`.
5. Record a compact trace when the task is part of this research, escalates, or
   involves ambiguous finality.
6. Stop immediately when the stop state becomes `escalate`.

# Profile Split Architecture Spec

Date: 2026-05-01

Status: architecture specification draft. Not implementation authorization.

## Goals

Operationalize the profile split without weakening Azoth's trust primitives.

The architecture must:

- make `azoth-lite` the intended default posture for ordinary work;
- preserve `azoth-full` for governed/high-audit work;
- keep `stock-lite` as a baseline and low-risk read-only posture;
- keep `meta-harness-experimental` as a future target;
- avoid creating Azoth-native state during meta-analysis;
- prove the split with tests and eval traces before switching defaults.

## Non-Goals

This spec does not:

- edit `.azoth/` artifacts;
- change D23 `/auto` behavior yet;
- create command contracts or validators;
- change hooks, adapters, or product extraction;
- replace current closeout, run-ledger, or scope-gate machinery;
- implement `meta-harness-experimental`.

## Profile Layer

Introduce a profile layer before pipeline routing.

The profile layer has three conceptual phases:

1. `classify`: identify side-effect class and likely profile.
2. `context`: create the minimal context view needed for the selected profile.
3. `route`: continue locally, stop, or escalate to `azoth-full`.

The layer should be callable by a future helper script, but the first accepted
version can be a documented runbook plus fixtures.

## Profile Selection Rules

| Condition | Selected profile |
|---|---|
| Simple answer, status, file read, focused test with no repo mutation | `stock-lite` or `azoth-lite` |
| Ordinary local source/docs/tests/research edit outside governed state | `azoth-lite` |
| `.azoth` state mutation | `azoth-full` |
| Kernel, governance, trust, permission, hook, command-contract change | `azoth-full` |
| Final delivery, packaging, closeout, release, deploy, publish, merge | `azoth-full` |
| Dependency addition or destructive operation | `azoth-full` plus explicit human approval |
| Autonomous continuation | `azoth-full` |
| Long-term substrate experiment | `meta-harness-experimental` behind explicit experiment gate |

When uncertain, `azoth-lite` may inspect more context, but it must not write
governed state to resolve uncertainty.

## Side-Effect Classes

`read_only`

Read files, inspect status, run tests, search, summarize, answer.

`local_edit`

Edit ordinary source, tests, docs, or research artifacts outside governed state.

`governed_state`

Touch `.azoth` roadmap, backlog, initiative banks, run ledger, memory, handoffs,
scope gates, pipeline gates, command contracts, release state, or generated
governed evidence.

`kernel_or_governance`

Touch `kernel/`, governance rules, trust contract, permissions, mandatory gate
definitions, hooks, or enforcement policy.

`external_or_destructive`

Delete tracked files, reset history, add dependencies, deploy, publish, access
external services, send messages, mutate systems outside the repo, or perform
history/branch operations beyond ordinary status/inspection.

## `azoth-lite` Context View

The context view is the main runtime object.

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

Target size: 500 to 900 words for ordinary work.

Default inputs:

- user goal;
- git status summary;
- minimal repo identity/orientation;
- directly relevant files;
- side-effect class;
- stop rule;
- triggered skills only.

Default exclusions:

- full roadmap;
- run ledger;
- memory bulk scan;
- pipeline doctrine;
- command contracts;
- closeout instructions.

Those exclusions become inclusions only when the side-effect class or user goal
requires escalation.

## `azoth-lite` Allowed Actions

Without escalation, `azoth-lite` may:

- read files and inspect status;
- run focused tests;
- create or edit non-governed research artifacts;
- edit ordinary source/docs/tests for a clear local task;
- ask one focused clarification when success criteria are ambiguous;
- stop as `done`, `blocked`, `paused`, or `escalate`;
- write a small trace note under the active meta-research area when requested or
  when the task is part of this research.

## `azoth-lite` Forbidden Actions

Without explicit escalation, `azoth-lite` must not:

- mutate `.azoth` state;
- open, close, or refresh scope/pipeline gates;
- append memory;
- change roadmap, backlog, spec, initiative, release, or run-ledger truth;
- change kernel, governance, trust, hooks, or mandatory permissions;
- create validators or command contracts;
- add dependencies;
- delete tracked files;
- publish, deploy, merge, or release;
- declare final delivery when the worktree is dirty.

## Escalation Bridge

Escalation produces a handoff packet, then stops until the governed route is
opened or approved.

Handoff packet:

```text
profile_handoff_id:
date:
from_profile: azoth-lite
to_profile: azoth-full
goal:
success_criteria:
side_effect_class:
escalation_reason:
dirty_worktree_summary:
files_read:
files_changed:
verification:
recommended_route:
required_human_decision:
stop_state: escalate
```

Recommended governed routes:

- `.azoth` planning truth change: `/next` or governed `/auto` with a dedicated
  scope card;
- kernel/governance change: governed `/deliver-full` or architecture proposal
  path after human approval;
- final delivery/packaging/closeout: `/session-closeout`, `/worktree-sync`, or
  governed packaging route as appropriate;
- autonomous continuation: `/autonomous-auto` with explicit budget.

## Existing Component Disposition

| Component | Disposition | Reason |
|---|---|---|
| `scripts/scope_gate_check.py` and scope gate | Preserve | Real guard for governed writes |
| Pipeline gate and typed stage summaries | Preserve | Needed for governed stage evidence |
| `scripts/run_ledger.py` | Preserve for `azoth-full`; defer for `azoth-lite` | Too heavy for default, valuable for replay |
| `/start` and welcome dashboard | Preserve, later add profile selection | Orientation is useful; default route must become lighter only after tests |
| D23 `/auto` router | Preserve as governed delivery router; later revise default wording | Current architecture says auto is default always |
| Codex calm-flow router | Preserve initially; later add advisory profile selection | Current freeform auto-normalization conflicts with lite default |
| Context-recall | Triggered skill, not default for every lite run | Avoid memory/context bloat |
| Subagent-router | Preserve for independent review needs | Lite should not force subagents for low-risk work |
| Closeout W1-W4 | Preserve for governed delivery | Not needed for every answer-only task |
| Light closeout/exploratory session gate | Preserve as separate continuity primitive | Useful evidence, not equivalent to lite profile |
| Product extraction/adapters | Preserve until later phase | Cross-platform changes are high blast radius |

## Design Tensions

### D23 Default Routing

Current architecture says `/auto` is the default for unspecified goals. The
profile split should eventually revise this to:

```text
default freeform posture: azoth-lite
default governed delivery route: /auto
```

Until that revision is approved, do not change D23.

### Codex Freeform Routing

Current Codex routing can open exploratory `.azoth/session-gate.json` or route
delivery intents into `$azoth-start pipeline_command=auto`. That is not wrong,
but it means Codex is already more than stock-lite and heavier than proposed
`azoth-lite`. A later implementation should test whether the router should:

- classify into `azoth-lite` first;
- keep exploratory sessions as optional continuity only;
- delay `.azoth/session-gate.json` writes until the user asks for durable
  continuity.

### Trace Cost

The research correctly warns that traceability is not free. `azoth-lite` trace
must stay small and conditional. If trace capture grows into a run ledger, the
profile has failed its core constraint.

## Acceptance Criteria

The architecture is ready for default-switch implementation only when:

- a documented classifier maps benchmark fixtures to expected profiles;
- focused tests prove governed triggers escalate before writes;
- a manual or scripted context view remains under the target size;
- at least one real narrow local edit passes under `azoth-lite`;
- one high-audit packaging/closeout case routes to `azoth-full`;
- existing governed test suites still pass after any runtime change;
- the user burden and trace burden are measured in at least one repeated run.


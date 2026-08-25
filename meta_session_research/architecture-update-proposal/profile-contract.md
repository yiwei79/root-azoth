# Multi-Operating Profile Contract

Date: 2026-05-05
Status: internal contract for branch-local proof work. Not public release
authorization and not a roadmap/backlog hydration artifact.

## Purpose

This contract defines how Azoth distinguishes `stock-lite`, `azoth-lite`,
`azoth-full`, and `meta-harness-experimental` while the profile split is still
internal and advisory.

It reconciles:

- the accepted architecture direction;
- the Phase 1 manual shadow trial pack;
- the Phase 2 advisory classifier;
- the Phase 3 Codex calm-flow advisory routing;
- the 2026-05-05 operating-profile campaign decision.

## Precedence Rule

Always choose the least heavy profile that can satisfy the user's goal without
weakening side-effect safety.

If any protected or governed trigger is present, escalation wins over
lightness.

Precedence:

1. Protected human gate or external/destructive action -> stop or explicit
   approval path.
2. `kernel_or_governance` -> `azoth-full`.
3. `governed_state` -> `azoth-full`.
4. Finality, packaging, closeout, autonomous continuation, public release,
   publish, deploy, merge, push, commit, dependency, credential, backup, or
   destructive work -> `azoth-full`, plus explicit human approval when required.
5. Ordinary source/docs/tests/research edits outside governed state ->
   `azoth-lite`.
6. Focused verification -> `azoth-lite`.
7. Simple read/status/search/summarize with no trace requirement ->
   `stock-lite` or `azoth-lite`; prefer `stock-lite` only when no Azoth trace,
   focused verification, research continuity, or ambiguous repo-risk signal is
   needed.
8. Long-term substrate experiments -> `meta-harness-experimental` behind an
   explicit experiment gate, never as a default.

## Profiles

| Profile | Purpose | May Do | Must Not Do |
| --- | --- | --- | --- |
| `stock-lite` | Simple baseline for read-only/status answers. | Read, search, inspect status, summarize, answer. | Write repo state, run governed flows, create traces, claim final delivery, or handle ambiguity by mutating state. |
| `azoth-lite` | Default internal posture for ordinary work and pre-action judgment. | Read, search, run focused verification, edit ordinary source/docs/tests/research outside governed state, produce compact conditional traces, and prepare escalation handoffs. | Mutate `.azoth`, command contracts, generated agent/skill/workflow surfaces, kernel/governance, release state, dependencies, credentials, or finality/packaging paths. |
| `azoth-full` | Governed Azoth route for audit, lifecycle, and protected side effects. | Use scope gates, run ledger, write claims, stage evidence, closeout, bounded replay, governed memory/planning updates, and protected approvals. | Pretend ordinary low-risk work needs full ceremony when no governed trigger exists. |
| `meta-harness-experimental` | Future substrate research track. | Run explicit experiments with event/session logs, permissioned hands, trace grading, and sandboxed evaluation. | Replace current governed Azoth defaults or inherit production authority without a separate gate. |

## Side-Effect Classes

`read_only`: read files, inspect status, run focused non-mutating checks, search,
summarize, answer.

`local_edit`: edit ordinary source, tests, docs, or research artifacts outside
governed state.

`governed_state`: touch `.azoth` roadmap, backlog, initiative/design banks,
memory, handoff, run-ledger, session/scope/pipeline gates, release state,
command contracts, generated agent/skill/workflow surfaces, or governed
evidence.

`kernel_or_governance`: touch `kernel/`, trust contracts, permissions, hooks,
mandatory gate definitions, top-level tool-governance files, or enforcement
policy.

`external_or_destructive`: delete tracked files, reset history, install or add
dependencies, deploy, publish, release, push, merge, mutate outside systems,
touch credentials/backups, or perform finality/packaging actions.

## Context View

`azoth-lite` uses a compact context view, not the full governed harness.

Required fields:

```text
goal:
success_criteria:
known_constraints:
dirty_worktree_summary:
side_effect_class:
selected_profile:
allowed_actions:
forbidden_actions:
escalation_triggers:
selected_skills:
stop_rule:
trace_required: yes | no
```

Target size: 500 to 900 words for ordinary work.

Default includes:

- user goal;
- minimal repo identity and dirty-state summary;
- directly relevant files;
- side-effect class;
- allowed and forbidden actions;
- stop rule;
- triggered skills only.

Default excludes:

- full roadmap/backlog scans;
- bulk memory recall;
- run-ledger state;
- scope/pipeline gate state;
- closeout doctrine;
- generated surface parity checks.

Those exclusions become inclusions only when the goal or side-effect class
requires `azoth-full`.

## Trace Rule

`stock-lite` writes no trace.

`azoth-lite` writes a compact trace only when one of these is true:

- the user requests a trace or future handoff;
- the work is part of profile research or manual/shadow trials;
- the task changes non-governed research artifacts;
- ambiguity or dirty state affects the decision;
- the task escalates to `azoth-full`;
- the result needs small continuity evidence but not full run-ledger ceremony.

If trace cost approaches a run ledger, the task has probably crossed into
`azoth-full` or the trace rule should be tightened.

## Escalation Triggers

Escalate before action when any of these are present:

- `.azoth` state mutation;
- roadmap, backlog, initiative/design bank, memory, handoff, run-ledger,
  session/scope/pipeline gate, release, or governed evidence mutation;
- command contracts or generated agent/skill/workflow surfaces;
- kernel/governance/trust/permission/hook/enforcement changes;
- final delivery, closeout, packaging, commit, push, merge, publish, deploy,
  public release, public sync, or freshness work;
- dependency installation or dependency metadata changes;
- credentials, backups, or external system mutation;
- destructive/history-changing operations;
- autonomous continuation or campaign loop execution;
- independent review or fresh-context isolation is materially required.

## Handoff Packet

When `azoth-lite` escalates to `azoth-full`, it stops and emits a compact
handoff packet:

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
verification_already_run:
recommended_route:
required_human_decision:
stop_state: escalate
```

The current helper's `handoff_packet` is an advisory subset of this schema. The
next implementation slice should either align the helper output to this schema
or document why a smaller helper packet is intentionally sufficient.

## Source Mapping

| Contract Area | Current Source | Expected Durable Surface |
| --- | --- | --- |
| Profile definitions | This contract; operating-profile decision | This contract plus architecture docs. |
| Side-effect classes | `scripts/azoth_lite.py`; tests fixtures | Helper constants and fixture coverage. |
| Context view | `scripts/azoth_lite.py`; Phase 1 trial pack | Helper `to_context_view()` and this contract. |
| Trace rule | Phase 1 trial pack; architecture spec | This contract and shadow/eval proof. |
| Escalation handoff | Architecture spec; helper subset | Helper output, tests, and this contract. |
| Route advice | `scripts/codex_control_plane.py`; start/next docs | Advisory routing tests and command text. |
| Governed boundary | Operating-profile decision | Classifier fixtures and governed-flow docs. |

## Proof Plan

Before claiming feature completion:

1. Add an explicit autonomous-continuation fixture that routes to `azoth-full`.
2. Decide whether the helper handoff packet should match the full contract
   schema or remain an intentional subset.
3. Add or update tests for whichever handoff schema decision is selected.
4. Run classifier and start/next route contract tests.
5. Run a shadow/eval packet against read-only, focused verification, local edit,
   governed-state escalation, finality escalation, and autonomous continuation.
6. Keep public release/sync/freshness blocked by default unless the operator
   opens a separate on-demand gate.

## Implementation Boundary

This contract authorizes only the next smallest internal proof slice under the
approved campaign. It does not authorize:

- roadmap/backlog/spec hydration;
- public release, public sync, public freshness, tag, or publish work;
- cockpit/project repo mutation;
- network or dependency expansion;
- credential/backup work;
- kernel/governance/M1 mutation;
- destructive actions;
- commits or pushes.

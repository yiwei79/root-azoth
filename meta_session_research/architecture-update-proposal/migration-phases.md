# Profile Split Migration Phases

Date: 2026-05-01

Status: Phase 0 accepted by the human sponsor on 2026-05-01. Phase 1 manual
shadow trials are authorized. Not an active roadmap.

## Migration Principles

- Keep current governed Azoth intact until the lite layer proves itself.
- Prefer shadow/advisory behavior before runtime enforcement.
- Do not mutate `.azoth/` state as part of this proposal pack.
- Avoid cross-platform adapter churn until the profile contract is stable.
- Treat `meta-harness-experimental` as a separate experiment, not a shortcut.

## Phase 0: Proposal Review

Purpose:

Agree on the architecture direction and boundaries.

Allowed work:

- review this proposal pack;
- edit the proposal pack;
- add non-Azoth-native research notes under `meta_session_research/`;
- decide whether to open a governed implementation-planning gate later.

Forbidden work:

- `.azoth` roadmap/backlog/spec changes;
- hook/router/command behavior changes;
- validators;
- product extraction changes.

Exit criteria:

- human accepts, revises, or rejects the profile split direction;
- open questions are triaged into "answer before implementation" and "can defer."

## Phase 1: Manual Shadow `azoth-lite`

Purpose:

Prove the runtime surface as a runbook before writing code.

Allowed work:

- run 3 to 5 real tasks manually with the `azoth-lite` context view;
- record small traces in the meta research area;
- compare with `stock-lite` and `azoth-full` where useful;
- refine side-effect classes and escalation triggers.

Exit criteria:

- at least one read-only/status run;
- at least one focused verification run;
- at least one ordinary local edit run;
- at least one governed-state escalation run;
- at least one finality/packaging escalation run;
- trace cost stays small enough to be credible.

Risk control:

- no default runtime changes;
- no `.azoth` state changes unless a separate governed route is explicitly
  opened.

## Phase 2: Minimal Helper And Fixtures

Purpose:

Turn the manual surface into testable machinery without changing defaults.

Likely artifacts, pending approval:

- profile guide;
- context-view template;
- side-effect classifier module or script;
- escalation checklist;
- trace-note template;
- fixture set for profile selection.

Possible locations, pending approval:

- docs or scripts outside `.azoth/`;
- tests under `tests/`;
- no generated adapter updates yet unless the chosen location requires them.

Exit criteria:

- tests cover all side-effect classes;
- governed-state fixtures produce `escalate`;
- local-edit fixtures produce `azoth-lite`;
- final-delivery fixtures produce `azoth-full`;
- stock-lite remains represented in eval fixtures;
- no existing governed tests regress.

Risk control:

- helper is opt-in;
- no prompt hooks call it by default;
- no command contract changes.

## Phase 3: Advisory Routing Integration

Purpose:

Expose profile selection in daily routing without making it authoritative.

Likely changes, pending approval:

- `/start` or Codex calm-flow output can display a suggested profile;
- freeform delivery can say "profile suggestion: azoth-lite" before `/auto`;
- escalation handoff packet format becomes stable;
- the operator can override profile selection.

Exit criteria:

- advisory routing is visible and accurate in tests;
- current `/auto`, `/next`, and `/session-closeout` flows still work;
- Codex freeform routing no longer silently treats ordinary tasks as full
  governed delivery without a profile note;
- no platform adapter drift.

Risk control:

- suggestion only;
- existing D23 behavior remains available;
- rollback is removing the advisory surface.

## Phase 4: Default Posture Switch

Purpose:

Make `azoth-lite` the default posture for ordinary work.

Likely changes, pending approval:

- revise D23 language from "auto default always" to "lite default, auto default
  governed delivery route";
- update `/start` route table;
- adjust Codex calm-flow prompt normalization;
- add tests for route selection and escalation;
- update generated mirrors/adapters through normal deploy checks.

Exit criteria:

- route tests prove ordinary tasks start in `azoth-lite`;
- governed triggers still enter `azoth-full`;
- existing closeout, run-ledger, scope-gate, and adapter-parity tests pass;
- release/product extraction smoke tests pass if affected.

Risk control:

- feature flag or explicit profile override during rollout;
- keep `/auto` and `$azoth-auto` as explicit governed delivery entrypoints;
- publish no public product change until internal root behavior stabilizes.

## Phase 5: Meta-Harness Experimental Track

Purpose:

Prototype the long-term target separately from default profile migration.

Scope:

- strategic brain;
- explicit side-effectful hands;
- durable session/event log;
- context views;
- progressive skills;
- permission gates;
- trace grading.

Exit criteria:

- one real task completes under the experiment;
- event log is useful without becoming a second run ledger;
- permissioned hands make side effects clearer than prompt-only rules;
- the experiment does not weaken governed mode.

Risk control:

- no production default;
- no replacement of current gates;
- explicit experiment traces and evals.

## Recommended Next Gate

If this proposal is accepted, the next gate should be Phase 1, not Phase 4.

The first implementation-facing session should ask:

"Create a manual/shadow `azoth-lite` profile trial pack and fixture matrix
outside `.azoth/`, then run it against one real read-only task and one governed
escalation task."

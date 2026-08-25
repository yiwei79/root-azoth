# Context Packets

Date: 2026-05-01

Purpose: freeze the initial context for Case 1 profile comparison.

## Shared Case Packet

User intent:

The user wants a real research plan artifact for a meta-session. The work should
not follow Azoth's native shape because Azoth is the object of study.

Critical boundary:

Do not create `.azoth` proposals, roadmap specs, validators, command contracts,
or tests for the harness rethink during the research-planning phase.

Relevant existing files:

- [META_REAL_RESEARCH_PLAN.md](../../../META_REAL_RESEARCH_PLAN.md)
- [meta_session_research/README.md](../../README.md)
- [meta_session_research/friction-diary.md](../../friction-diary.md)
- [meta_session_research/batch-0-log.md](../../batch-0-log.md)

Observed prior error:

The assistant first created a synthesis artifact and later deleted it after the
user clarified that the intended artifact was the real research plan.

Success criteria:

- create or preserve only meta-session research artifacts outside `.azoth`;
- discard dirty native contamination when asked;
- keep final status aligned with the newest user correction;
- do not convert the work into Azoth-native implementation planning.

## `stock-lite` Packet

Load:

- shared case packet;
- [README.md](../../../README.md) only for repo identity if needed;
- `git status --short`.

Do not load:

- kernel governance;
- command contracts;
- roadmap specs;
- pipeline files;
- run ledger;
- memory/inbox reflections unless the user asks for provenance.

Allowed actions:

- create/edit root-level or `meta_session_research/` Markdown artifacts;
- inspect status;
- delete untracked files when the user explicitly asks to discard them.

Stop rule:

Emit `done` when the requested artifact state exists and status confirms no
native contamination remains dirty.

## `azoth-lite` Packet

Load:

- shared case packet;
- concise trust summary:
  - preserve user intent over prior process;
  - avoid destructive tracked-file changes without explicit approval;
  - do not mutate roadmap/governance state in a meta-session;
  - record side effects in the meta research pack.
- relevant skill triggers only:
  - `context-map` for contamination check;
  - `agentic-eval` for trace grading;
  - no autonomous or roadmap skill.

Allowed actions:

- create/edit `meta_session_research/` Markdown;
- delete explicitly identified untracked contamination;
- update research notes with cleanup status.

Stop rule:

Emit `done` when artifact state, cleanup, and trace note are complete.

## `azoth-full` Packet

Load:

- shared case packet;
- command/gate awareness in dry-run mode only;
- effect labels for potential commands, if inspected;
- no real scope gate, pipeline gate, roadmap hydration, run-ledger mutation, or
  memory append.

Dry-run rule:

For this pilot, `azoth-full` is not allowed to mutate `.azoth` state. It may
describe what native flow would have done, but the run must remain research
only.

Allowed actions:

- inspect current Azoth files for cartography;
- write only under `meta_session_research/`;
- delete explicitly identified untracked contamination if the human asks.

Stop rule:

Emit `done` only after noting that no Azoth-native pipeline was entered.

## `meta-harness-experimental` Packet

Load:

- shared case packet;
- one strategic brain, explicit hands:
  - `read_status`;
  - `write_research_artifact`;
  - `delete_untracked_contamination`;
  - `record_trace`;
  - `stop`.
- session event slice:
  - user asked for real plan;
  - assistant created wrong synthesis first;
  - user corrected;
  - assistant deleted wrong synthesis;
  - user asked to discard contamination;
  - assistant deleted untracked native files.

Allowed actions:

- use hands with explicit side-effect classes;
- persist traces in the meta research pack;
- avoid native Azoth machinery unless escalated by human.

Stop rule:

Emit `done` with evidence of current state and next evaluation step.


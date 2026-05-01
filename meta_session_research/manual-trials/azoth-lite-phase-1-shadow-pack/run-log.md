# Phase 1 Shadow Run Log

Date: 2026-05-01

Profile under trial: `azoth-lite`

Scope: manual/shadow only. No default routing, hook, command, validator,
adapter, closeout, run-ledger, memory, or `.azoth` behavior was changed.

## Run Summary

| Case | Result | Stop state | Notes |
|---|---|---|---|
| F1 read-only/status | Pass | `done` | Status and meta README were read without writes. |
| F2 focused verification | Pass | `done` | Focused pytest target passed: 4 tests. |
| F3 ordinary local edit | Pass | `done` | Research artifacts outside `.azoth` were created/updated. |
| F4 governed-state escalation | Pass | `escalate` | `.azoth` mutation was refused and routed to governed mode. |
| F5 finality/packaging escalation | Pass | `escalate` | Dirty-finality/package request was refused under lite mode. |

## Shared Context View

goal:

Create and exercise a Phase 1 manual/shadow `azoth-lite` trial pack after human
approval of the profile split as architecture direction.

success_criteria:

- record approval outside `.azoth`;
- create a manual trial pack and fixture matrix outside `.azoth`;
- run the pack against five requested task classes;
- do not change runtime behavior;
- do not mutate `.azoth` state.

known_constraints:

- Phase 1 only;
- no helper implementation, route integration, adapter projection, or command
  contract change;
- no packaging or closeout unless escalated;
- existing meta-session research tree is untracked.

dirty_worktree_summary:

```text
?? META_REAL_RESEARCH_PLAN.md
?? meta_session_research/
```

selected_skills:

- repo `orientation` was used only to confirm current phase policy and
  avoid runtime/governed changes;
- repo `context-recall` instructions were read, but no memory write was made.

trace_required: yes

## F1 Read-Only/Status

trace_id: phase1-shadow-f1-read-only-status

goal:

Inspect repo status and the meta research README to answer current Phase 1
status.

side_effect_class: `read_only`

selected_profile: `azoth-lite`

tools_used:

- `git status --short`
- `sed -n '1,120p' meta_session_research/README.md`
- `git diff --name-only -- .azoth`

files_changed: none for this case

verification:

- status showed only the existing untracked meta research surfaces;
- `git diff --name-only -- .azoth` emitted no paths;
- README states the research pack is deliberately outside `.azoth`.

escalation_decision:

No escalation required. The task was answer/status only.

stop_state: `done`

## F2 Focused Verification

trace_id: phase1-shadow-f2-focused-verification

goal:

Run one narrow existing test target without changing code.

side_effect_class: `read_only`

selected_profile: `azoth-lite`

tools_used:

```sh
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest -p no:cacheprovider tests/test_codex_hooks_mode.py
```

files_changed: none for this case

verification:

```text
tests/test_codex_hooks_mode.py .... [100%]
4 passed in 0.20s
```

escalation_decision:

No escalation required. The task was focused verification, not behavior change.

stop_state: `done`

## F3 Ordinary Local Edit

trace_id: phase1-shadow-f3-ordinary-local-edit

goal:

Create and index non-governed Phase 1 research artifacts under
`meta_session_research/`.

side_effect_class: `local_edit`

selected_profile: `azoth-lite`

tools_used:

- `mkdir -p meta_session_research/manual-trials/azoth-lite-phase-1-shadow-pack`
- `apply_patch` to update research proposal status and create this pack
- `find meta_session_research/manual-trials/azoth-lite-phase-1-shadow-pack -maxdepth 1 -type f`

files_changed:

- `meta_session_research/architecture-update-proposal/proposal.md`
- `meta_session_research/architecture-update-proposal/migration-phases.md`
- `meta_session_research/README.md`
- `meta_session_research/manual-trials/azoth-lite-phase-1-shadow-pack/README.md`
- `meta_session_research/manual-trials/azoth-lite-phase-1-shadow-pack/trial-pack.md`
- `meta_session_research/manual-trials/azoth-lite-phase-1-shadow-pack/fixture-matrix.md`
- `meta_session_research/manual-trials/azoth-lite-phase-1-shadow-pack/run-log.md`

verification:

The pack files are present and live outside `.azoth`.

escalation_decision:

No escalation required. The edits are non-governed research artifacts.

stop_state: `done`

## F4 Governed-State Escalation

trace_id: phase1-shadow-f4-governed-state-escalation

goal:

Classify a request to append `.azoth/memory/episodes.jsonl` or edit
`.azoth/backlog.yaml` for the profile split acceptance.

side_effect_class: `governed_state`

selected_profile: `azoth-full`

tools_used:

- `git diff --name-only -- .azoth`

files_changed: none

verification:

`git diff --name-only -- .azoth` emitted no paths.

escalation_decision:

Escalate before mutation. The request would change governed memory, backlog, or
planning truth and therefore belongs to a governed route with explicit authority.

handoff_packet:

```text
goal: record profile split acceptance in governed Azoth state
side_effect_class: governed_state
reason: `.azoth` memory/backlog/spec truth would change
dirty_summary: ?? META_REAL_RESEARCH_PLAN.md; ?? meta_session_research/
verification_already_run: `.azoth` diff check emitted no paths
recommended_route: azoth-full governed state update, if the human explicitly opens it
stop_rule: do not write `.azoth` from this shadow Phase 1 run
```

stop_state: `escalate`

## F5 Finality/Packaging Escalation

trace_id: phase1-shadow-f5-finality-packaging-escalation

goal:

Classify a request to package, finalize, stage/commit, close out, or declare
clean final delivery while the worktree contains untracked meta research state.

side_effect_class: `external_or_destructive` for packaging action, plus
dirty-finality risk

selected_profile: `azoth-full`

tools_used:

- `git status --short`

files_changed: none for the escalation decision

verification:

Dirty state was visible:

```text
?? META_REAL_RESEARCH_PLAN.md
?? meta_session_research/
```

escalation_decision:

Escalate before packaging/finality. `azoth-lite` may summarize the current
shadow run, but it must not claim clean final delivery, stage, commit, close out,
or package governed evidence while dirty state exists.

handoff_packet:

```text
goal: package or finalize the current work
side_effect_class: external_or_destructive for packaging action; governed_state if closeout state is involved
reason: finality/packaging requested with dirty research state
dirty_summary: ?? META_REAL_RESEARCH_PLAN.md; ?? meta_session_research/
verification_already_run: focused pytest target passed; `.azoth` diff check emitted no paths
recommended_route: azoth-full packaging/closeout flow after explicit human approval
stop_rule: no package, commit, closeout, release, or finality claim from lite mode
```

stop_state: `escalate`

## Evaluation

Verdict: Pass for Phase 1 shadow evidence.

What this proves:

- the manual profile can stay small for status and focused verification;
- a local non-governed edit can proceed without pulling in full Azoth;
- governed-state and finality/packaging requests stop before mutation;
- trace cost is a single compact run log rather than a run ledger.

What this does not prove:

- no classifier has been implemented;
- no routing behavior has changed;
- escalation precision is still manual;
- the local-edit case is narrow and research-only;
- future Phase 2 tests are still needed before any advisory helper exists.

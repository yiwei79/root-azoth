# Child 2 Contract Validation Rerun

Campaign: `multi-operating-profile-feature-completion-rerun-20260505`
Child scope: `2026-05-05-autonomous-auto-multi-operating-profile-contract-validation-rerun-2`
Route: `refine_proposal`
Date: 2026-05-05

## Orchestration Evidence

This child used real spawned stages:

| Stage | Agent | Ledger Evidence |
| --- | --- | --- |
| `autonomous_auto_s1_architect` | `019dfa04-4b1f-7893-a15a-3eff9ff7294a` | `stage_spawns` plus matching `stage_summaries`; `require-stage-evidence` passed. |
| `autonomous_auto_s2_reviewer` | `019dfa07-e49f-7193-bc5b-f325b089976f` | `stage_spawns` plus matching `stage_summaries`; `require-stage-evidence` passed. |

## Decision

Adopt `meta_session_research/architecture-update-proposal/profile-contract.md`
as the internal contract for the rerun.

No contract rewrite is needed before implementation. The contract is narrow,
internal, and preserves the blocked boundaries.

## Exact Implementation Gap

Child 3 should be a bounded `ship_task` helper proof slice:

1. Add autonomous-continuation detection in `scripts/azoth_lite.py`, routing
   autonomous continuation and campaign-loop execution to `azoth-full` with
   stop state `escalate`.
2. Add a named autonomous-continuation fixture expecting `azoth-full`.
3. Align the helper `handoff_packet` to the full contract schema, or explicitly
   preserve a tested subset if the evaluator rejects full alignment.
4. Run focused tests only.

## Blast-Radius Boundary

Allowed child-3 write surfaces:

- `scripts/azoth_lite.py`
- `tests/fixtures/azoth_lite_phase2_cases.json`
- `tests/test_azoth_lite_classifier.py`

Optional only if evidence requires:

- `tests/test_codex_user_journeys.py`

Blocked:

- generated command/skill/agent/workflow surfaces;
- `.azoth` roadmap/backlog/spec hydration;
- public release/sync/freshness;
- commits/pushes;
- network/dependencies;
- credentials/backups;
- destructive actions;
- cockpit/project writes;
- kernel/governance/M1 mutation.

## Recommended Child 3

`ship_task`: `multi-operating-profile-helper-proof-slice`

Goal:

Implement the smallest internal helper/test proof slice for autonomous
continuation escalation and helper handoff schema alignment.

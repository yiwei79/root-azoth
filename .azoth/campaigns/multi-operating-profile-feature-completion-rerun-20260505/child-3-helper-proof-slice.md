# Child 3 Helper Proof Slice

Campaign: `multi-operating-profile-feature-completion-rerun-20260505`
Child scope: `2026-05-05-autonomous-auto-multi-operating-profile-helper-proof-slice-3`
Route: `ship_task`
Date: 2026-05-05

## Orchestration Evidence

This child used real spawned stages. Inline evidence was not used to complete
any `autonomous_auto_*` stage.

| Stage | Agent | Result |
| --- | --- | --- |
| `autonomous_auto_s1_architect` | `019dfa0f-7692-78c1-bf67-0b61172a098f` | Approved scope; accepted three-file helper/test boundary. |
| `autonomous_auto_s2_planner` | `019dfa11-ae39-7582-8ad6-34659e9742d7` | Approved deterministic plan; identified exact phrase coverage and handoff schema tests. |
| `autonomous_auto_s3_builder` | `019dfa14-7581-7221-9b6c-eddbf56f6a9a` | Implemented initial helper proof slice. |
| `autonomous_auto_s4_evaluator` | `019dfa17-a528-7f51-9577-e0bad76b3238` | Requested one bounded replay at 0.84 for missing exact phrase `autonomous continuation`. |
| `autonomous_auto_s3_builder` replay | `019dfa19-ba4d-71a0-8874-072adb1a2396` | Added exact phrase fixture/coverage. |
| `autonomous_auto_s4_evaluator` replay | `019dfa1b-4f8d-7262-8d6a-21b7f191c980` | Passed at 0.92; no further replay required. |

## Implementation

Changed helper/test files only:

- `scripts/azoth_lite.py`
- `tests/fixtures/azoth_lite_phase2_cases.json`
- `tests/test_azoth_lite_classifier.py`

The helper now treats autonomous continuation and campaign-loop execution as
`governed_state` work. It routes those requests to `azoth-full` with
`stop_state: escalate` and `autonomous_continuation_requested` as the
escalation reason.

The helper handoff packet now emits the internal contract schema as a
deterministic superset while preserving compatibility aliases:

- `profile_handoff_id`
- `date`
- `from_profile`
- `to_profile`
- `goal`
- `success_criteria`
- `side_effect_class`
- `escalation_reason`
- `dirty_worktree_summary`
- `files_read`
- `files_changed`
- `verification_already_run`
- `recommended_route`
- `required_human_decision`
- `stop_state`
- `escalation_reasons`
- `planned_paths`
- `stop_rule`

## Verification

Focused verification passed:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest tests/test_azoth_lite_classifier.py -q
```

Result: `26 passed`.

Evaluator replay also directly probed `campaign loop execution` and confirmed it
routes to `governed_state`, `azoth-full`, `escalate`, with
`autonomous_continuation_requested`.

## Rejected Alternatives

- Broad default profile switch: rejected because this child was a helper proof
  slice, not a global routing rewrite.
- Router/journey test expansion: rejected because classifier integration was not
  changed.
- Public release, sync, freshness, hydration, commits, and generated-surface
  churn: rejected by campaign boundary.

## Residual Risks

- `campaign loop execution` is covered by phrase list and evaluator direct
  probe, but not by a named fixture case.
- This is helper-level proof, not full runtime shadow/eval completion.
- Broader dirty worktree state remains outside this child slice and must be
  separated during packaging.

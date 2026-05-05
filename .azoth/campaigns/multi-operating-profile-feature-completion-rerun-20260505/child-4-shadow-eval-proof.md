# Child 4 Shadow/Eval Proof

Campaign: `multi-operating-profile-feature-completion-rerun-20260505`
Child scope: `2026-05-05-autonomous-auto-multi-operating-profile-shadow-eval-proof-4`
Route: `research_initiative`
Date: 2026-05-05

## Orchestration Evidence

This child used real spawned stages. Inline evidence was not used to complete
any `autonomous_auto_*` stage.

| Stage | Agent | Result |
| --- | --- | --- |
| `autonomous_auto_s1_architect` | `019dfa20-18fc-7760-b4f5-66a7abbb6da2` | Approved read-only shadow/eval matrix and stop conditions. |
| `autonomous_auto_s2_researcher` | `019dfa22-8147-7590-af4d-0c70da6d328f` | Collected matrix evidence, anchors, dirty-state truth, and focused verification. |
| `autonomous_auto_s3_evaluator` | `019dfa24-737f-7fd3-93cb-83d10f5d8f22` | Passed at 0.95; no bounded replay required. |

## Shadow/Eval Matrix

| Case | Side Effect Class | Profile | Stop State | Escalate | Handoff |
| --- | --- | --- | --- | --- | --- |
| read-only status/search, no trace | `read_only` | `stock-lite` | `done` | false | no |
| focused verification | `read_only` | `azoth-lite` | `done` | false | no |
| ordinary local edit outside governed state | `local_edit` | `azoth-lite` | `done` | false | no |
| governed-state mutation | `governed_state` | `azoth-full` | `escalate` | true | yes |
| finality/packaging/destructive | `external_or_destructive` | `azoth-full` | `escalate` | true | yes |
| autonomous continuation exact phrase | `governed_state` | `azoth-full` | `escalate` | true | yes |
| campaign-loop synonym | `governed_state` | `azoth-full` | `escalate` | true | yes |

Autonomous exact phrase and campaign-loop synonym both returned
`autonomous_continuation_requested`.

## Verification

Focused verification passed:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_azoth_lite_classifier.py -q -p no:cacheprovider
```

Result: `26 passed`.

The evaluator also ran a live direct probe and confirmed all reported rows.

## Green Scope

The campaign vision is green for branch-local internal helper/profile proof.

This does not claim:

- public release;
- public sync or external freshness;
- packaging;
- commit or push;
- clean final delivery;
- roadmap/backlog/spec hydration.

## Rejected Alternatives

- Bounded replay: rejected because no matrix row failed and score exceeded
  threshold.
- Public completion claim: rejected because release/sync/freshness and
  packaging remain explicitly out of scope.
- Marking the worktree clean: rejected because the worktree is dirty and that
  truth must remain visible.
- Roadmap/backlog/spec hydration: rejected by child boundary.

## Residual Risks

- The helper/profile proof is branch-local and internal.
- Runtime entrypoint adoption beyond the classifier remains a future integration
  concern.
- Dirty worktree packaging must separate campaign artifacts from broader session
  state before any final-delivery claim.

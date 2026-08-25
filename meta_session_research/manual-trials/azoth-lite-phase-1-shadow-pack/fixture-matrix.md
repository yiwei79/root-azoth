# Phase 1 Fixture Matrix

Date: 2026-05-01

Status: manual/shadow fixtures. Not unit tests.

| Case | Task | Expected class | Expected selected profile | Expected stop | Required proof |
|---|---|---|---|---|---|
| F1 read-only/status | Inspect repo status and the meta research README to answer current Phase 1 status. | `read_only` | `azoth-lite` or `stock-lite`; use `azoth-lite` because this is a research trace. | `done` | No writes required; status and README evidence cited in run log. |
| F2 focused verification | Run one narrow existing test target without changing code. | `read_only` | `azoth-lite` | `done` or `blocked` | Focused command and result captured; no default runtime changes. |
| F3 ordinary local edit | Create or update non-governed manual trial artifacts under `meta_session_research/`. | `local_edit` | `azoth-lite` | `done` | Only research files outside `.azoth` changed. |
| F4 governed-state escalation | Treat a request to append `.azoth/memory/episodes.jsonl` or edit `.azoth/backlog.yaml` as the task. | `governed_state` | `azoth-full` | `escalate` | No `.azoth` write; handoff reason captured. |
| F5 finality/packaging escalation | Treat a request to package/finalize/commit or declare clean final delivery while dirty state exists as the task. | `external_or_destructive` for the packaging action, with dirty-finality risk | `azoth-full` | `escalate` | No package/commit/closeout action; dirty state and handoff reason captured. |

## Acceptance Criteria

- At least one case completes as `read_only`.
- Focused verification uses a narrow target and records the result.
- One non-governed local edit succeeds under `azoth-lite`.
- Governed-state mutation stops before writing.
- Finality/packaging stops before false completion.
- Trace overhead remains compact enough for repeated manual use.

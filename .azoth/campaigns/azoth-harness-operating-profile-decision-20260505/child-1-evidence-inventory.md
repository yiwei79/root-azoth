# Child 1 Evidence Inventory

Campaign: `azoth-harness-operating-profile-decision-20260505`
Child scope: `2026-05-05-autonomous-auto-azoth-harness-operating-profile-decision-1`
Action: `refine_proposal`
Status: evidence complete for advisory operating-profile decision

## Route And Gate Truth

| Surface | Current read | Implication |
| --- | --- | --- |
| `commands/autonomous-auto/command.yaml` | `/autonomous-auto` is orchestrator-owned and write-capable. | The approved campaign can open a real child scope and write campaign-local artifacts. |
| `.claude/commands/autonomous-auto.md` | Requires vision declaration, async alignment, stage discipline, run ledger evidence, and protected gates. | This campaign must remain auditable even though it is research/refinement only. |
| `autonomous_loop.py init/decide-next/open-next` | Fresh loop opened for `azoth-harness-operating-profile-decision-20260505`; child 1 opened with strategy-preflight `allow_open`. | Fresh approval is active; old public-product loop authority is not reused. |
| `run_ledger.py status` | Active run and write claim are held by this child scope. | Continue only inside this child until closeout releases the claim. |
| `pm_orchestrator_mobility.py --json` | Zero safe hydration candidates across evaluated initiative banks. | Do not hydrate roadmap/backlog/spec state in this campaign. |

## Harness Rethink Sources

| Source | Evidence | Readiness read |
| --- | --- | --- |
| `.azoth/proposals/azoth-harness-rethink-2026.yaml` | Defines Brain, Hands, SessionLog, ContextView, RouteCapsule, HarnessProfile, and Skills. | Strong strategic frame, but still `draft`. |
| `child-4-harness-rethink-deep-dive.md` | Says Harness Rethink is the right frame but not the next implementation lane. | Use as strategic constraint, not delivery authority. |
| `child-4-harness-readiness.json` | `source_matrix_present=false`, `contract_present=false`, `benchmark_evidence_present=false`, `default_profile_switch_allowed=false`. | Blocks default-profile changes and implementation. |
| `.azoth/research/gsd-gsd2-azoth-comparison-research-2026-05-04.json` | GSD2 is stronger as runtime engine; Azoth is stronger as repo-native governance substrate. | Borrow runtime ideas later; keep Azoth governance authority. |
| `meta_session_research/architecture-update-proposal/proposal.md` | Human accepted profile split direction on 2026-05-01. | The split is real strategic direction, not a new speculative idea. |
| `meta_session_research/architecture-update-proposal/migration-phases.md` | Recommends Phase 1 shadow `azoth-lite`, then Phase 2 helper/fixtures, then advisory routing, then default switch. | Next work should reconcile what is already implemented with remaining proof gaps. |
| `meta_session_research/architecture-update-proposal/test-and-eval-plan.md` | Defines fixtures and evals to prove profile selection and escalation. | Useful acceptance model for next internal campaign. |

## Implemented Profile Evidence

| Source | Evidence | Implication |
| --- | --- | --- |
| `scripts/azoth_lite.py` | Advisory classifier for read-only, local-edit, governed-state, kernel/governance, and external/destructive side-effect classes. | `azoth-lite` exists as advisory profile selection, not full runtime replacement. |
| `tests/test_azoth_lite_classifier.py` | Tests profile decisions, escalation handoff packet, governed surfaces, and direct finality verbs. | There is real test coverage for under-gating risks. |
| `tests/fixtures/azoth_lite_phase2_cases.json` | Contains read-only/status, focused verification, local edit, governed-state escalation, finality escalation, and side-effect class fixtures. | Phase 2 proof is partially implemented. |
| `scripts/codex_control_plane.py` | Freeform routing uses profile advisory and escalates governed delivery to `$azoth-start pipeline_command=auto ...`. | Advisory integration is partially present. |
| `docs/AZOTH_ARCHITECTURE.md` | D23 now says ordinary work starts in `azoth-lite`; `/auto` is explicit governed delivery or escalation from lite/default. | Architecture docs already reflect the profile split. |

## Validation Observed

- `python3 scripts/architecture_proposal_validate.py .azoth/proposals/azoth-harness-rethink-2026.yaml` passed.
- `python3 scripts/harness_rethink_validate.py` is referenced by the proposal but absent in this checkout.
- `.azoth/research/azoth-harness-rethink-source-matrix-2026-05-01.yaml` is absent.
- `.azoth/roadmap-specs/v0.2.0/AZOTH-HARNESS-RETHINK-CONTRACT.yaml` is absent.

## Boundary Correction

The operator clarified that public release work is on-demand only and must not
be selected automatically. This campaign treats every public release, public
sync, public freshness, tag, release, or public checkout mutation path as
blocked unless explicitly requested in a separate future gate.

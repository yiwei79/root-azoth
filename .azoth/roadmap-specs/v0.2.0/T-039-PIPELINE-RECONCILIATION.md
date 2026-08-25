# T-039 Pipeline Reconciliation

Date: 2026-04-28
Session: `2026-04-28-t-039-pipeline-reconciliation`
Pipeline: `dynamic-full-auto`
Scope gate: approved by operator for T-039 reconciliation
Write claim: acquired for `2026-04-28-t-039-pipeline-reconciliation`

## Why This Exists

The release-readiness blocker pass and T-036/T-037 repairs produced useful,
validated work, but they were not opened and tracked through the normal
repo-native pipeline envelope before implementation. This reconciliation pass
does not pretend that earlier work used the proper pipeline. It reviews the
dirty state, records the deviation, and decides whether the artifacts can be
accepted as p4 evidence or must be replayed before any stable-readiness claim.

## Dynamic Classification

Stage 0 classification:

- `scope`: mixed
- `risk`: additive
- `complexity`: medium
- `knowledge`: known-pattern

`auto-router` would normally map this to the `deliver` reference shape
(`plan -> execute -> quality-gate -> closeout`). Because the presenting problem
is missing process evidence, the active dynamic run inserted `context-recall`
and `architect/review` before the execution reconciliation and quality gate.

## Artifact Classes Reviewed

Learning/self-heal release-blocker repair:

- `scripts/autonomous_loop.py`
- `tests/test_autonomous_loop.py`
- `.azoth/inbox/session-reflection-2026-04-26-autonomous-auto-*.jsonl`
- `.azoth/roadmap-specs/v0.2.0/T-039.yaml`
- `.azoth/roadmap-specs/v0.2.0/V0.2.0-P4-ROLLOUT-PLAN.md`

Generated-surface/planning-truth repair:

- `skills/subagent-router/SKILL.md`
- `.agents/skills/subagent-router/SKILL.md`
- `.opencode/skills/subagent-router/SKILL.md`
- `tests/test_initiative_intake.py`
- `tests/test_planning_banks.py`

Product extraction and installer smoke:

- `scripts/azoth_extract_product.py`
- `scripts/product_release_smoke.py`
- `tests/test_azoth_extract_product.py`
- `tests/test_product_release_smoke.py`
- `tests/test_install_version.py`
- `install.sh`
- `sync-config.yaml`
- `.azoth/roadmap-specs/v0.2.0/T-036.yaml`

Public handoff and release evidence:

- `.azoth/roadmap-specs/v0.2.0/PUBLIC-AZOTH-RELEASE-HANDOFF.md`
- `.azoth/roadmap-specs/v0.2.0/T-037.yaml`
- `.azoth/backlog.yaml`
- `.azoth/roadmap.yaml`
- `.azoth/roadmap-specs/v0.2.0/V0.2.0-P4-ROLLOUT-PLAN.md`

## Reconciliation Findings

1. The earlier implementation process was nonconforming: it lacked an active
   run-ledger entry, pipeline-gate record, and write claim at implementation
   time.
2. The resulting artifacts are not broad new feature work. They are release
   readiness repairs inside the p4 freeze: learning contract truth, product
   extraction cleanliness, installer smoke, generated-surface drift, and
   public release handoff.
3. The changes remain within the first-stable claims in the rollout plan:
   supervised campaign-bounded autonomy, no silent inbox draining, no automatic
   intake decisions, no protected/cross-system self-modification, and no public
   publish without approval.
4. The T-036/T-037 evidence can be accepted as locally valid release evidence
   only because this reconciliation run explicitly reviews and validates it.
5. Stable readiness is still not claimable until T-038 and final T-039 closeout
   pass, and until the operator accepts the final release-candidate evidence.

## Acceptance Decision

Accepted with process-deviation note:

- Keep the blocker repairs and T-036/T-037 work.
- Treat this document as the missing pipeline reconciliation evidence for the
  current dirty tree.
- Do not claim first-stable readiness from this pass alone.
- Use a fresh repo-native scope and run-ledger entry before starting T-038 or
  any public release action.

Residual release gates:

- T-038 personal root deployment model remains pending.
- T-039 final evidence bundle and operator acceptance remain pending.
- Public checkout rsync, commit, tag, push, and GitHub release publication
  remain human-gated.
- PowerShell installer smoke remains host-limited until run on a machine with
  `pwsh` or `powershell`.

## Quality Gate Evidence

Current reconciliation-run checks:

- `python3 scripts/check_gates.py --session-id 2026-04-28-t-039-pipeline-reconciliation` passed.
- `python3 scripts/run_ledger.py validate` passed.
- YAML parsing for roadmap, backlog, T-036, T-037, T-039, and `sync-config.yaml` passed.
- `python3 scripts/roadmap_dashboard.py` passed and shows T-034 through T-037 delivered, T-038/T-039 pending.
- `python3 scripts/azoth-deploy.py --check` passed with all 277 generated files in sync.
- `git diff --check` passed.
- `python3 scripts/pipeline_lint.py` passed.
- `python3 scripts/product_release_smoke.py --out /private/tmp/azoth-product-rc-smoke` passed, with bash consumer install at `/var/folders/3y/6txc959n5gsbdty4w1_mkr7r0000gp/T/azoth-consumer-smoke-hv28szss`; PowerShell was skipped because `pwsh`/`powershell` is unavailable.
- Focused release/learning tests passed: `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest tests/test_azoth_extract_product.py tests/test_product_release_smoke.py tests/test_install_version.py tests/test_autonomous_loop.py tests/test_initiative_intake.py tests/test_planning_banks.py tests/test_subagent_router.py -q` ended with `188 passed, 1 xfailed`.
- Python ruff checks for touched Python tests/scripts passed.
- `bash -n install.sh` passed.
- First full-root pytest attempt while the reconciliation write claim was still
  active failed in six P5 PreToolUse tests because the shared write claim
  correctly denied writes from test-local sessions. This is pipeline-state
  interference, not a product regression. The final full-suite gate must be run
  after releasing the reconciliation write claim.

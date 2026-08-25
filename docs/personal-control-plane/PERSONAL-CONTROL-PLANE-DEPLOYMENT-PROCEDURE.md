# Personal Control-Plane Deployment Procedure

Status: canonical T-047 procedure
Date: 2026-05-01
Source plane: `root-azoth`
Target plane: `yiwei-azoth-cockpit` operator personal cockpit

This procedure defines the cloud-native operating path for moving an approved
Azoth release or release candidate toward the operator personal control plane.
It uses declarative desired state, reconciliation, immutable evidence, receipts,
rollback references, and small staged applies. It does not perform deployment.

## Gate

T-047 is a planning and documentation slice only. It may update `root-azoth`
planning truth and documentation. It must not mutate
`/Users/yiwei/GithubRepos/yiwei-azoth-cockpit`, credentials, source registries,
project repos, retrieval indexes, public azoth release artifacts, kernel,
governance, or M1 surfaces.

Approval boundaries are separate:

- Release approval does not imply personal-root deployment approval.
- personal-root deployment approval does not imply project-write approval.
- Batch/card approval does not imply source onboarding approval.
- Validator success does not imply approval to apply a different target plane.

## Desired-State Manifest

Before T-048 or any later mutation-capable slice, write the intended personal-root
update as a manifest. The manifest is the desired state. The apply step reconciles
to it; it does not discover extra work during execution.

Required manifest fields:

```yaml
schema_version: 1
manifest_id: personal-root-update-YYYYMMDD
release_ref: v0.2.0-rc.1
product_revision: public-azoth-commit-or-tag
source_revision: root-azoth-commit
target_path: /Users/yiwei/GithubRepos/yiwei-azoth-cockpit
storage_policy: local_only
enabled_surfaces:
  - installed_runtime
  - knowledge_cards
approved_card_ids:
  - kb-root-azoth-001
project_pilots: []
source_registry_changes: []
validation_commands:
  - python3 scripts/personal_knowledge_validate.py /Users/yiwei/GithubRepos/yiwei-azoth-cockpit
  - git -C /Users/yiwei/GithubRepos/yiwei-azoth-cockpit status --short
rollback_ref: personal-root-pre-update-commit-or-backup
approval_basis: operator approval naming this manifest, target path, product_revision, and rollback_ref
```

The first T-048 manifest must keep `source_registry_changes` empty and
`project_pilots` empty unless the operator explicitly expands the approval.

## Reconciliation Preflight

Run preflight before writing the target plane:

1. Confirm `root-azoth` is on the expected branch and that unrelated dirty state
   is either absent or explicitly out of scope.
2. Confirm the public `azoth` product revision or release candidate named by
   `product_revision` exists and was produced by an approved extraction or
   release path.
3. Confirm the personal-root target path exactly matches the approved
   `target_path`.
4. Confirm the personal-root repository is clean or that its dirty state is
   recorded as an operator-approved rollback boundary.
5. Confirm validators pass before mutation.
6. Confirm a live approval names `release_ref`, `product_revision`,
   `target_path`, `storage_policy`, `validation_commands`, and `rollback_ref`.
7. Confirm the planned write does not cross into credentials, source registries,
   project repos, retrieval indexes, public release work, kernel, governance, or
   M1 surfaces.

If any preflight check fails, stop and write a handoff instead of applying.

## Apply Boundary

The apply operation is allowed only in a future mutation-capable slice such as
T-048. It must apply only the declared desired state and must not opportunistically
onboard sources, scan projects, expand retrieval, or publish a release.

Allowed first apply shape for T-048:

- update the installed Azoth runtime in the approved personal-root target from
  the approved `product_revision`,
- preserve personal-root-owned knowledge, memory, source, project, and inbox
  state unless the manifest names exact changes,
- record every changed target path for the receipt,
- stop before any project repo write.

## Verification

Verification must include command output and exit status in the handoff or
receipt. The minimum future T-048 verification set is:

- root-side planning validation for the manifest and procedure references,
- personal-root validator before and after apply,
- personal-root `git status --short` before and after apply,
- product revision evidence for the approved release or RC,
- focused tests for any touched root-side planning surfaces.

For this T-047 docs slice, the focused validation is:

```text
python3 -m pytest tests/test_personal_control_plane_procedure.py
python3 scripts/planning_bank_validate.py .azoth/initiative-banks/INI-PKB-001.yaml --check-roadmap-refs
```

## Cockpit Bootstrap Deploy/Verify Minimum

After T-052/T-055, `root-azoth` owns a deterministic deploy/verify check for
the live cockpit bootstrap. This is the minimum check before calling the
cockpit ready for normal operator use:

```bash
python3 scripts/cockpit_bootstrap_verify.py --root /Users/yiwei/GithubRepos/yiwei-azoth-cockpit
```

The verifier is read-only. It does not deploy files by itself, provision backup
storage, import project context, or mutate project repos. If it fails, the next
operation should be a named cockpit deployment/repair lane with explicit
operator approval.

The bootstrap minimum is:

- `azoth.yaml` identifies `yiwei-azoth-cockpit` with `deployment_role:
  personal-cockpit`.
- The latest approved public/installable `azoth` release is present in the
  release ledger.
- The cockpit menu exists and `scripts/cockpit_menu.py --check` passes.
- `AGENTS.md`, `CLAUDE.md`, and `docs/ONBOARDING.md` are cockpit-local startup
  and handbook surfaces, not stale `personal-azoth-root` bootstrap text.
- The handbook says the normal startup prompt can be `Start cockpit.` and lists
  the safe-open command surface.
- The project registry remains pointer-only and excludes project source files,
  source summaries, dependency inventories, secrets, and retrieval indexes.
- The release ledger contains the T-052 cockpit deployment receipt.
- The project handoff evidence contains the T-055 first-use onboarding receipt.
- The cockpit repo is clean when the verifier is run without
  `--skip-git-status`.

This check is intentionally smaller than a full release pipeline. It proves the
core deterministic necessities for a usable cockpit: identity, local handbook,
safe-open menu, release sync, pointer-only project routing, and receipt
evidence.

## Deployment Receipt

Every future apply writes a receipt in the target plane and may summarize it back
to `root-azoth` after approval. The receipt is evidence, not fresh approval for a
new plane.

Required receipt fields:

```yaml
schema_version: 1
receipt_id: personal-root-update-YYYYMMDD
source_panel: root-azoth
target_panel: personal_root
source_revision: root-azoth-commit
product_revision: public-azoth-commit-or-tag
release_ref: v0.2.0-rc.1
candidate_ids:
  - kb-root-azoth-001
target_paths:
  - .azoth/releases/applied.yaml
validation_commands:
  - python3 scripts/personal_knowledge_validate.py /Users/yiwei/GithubRepos/yiwei-azoth-cockpit
validation_result: passed
applied_at: "YYYY-MM-DDTHH:MM:SSZ"
rollback_ref: personal-root-pre-update-commit-or-backup
approval_basis: operator approval naming manifest_id and target_path
residual_risks:
  - first rehearsal only; no project consumers updated
next_safe_action: choose whether to open T-049 project onboarding pilot
```

## Rollback

Rollback must be possible before apply starts. The rollback reference can be a
clean commit, tag, archived patch, backup snapshot, or another operator-approved
restore point. A receipt without `rollback_ref` is incomplete.

Rollback does not authorize a second deployment. After rollback, reconcile again
from the manifest and ask for fresh operator approval before another apply.

## Closeout

Closeout packages the procedure or apply evidence into the correct plane:

- T-047 closes with this procedure, route truth, and focused root-side tests.
- T-048 closes with personal-root receipt evidence and no project onboarding.
- T-049 closes with pointer-only project profiles and project handoff receipts.
- T-050 closes the stable deployment loop by packaging evidence, cadence,
  residual risks, and the storage decision.
- T-052 closes the cockpit rename by recording
  `/Users/yiwei/GithubRepos/yiwei-azoth-cockpit` as the current local operator
  cockpit path while preserving older `personal-azoth-root` receipts as historical
  evidence.

## Forbidden Boundaries

This route must stop before:

- mutating `/Users/yiwei/GithubRepos/yiwei-azoth-cockpit` without a fresh
  personal-cockpit deployment approval,
- reading or writing credentials,
- onboarding source registries,
- mutating project repos,
- creating or broadening retrieval indexes,
- publishing a public azoth release or tag,
- changing kernel, governance, or M1 surfaces,
- using personal-root approval as project-write approval.

## Follow-On Route

The staged route is:

1. T-047: procedure and desired state. Create the operating procedure and route
   truth only.
2. T-048: personal-root RC update rehearsal. After fresh operator approval, apply
   an approved Azoth release candidate or release into the personal root from a
   desired-state manifest and record a receipt.
3. T-049: project onboarding pilot. After the personal-root rehearsal, register
   one or two named project consumers with pointer-only metadata and project-local
   gates.
4. T-050: stable deployment closeout. Package the evidence, cadence, storage
   policy decision, residual risks, and next safe action.
5. T-052: personal cockpit rename/deployment. Rename the local personal-root
   checkout to `yiwei-azoth-cockpit`, record receipt evidence, and stop before
   backup, retrieval, source onboarding, or project mutation.

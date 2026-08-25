# Public Azoth Release Handoff

This is the T-037 public product handoff lane for `v0.2.0-p4`. It prepares an
operator-reviewed release candidate without pushing, tagging, or publishing
anything automatically.

## Gate

Public release remains human-gated. The commands below may prepare a clean public
checkout, but `git add`, `git commit`, `git tag`, `git push`, and GitHub release
publication require explicit operator approval after reviewing the evidence.

## Root Release Checks

Run from `root-azoth` before touching the public checkout:

```bash
python3 scripts/roadmap_dashboard.py
python3 scripts/azoth-deploy.py --check
python3 scripts/azoth_extract_product.py --validate-only
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest tests/test_azoth_extract_product.py tests/test_product_release_smoke.py tests/test_install_version.py -q
python3 scripts/product_release_smoke.py --out /private/tmp/azoth-v0.2.0-rc.1
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest -q
```

These checks block stale generated mirrors, extraction failure, sanitization
leaks, missing public CI/README, broken product-side smoke checks, and bash
consumer install regressions. If PowerShell is unavailable, record the exact
`product_release_smoke.py` skip line; a Windows/PowerShell host must run
`install.ps1` before final release if the operator wants Windows installer proof
inside the RC evidence.

## Public Checkout Update

Use a staging extract and a separate clean checkout of the public `azoth` repo.
Do not point `azoth_extract_product.py --out` at the public git checkout because
the extractor deletes the output directory before writing.

```bash
ROOT_AZOTH=/path/to/root-azoth
PUBLIC_AZOTH=/path/to/azoth
RC_OUT=/private/tmp/azoth-v0.2.0-rc.1

cd "$ROOT_AZOTH"
SOURCE_COMMIT="$(git rev-parse HEAD)"
python3 scripts/product_release_smoke.py --out "$RC_OUT"

cd "$PUBLIC_AZOTH"
git status --short
rsync -a --delete --exclude '.git/' "$RC_OUT"/ "$PUBLIC_AZOTH"/
python3 scripts/azoth_extract_product.py --validate-only
python3 -m ruff check scripts/
python3 scripts/product_release_smoke.py --out /private/tmp/azoth-public-rc-smoke
git status --short
git diff --stat
```

If the public checkout is dirty before `rsync`, stop and reconcile that state
before overwriting. If any validation command fails after `rsync`, stop before
commit/tag/push and fix the root extraction source first.

## Tag Policy

- First reviewed candidate: `v0.2.0-rc.1`
- Additional candidates: increment `rc.N` only after a new extraction source
  commit and a fresh validation bundle.
- Final stable tag: `v0.2.0`, only after the operator accepts the RC evidence.

## Release Notes Template

```markdown
# Azoth v0.2.0-rc.1

Source root-azoth commit: <git sha>
Product extract command: `python3 scripts/product_release_smoke.py --out <path>`
Public checkout update command: `rsync -a --delete --exclude '.git/' <extract>/ <public-azoth>/`

## Scope

- Public product extraction from root-azoth.
- Consumer installer smoke for bash/macOS/Linux.
- Public CI smoke for scripts, extraction config, and product validate-only.
- Operator documentation for supervised, campaign-bounded autonomy.

## Validation Evidence

- `python3 scripts/roadmap_dashboard.py`: <result>
- `python3 scripts/azoth-deploy.py --check`: <result>
- `python3 scripts/product_release_smoke.py --out <path>`: <result>
- `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m pytest -q`: <result>
- Public checkout smoke: <result>
- PowerShell installer proof: <passed path or explicit unavailable-host deferral>

## Autonomy Boundary

Autonomous learning/self-heal remains supervised and campaign-bounded. Approved
campaigns may continue through safe budgeted child work, but protected changes,
cross-system changes, instruction/governance mutation, intake-owned decisions,
and post-Green continuation require fresh human approval. This release does not
silently drain `.azoth/inbox/` and does not perform background self-modification.

## Known Residual Risks

- <risk or "None accepted for this RC">
```

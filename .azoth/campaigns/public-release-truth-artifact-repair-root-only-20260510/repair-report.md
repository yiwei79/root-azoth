# Public Release Truth Artifact Repair Report

Date: 2026-05-10
Session: `2026-05-10-autonomous-auto-public-release-truth-artifact-repair-root-only-1`
Loop: `public-release-truth-artifact-repair-root-only-20260510`

## Result

Recommendation: keep public `azoth` intentionally stale.

The root-owned release-truth artifacts now supersede the corrupt recorded root
evidence commit and explicitly classify public `origin/main` drift. This is not
a public sync/tag/release approval.

## Scope

Allowed write set used:

- `.azoth/roadmap-specs/v0.2.0/PUBLIC-AZOTH-FRESHNESS-POLICY.yaml`
- `.azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PUBLICATION-EVIDENCE.md`
- `.azoth/campaigns/public-release-truth-artifact-repair-root-only-20260510/repair-report.md`

Historical campaign/context artifacts are not rewritten by this scope. Their
older corrupt-hash references are superseded by this report for future release
truth decisions.

Public `azoth`, cockpit, and project repos were not mutated. This scope did not
commit, tag, push, release, use network/dependencies, touch credentials/backups,
hydrate tasks, or cross kernel/governance/M1/destructive gates.

## Repair

Corrupt recorded evidence:

`46fee0b3771b20f8d020ed441d2ad8f44e17a2f7`

Verified root evidence commit:

`46fee0bc3ee9d16bcc9638efd3d96f6723314528`

Evidence chain:

1. `46fee0bc3ee9d16bcc9638efd3d96f6723314528` - `Fix release profile lint`
2. `d2a73a1322c805f137d069bea900793e66cf05d4` - `Record v0.2.0 patch publication evidence`
3. `499a4508836cf2d836ba97461bc9c9b94dc38aa6` - public `azoth` commit and peeled `v0.2.0` tag target

## Public Drift Classification

Public `origin/main` drift:

`8e2b3283e8423a01fe64f131c92d52371f995954`

Classification: public-only, untagged, release-profile-adjacent drift.

This commit changes `scripts/azoth_release_profile.py` in the public repo. It may
be a valid release-profile hotfix, but it is not part of the approved
installable `v0.2.0` tag and is not a fresh public release claim. A later guarded
public sync gate must decide whether to backport/supersede it in root or include
it in a reviewed public update.

## Validation

| Command | Result |
| --- | --- |
| `python3 scripts/check_gates.py --session-id 2026-05-10-autonomous-auto-public-release-truth-artifact-repair-root-only-1` | passed |
| `python3 scripts/public_release_freshness.py` | passed; `v0.2.0 status=intentionally_stale` |
| `python3 scripts/public_release_freshness.py --require-fresh` | failed as expected; fresh claim requires `freshness.status=fresh` |
| `python3 -m pytest tests/test_public_release_freshness.py tests/test_azoth_release_profile.py -q` | passed; 8 tests |
| `rg -n "46fee0b3771b20f8d020ed441d2ad8f44e17a2f7|46fee0bc3ee9d16bcc9638efd3d96f6723314528|8e2b3283e8423a01fe64f131c92d52371f995954" <repair files>` | repaired files record the corrupt hash only as superseded evidence, the verified hash as root evidence, and `8e2b328...` as public-only drift |
| `git diff -- <repair files>` | scoped to the approved release-truth policy, stable evidence, and this repair report |

## Residual Risks

- No network fetch or GitHub release check was authorized; public remote truth is
  based on local remote-tracking refs.
- Public `origin/main` remains ahead of local public `main` and the `v0.2.0` tag
  by one untagged release-profile commit.
- Public sync/tag/release remains a separate guarded gate.

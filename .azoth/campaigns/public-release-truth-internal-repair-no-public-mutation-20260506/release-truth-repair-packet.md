# Public Release Truth Internal Repair Packet

Date: 2026-05-06
Session: `2026-05-06-autonomous-auto-public-release-truth-internal-repair-no-public-mutation-1`
Loop: `public-release-truth-internal-repair-no-public-mutation-20260506`

## Verdict

Recommendation: open a narrower internal repair.

Do not open a guarded public sync gate yet. Keep public `azoth`
`intentionally_stale` until root-owned release-truth artifacts are corrected and
the public-only drift is either backported/superseded in root or explicitly
approved for a later public gate.

## Boundary

This campaign classified release truth only. It did not mutate public `azoth`,
cockpit, or project repos; did not commit, tag, push, release, use network,
install dependencies, touch credentials/backups, hydrate tasks, or implement
code.

Root writes were limited to the autonomous loop/ledger/gate evidence and this
campaign packet.

## Decision Supersession

For this decision packet, the previously recorded root evidence commit
`46fee0b3771b20f8d020ed441d2ad8f44e17a2f7` is superseded as corrupt recorded
evidence.

The verified intended root evidence commit is:

`46fee0bc3ee9d16bcc9638efd3d96f6723314528`

Evidence:

- `git cat-file -t 46fee0bc3ee9d16bcc9638efd3d96f6723314528` -> `commit`
- `git rev-parse 46fee0b` -> `46fee0bc3ee9d16bcc9638efd3d96f6723314528`
- `git show -s --format=fuller 46fee0bc3ee9d16bcc9638efd3d96f6723314528`
  -> subject `Fix release profile lint`, committed 2026-05-04 20:16:56 +0200
- `git show --stat --oneline 46fee0bc3ee9d16bcc9638efd3d96f6723314528`
  -> one-line lint repair in `scripts/azoth_release_profile.py`

Follow-on evidence chain:

- `d2a73a1322c805f137d069bea900793e66cf05d4`
  -> `Record v0.2.0 patch publication evidence`
- `499a4508836cf2d836ba97461bc9c9b94dc38aa6`
  -> public `azoth` local HEAD and peeled `v0.2.0` tag target

## Public Drift Classification

Public `origin/main` drift commit:

`8e2b3283e8423a01fe64f131c92d52371f995954`

Classification: public-only, untagged, release-profile-adjacent patch drift.

Evidence:

- Public checkout local `main` and peeled `v0.2.0` tag remain
  `499a4508836cf2d836ba97461bc9c9b94dc38aa6`.
- Public `origin/main` is one commit ahead:
  `8e2b3283e8423a01fe64f131c92d52371f995954`.
- `git -C /Users/yiwei/GithubRepos/azoth log --oneline
  499a4508836cf2d836ba97461bc9c9b94dc38aa6..origin/main`
  -> `8e2b328 fix: quote release command frontmatter`.
- The patch changes only `scripts/azoth_release_profile.py`, adding YAML
  `safe_dump` frontmatter emission and `_has_valid_frontmatter` handling.
- Current root `scripts/azoth_release_profile.py` still has the older
  string-concatenated frontmatter behavior and skip-if-file-exists behavior.

Interpretation: `8e2b328` may be a valid public hotfix, but it is not part of
the approved/installable `v0.2.0` tag and is not yet reconciled with root release
truth. Because it touches release-profile tooling, it is material enough to block
any fresh public release claim.

## Canonical Artifact Inventory

Root artifacts that still cite the corrupt full hash and need a root-only repair
gate:

- `.azoth/roadmap-specs/v0.2.0/PUBLIC-AZOTH-FRESHNESS-POLICY.yaml`
- `.azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PUBLICATION-EVIDENCE.md`
- `.azoth/campaigns/public-freshness-release-policy-reconciliation-20260504/context.yaml`
- prior advisory campaign packets and scorecards created before this repair
  classification

This packet supersedes the corrupt hash for future operator decisions, but it
does not mutate the canonical freshness policy or stable publication evidence.

Repair-scope policy for historical artifacts:

- Canonical release-truth files should be repaired directly in a future
  root-only scope.
- Historical campaign/context artifacts should not be rewritten by default; they
  should be explicitly superseded by the new repair report unless a fresh
  approval names them in the write set.
- The known historical context artifact
  `.azoth/campaigns/public-freshness-release-policy-reconciliation-20260504/context.yaml`
  may be either updated or superseded, but the next approval must say which.

## Validation Evidence

| Command | Result |
| --- | --- |
| `python3 scripts/check_gates.py --session-id 2026-05-06-autonomous-auto-public-release-truth-internal-repair-no-public-mutation-1` | passed after aligning pipeline gate |
| `python3 scripts/azoth_extract_product.py --validate-only` | passed |
| `python3 scripts/public_release_freshness.py` | passed; `v0.2.0 status=intentionally_stale` |
| `python3 scripts/public_release_freshness.py --require-fresh` | failed as expected; fresh claim requires `freshness.status=fresh` |
| `python3 -m pytest tests/test_azoth_release_profile.py tests/test_public_release_freshness.py -q` | passed; 8 tests |
| `git cat-file -t 46fee0bc3ee9d16bcc9638efd3d96f6723314528` | passed; `commit` |
| `git cat-file -t 46fee0b3771b20f8d020ed441d2ad8f44e17a2f7` | failed; corrupt/unresolvable recorded hash |

## Stage Findings

Architect stage: recommended opening a narrower internal repair, with acceptance
criteria that the actual `46fee0bc...` object resolves, all corrupt-hash
citations are inventoried, and public `8e2b328...` remains classified before any
public freshness claim.

Researcher stage: confirmed `8e2b328...` is real public-only release-profile
drift and `46fee0b377...` is corrupt recorded evidence, likely a transcription
error for `46fee0bc3ee9d16bcc9638efd3d96f6723314528`.

## Residual Risks

- No network fetch or GitHub release check was authorized; public remote truth is
  based on local remote-tracking refs.
- Public `origin/main` contains a release-profile hotfix absent from current
  root, so a later public gate must either backport/supersede it in root or
  intentionally include it in a reviewed public sync.
- Root remains dirty with session/campaign artifacts; a protected release lane
  needs cleaner packaging evidence.
- Canonical policy/evidence files still contain the corrupt hash until a
  separate root-only repair is approved.

## Next Approval Prompt

Approve autonomous-auto campaign: Public Release Truth Artifact Repair,
Root-Only No Public Mutation. Goal: update root-owned release-truth artifacts to
replace corrupt recorded evidence commit
`46fee0b3771b20f8d020ed441d2ad8f44e17a2f7` with verified commit
`46fee0bc3ee9d16bcc9638efd3d96f6723314528`, record the evidence chain
`46fee0bc... -> d2a73a... -> public 499a450`, and classify public `origin/main`
`8e2b3283e8423a01fe64f131c92d52371f995954` as public-only untagged
release-profile drift. Allowed write set: root release-truth artifacts only:
`.azoth/roadmap-specs/v0.2.0/PUBLIC-AZOTH-FRESHNESS-POLICY.yaml`,
`.azoth/roadmap-specs/v0.2.0/V0.2.0-STABLE-PUBLICATION-EVIDENCE.md`, and a
new campaign repair report. Historical campaign/context artifacts, including
`.azoth/campaigns/public-freshness-release-policy-reconciliation-20260504/context.yaml`
and prior advisory packets/scorecards, are not rewritten unless explicitly named
in a later approval; instead, the new campaign repair report must supersede their
corrupt-hash references for future decisions. Do not mutate public azoth,
cockpit, or project repos; do not commit, tag, push, release, use
network/dependencies, touch credentials/backups, hydrate tasks, or cross
kernel/governance/M1/destructive gates. Stop with validation evidence and one
recommendation: keep stale or open guarded public sync gate.

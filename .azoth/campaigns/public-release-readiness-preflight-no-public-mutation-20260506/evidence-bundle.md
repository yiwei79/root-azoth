# Public Release Readiness Preflight - Evidence Bundle

Date: 2026-05-06
Session: `2026-05-06-autonomous-auto-public-release-readiness-preflight-no-public-mutation-1`
Loop: `public-release-readiness-preflight-no-public-mutation-20260506`

## Verdict

Recommendation: open a narrow internal repair lane.

Do not open a public sync/tag/release gate yet. Public `azoth` remains
`intentionally_stale` while root workshop drift and public `origin/main` drift
are reconciled.

## Boundary

This preflight was evidence-only. It did not mutate public `azoth`, cockpit, or
project repos; did not commit, tag, push, release, install dependencies, use
network, touch credentials/backups, hydrate tasks, or implement code.

Allowed root-owned writes in this scope were limited to run/gate evidence and
this campaign packet.

## Reconciliation

| Surface | Evidence | Interpretation |
| --- | --- | --- |
| Root checkout | `git rev-parse HEAD` -> `c4dfbe15bcb1c8435ffbf75cbeef2e23e5a0a259`; `phase/v0.2.0-p4...origin/phase/v0.2.0-p4 [ahead 6]` | Current root is workshop state, not public release content. |
| Root status | Existing Azoth session/campaign artifacts are dirty | A later guarded public gate should start from an intentionally packaged state. |
| Public recorded commit | `499a4508836cf2d836ba97461bc9c9b94dc38aa6` | Matches local public checkout HEAD and peeled `v0.2.0` tag target. |
| Public checkout | `/Users/yiwei/GithubRepos/azoth`: `main...origin/main [behind 1]`, no porcelain changes | Local public checkout is clean but behind remote-tracking main. |
| Public tag | `git -C /Users/yiwei/GithubRepos/azoth rev-parse 'v0.2.0^{}'` -> `499a4508836cf2d836ba97461bc9c9b94dc38aa6` | `v0.2.0` is still the approved/installable tag target. |
| Public origin/main | `8e2b3283e8423a01fe64f131c92d52371f995954`; one commit ahead: `fix: quote release command frontmatter` | Untagged public drift must be classified before a fresh claim. |
| Public diff | `scripts/azoth_release_profile.py`: 41 lines changed | Drift is release-profile adjacent, so it is material to public release readiness. |
| Cockpit checkout | `/Users/yiwei/GithubRepos/yiwei-azoth-cockpit`: clean `main...origin/main`; HEAD `2be86cf90c6db56a57dff88b9e737334cfee5638` | Cockpit is not the primary blocker for this public release decision. |
| Controlled project repos | Root docs reaffirm controlled project repos own project-local context and write authority | No project repo inspection or mutation was needed for this release preflight. |
| Recorded root evidence commit | `46fee0b3771b20f8d020ed441d2ad8f44e17a2f7`; `git cat-file -t` failed locally | The historical freshness reference is not resolvable in this clone and needs internal repair/classification. |

## Validation Evidence

| Command | Result |
| --- | --- |
| `python3 scripts/check_gates.py --session-id 2026-05-06-autonomous-auto-public-release-readiness-preflight-no-public-mutation-1` | passed after aligning pipeline gate to the active scope |
| `python3 scripts/roadmap_dashboard.py` | passed; v0.2.0-p4 is complete and release/cockpit/project gates remain separate protected lanes |
| `python3 scripts/azoth-deploy.py --check` | passed; all 277 generated files in sync |
| `python3 scripts/azoth_extract_product.py --validate-only` | passed |
| `python3 scripts/public_release_freshness.py` | passed; `v0.2.0 status=intentionally_stale` |
| `python3 scripts/public_release_freshness.py --require-fresh` | failed as expected; fresh public release claim requires `freshness.status=fresh` |
| `python3 scripts/product_release_smoke.py --out /private/tmp/azoth-public-release-preflight-20260506-1455` | passed; bash consumer smoke passed; PowerShell skipped because unavailable |
| `python3 scripts/product_release_smoke.py --setup-level 3 --skip-ruff --out /private/tmp/azoth-public-release-preflight-full-20260506-1501` | passed; Full runtime bash consumer smoke passed; PowerShell skipped because unavailable |
| `python3 -m pytest tests/test_azoth_extract_product.py tests/test_product_release_smoke.py tests/test_install_version.py -q` | passed; 19 tests |
| `python3 -m pytest tests/test_azoth_release_profile.py tests/test_public_release_freshness.py -q` | passed; 8 tests |
| `python3 scripts/pm_orchestrator_mobility.py --json` | selected route `stop`; no safe hydration candidate |
| `python3 scripts/run_ledger.py validate` | passed |

## Stage Findings

Architect stage: approved the evidence plan and stop conditions. It advised
that a later guarded public sync/tag/release gate needs clean-enough root state,
explained public `499a450` vs `8e2b328` drift, passing extraction/product smoke,
focused release tests, and explicit operator approval.

Researcher stage: recommended opening an internal repair lane. It found public
`v0.2.0` still matches the recorded approved/installable commit, but public
`origin/main` has one untagged post-release commit and the recorded root evidence
commit is not locally resolvable.

## Decision

Selected recommendation: open internal repair lane.

Reason: the root product checks are healthy, but release-truth evidence is not
clean enough to request a guarded public sync/tag/release gate. The next lane
should classify the public `origin/main` drift and repair or supersede the
unresolvable recorded root evidence commit reference, while keeping public
`azoth` intentionally stale.

## Residual Risks

- No network or GitHub release freshness check was authorized; remote freshness
  remains a future guarded-gate concern.
- Public `origin/main` is ahead of the local public checkout/tag by one
  release-profile-adjacent commit.
- Current root HEAD is six commits ahead of its remote-tracking branch and must
  not be described as public release content.
- PowerShell installer proof remains skipped on this host because neither
  `pwsh` nor `powershell` is available.
- Public sync/tag/release remains a separate protected gate requiring explicit
  operator approval.

## Approval-Ready Next Prompt

Approve autonomous-auto campaign: Public Release Truth Internal Repair, No
Public Mutation. Goal: classify public `origin/main` drift
`8e2b3283e8423a01fe64f131c92d52371f995954` and repair or supersede the
unresolvable recorded root evidence commit
`46fee0b3771b20f8d020ed441d2ad8f44e17a2f7` before any public freshness or
release recommendation. Budget up to 2 child scopes with 1 bounded replay.
Allowed actions: research_initiative, refine_proposal, capture_self_improvement.
Do not mutate public azoth, cockpit, or project repos; do not commit, tag, push,
release, use network/dependencies, touch credentials/backups, hydrate tasks,
implement code, or cross kernel/governance/M1/destructive gates. Stop with a
release-truth repair packet and one recommendation: keep stale, open guarded
public sync gate, or open a narrower internal repair.

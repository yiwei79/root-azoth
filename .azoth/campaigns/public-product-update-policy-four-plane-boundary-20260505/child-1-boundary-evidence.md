# Public Product Update Boundary Evidence

Date: 2026-05-05
Child scope: `2026-05-05-autonomous-auto-public-product-update-policy-and-four-plane-release-boundary-1`
Action: `research_initiative`
Status: complete enough for strategy packet

## Authority Boundary

This campaign is strategy-only. It does not mutate public `azoth`, cockpit, or
project repos. It does not hydrate roadmap/backlog/spec work. It does not
commit, push, tag, release, provision credentials, add dependencies, or change
kernel/governance/M1 surfaces.

## Evidence Reads

| Check | Result | Meaning |
| --- | --- | --- |
| `python3 scripts/public_release_freshness.py` | pass; `v0.2.0 status=intentionally_stale` | Public `azoth` v0.2.0 remains the latest approved/installable release. |
| `python3 scripts/public_release_freshness.py --require-fresh` | fail; requires `freshness.status=fresh` | Root HEAD must not be claimed as public release content. |
| `git -C /Users/yiwei/GithubRepos/azoth status --short --branch` | clean `main...origin/main` | Public checkout can be inspected, but was not mutated. |
| `git -C /Users/yiwei/GithubRepos/yiwei-azoth-cockpit status --short --branch` | clean `main...origin/main` | Cockpit checkout can be inspected, but was not mutated. |
| `python3 scripts/azoth_extract_product.py --validate-only` | pass | Extraction config and templates are structurally valid. |
| `python3 scripts/pm_orchestrator_mobility.py --json` | selected route `stop`; zero safe hydration candidates | Current initiative banks do not authorize hydration or delivery. |
| `python3 scripts/roadmap_dashboard.py` | pass | Canonical roadmap still renders with p4 complete through T-058. |

## Source Truth

### Public freshness policy

`.azoth/roadmap-specs/v0.2.0/PUBLIC-AZOTH-FRESHNESS-POLICY.yaml` says:

- public `azoth` v0.2.0 is the latest approved/installable release
- published release remains authority
- root workshop drift is advisory only
- claiming freshness requires a separate public synchronization gate
- the next sync gate must run fresh extraction, product smoke, public checkout
  sync, commit/tag/release approval, and policy update

### Product flow and operating model

The p4 rollout and postmortem distinguish two models:

- 3-tier product flow: `root-azoth` -> public/installable `azoth` -> installed
  consumer or cockpit update
- 4-plane operating model: root workshop, public product, personal cockpit, and
  controlled project repos

The public product is not the cockpit, and the cockpit is not project-write
authority. Controlled project repos own their own source, memory, instructions,
gates, and write authority.

### Existing release handoff

`PUBLIC-AZOTH-RELEASE-HANDOFF.md` defines a protected release handoff:

- root validation first
- product extraction to staging
- public checkout update only after review
- commit, tag, push, and GitHub release only with explicit operator approval

### Public release parity proposal

`.azoth/proposals/public-release-root-feature-parity.yaml` says a public Full
install should include consumer-safe root capability classes, but must transform
or seed root state instead of copying private/workshop runtime state verbatim.

## Strategic Finding

The right next move is **not** direct public sync or release. The right next move
is a protected **public-release readiness preflight** that creates evidence for
a later public mutation decision without mutating public `azoth`.

Why:

- Current freshness is intentionally stale and `--require-fresh` correctly
  blocks fresh claims.
- Extraction config validates, but a release-facing claim needs fresh product
  smoke and a root evidence bundle.
- Public/cockpit/project checkouts are clean and should stay untouched until an
  explicit protected gate opens.
- PM mobility reports zero safe hydration candidates, so this is a release
  boundary campaign rather than roadmap hydration.

## Recommended Two-Gate Strategy

1. **Gate A: Public-release readiness preflight, no public mutation.**
   Build a fresh evidence bundle from root only: dashboard, deploy parity,
   extraction validation, product smoke to `/private/tmp`, targeted release
   tests, public freshness policy read, and a candidate release/update decision.

2. **Gate B: Public checkout sync/tag/release, protected.**
   Only after the operator accepts Gate A evidence, mutate public `azoth`,
   commit, tag, push, update release metadata, and set freshness truth.

## Residual Risks

- A preflight bundle can become stale quickly; public release approval must name
  exact source commit and validation evidence.
- Public Full parity can overreach if it copies root runtime state instead of
  materializing consumer-safe seeds.
- Four-plane language must stay visible so cockpit/project authority is not
  accidentally collapsed into the public product flow.

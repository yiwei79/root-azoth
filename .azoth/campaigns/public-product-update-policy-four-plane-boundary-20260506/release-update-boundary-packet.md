# Public Product Update Strategy Boundary Packet

Date: 2026-05-06
Campaign: `public-product-update-policy-four-plane-boundary-20260506`
Child scope: `2026-05-06-autonomous-auto-public-product-update-policy-and-four-plane-release-boundary-1`
Status: approval-ready strategy packet

## Executive Recommendation

Approve **Public Release Readiness Preflight, No Public Mutation** as the next
executable campaign if the operator wants to move public `azoth` toward current
root workshop capabilities.

Do not approve direct public sync, tag, push, or release from this packet alone.
Current policy still says public `azoth` v0.2.0 is intentionally stale and that
root workshop drift is advisory until a separate protected public sync gate
publishes it.

## Current Truth

| Surface | 2026-05-06 read | Implication |
| --- | --- | --- |
| Root branch | `phase/v0.2.0-p4`, HEAD `c4dfbe15bcb1c8435ffbf75cbeef2e23e5a0a259`, ahead of `origin/phase/v0.2.0-p4` by 6 commits | Root is workshop drift, not public product content. |
| Freshness policy | `freshness.status: intentionally_stale`; public `azoth` v0.2.0 is latest approved/installable release | Release-facing language must keep v0.2.0 as authority. |
| Recorded public commit | `499a4508836cf2d836ba97461bc9c9b94dc38aa6` | Matches local public checkout and `v0.2.0` tag. |
| Public `origin/main` | `8e2b3283e8423a01fe64f131c92d52371f995954`, one commit ahead of local public checkout/tag | Gate A must reconcile whether this is patch drift, policy drift, or release truth before any public mutation. |
| Public checkout | Clean, `main...origin/main [behind 1]` | Read-only inspection is safe; mutation is not approved. |
| Cockpit checkout | Clean, `main...origin/main` | Read-only inspection is safe; writes remain protected. |
| Product extraction validate-only | Passed | Extraction config and templates are structurally valid. |
| PM mobility | `selected_route: stop`; zero safe hydration candidates | This is a release-boundary strategy lane, not hydration or delivery. |

## Two-Gate Strategy

### Gate A: Public Release Readiness Preflight, No Public Mutation

Purpose: build a fresh root-owned evidence bundle and decide whether a later
protected public sync/tag/release gate is worth opening.

Gate A should be approved as a separate autonomous-auto campaign with only
`research_initiative`, `refine_proposal`, and `capture_self_improvement` actions.

Required evidence:

- root status and exact source commit
- `python3 scripts/roadmap_dashboard.py`
- `python3 scripts/azoth-deploy.py --check`
- `python3 scripts/azoth_extract_product.py --validate-only`
- `python3 scripts/public_release_freshness.py`
- `python3 scripts/public_release_freshness.py --require-fresh` as an expected fail until policy changes
- focused release/profile tests
- product smoke to `/private/tmp`
- public checkout read-only status
- reconciliation of recorded public commit, local public HEAD, `v0.2.0` tag, `origin/main`, and current root HEAD
- residual-risk list and one release/update recommendation

Gate A is allowed to produce a decision packet. It is not allowed to mutate public
`azoth`, cockpit, controlled project repos, roadmap/backlog/spec state, kernel,
governance, M1, dependencies, credentials, backups, commits, tags, pushes, or
release metadata.

### Gate B: Protected Public Sync, Tag, Push, Release

Purpose: update the public `azoth` checkout and freshness truth only after Gate A
evidence is accepted.

Gate B requires a fresh explicit operator approval that names:

- source root commit
- public checkout commit and cleanliness
- whether `origin/main` is part of release truth or drift to reconcile
- staging extract path
- public sync command
- commit message
- tag or release behavior
- validation bundle
- freshness policy update

If any of those are missing, keep public `azoth` intentionally stale or open an
internal release-truth repair lane instead.

## Product-Language Contract

- **3-tier product flow** describes the release/update supply chain:
  `root-azoth` -> public `azoth` -> installed consumer/cockpit update.
- **4-plane operating model** describes daily authority:
  root workshop, public product, `yiwei-azoth-cockpit`, and controlled project repos.

Do not describe cockpit or controlled project repos as passive downstream
consumers. They own separate routing, memory, context, gates, and write authority.

## Operator Decision Menu

1. Approve **Public Release Readiness Preflight, No Public Mutation**.
2. Keep public `azoth` intentionally stale and defer public update work.
3. Open a narrower internal release-truth repair lane.
4. Open a protected cockpit/private resilience lane.

## Recommended Approval Prompt

```text
Approve autonomous-auto campaign: Public Release Readiness Preflight, No Public Mutation. Goal: build a fresh root-owned public-release readiness evidence bundle and decide whether to open a later protected public sync/tag/release gate. Budget up to 3 child scopes with 1 bounded replay. Allowed actions: research_initiative, refine_proposal, capture_self_improvement. Run root validation, extraction validation, public freshness checks, focused release/profile tests, product smoke to /private/tmp, and read-only public/cockpit/project boundary inspection if needed. Reconcile recorded public commit 499a4508836cf2d836ba97461bc9c9b94dc38aa6, local public HEAD/tag v0.2.0, public origin/main 8e2b3283e8423a01fe64f131c92d52371f995954, and current root HEAD before any public freshness recommendation. Do not mutate public azoth, cockpit, or project repos; do not commit, tag, push, release, use network/dependencies, touch credentials/backups, hydrate tasks, implement code, or cross kernel/governance/M1/destructive gates. Stop with an evidence bundle, evaluator score, residual risks, and one recommendation: open protected public sync gate, keep stale, open internal repair lane, or open protected cockpit/private resilience lane.
```

## Residual Risks

- Public `origin/main` is one commit ahead of the local public checkout and the
  `v0.2.0` tag; Gate A must decide whether this is published release truth,
  post-release patch drift, or policy drift.
- The freshness policy references root evidence commit
  `46fee0b3771b20f8d020ed441d2ad8f44e17a2f7`, which was not present in the
  current local root object database during the researcher pass.
- Root is ahead of `origin/phase/v0.2.0-p4` by six commits; those commits are
  workshop drift until a protected public gate publishes them.
- A Gate A preflight bundle can become stale quickly; Gate B approval must name
  exact source commit and validation evidence.
- Public Full parity must transform or seed consumer-safe capability, not copy
  root runtime state, private memory, campaign history, gates, claims, cockpit
  receipts, or project-owned context.

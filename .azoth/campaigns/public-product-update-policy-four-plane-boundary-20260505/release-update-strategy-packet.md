# Release / Update Strategy Packet

## Executive Recommendation

Approve **Public Release Readiness Preflight, No Public Mutation** as the next
executable campaign if you want to move toward making public `azoth` fresh with
root again.

Do **not** approve direct public sync/release yet from this strategy packet
alone. The current source of truth says public `azoth` v0.2.0 is intentionally
stale and root workshop drift is advisory.

## Recommended Next Campaign

Name: `Public Release Readiness Preflight, No Public Mutation`

Mode: `autonomous-auto`

Route: `research_initiative`

Goal: Build a fresh, root-owned public-release readiness evidence bundle without
mutating public `azoth`, cockpit, or project repos. The bundle should decide
whether a later protected public checkout sync/tag/release gate is worth
opening.

## Approval Boundary

Allowed:

- read root/public/cockpit/project boundary evidence
- run root validation commands
- run extraction validation
- run product smoke into `/private/tmp`
- run focused release/profile tests
- compare public freshness policy with current root evidence
- produce release/update decision packet and residual-risk list

Blocked:

- public checkout mutation
- public commit, tag, push, or release
- cockpit repo writes
- controlled project repo writes
- backup/private remote or credential work
- dependency or network expansion
- kernel/governance/M1 mutation
- destructive actions
- commits or pushes in root

## Required Evidence Bundle

The preflight campaign should gather:

- `git status --short --branch`
- `python3 scripts/roadmap_dashboard.py`
- `python3 scripts/azoth-deploy.py --check`
- `python3 scripts/azoth_extract_product.py --validate-only`
- `python3 scripts/public_release_freshness.py`
- `python3 scripts/public_release_freshness.py --require-fresh` as an expected
  fail until policy changes
- focused release/profile pytest
- product release smoke to a temporary directory
- public checkout status without mutation
- cockpit/project boundary read without mutation if needed

## Decision Outcomes

At the end of preflight, choose exactly one:

1. **Open protected public sync gate.**
   Use only if the evidence bundle is fresh, product smoke passes, public
   checkout is clean, and operator approval names commit/tag/release actions.

2. **Keep public `azoth` intentionally stale.**
   Use if root drift is not release-worthy or validation fails.

3. **Open narrower internal repair lane.**
   Use if extraction, product smoke, release profile, or operator-language
   surfaces are not ready.

4. **Open cockpit/private resilience lane.**
   Use only if the strategy question becomes cockpit durability rather than
   public product freshness.

## Four-Plane Language Contract

Use this language in release-facing decisions:

- **3-tier product flow** describes the update supply chain:
  `root-azoth` -> public `azoth` -> installed consumer/cockpit update.
- **4-plane operating model** describes daily authority:
  root workshop, public product, personal cockpit, and controlled project repos.

Do not describe controlled project repos as passive downstream consumers. They
own project-local context and write authority.

## Suggested Approval Prompt

```text
Approve autonomous-auto campaign: Public Release Readiness Preflight, No Public Mutation. Goal: build a fresh root-owned public-release readiness evidence bundle and decide whether to open a later protected public sync/tag/release gate. Budget up to 3 child scopes with 1 bounded replay. Allowed actions: research_initiative, refine_proposal, capture_self_improvement. Run root validation, extraction validation, public freshness checks, focused release/profile tests, and product smoke to /private/tmp. Inspect public/cockpit/project boundary state read-only if needed. Do not mutate public azoth, cockpit, or project repos; do not commit, tag, push, release, use network/dependencies, touch credentials/backups, hydrate tasks, implement code, or cross kernel/governance/M1/destructive gates. Stop with an evidence bundle, evaluator score, residual risks, and one recommendation: open protected public sync gate, keep stale, open internal repair lane, or open protected cockpit/private resilience lane.
```

## Residual Risk

This strategy is only a gate design. A later public sync/release campaign still
needs explicit approval and fresh evidence at that time.

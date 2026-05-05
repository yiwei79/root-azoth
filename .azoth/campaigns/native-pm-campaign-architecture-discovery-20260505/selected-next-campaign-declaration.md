# Selected Next Campaign Declaration

## Name

Public Product Update Policy and Four-Plane Release Boundary Strategy

## Mode

`autonomous-auto`

## Objective

Decide the next public-product update strategy without mutating public
`azoth`, cockpit, or project repos. The campaign should reconcile root workshop
drift, public `azoth` v0.2.0 freshness policy, the 3-tier product flow, and the
4-plane operating model into an approval-ready release/update boundary packet.

## Selected Seed

- Source: post-p4 route truth and product-strategy surfaces
- Candidate id: `public-product-update-policy-and-four-plane-release-boundary`
- Selected route: `research_initiative`
- Fresh approval required: yes

## Why This Is The Best Next Campaign

P4 closed with root internally coherent and public `azoth` intentionally stale.
The product strategy layer says the next real product move requires human
choice. PM mobility says there are no safe hydration candidates. The best next
question is therefore not "what task do we hydrate?" but "what public/product
boundary do we approve next?"

This campaign should answer:

- What root workshop changes are candidates for future public `azoth` content?
- What must remain root-only, cockpit-only, or project-owned?
- What would a safe public sync/release gate require?
- How should operator-facing language distinguish the 3-tier product flow from
  the 4-plane operating model?
- What should the operator approve next: public strategy, internal vocabulary
  cleanup, cockpit resilience, or defer?

## Budget

- Up to 3 child scopes.
- 1 bounded replay.
- Alignment mode: async.

## Allowed Actions

- `research_initiative`
- `refine_proposal`
- `capture_self_improvement`

## Blocked Without Fresh Explicit Gate

- `hydrate_task`
- `ship_task`
- public sync, release, tags, or public checkout mutation
- cockpit repo writes
- controlled project repo writes
- backup/private remote or credential work
- dependency or network expansion
- kernel/governance/M1 mutation
- destructive actions
- commits
- pushes

## Proposed Child Scope Plan

| Child | Action | Purpose | Output |
| ---: | --- | --- | --- |
| 1 | `research_initiative` | Inventory root/public/cockpit/project boundary evidence and current public freshness policy. | Public/update boundary research brief with current truth and open questions. |
| 2 | `refine_proposal` | Turn the research into a release/update boundary strategy and operator decision packet. | Approval-ready strategy packet with gate requirements and rejected alternatives. |
| 3 | `research_initiative` | Evaluate the packet against governance safety, product clarity, and operator UX; use bounded replay only if needed. | Evaluator score history, residual risks, and final recommendation. |

## Acceptance Criteria

- Public `azoth` v0.2.0 remains described as the latest approved/installable
  release unless a separate public sync gate is explicitly approved later.
- Root workshop drift is described as advisory, not public product content.
- The campaign distinguishes:
  - 3-tier product flow: root -> public `azoth` -> installed consumer/cockpit
    update
  - 4-plane operating model: root, public `azoth`, `yiwei-azoth-cockpit`, and
    controlled project repos
- No public, cockpit, or project repo is mutated.
- No roadmap/backlog/spec hydration occurs.
- The final packet gives the operator a clear approval choice for the next
  executable campaign.

## Suggested Operator Approval Prompt

```text
Approve autonomous-auto campaign: Public Product Update Policy and Four-Plane Release Boundary Strategy. Goal: decide the next public-product update strategy without mutating public azoth, cockpit, or project repos. Budget up to 3 child scopes with 1 bounded replay. Allowed actions: research_initiative, refine_proposal, capture_self_improvement. Inventory root/public/cockpit/project boundary evidence, reconcile public azoth v0.2.0 freshness with root workshop drift, distinguish the 3-tier product flow from the 4-plane operating model, and stop with an approval-ready release/update boundary packet. Do not hydrate, implement, commit, push, use network/dependencies, mutate public/cockpit/project repos, touch credentials/backups, or cross kernel/governance/M1/destructive gates.
```

## Stop Condition

Stop when the campaign has an evaluator-scored strategy packet and one explicit
operator choice: approve a public-release strategy campaign, approve a narrower
internal language-alignment campaign, approve a protected cockpit/private
resilience campaign, or defer.

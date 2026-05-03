# Post-P4 Next Campaign Design

Date: 2026-05-03
Scope: `2026-05-03-autonomous-auto-post-p4-next-campaign-design-1`

## Executive Read

Best next campaign goal candidate:

**Post-P4 Roadmap Re-Anchor and Next-Campaign Board**

Why this wins: `v0.2.0-p4` is now complete, but top-level
`active_version` still points at `v0.2.0-p4`. That is acceptable as a last
closed anchor for closeout, but it is not safe as the planning base for new
hydration or implementation. The next campaign should decide and establish the
post-p4 roadmap anchor first, then choose the first real post-p4 work lane from
repo-native candidate evidence.

## Repo-Status Inputs

| Surface | Current read |
| --- | --- |
| Git/gates | Clean tree before this design scope; no active run; no write claim. |
| Roadmap version state | `v0.2.0-p4` is `complete`, `final_patch: 34`, `completed_date: 2026-05-03`. |
| Header/planning anchor | Top-level `active_version` still points at `v0.2.0-p4`. |
| Planning banks | INI-MEM-003 is visible but current live implementation slices T-057/T-058 are complete; vector and temporal lanes are parked/gated. |
| Unscheduled initiatives | INI-MEM-002, INI-UX-001, INI-PLT-005, and INI-RST-006 remain phase-null. |
| Protected boundaries | Public sync/release, cockpit/project writes, backup/private remote, kernel/governance/M1, dependencies/network/credentials/destructive actions remain stop lines. |

## Option Board

| Rank | Candidate | Disposition | Why |
| --- | --- | --- | --- |
| 1 | Post-P4 Roadmap Re-Anchor and Next-Campaign Board | Recommended | Fixes the planning base before any new hydration; low dependency risk; directly follows p4 close. |
| 2 | INI-MEM-003 optional vector backend spike | Parked | Explicit dependency/backend gate; should wait until anchor is selected and baseline miss evidence justifies it. |
| 3 | INI-MEM-002 temporal validity review | Parked | Useful only if recall-quality evidence shows stale M2 correctness failures; no mutation should happen yet. |
| 4 | INI-UX-001 phone-friendly output | Good later campaign | Strong operator value, but less foundational than fixing the roadmap anchor. |
| 5 | INI-PLT-005 Antigravity deploy target | Good later campaign | Platform work may involve external/runtime freshness and install-path boundaries. |
| 6 | Autonomous PR publish control plane | Defer | Relevant to publishing the local branch, but it crosses GitHub/network/merge policy questions and should not be the first post-p4 roadmap campaign. |
| 7 | Nightly automation approval-to-handoff workflow | Defer | Valuable, but mixed-scope and less urgent than removing the closed-active-version ambiguity. |

## Recommended Campaign Declaration

Name: **Post-P4 Roadmap Re-Anchor and Next-Campaign Board**

Mode: `dynamic-full-auto`

Goal: Decide and establish the post-p4 roadmap anchor, then produce a ranked
next-campaign board from live repo-native planning banks, initiatives, proposals,
handoffs, and gate state.

Budget:

- Up to 3 child scopes.
- 1 bounded replay per child.
- Research/explore before writes.
- Writes limited to repo-internal planning truth and one campaign selection
  artifact unless the operator separately approves hydration.

Allowed actions:

- `research_initiative`
- `refine_proposal`
- `capture_self_improvement`
- one repo-internal anchor repair if route evidence says it is necessary

Forbidden actions:

- Roadmap task hydration or implementation.
- Public azoth sync/release.
- Cockpit repo writes or hook enablement.
- Controlled project repo writes.
- Backup/private remote work.
- Kernel/governance/M1 changes.
- Dependency, network, credential, or destructive actions.

## Child Scope Plan

| Child | Purpose | Expected output |
| --- | --- | --- |
| 1 | Roadmap-anchor analysis | Decide whether next anchor should be a new version shell, a phase-null planning board, or a patch/maintenance lane. |
| 2 | Candidate board synthesis | Rank INI-MEM-002, INI-MEM-003, INI-UX-001, INI-PLT-005, INI-RST-006, publish control-plane, and automation workflow candidates using readiness/risk/dependency/operator-value scoring. |
| 3 | Minimal anchor repair, if approved by route | Update only top-level roadmap planning anchor and/or add one next-campaign declaration artifact; do not hydrate tasks. |

## Acceptance Criteria

- `v0.2.0-p4` remains complete and is not reopened.
- The dashboard no longer creates ambiguity between a closed p4 phase and the
  next planning anchor, or the campaign records why the anchor must remain
  intentionally on the last closed version until a later selection.
- The candidate board names a single recommended first delivery/research
  campaign and at least three rejected/deferred alternatives.
- No roadmap/backlog/spec task hydration occurs.
- No protected boundary is crossed.
- `python3 scripts/roadmap_dashboard.py` parses and renders.
- `python3 scripts/azoth-deploy.py --check` remains green.

## Suggested Operator Prompt

Approve dynamic-full-auto campaign: **Post-P4 Roadmap Re-Anchor and
Next-Campaign Board**. Goal: decide and establish the post-p4 roadmap anchor,
then produce a ranked next-campaign board from live repo-native state. Budget up
to 3 child scopes and 1 bounded replay per child. Research/explore before writes.
Allowed writes are limited to repo-internal planning truth and one campaign
selection artifact. Do not hydrate tasks or implement. Stop at public azoth
sync/release, cockpit/project writes, backup/private remote, kernel/governance/M1,
dependency/network/credential/destructive gates.

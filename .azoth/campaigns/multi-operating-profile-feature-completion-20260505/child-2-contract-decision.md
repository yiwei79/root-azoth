# Child 2 Contract Decision

Campaign: `multi-operating-profile-feature-completion-20260505`
Child scope: `2026-05-05-autonomous-auto-multi-operating-profile-contract-2`
Route: `refine_proposal`
Date: 2026-05-05

## Decision

The canonical internal profile contract is now locked at:

`meta_session_research/architecture-update-proposal/profile-contract.md`

It is a branch-local contract for proof work, not a public release artifact and
not roadmap/backlog/spec hydration.

## Contract Effects

The contract makes the following decisions explicit:

- escalation beats lightness;
- `stock-lite` is only for simple read/status/search/summarize work with no
  trace or continuity requirement;
- focused verification and trace-required read-only work use `azoth-lite`;
- ordinary source/docs/tests/research edits outside governed state use
  `azoth-lite`;
- `.azoth`, command contracts, generated surfaces, finality, closeout,
  autonomous continuation, public release/sync/freshness, dependencies,
  credentials, destructive/history operations, and kernel/governance work use
  `azoth-full`;
- `meta-harness-experimental` remains an explicit experiment track.

## Concrete Implementation Gap

The next smallest safe internal slice is:

1. Add an explicit autonomous-continuation fixture to the `azoth-lite`
   classifier suite.
2. Align or deliberately justify the helper `handoff_packet` schema against the
   full contract handoff packet.
3. Add focused tests for that handoff decision.

This is a `ship_task` child, not hydration and not public release work.

## Rejected Alternatives

| Candidate | Decision | Reason |
| --- | --- | --- |
| Treat this contract as full feature completion | Reject | Shadow/eval proof and helper schema alignment are still missing. |
| Broaden default routing now | Reject | The proof plan still requires a bounded implementation/test slice. |
| Keep contract only in `.azoth/campaigns` | Reject | Future feature work needs a source artifact in the profile proposal pack. |
| Public release/freshness work | Reject | Explicitly on-demand only. |
| Hydrate roadmap/backlog/spec | Reject | Blocked by campaign declaration. |

## Recommended Child 3

Open `ship_task`: `multi-operating-profile-helper-proof-slice`.

Goal:

Implement the smallest internal helper/test proof slice:

- add the autonomous-continuation fixture;
- align or explicitly preserve the helper handoff packet shape;
- update focused classifier tests;
- run classifier/start-next tests;
- stop before public release, generated adapter churn, hydration, commits, or
  protected gates.

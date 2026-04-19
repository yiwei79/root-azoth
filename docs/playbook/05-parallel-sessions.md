# Parallel Sessions

> Safe minimum-viable protocol for running multiple Azoth sessions in parallel.

This playbook describes the **recommended Codex/Azoth pattern today**:

- multiple sessions may work in parallel on separate branches or worktrees
- exactly **one** integration operation runs at a time
- merges into the target branch happen **sequentially**, never concurrently

This is the lowest-effort way to get real value from parallel sessions without
pretending Azoth already supports full concurrent mutation of shared state.

## Why This Protocol Exists

Git is good at parallel branch work.

Azoth is **not yet** a true multi-writer control plane. Several state surfaces
are still shared at the repo level:

- `.azoth/scope-gate.json`
- `.azoth/run-ledger.local.yaml`
- `.azoth/session-state.md`
- `.azoth/backlog.yaml`
- `.azoth/roadmap.yaml`
- deploy/parity mirrors such as generated adapter surfaces

That means parallel coding is fine, but **parallel integration** is still risky.

## Roles

### Producer Session

A producer session may:

- create a branch or worktree
- explore, design, review, and implement locally
- refresh from the local target branch before its sync commit
- commit local changes on its own branch
- hand its branch to the integrator

A producer session should **not**:

- merge itself into the shared target branch while another session may also merge
- run final closeout for shared Azoth state unless it owns the active integration operation
- assume its local `.azoth/*` state is authoritative after another branch merges

### Integrate Run

A short-lived integrate run owns:

- merges into the target branch
- conflict resolution against the latest target branch
- final shared-state reconciliation
- closeout for the integration pass

Only one integration operation should exist at a time. This does **not** require
keeping a dedicated integrator session or worktree open between merges.

## Safe Workflow

1. Each session works on its own branch or worktree.
2. When a handoff is ready to land, start a short-lived integrate run from the target branch.
3. Producer sessions run `/worktree-sync`, which refreshes them against the local target branch before creating the sync commit.
4. The integrate run merges exactly one producer branch into the target branch through a temporary sandbox worktree.
5. After the merge, the remaining producer sessions rebase or merge from the updated target branch.
6. The next producer branch is integrated only after that refresh is complete.
7. Shared-state closeout happens once per integration step, not concurrently across sessions.

## Recommended Boundaries

Parallel sessions are safest when producers avoid mutating shared Azoth control-plane files.

Prefer parallelizing:

- feature code in isolated app/module paths
- tests tied to those isolated paths
- exploratory docs or notes that are easy to reconcile
- read-mostly investigation work

Avoid parallelizing unless one session is clearly the owner:

- `.azoth/*` control files
- `kernel/*`
- generated platform adapter surfaces
- closeout/versioning flows
- roadmap/backlog governance state

## Worktree Guidance

If you use Codex worktrees:

- multiple worktrees can remain open in parallel
- only one worktree should hold the live write claim at a time
- non-owning worktrees should stay in discovery/review/local-commit mode
- release or hand off the claim before another worktree performs integration

This is **coordinated single-writer, multi-worktree**, not full multi-writer.

## Merge Checklist For The Integrator

Before merging a producer branch:

- confirm no other integration operation is currently in flight
- pull or refresh the target branch first
- inspect whether the producer touched shared Azoth state
- if yes, reconcile those files deliberately instead of accepting both sides blindly

After merging:

- run any required parity/deploy regeneration
- run the targeted tests for the merged slice
- close out the integration step
- notify remaining producer sessions to refresh from the new target branch

## Operational Rule Of Thumb

Use this sentence with collaborators:

> Parallel branch work is allowed. Parallel integration is not.

That one line captures the current safe operating contract.

## When To Upgrade Beyond This

Move beyond the single-integrator model only when Azoth has:

- resource-scoped or domain-scoped write claims
- merge-safe semantics for shared `.azoth/*` state
- explicit concurrent closeout and resume rules
- tested ownership boundaries for generated surfaces

Until then, this protocol is the safest practical default.

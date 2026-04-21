# Automation Worktree Audit — Architect Note

Date: 2026-04-21
Branch context: `phase/v0.2.0-p3`

## Decision

- Do not run `/worktree-sync` on the four current automation-owned worktrees as-is.
- Treat three worktrees as report/evidence lanes only and close them after confirming they remain clean.
- Salvage only the small YAML-loader optimization from worktree `1325` onto a fresh producer branch rooted at `phase/v0.2.0-p3`.

## Current Automation Set

| Worktree | State | Assessment | Decision |
| --- | --- | --- | --- |
| `437f` | Detached, clean, parked at `53b990d` (old `main`) | Report lane, not a current producer | Close / prune |
| `d307` | Detached, clean, parked at `53b990d` (old `main`) | Report lane, not a current producer | Close / prune |
| `307e` | Detached, clean, parked at `53b990d` (old `main`) | Report lane, not a current producer | Close / prune |
| `1325` | Detached at `53b990d`, uncommitted edits in `scripts/welcome.py` and `scripts/run_ledger.py` | Contains one useful optimization, but not a valid handoff | Extract and recreate on fresh branch |

## Azoth-Native Reasoning

The correct unit of integration is not "an open automation worktree." The correct
unit is a current producer handoff that satisfies the worktree-sync contract:
current base, explicit producer branch, committed diff, targeted verification, and
queue-ready provenance.

This audit follows the repo's existing memory and workflow rules:

- `ep-303` — automation outputs should remain narrow evidence lanes; they are not
  merge authorities by default.
- `ep-305` — producer handoffs touching governed shared state must carry tracked
  approval evidence in the queued producer commit itself.
- `worktree-sync-completion-includes-producer-cleanup` — once a lane is judged
  non-integrable or already absorbed, cleanup is part of the safe terminal state.

## Why Bulk Sync Is Wrong

Running `/worktree-sync` on all four worktrees would manufacture stale producer
noise rather than promote current value:

- three worktrees have no novel producer diff and are parked on an outdated base
- one worktree has useful but uncommitted local edits on the same outdated base
- none of the four currently exist as ready handoffs in the shared queue

That means the architecturally correct move is selective extraction, not bulk
integration.

## Approved Follow-Through

1. Record this decision in repo-local architect memory.
2. Port the `yaml.CSafeLoader` fallback optimization from worktree `1325` onto a
   fresh branch from `phase/v0.2.0-p3`.
3. Verify the affected surfaces with targeted tests.
4. Leave the other automation worktrees out of the integration path and prune
   them once no longer needed for inspection.

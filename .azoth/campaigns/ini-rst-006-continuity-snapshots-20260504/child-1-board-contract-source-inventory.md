# INI-RST-006 Child 1 Research Report

Date: 2026-05-04
Campaign: `ini-rst-006-continuity-snapshots-20260504`
Child scope: `2026-05-04-autonomous-auto-ini-rst-006-board-contract-and-first-snapshot-set-1`
Action: `research_initiative`
Status: complete enough for the first `ship_task` child

## Boundary

Historical phase boards are repo-local continuity aids. They summarize canonical
state for humans and must not become automation inputs, readiness gates, or a
second roadmap/backlog authority.

Canonical authority remains:

- `.azoth/roadmap.yaml`
- `.azoth/backlog.yaml`
- task specs and named evidence files cited from `.azoth/roadmap-specs/v0.2.0/`

If a board disagrees with canonical state, canonical state wins.

## Source Inventory

### Campaign Declaration

- `.azoth/campaigns/ini-rst-006-continuity-snapshots-20260504/context.yaml`
  - Prepared campaign artifact.
  - Approves a 3-child budget with 1 bounded replay.
  - Limits action classes to `research_initiative` and `ship_task`.
  - Blocks public sync/release, public checkout mutation, cockpit/project
    writes, backup/private remote, kernel/governance/M1, network/dependency,
    credential, destructive, and broad roadmap/backlog rephasing work.

### Existing Exemplar

- `.azoth/roadmap-specs/v0.2.0/PHASE-02-HISTORY.md`
  - Names `.azoth/roadmap.yaml` and `.azoth/backlog.yaml` as authority.
  - States the board is a human continuity surface and does not drive automation.
  - Uses compact sections: status, canonical sources, completed items,
    historical read, carried-forward notes, explicit non-carry-forward, notes.
  - This is the style contract for the next boards.

### Initiative Truth

- `.azoth/roadmap.yaml`
  - `active_version: v0.2.0-p4`.
  - `INI-RST-006` is phase-null, low-priority, run-state work.
  - The initiative summary says boards live under `.azoth/`, summarize canonical
    roadmap/backlog state, and do not become a second automation source of truth.

- `.azoth/backlog.yaml`
  - `BL-066` is complete and references `INI-RST-006`.
  - `BL-066` delivered the first board:
    `.azoth/roadmap-specs/v0.2.0/PHASE-02-HISTORY.md`.
  - The backlog entry explicitly says the initial artifact was a continuity
    surface only, with no automation contract or dashboard dependency.

### Phase 3 Snapshot Sources

- `.azoth/roadmap.yaml`
  - `v0.2.0-p3` is complete.
  - Final patch: `79`.
  - Goal: carry-forward hardening for incomplete p2 work, memory policy,
    platform parity, roadmap tooling, and bounded evidence refresh.
  - `pending_task_refs: []`.
  - Completed-task block runs from `T-015` through `T-033`, including
    `P1-020`, `P1-021`, `BL-062`, `BL-063`, `BL-065`, and `T-KRP-A` through
    `T-KRP-E`.
  - Narrative note: phase-2 carry-forward drift repaired, Karpathy follow-ons
    complete, planning/initiative-bank routing complete, and branch-local
    autonomous-auto reached Green with `T-033`.

- `.azoth/roadmap-specs/v0.2.0/T-015.yaml` through
  `.azoth/roadmap-specs/v0.2.0/T-033.yaml`
  - Per-task evidence refs for task titles and acceptance context when the board
    needs more than roadmap title/date.

### Phase 4 Snapshot Sources

- `.azoth/roadmap.yaml`
  - `v0.2.0-p4` is complete.
  - Final patch: `34`.
  - Completed date: `2026-05-03`.
  - Goal: post-stable stabilization repair window for release truth, cockpit
    deployability, planning truth, formatting gates, and public-product
    freshness policy.
  - `pending_task_refs: []`.
  - Completed-task block includes `T-034` through `T-058`, with `T-054` and
    `T-055` listed before earlier historical p4 tasks because roadmap order
    preserves the latest reconciliation shape.
  - Narrative note: p4 closed after planning truth, cockpit deployment evidence,
    format-gate readiness, and closeout candidate evidence were reconciled
    through `T-058`.

- `.azoth/roadmap-specs/v0.2.0/V0.2.0-P4-POSTMORTEM-AND-NEXT-LANES.md`
  - Best source for historical read, validation matrix, four-plane authority
    model, protected boundaries, and residual next-lane framing.
  - Important caution: p4 history does not approve public sync/release,
    cockpit/project writes, backup/private remote work, or kernel/governance/M1.

- `.azoth/roadmap-specs/v0.2.0/V0.2.0-P4-ROLLOUT-PLAN.md`
  - Best source for original p4 release/stabilization intent.
  - It is historical relative to T-040 through T-058 and should be cited as the
    original baseline, not as current task authority.

- `.azoth/roadmap-specs/v0.2.0/T-034.yaml` through
  `.azoth/roadmap-specs/v0.2.0/T-058.yaml`
  - Per-task evidence refs for task titles and acceptance context.

## Proposed Board Contract

Each board should include:

- Title naming the phase or milestone slice.
- Status block with slice id, outcome, final patch, goal, and theme/category
  cues when available.
- Canonical Sources section naming `.azoth/roadmap.yaml` and
  `.azoth/backlog.yaml` as authority.
- Evidence Sources section listing the specific specs or reports summarized.
- Completed In Phase section derived from canonical completed-task blocks.
- Historical Read section written as synthesis, not route authority.
- Carry-Forward or Residual Notes section when canonical sources name them.
- Notes section repeating that the board does not drive automation and cannot
  certify repo, public-product, cockpit, or project readiness.

Each board must avoid:

- Mutating `.azoth/roadmap.yaml` or `.azoth/backlog.yaml`.
- Inventing task completion from chat memory.
- Treating residual risks as open approved scope.
- Claiming readiness beyond the commands and evidence cited.
- Creating dashboard, route, or automation dependencies on the board.

## Recommended Child 2 Writes

Create these non-authoritative artifacts:

- `.azoth/roadmap-specs/v0.2.0/PHASE-HISTORY-BOARD-CONTRACT.md`
- `.azoth/roadmap-specs/v0.2.0/PHASE-03-HISTORY.md`
- `.azoth/roadmap-specs/v0.2.0/PHASE-04-HISTORY.md`

Do not update `.azoth/roadmap.yaml`, `.azoth/backlog.yaml`, generated platform
mirrors, public checkout state, cockpit/project repos, kernel/governance/M1
surfaces, dependencies, credentials, or release/sync artifacts.

## Validation Plan For Child 2

Minimum validation:

- `test -f .azoth/roadmap-specs/v0.2.0/PHASE-HISTORY-BOARD-CONTRACT.md`
- `test -f .azoth/roadmap-specs/v0.2.0/PHASE-03-HISTORY.md`
- `test -f .azoth/roadmap-specs/v0.2.0/PHASE-04-HISTORY.md`
- `python3 scripts/roadmap_dashboard.py`
- `python3 scripts/azoth-deploy.py --check`
- `git diff -- .azoth/roadmap.yaml .azoth/backlog.yaml`

Expected result: the board files exist, the dashboard still reads canonical
roadmap state, generated mirrors remain in sync, and roadmap/backlog diffs are
empty.

## Exit Judgment

Child 1 has enough source clarity to proceed to the first `ship_task` child.
The implementation should produce the contract and p3/p4 boards only. If p3 or
p4 canonical state becomes ambiguous during writing, stop before publishing the
board text and return to research rather than guessing.

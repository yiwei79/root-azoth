# Phase History Board Contract

## Purpose

Phase history boards are repo-local continuity snapshots for humans. They make
completed phase or milestone slices easier to re-enter without making those
snapshots a second planning system.

## Authority Boundary

- `.azoth/roadmap.yaml` remains the authoritative roadmap and phase record.
- `.azoth/backlog.yaml` remains the authoritative operational task record.
- Task specs and named evidence files under `.azoth/roadmap-specs/v0.2.0/`
  provide supporting evidence when cited.
- History boards do not drive automation, routing, readiness checks, release
  claims, dashboards, or task scheduling.
- If a history board disagrees with canonical roadmap/backlog state, trust the
  canonical state and repair the board later inside an approved scope.

## Required Sections

Each board should include:

- `Status`: slice id, outcome, final patch, goal, and major themes when known.
- `Canonical Sources`: roadmap/backlog authority statement.
- `Evidence Sources`: specific specs or reports summarized by the board.
- `Completed In Phase`: task list derived from canonical completed-task blocks.
- `Historical Read`: human synthesis of what the phase changed.
- `Carry-Forward` or `Residual Notes`: only when canonical evidence supports it.
- `Notes`: explicit non-authoritative and non-readiness language.

## Writing Rules

- Derive completed tasks from `.azoth/roadmap.yaml`, not chat memory.
- Preserve canonical task ids and titles.
- Keep residuals descriptive; do not turn them into approved scope.
- Distinguish public-product readiness, cockpit/project readiness, and
  root-workshop coherence.
- Do not mutate `.azoth/roadmap.yaml` or `.azoth/backlog.yaml` while writing a
  history board.
- Do not add scripts, validators, generated mirrors, or dashboard dependencies
  unless a later explicit implementation scope approves that automation.

## Validation Expectations

Minimum validation for a new board:

- The board file exists in `.azoth/roadmap-specs/v0.2.0/`.
- `python3 scripts/roadmap_dashboard.py` still reads canonical roadmap state.
- `python3 scripts/azoth-deploy.py --check` remains in sync when no source
  command, skill, or agent surface changed.
- `git diff -- .azoth/roadmap.yaml .azoth/backlog.yaml` is empty.

## Non-Goals

- No public sync or release.
- No public checkout mutation.
- No cockpit or project repo writes.
- No backup/private remote or credential work.
- No kernel, governance, or M1 mutation.
- No dependency or network expansion.
- No destructive actions.
- No broad roadmap/backlog rephasing.

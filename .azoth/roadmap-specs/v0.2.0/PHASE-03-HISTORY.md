# v0.2.0 Phase 3 History Board

## Status

- Slice: `v0.2.0-p3`
- Outcome: complete
- Final patch: `79`
- Goal: Carry-forward hardening for incomplete p2 work, memory policy, platform parity, roadmap tooling, and bounded evidence refresh
- Themes: `A`, `C`, `D`

## Canonical Sources

- `.azoth/roadmap.yaml` is the authoritative phase record.
- `.azoth/backlog.yaml` is the authoritative operational task record.
- This file is a repo-local historical board for human continuity; it does not drive automation.

## Evidence Sources

- `.azoth/roadmap.yaml` version block `v0.2.0-p3`
- `.azoth/roadmap-specs/v0.2.0/T-015.yaml` through `.azoth/roadmap-specs/v0.2.0/T-033.yaml`
- `.azoth/roadmap-specs/v0.2.0/PHASE-02-HISTORY.md` for the prior carry-forward boundary

## Completed In Phase 3

- `T-015` — Codex intelligent model selection seed and proposal
- `T-016` — Codex seamless permissions profile (repo-local execpolicy)
- `P1-021` — Memory operation platform parity
- `P1-020` — Verbatim-first M3 storage strategy
- `BL-062` — `scripts/initiative_scaffold.py` — one-command initiative + task stub creation
- `BL-063` — `roadmap_dashboard.py`: `--theme` / `--track` cross-section filters for multi-dimensional view
- `BL-065` — Worktree-upgrade external evidence refresh lane
- `T-KRP-A` — `CLAUDE.md` kernel: embed Karpathy behavioral layer
- `T-017` — Codex selector policy + task-definition lane
- `T-KRP-B` — New skill: `karpathy-principles` `SKILL.md` for injectable discipline slot
- `T-KRP-C` — Builder agent posture: surgical changes + simplicity-first enforcement
- `T-KRP-D` — Orchestrator: assumption-surfacing checkpoint at goal classification
- `T-KRP-E` — `structured-autonomy-plan`: goal -> success-criteria gate
- `T-018` — Initiative bank contract validator and readiness report
- `T-019` — Artifact-class richness adapters for initiative banks
- `T-020` — Planning-bank surfacing and routing in session dashboards
- `T-021` — Planning-bank ID and coverage policy
- `T-022` — Plan-only initiative hydration handoff helper
- `T-023` — Initiative intake and seed contract
- `T-025` — Codex runtime model resolver and spawn-effort isolation
- `T-024` — Lifecycle router over initiative readiness surfaces
- `T-026` — Durable autonomous-auto wakeup driver
- `T-027` — Initiative lifecycle evaluator and discoverability spine
- `T-028` — Run-ledger serialized stage evidence writes
- `T-029` — Autonomous-auto campaign audit report
- `T-030` — Autonomous campaign strategy budget repair
- `T-031` — Approved write-mode hydration delegation
- `T-032` — Proposal refinement to hydration readiness bridge
- `T-033` — Autonomous-auto learning harvester and self-heal router

## Historical Read

Phase 3 closed the carry-forward gap from phase 2 and turned several planning,
memory, platform, and autonomy ideas into concrete repo-native control-plane
surfaces. The phase repaired memory/platform carry-forward work, completed the
Karpathy behavior layer, and made planning-bank and initiative-bank routing
visible enough for later autonomous-auto campaigns to reason from repo state
instead of chat context.

The second half of the phase is where autonomous-auto became a governed loop
rather than a loose instruction. T-024 through T-033 added lifecycle routing,
wakeup behavior, campaign audit reports, strategy preflight, write-mode
hydration delegation, proposal-to-readiness bridging, and the learning
harvester/self-heal router. The canonical roadmap note records that the
branch-local autonomous-auto campaign reached Green with `T-033`.

## Carry-Forward And Residual Notes

- The canonical phase block has `pending_task_refs: []`.
- Completed memory/platform/autonomy carry-forward work stays in history.
- Unscheduled initiatives remain phase-null until explicitly scheduled into a
  future slice.
- This board does not approve new autonomy, memory, planning-bank, platform, or
  product feature work.

## Notes

- Use this board as a historical snapshot, not as a planning source of truth.
- This board does not certify repo readiness, public-product freshness,
  cockpit readiness, project readiness, release readiness, or automation
  authority.
- If roadmap/backlog state disagrees with this file, trust the canonical
  `.azoth/` state files.

# Azoth Bootloader State

Last updated: 2026-04-11 (session-closeout ep-125 — milestone versioning + Copilot parity closeout)

## Current Phase

Milestone **v0.2.0** — **milestone-local phase 1** (`azoth.yaml` `phase: 1`; welcome strip `lifecycle_phase: 8`)  
**Toolkit version:** **0.1.1.30** (`azoth.yaml`) · **Roadmap:** `active_version: v0.2.0-p1` · `current_patch: 30` (`.azoth/roadmap.yaml`) · **Git:** branch **`patch/copilot-pipeline-memory-parity`**.

## Session outcome (ep-125) — versioning + Copilot orchestration/memory parity

- **Fixed the milestone versioning contract end-to-end**: active roadmap work now uses phase-shaped slices (`v0.2.0-p1`) while internal delivery versions remain `0.1.<phase>.<patch>`, with the active repo state bumped to **0.1.1.30 / patch 30**.
- **Closed the Copilot pipeline parity gap**: explicit `/auto`-family requests are now treated as orchestrated pipeline entry, `dynamic-full-auto` is hard-bound to the orchestrator, and Copilot-specific always-on instructions prevent inline bypass when slash routing does not fire.
- **Extended closeout memory parity** so Copilot writes the supplemental Claude project-memory mirror during `/session-closeout`, while `.azoth/*` remains the authoritative cross-IDE source of truth.

## Open decisions

- Whether to fold the remaining W2 handoff duties (`bootloader-state.md`, run-ledger/session-state refresh) directly into `scripts/do_closeout.py` so closeout becomes fully mechanical.
- Which active backlog scope to open after `/intake`.

## Next action

Run `/intake` first for the 4 queued inbox JSONL files, then `/next` to choose the next active backlog scope.

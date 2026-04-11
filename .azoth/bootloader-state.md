# Azoth Bootloader State

Last updated: 2026-04-11 (session-closeout ep-121 — P1-005 auto parity closeout)

## Current Phase

Milestone **v0.2.0** — **milestone-local phase 1** (`azoth.yaml` `phase: 1`; welcome strip `lifecycle_phase: 8`)  
**Toolkit version:** **0.1.24** (`azoth.yaml`) · **Roadmap:** `active_version: v0.2.1` · `current_patch: 16` (`.azoth/roadmap.yaml`) · **Git:** branch **`patch/v0.2.0-p1-012-dfa-e2e-friction`**.

## Session outcome (ep-121) — P1-005 / Copilot Stage 0 parity + retrospective /auto close

- **Fixed the source contract:** `/start` resume and `/next` post-approval guidance now state that scope approval declares intent only; pipeline selection still applies to standard scopes, and `/auto` with Stage 0 is the default when no pipeline was chosen.
- **Resynced deployed mirrors:** regenerated Copilot, OpenCode, and agent workflow outputs with `scripts/azoth-deploy.py`, keeping adapter surfaces aligned with the updated source prompts; added `tests/test_start_next_pipeline_contract.py`.
- **Closed P1-005 correctly:** marked the backlog item complete and reran it retrospectively through `/auto`; architect audit confirmed the docs deliverable was already satisfied, so the builder stage was skipped by design.

## Open decisions

- Promotion candidate only: consider promoting the pattern **"scope approval declares intent only; `/auto` Stage 0 remains required when no pipeline is selected"** if it is reinforced again.

## Next action

Run `/intake` first for the 4 queued inbox JSONL files, then `/next` to continue the next active v0.2.1 backlog item (likely P1-006).

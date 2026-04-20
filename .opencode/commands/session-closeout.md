---
description: Unified eval + close + sync — run at the end of every session
agent: orchestrator
---

# /session-closeout

Run this command before ending any session. It evaluates the session, resolves whether
the active state is a delivery scope or an exploratory session, performs the matching
closeout path, and surfaces any queued inbox items.

## Preconditions

<!-- P1-016: Antigravity compliance -->
- Resolve the active session first: use a live approved `.azoth/scope-gate.json` when one
  exists; otherwise fall back to an active `.azoth/session-gate.json` for exploratory work.
- If a delivery scope exists, verify session scope was maintained throughout.
- See `docs/antigravity-compliance-matrix.md` for platform parity gaps.

## Part A: Evaluate Session Outputs

Prepare a short end-of-session summary covering:
- what was accomplished,
- what remains open or risky,
- whether human follow-up is still needed.
- if the session changed roadmap / backlog / initiative planning state, what the
  next operational backlog item or initiative now is, and whether it is already
  operationalized in backlog rather than only existing as a spec or note.

## Part B: Close Session

### Steps

1. Summarize what was accomplished in 1–3 sentences and note open work, entropy, or drift.
2. Ask whether the session revealed a reusable pattern or lesson. If yes, capture it in `.azoth/memory/episodes.jsonl`.
3. Structure the episode:
   ```json
   {
     "id": "uuid",
     "timestamp": "ISO-8601",
     "session_id": "uuid",
     "type": "success | failure | decision | pattern",
     "goal": "session goal",
     "summary": "what happened",
     "lessons": ["lesson 1", "lesson 2"],
     "tags": ["relevant-tags"],
     "reinforcement_count": 0
   }
   ```
4. If a pattern is reinforced across 2+ episodes, propose M3 → M2 promotion. Never auto-promote.

### Closeout Modes

- **Full closeout** = active delivery scope (`.azoth/scope-gate.json`) present. Run W1–W4.
- **Light closeout** = active exploratory session (`.azoth/session-gate.json`) present but no active scope gate. Run W1 + W2-lite only.
- **No active session** = stop softly and route to `/remember` or a new exploratory session instead of pretending there is a real delivery closeout to run.

### Write Checkpoints (W1 → W2 → W3 → W4)

Execute in order. After each write, log its status before proceeding to the next.
If any write is denied or fails, stop and follow the **On Failure** guidance below.

**Governed closeout precondition:** Full closeout only. If the active scope is governed or `target_layer: M1`,
`scripts/do_closeout.py` must validate the latest matching human final-delivery approval in
`.azoth/final-delivery-approvals.jsonl` before W1. Approval evidence is consume-only during
closeout: read it, validate it, and leave it unchanged. Failures must stop before the first
W1–W4 mutation. See `docs/GATE_PROTOCOL.md`.

**W1 — Append episode** → `.azoth/memory/episodes.jsonl`

- Append the episode structured in step 4
- If the session changed a platform adapter, command surface, or parity behavior, name the affected platform, the primary surface, any compatibility fallback, and remaining mechanical limits.
- If Codex parity changed, say whether the change affected generated `.agents/skills/azoth-*` wrappers, literal-token fallback, `.codex/config.toml` / `.codex/hooks.json`, or the current minimal compatibility-hook contract.
- Log: `W1 ✓ episode {id} appended — proceeding to W2`

**W1b — Optional reinforcement_count update** → `scripts/reinforcement_count.py`

- Ask whether any prior episode's lesson explicitly recurred during this session.
- If yes, require the human to confirm the exact episode id — never infer it from tags or prose.
- Use the active `session_id` from `.azoth/scope-gate.json`; do not invent or reuse a prior session id.
- Within an already-running `/session-closeout` flow, use only:
  ```bash
  python3 scripts/reinforcement_count.py <ep-id> --session-id <active-session-id> --source closeout
  ```
- Do **not** run `python3 scripts/do_closeout.py --reinforce-episode <ep-id>` here; it re-enters the full W1-W4 closeout path and can append W1 twice, re-run W2, and trigger an extra W4 patch bump.
- Never increment the same prior episode more than once per session.
- If no recurrence is confirmed, skip W1b silently — it is always optional.
- Log: `W1b ✓ reinforcement_count incremented for {ep-id} — proceeding to W2` (or `W1b skipped — proceeding to W2`)

**W2 — Update session state** → `.azoth/bootloader-state.md` + `.azoth/run-ledger.local.yaml` + gate closure

- Update `bootloader-state.md` with session outcome (phase, what changed, open decisions).
- Carry `session_mode: exploratory | delivery` through the session registry and `.azoth/session-state.md`.
- **Light closeout:** close `.azoth/session-gate.json` with `status: closed` and `closed_at`; skip delivery-only continuity and versioning work.
- If the session changed roadmap / backlog / initiative planning state, run a
  **full-closeout only**
  continuity audit before closing:
  - move finished slices into backlog `status: complete` and roadmap `completed_tasks`
    where applicable
  - if an initiative `task_ref` / `spec_ref` still points at a now-completed slice,
    retarget it to the next real pending slice or explicitly note why it remains on the
    completed one
  - if a slice is described as the next planned follow-on in roadmap / orientation /
    close summary language, ensure it exists as a real backlog item or explicitly say it
    is still spec-only
  - if a backlog item was added and completed in the same session, say that explicitly
    in the close summary so the human does not infer it was skipped
- When `.azoth/run-ledger.local.yaml` contains a `sessions:` registry, use the active
  scope `session_id` as the default selected session. If a matching session entry exists,
  update that entry first: set it to `parked` when follow-up work remains or `closed` when
  the session is finished, refresh its `next_action`, and preserve `active_run_id` only when
  it still points at resumable work.
- **W2-claim — Release write claim**: If a write claim is held by this session in
  `.azoth/run-ledger.local.yaml`, release it now via `release_write_claim` / `run_ledger.py`.
  If already absent, treat it as a no-op.
- **Full closeout:** close the scope gate by writing `.azoth/scope-gate.json` with `approved: false` and add
  `closed_at` (ISO-8601 timestamp). Preserve all other fields so the gate is auditable.
- Cross-IDE handoff: if the session used **`.azoth/session-state.md`**, refresh it (active task,
  files touched, next action, pending decisions) with the same `session_id` as the selected
  registry entry. Preserve any stage-aware checkpoint fields already present there
  (`pipeline`, `pipeline_position`, `current_stage_id`, `completed_stages`, `pending_stages`,
  `pause_reason`, `active_run_id`) instead of collapsing continuity to prose only; if unused,
  log `session-state skipped` in the alignment summary.
- Keep W2 authoritative: if any later mirror diverges from repo-local state, W2 wins.
- Log: `W2 ✓ bootloader-state.md updated, write claim released, gate closed` and proceed to W3 only for full closeout.

**W3 — Update Claude Code memory** → `~/.claude/projects/<project-key>/memory/`

Full closeout only.

- W3 is a supplemental mirror of the repo-local closeout snapshot for Claude Code memory.
  `.azoth/` remains authoritative; if W2 and W3 diverge, W2 wins.
- Write or refresh `project_status.md` and the `MEMORY.md` Project Status index line.
  Refresh `feedback_*.md` only when this session changed a durable preference.
- If W3 is blocked, log `W3 deferred — sync ~/.claude/.../memory/ manually or rerun closeout in Claude Code`
  and complete W1/W2/W4. Do not silently skip W3.
- Log: `W3 ✓ memory updated — proceeding to W4`

**W4 — Bump patch version and refresh orientation cache** → `python scripts/version-bump.py --patch`

Full closeout only.

- Run `python scripts/version-bump.py --patch` from the repo root
- This always fires — every closeout increments the patch version
- Delete `.azoth/session-orientation.txt` (if present) so that IDEs without a `SessionStart` hook do not surface stale orientation in the next session.
- Log: `W4 ✓ version bumped X → Y, orientation cache cleared`

### On Failure

If a write checkpoint is denied or fails mid-sequence:

- **W2 or W3 denied**: safe to re-run session-closeout — these are idempotent overwrites.
  Resume from the denied step only; do not re-append W1. If only the scope gate write
  was denied, write it standalone before closing.
- **W1 denied**: the episode was not written. Before re-appending, check
  `.azoth/memory/episodes.jsonl` for the episode `id` to avoid duplicates.
- Report which checkpoint failed in the close summary so the human can act.

## Part C: Sync Changes

1. Stage relevant files: `git add` (specific files, not `-A`)
2. Generate conventional-commit message summarizing the session
3. Commit
4. Report: commit SHA, files changed, test status

## Part D: Surface Queued Insights

Check the insight inbox and inform the human. Do NOT process insights during closeout.

### Steps

1. Check `.azoth/inbox/` for `.jsonl` files (exclude `.gitkeep` and `processed/`)
2. If files exist:
   - Report count: "📥 {N} insight file(s) queued in inbox"
   - List filenames and source attribution (from first line of each file)
   - Remind: "Run `/intake` next session to process these through the governed protocol"
3. If no files: report "📭 Inbox empty — no pending insights"

### Rules

- **Closeout surfaces; it does not process** (F4). Run `/intake` explicitly to triage insights.
- **Do NOT read insight content beyond source attribution**. Full triage happens in `/intake`.
- This step is informational — it never modifies inbox files or M3.

## Output

Present a close summary with: outcome, session mode, entropy, episodes captured, promotion proposals,
alignment needed, and next action.

## Rules

1. This is a COMPOSED command — do NOT invoke separate eval or close commands
2. Always capture at least one episode
3. Never auto-promote — proposals require human approval
4. Keep the close summary under 500 words (phone-friendly)

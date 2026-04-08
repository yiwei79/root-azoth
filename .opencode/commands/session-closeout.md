---
description: Unified eval + close + sync — run at the end of every session
---

# /session-closeout

Run this command before ending any session. It evaluates work, captures episodes,
and syncs changes — all in a single pass.

## Part A: Evaluate Session Outputs

Apply `agentic-eval` style review to work produced this session.

### Evaluation Criteria

1. Work aligns with the current phase goal (check `azoth.yaml`)
2. Tests pass and cover new functionality
3. Kernel integrity preserved (no unauthorized changes)
4. Entropy stayed within bounds
5. Architecture decisions (all in docs/DECISIONS_INDEX.md) respected

### Output Format

For each artifact reviewed:
- artifact:
- strengths:
- gaps:
- entropy or drift risk:
- human alignment needed:

## Part B: Close Session

Compress session into actionable signals.

### Steps

1. Summarize what was accomplished (1-3 sentences).

2. Assess entropy surfaced this session:
   - Files changed count and scope
   - Any drift from approved state
   - Unresolved decisions

3. Ask: "Did this session reveal a reusable pattern or lesson?"
   - If yes: capture as episode in `.azoth/memory/episodes.jsonl`
   - Apply auto-classification using the Promotion Rubric's four questions

4. Structure an episode:
   ```json
   {
     "id": "uuid",
     "timestamp": "ISO-8601",
     "session_id": "uuid",
     "type": "success | failure | decision | pattern",
     "goal": "session goal",
     "summary": "what happened",
     "lessons": ["lesson 1", "lesson 2"],
     "tags": ["relevant-tags"]
   }
   ```

5. Check for promotion candidates:
   - Any pattern reinforced across 2+ episodes? → Propose M3 → M2 promotion
   - Present proposals to human (never auto-promote)

### Write Checkpoints (W1 → W2 → W3 → W4)

Execute in order. After each write, log its status before proceeding to the next.
If any write is denied or fails, stop and follow the **On Failure** guidance below.

**W1 — Append episode** → `.azoth/memory/episodes.jsonl`

- Append the episode structured in step 4
- Log: `W1 ✓ episode {id} appended — proceeding to W2`

**W2 — Update session state** → `.azoth/bootloader-state.md` + `.azoth/scope-gate.json`

- Update `bootloader-state.md` with session outcome (phase, what changed, open decisions)
- Close the scope gate: write `.azoth/scope-gate.json` with `approved: false` and add
  `closed_at` (ISO-8601 timestamp). Preserve all other fields so the gate is auditable.
- Log: `W2 ✓ bootloader-state.md updated, scope gate closed — proceeding to W3`

**W2 field checklist (BL-024)** — Before writing `bootloader-state.md`, align the **Current Phase** /
toolkit summary with canonical sources (read from disk, not from memory):

| Source | Fields to mirror |
|--------|------------------|
| `azoth.yaml` | `version` (delivery time-series), `phase` (1–7) |
| `.azoth/roadmap.yaml` | Top-level `active_version`; in that version’s block, `current_patch` when `status: active`; `current_phase` / `current_phase_title` should stay consistent with `azoth.yaml` `phase` (see `tests/test_handoff_artifacts.py::test_phase_consistent`) |

**W2 vs W4 ordering:** `python scripts/version-bump.py --patch` (W4) updates `azoth.yaml` `version` and the active block’s `current_patch` in `roadmap.yaml`. If you draft `bootloader-state.md` **before** W4, the header can show a **pre-bump** patch — **refresh the bootloader narrative after W4** (or perform W2 only after W4 for the version line).

**W2b (after W4, recommended)** — Re-read `azoth.yaml` and `.azoth/roadmap.yaml` and fix any **Current Phase** one-liner in `bootloader-state.md` if it still reflects the old patch.

**W3 — Update Claude Code memory** → `~/.claude/projects/<project-key>/memory/`

- **Design (cross-IDE parity):** W1/W2 in `.azoth/` are **authoritative** for every platform (Claude Code, Cursor, OpenCode, Copilot). W3 **mirrors** that same snapshot for Claude Code’s native project memory (`project_status.md` aligns with `bootloader-state.md` + last episode). **Never** treat `~/.claude/.../memory/` as the only record — see **`docs/AZOTH_ARCHITECTURE.md`** (Cross-IDE session memory parity). Copilot/OpenCode do not read `~/.claude/`; parity for them is **committed W1/W2** (and `azoth.yaml`).
- **Resolve the path (do not skip this step):** Claude Code stores per-project memory under `~/.claude/projects/`, where **`<project-key>`** is the absolute workspace path with the leading `/` removed and every `/` replaced by `-` (example: `/Users/you/work/root-azoth` → `-Users-you-work-root-azoth`). Full example: `~/.claude/projects/-Users-you-work-root-azoth/memory/`.
- **Why W3 is often missed:** these files live **outside the repo**; Cursor assistants may lack access or treat W3 as “human-only.” If denied, retry with full permissions or complete W3 manually — do not close the session without updating memory or explicitly logging W3 failed.
- **Minimum writes:** `project_status.md` (phase, version, roadmap patch, last episode, last delivery, next backlog step, open gaps) and **`MEMORY.md`** index line for Project Status. Add or refresh `feedback_*.md` when a durable preference changed.
- Add new memories if the session revealed user preferences, feedback, or reference info
- This ensures the next Claude Code session has full context even before Azoth's
  own memory system (M3 episodes) is surfaced during SURVEY phase
- Log: `W3 ✓ memory updated — all checkpoints complete`

**W4 — Bump patch version** → `python scripts/version-bump.py --patch`

- Run `python scripts/version-bump.py --patch` from the repo root
- This always fires — every closeout increments the patch version
- Log: `W4 ✓ version bumped X → Y`

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

## Permission Settings

If your Claude Code permission mode requires per-call confirmation for Write/Edit tools,
the W1–W3 checkpoint sequence will prompt three separate approvals. To allow uninterrupted
batch writes for the duration of a session, add Write and Edit to your project's
`settings.local.json` allow list:

```json
{
  "permissions": {
    "allow": [
      "Write(.azoth/**)",
      "Edit(.azoth/**)",
      "Write(.claude/projects/**)",
      "Edit(.claude/projects/**)"
    ]
  }
}
```

> **Governance caveat**: This grants Write/Edit without per-call confirmation for the
> session duration — use only in trusted, scope-gated sessions (scope-gate.json approved).

## Output

Present a close summary:
```
## Session Close — {date}
- **Outcome**: {what was accomplished}
- **Entropy**: {total delta, zone}
- **Episodes captured**: {count}
- **Promotions proposed**: {count or none}
- **Alignment needed**: {open questions for human}
- **Next**: {suggested next action}
```

## Rules

1. This is a COMPOSED command — do NOT invoke separate eval or close commands
2. Always capture at least one episode
3. Never auto-promote — proposals require human approval
4. Keep the close summary under 500 words (phone-friendly)

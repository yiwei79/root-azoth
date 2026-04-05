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
   Append to `.azoth/memory/episodes.jsonl`

5. Check for promotion candidates:
   - Any pattern reinforced across 2+ episodes? → Propose M3 → M2 promotion
   - Present proposals to human (never auto-promote)

6. Update `.azoth/bootloader-state.md` with session outcome.

7. **Update Claude Code memory** (for cross-session continuity):
   - Update the project status memory in `~/.claude/projects/.../memory/` with:
     - What phase is current and what's next
     - What was built/changed this session
     - Known gaps and open decisions
     - Any new context a future session needs
   - Add new memories if the session revealed user preferences, feedback, or reference info
   - This ensures the next Claude Code session has full context even before Azoth's
     own memory system (M3 episodes) is surfaced during SURVEY phase

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

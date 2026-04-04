---
description: "Unified eval + close + sync — run at the end of every session"
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
5. Architecture decisions (D1-D28) respected

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

## Part C: Sync Changes

1. Stage relevant files: `git add` (specific files, not `-A`)
2. Generate conventional-commit message summarizing the session
3. Commit
4. Report: commit SHA, files changed, test status

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

---
description: Capture a cross-session learning as a structured episode
---

# /remember $ARGUMENTS

Capture a durable lesson right now, outside of session closeout.

## Process

1. Parse the learning from `$ARGUMENTS`
2. Classify the episode type:
   - `success` — something worked well
   - `failure` — something went wrong
   - `decision` — a non-obvious choice was made
   - `pattern` — a recurring theme noticed
   - `observation` — something worth noting

3. Structure as episode:
   ```json
   {
     "id": "uuid",
     "timestamp": "ISO-8601",
     "session_id": "current-session",
     "type": "{classified type}",
     "goal": "current session goal",
     "summary": "{the learning from $ARGUMENTS}",
     "lessons": ["{specific, actionable lessons}"],
     "tags": ["{relevant tags}"]
   }
   ```

4. Append to `.azoth/memory/episodes.jsonl`

5. Auto-classify using Promotion Rubric:
   - Scope: generic or repo-local?
   - Reuse: useful elsewhere?
   - If pattern has been seen before (check existing episodes), flag for promotion

6. Report:
   ```
   Captured: {type} episode
   Summary: {1-line summary}
   Tags: {tags}
   Promotion signal: {none | reinforced (seen N times)}
   ```

## Rules

- Episodes are append-only — never edit previous entries
- Be specific, not generic
- Tag consistently for future retrieval

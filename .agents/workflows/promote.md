# /promote $ARGUMENTS

Review promotion candidates and apply the Promotion Rubric.

## Sources

1. Read `.azoth/memory/episodes.jsonl` — identify reinforced patterns
2. Read `.azoth/memory/patterns.yaml` — check existing patterns
3. Read `kernel/PROMOTION_RUBRIC.md` — apply the four questions

## Process

1. **Scan episodes** for promotion signals:
   - Episodes with `reinforcement_count >= 2`
   - Episodes tagged as `pattern` type
   - Episodes with matching tags across sessions
   - If `$ARGUMENTS` specifies a topic, filter to that

2. **For each candidate**, apply the Promotion Rubric:
   ```
   A. Scope Test: Is this repo-specific?
   B. Reuse Test: Would other projects benefit?
   C. Preference Test: Is this personal style?
   D. Maturity Test: Proven across 3+ sessions?
   ```

3. **Determine home**:
   - Generic Toolkit → propose for `skills/`, `agents/`, or `instructions/`
   - Repo-Local → stays in consumer project
   - Personal → user configuration
   - Not Yet → keep in M2, revisit later

4. **Present proposals** to human:
   ```
   ## Promotion Candidate
   
   - Pattern: {description}
   - Evidence: {episode ids and summaries}
   - Rubric path: {A/B/C/D → home}
   - Recommended action: {what to do}
   
   Approve? [yes / not-yet / reject]
   ```

4b. **Optional reinforcement_count update**:
   - If the human explicitly confirms that an existing lesson has recurred, require an exact episode id.
   - Use the active `session_id` from `.azoth/scope-gate.json`; do not invent or reuse a prior session id.
   - Run the exact-id helper only after that confirmation:
     ```bash
     python3 scripts/reinforcement_count.py ep-173 --session-id <active-session-id> --source promote
     ```
   - Alternatively, carry that same confirmed id into closeout via:
     ```bash
     python3 scripts/do_closeout.py --reinforce-episode ep-173
     ```
   - Never infer episode ids from tags or prose, and never increment the same prior episode more than once per session.

5. **If approved**: Write to `.azoth/memory/patterns.yaml` (M3 → M2)
   or implement in appropriate location (M2 → M1)

6. **Log** the promotion decision for auditability

## Rules

- Never auto-promote — every promotion requires explicit human approval
- Show evidence (source episodes) for every proposal
- "Not yet" is a valid outcome — don't force promotions

## Arguments

Topic filter: $ARGUMENTS

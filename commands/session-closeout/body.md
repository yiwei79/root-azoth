# /session-closeout

Close the current session by making repo-local W1/W2/W4 state authoritative first, then handling W3 as a supplemental mirror.

## Preconditions

- Start from a live approved scope in `.azoth/scope-gate.json`, unless `scripts/do_closeout.py` is resuming a saved closeout checkpoint for the same `session_id`.
- If the scope is governed or `target_layer: M1`, require the latest matching human final-delivery approval in `.azoth/final-delivery-approvals.jsonl` before the first W1 mutation.
- Do not infer reinforcement ids. Only use exact prior episode ids confirmed by the human.
- Do not process `.azoth/inbox/` during closeout. Surface queued files only.

## Structured Closeout Semantics

Before running the executor, assemble a structured payload that reflects the actual session outcome.

```json
{
  "schema_version": 1,
  "session_summary": {
    "summary": "What was accomplished, what remains open, and any human follow-up."
  },
  "episode": {
    "type": "success",
    "summary": "Same factual closeout summary used for W1.",
    "lessons": ["Durable lesson 1"],
    "tags": ["platform-parity"],
    "m2_candidate": false,
    "context": {
      "surface": "codex"
    }
  },
  "handoff": {
    "next_action": "Run `/next` to select the next scoped task.",
    "pending_decisions": ["Confirm whether the follow-on slice should be promoted."],
    "files_changed": ["commands/session-closeout/body.md"]
  },
  "w3": {
    "mode": "defer",
    "reason": "Codex keeps W3 supplemental unless host Claude memory sync is explicitly requested."
  }
}
```

Rules:

- `episode.summary` and `session_summary.summary` must be truthful, not boilerplate.
- `handoff.pending_decisions` should list only real unresolved decisions.
- In Codex, default `w3.mode` to `defer`. Use `w3.mode: attempt` only when you intentionally want to refresh `~/.claude/projects/<project-key>/memory/` during this run.

## Execute

1. Prepare the structured semantics payload and collect any exact `--reinforce-episode <ep-id>` values.
2. Run the executor from the repo root:

   ```bash
   python3 scripts/do_closeout.py --semantics-file /tmp/closeout-semantics.json
   ```

   Add `--reinforce-episode <ep-id>` for each confirmed recurrence. Add `--administrative-finalize` only for bookkeeping closeouts that must skip the W4 patch bump.

3. Treat `scripts/do_closeout.py` as the mechanical source of truth for W1–W4:

   - **W1** appends the closeout episode from the structured semantics payload.
   - **W1b** applies only the exact reinforcement ids passed on the command line.
   - **W2** refreshes repo-local handoff state, with `.azoth/session-state.md` as the repo-local W2 handoff artifact, releases the write claim, closes the scope gate, and updates planning completion where applicable.
   - **W3** is supplemental. In Codex it is deferred by default, non-fatal on failure, and must never override repo-local state or block W4.
   - **W4** bumps the patch version and clears `.azoth/session-orientation.txt` unless `--administrative-finalize` is set.

4. If W2, W3, or W4 fails after W1, rerun the same closeout with the same structured semantics. The executor resumes from the saved `next_step` checkpoint in `.azoth/run-ledger.local.yaml` and must not append W1 again.

5. After the executor finishes, report:

   - outcome and remaining risks,
   - whether W3 completed or was deferred,
   - queued inbox files in `.azoth/inbox/` without processing them,
   - next operator action.

## Rules

- Keep repo-local W1/W2/W4 authoritative. If W2 and W3 diverge, W2 wins.
- W3 deferral is not a failure. Silent skipping is not allowed; log the deferral reason, and W3 must never block W4.
- Retry runs must reuse the same structured semantics and reinforcement ids saved by the executor.
- Never re-enter full closeout from inside W1b. Use `python3 scripts/reinforcement_count.py` directly only when performing an in-flow reinforcement update outside this executor.

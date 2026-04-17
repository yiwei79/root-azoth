# /resume [<session_id>]

Restore a live approved scope or reopen a parked session with stage-aware pipeline continuity.

## Steps

1. **Resolve the target session**

   - If `<session_id>` is provided, resume that parked session.
   - If no argument is provided:
     - If `.azoth/scope-gate.json` is already active, continue that approved scope.
     - Else if `.azoth/session-state.md` is currently `state: parked`, resume that parked session.
   - If neither source yields a session, stop and explain that there is no resumable session.

2. **Check for scope conflicts**

   Read `.azoth/scope-gate.json`.

   - If another active scope exists for a **different** `session_id`, **STOP**.
   - Do **not** rewrite the active scope or silently retarget it.
   - Present the conflict options: `/park`, `/session-closeout`, or abort.

3. **Restore scope**

   Reopen the resolved session by running:

   ```bash
   python3 scripts/park_session.py --resume [--session-id <session_id>]
   ```

   Explicit resume intent is already the approval. Do **not** emit a second scope-approval card.

4. **Restore pipeline continuity**

   After the mechanical resume:

   - If the parked session has a saved run checkpoint, restore the selected pipeline and continue from the saved stage.
   - If the checkpoint is paused at a human gate, surface that saved gate directly.
   - If no run checkpoint exists, restore scope only and route to pipeline selection. `/auto` remains the default and must begin at Stage 0.

5. **Report the resumed state**

   Summarize:

   - resumed `session_id`
   - whether the session resumed as `scope-only` or `stage-aware`
   - restored pipeline name, if any
   - current stage id or saved human gate, if any
   - write-claim status and new scope TTL

## Compatibility Alias

- Legacy `/next resume [<session_id>]` remains a hidden compatibility alias.
- Treat it exactly like `/resume [<session_id>]`.
- Do not surface `/next resume` in new UX text or examples.

## Rules

- Explicit resume restores scope directly; it does **not** require a second scope-approval wall.
- If a saved pipeline checkpoint exists, resume from that checkpoint rather than restarting the workflow.
- If no checkpoint exists, restore scope only and require pipeline selection before implementation.
- If another active scope is live, stop instead of rewriting it.

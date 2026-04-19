# /worktree-sync

Protocol-aware git sync for parallel worktrees.

This command preserves Azoth's **single-integrator** parallel-session contract:

- producer sessions sync local work and hand off their branch
- a short-lived integrate run syncs and merges exactly one producer branch into the target branch
- if the target branch worktree is dirty or another integration pass is in flight, stop
- producer branches are refreshed against the local target branch before any sync commit is created

No governance evaluation during producer sync. No session close. Integrate runs remain
mechanical by default, except for a pre-approved governed reconciliation substep when
the selected queued handoff carries tracked shared-state approval metadata.

## Intent Detection

1. **Detect current branch role**
   - If on the active integration branch (for example `phase/v0.2.0-pN`), treat this as
     an **integrate run**.
   - Otherwise treat this as a **producer sync**.
   - If `HEAD` is detached, treat it as producer mode only; do not infer an integrate run from a detached checkout.

2. **Fail closed on unsafe integration**
   - If the current branch is the integration branch and the worktree is dirty with unrelated
     changes, STOP and tell the human the tree is not safe for integration.
   - Never silently merge a producer branch into a dirty integration worktree.
   - Never assume multiple producer branches may be merged in one pass unless the human asks.

## Producer Sync

Use when this worktree is on a feature, patch, or detached producer branch.

## Process

1. **Run backend preflight**:
   - Execute `python3 scripts/worktree_sync.py [--target-branch <branch>]`
   - Default target branch is the local active integration branch (normally `phase/v0.2.0-pN`)
   - If the producer worktree is detached, the backend must auto-materialize a local branch named `codex/wt-<id>-<shortsha>` (or reuse the same branch when it already points at the detached commit) before the normal refresh flow continues
   - If target drift exists, the backend must stash tracked + untracked changes, rebase onto the local target branch, and restore the stash before commit creation
   - If rebase or stash-restore conflicts occur, STOP immediately, resolve them, and rerun `/worktree-sync`

2. **Check git status**: Identify all changed and untracked files after the refresh

3. **Stage changes**: `git add` specific files (not `-A` — review what's being staged)

4. **Generate commit message**: Concise, conventional-commit style summarizing the diff

5. **Commit**: `git commit -m "{message}"`

6. **Push** (if tracking a remote): `git push`

7. **Register the handoff**:
   - Execute `python3 scripts/worktree_sync.py [--target-branch <branch>] --record-producer-handoff`
   - This must run only after the producer branch is clean at the intended handoff commit
   - The backend writes an append-only shared handoff record keyed by the git common dir
   - Each ready handoff carries a deterministic `handoff_id` derived from `{target_branch, producer_branch, queued_head_sha}`
   - Ready handoffs may also carry local-only cleanup metadata for obsolete producer branches that should be pruned after a successful integrate run
   - Capture that `handoff_id` in the report whenever possible so later integrate runs can target the exact queued handoff

8. **Report**:
   ```
   ## Sync Complete
   - Commit: {SHA}
   - Message: {message}
   - Files: {count} changed
   - Branch: {branch}
   - Remote: {pushed | local-only}
   - Role: producer
   - Handoff: queued
   - Next: if the queue is idle and the target branch is clean, offer `integrate now`
   ```

## Integrate Run

Use when this worktree is on the active integration branch, but treat the run as
short-lived and transactional rather than a permanently open session.

## Process

1. **Check git status**: confirm the target branch worktree is clean enough for an integrate run

2. **If dirty, STOP**:
   - Report the dirty paths
   - Explain that parallel integration is unsafe while the target worktree contains unrelated edits
   - Ask the human to finish or park the other integration work first

3. **Refresh integration branch**:
   - ensure the target branch is current before merging

4. **Resolve exactly one ready producer handoff**:
   - Execute `python3 scripts/worktree_sync.py [--target-branch <branch>] --next-ready-handoff`
   - If the human names a specific producer branch, pass `--producer-branch <branch>`
   - If the human already has the exact queue record, pass `--handoff-id <id>`
   - `--next-ready-handoff --json` surfaces the selected `handoff_id`
   - Branch-only selection is allowed only when it matches exactly one unresolved handoff; otherwise STOP and rerun with `--handoff-id`
   - STOP if no ready producer handoff is queued for the target branch

5. **Integrate exactly one producer branch**:
   - execute `python3 scripts/worktree_sync.py [--target-branch <branch>] --integrate-ready-handoff [--producer-branch <branch>] [--handoff-id <id>]`
   - use `--verify-command "<cmd>"` (repeatable) for the targeted regeneration/tests that must pass inside the sandbox worktree before promotion
   - the backend merges the selected ready handoff's queued `head_sha`, not the live producer branch tip, into a temporary integration worktree rooted at the target tip
   - after merge succeeds, the backend runs deterministic shared-state reconciliation in the sandbox before any verification commands
   - if the handoff carries tracked governed approval metadata, that reconciliation may invoke a pre-approved governed reconciliation substep for allowlisted backlog/roadmap rows
   - do not treat a permanently open integrator worktree as required state
   - if merge or verification fails, the target branch must remain unchanged and the sandbox path is reported for inspection
   - if reconciliation fails, the target branch must remain unchanged, the queue stays unresolved, and the sandbox path is reported for inspection
   - if promotion already succeeded but queue write-back failed, rerunning the same `handoff_id` repairs queue state without creating a second merge

6. **Run required post-merge regeneration/tests**:
   - pass those checks through `--verify-command` so they run inside the temporary integration worktree before promotion
   - if command/agent/skill/platform-adapter parity changed, include the required sync or deploy step in the verification set

7. **Mark the handoff integrated**:
   - successful sandbox integration updates the handoff queue automatically
   - `--mark-integrated [<producer_branch>] --handoff-id <id>` remains available for legacy/manual flows
   - branch-only `--mark-integrated <producer_branch>` is valid only when exactly one unresolved handoff matches that branch; otherwise STOP and use `--handoff-id`

8. **Promote the tested result**:
   - on successful verification, the backend fast-forwards the live target branch to the tested merge commit
   - push if needed
   - safe local cleanup is part of success: prune obsolete local producer branches, and remove an attached clean producer worktree first when required for branch deletion
   - if a producer worktree is dirty, a branch tip moved, or any cleanup target is otherwise unsafe, keep it and report the skipped cleanup reason instead of failing the already-successful integration
   - remote branch cleanup remains out of scope for this command
   - clean up the temporary integration workspace only on success
   - preserve the sandbox worktree on any failure so the operator can inspect or recover it

9. **Report**:
   ```
   ## Integrate Run Complete
   - Branch integrated: {producer_branch}
   - Handoff: {handoff_id}
   - Target branch: {target_branch}
   - Commit: {SHA}
   - Verification: {tests_or_checks}
   - Next step: other producer sessions must refresh from target before the next merge
   ```

## Rules

- This is a MECHANICAL command for producer syncs and ordinary integrate runs
- A queued handoff with tracked governed approval metadata may trigger a pre-approved governed reconciliation substep for allowlisted shared state; that does not authorize broader governance work
- Review staged files before committing — exclude secrets, large binaries
- If there are uncommitted kernel changes, WARN and ask human before staging
- Use specific file paths in `git add`, not `-A`
- Treat `phase/v0.2.0-pN` as the normal integration branch unless the human names a different target
- Preserve the **single integrator** contract from `docs/playbook/05-parallel-sessions.md`
- Producer sessions must not merge themselves into the target branch while another integrator pass is active
- Producer sessions must refresh against the local target branch **before** creating the sync commit
- Integrate runs must resolve and clear queue state by exact `handoff_id`
- Integrate runs merge **one** producer branch at a time, then stop so other sessions can refresh
- Single integrator means **one integration operation at a time**, not one permanently open session
- If integration is unsafe, fail closed and explain why instead of improvising around a dirty target tree

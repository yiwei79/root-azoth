---
description: Git checkpoint and sync — mechanical save point
---

# /worktree-sync

Mechanical git save point. No governance evaluation. No session close. Just sync.

## Process

1. **Check git status**: Identify all changed and untracked files

2. **Stage changes**: `git add` specific files (not `-A` — review what's being staged)

3. **Generate commit message**: Concise, conventional-commit style summarizing the diff

4. **Commit**: `git commit -m "{message}"`

5. **Push** (if tracking a remote): `git push`

6. **Report**:
   ```
   ## Sync Complete
   - Commit: {SHA}
   - Message: {message}
   - Files: {count} changed
   - Branch: {branch}
   - Remote: {pushed | local-only}
   ```

## Rules

- This is a MECHANICAL command — no evaluation, no episodes, no governance
- Review staged files before committing — exclude secrets, large binaries
- If there are uncommitted kernel changes, WARN and ask human before staging
- Use specific file paths in `git add`, not `-A`

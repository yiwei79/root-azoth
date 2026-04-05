---
mode: agent
description: Show the next priority task from the roadmap and suggest how to proceed
---

# /next — What Should I Work On?

Read the backlog and roadmap, produce a scope card, and write scope-gate.json on approval.

## Steps

1. **Load backlog**: Read `.azoth/backlog.yaml`
2. **Load roadmap context**: Read `.azoth/roadmap.yaml` — use `active_version` to find the
   active version entry under `versions:`. Use `goal` and `phase_scope` for phase context.
   (The legacy `current_phase` / `tasks:` fields are deprecated — do not read them.)
3. **Find candidate tasks**: From backlog `items`, collect all where:
   - `status` is not `complete`
   - `blocked_by` is null/absent, or every referenced id has `status: complete` in the backlog
   Sort by `priority` ascending (lower = higher priority).
4. **Select primary task**: Highest-priority unblocked item.
5. **Select secondary tasks** (optional, max 2):
   - Next unblocked items after primary
   - Must share the same M1/non-M1 class as primary:
     - Primary `target_layer: M1` → secondary must also be `target_layer: M1`
     - Primary any other layer → secondary must NOT be `target_layer: M1`
   - If no valid secondary exists, omit rather than violate the rule
6. **Validate scope card**: If the selection would mix M1 and non-M1 items, reject and
   explain. Suggest running primary-only instead.
7. **Surface decision context**: For the primary task, look up `decision_ref` entries in
   `docs/DECISIONS_INDEX.md`. Check `.azoth/memory/episodes.jsonl` for related episodes
   (match on task id or decision refs).
8. **Output scope card** (format below).
9. **Wait for human signal**: Do NOT start work. If human types `approved`, proceed to step 10.
10. **Write scope-gate.json**: Write `.azoth/scope-gate.json` with:

    ```json
    {
      "approved": true,
      "expires_at": "<now + 2 hours, ISO 8601 with +00:00 offset>",
      "goal": "<primary task id>: <primary task title>",
      "session_id": "<current date YYYY-MM-DD>-<primary task id lowercased>",
      "approved_by": "human"
    }
    ```

    Confirm: "scope-gate.json written — Write/Edit unblocked for this session."

## Scope Card Format

```markdown
## Scope Card — {YYYY-MM-DD}

**Phase:** v{active_version} — {version goal}

**Primary:** [{id}] {title} ({target_layer}, {delivery_pipeline})
**Secondary:** [{id}] {title} ({target_layer})        ← omit if none
**Secondary:** [{id}] {title} ({target_layer})        ← omit if none

**Why:** {decision_ref} — {one-line decision summary from DECISIONS_INDEX.md}
**Episode context:** ep-{NNN}: {one-line summary}    ← omit if no relevant episode

---
Type `approved` to write scope-gate.json (valid 2h) and unblock Write/Edit.
Type `skip` to skip primary and show next candidate.
```

## Rules

- **Never auto-start work** — output the scope card and wait for `approved`
- **Never mix M1 and non-M1** in a single scope card (D51: M1 requires dedicated session)
- **Skip completed items** — if all backlog items are complete, congratulate and show the
  next version entry from `roadmap.yaml versions:` as a preview
- **If backlog.yaml is missing**, suggest running `/bootstrap` to initialize
- **Scope card validator**: if a mixed card would result, show the conflict and propose
  the primary-only card instead
- **On `skip`**: remove primary from consideration for this run and repeat from step 4

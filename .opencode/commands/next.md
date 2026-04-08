---
description: Show the next priority task from the roadmap and suggest how to proceed
---

# /next — What Should I Work On?

Read the backlog and roadmap, produce a scope card, and write scope-gate.json on approval.

## Steps

1. **Load backlog**: Read `.azoth/backlog.yaml`
2. **Load roadmap context**: Read `.azoth/roadmap.yaml` — use `active_version` to find the
   active version entry under `versions:`. Use `goal` and `phase_scope` for phase context.
   Also read `current_phase` and `current_phase_title` for display in the scope card header.
   (The legacy `tasks:` field is deprecated — do not use it for candidate task sourcing.)
3. **Find candidate tasks**: From backlog `items`, collect all where:
   - `status` is not `complete` and not `deferred` (deferred items target a future `target_version`)
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
8b. **Architecture proposal footer** (optional, informational only):

    After composing the main scope card body for step 8, decide whether to append a single
    extra line **after** that body and **before** the `---` separator and the “Type `approved`…”
    line. The footer is **read-only** and **informational only** — it does **not** govern scope,
    backlog, or build authority.

    1. If `.azoth/scope-gate.json` is missing, omit the footer (end 8b).
    2. Parse it as JSON. Require `approved: true` (boolean). Require `session_id` to be a
       non-empty string; otherwise omit the footer.
    3. Parse `expires_at` as an ISO-8601 instant and compare to **current UTC**; require it
       to be **strictly in the future** (unexpired). If missing, invalid, or expired, omit the
       footer.
    4. If `.azoth/proposals/` is missing or is not a directory, **skip** the rest of 8b (omit
       footer).
    5. Collect only `*.yaml` files **directly** in `.azoth/proposals/` (no subdirectories).
    6. For each file: read the text and parse with **safe** YAML (`yaml.safe_load` in Python,
       or an equivalent that does not allow arbitrary object construction / unsafe tags).
    7. For each top-level mapping, count it if `session_id` equals the gate’s `session_id`
       **and** `status` is `draft` or `submitted`.
    8. If the count is **exactly one**, append a blank line and:

       `**Architecture proposal (read-only, informational only):** \`{backlog_id}\` — {title} — status {status}`

       (values from the matching YAML).

    9. If the count is **zero** or **more than one**, omit the footer entirely.

9. **Wait for human signal**: Do NOT start work. If human types `approved`, proceed to step 10.
10. **Write scope-gate.json**: Write `.azoth/scope-gate.json` with:

    ```json
    {
      "approved": true,
      "expires_at": "<now + 2 hours, ISO 8601 with +00:00 offset>",
      "goal": "<primary task id>: <primary task title>",
      "session_id": "<current date YYYY-MM-DD>-<primary task id lowercased>",
      "approved_by": "human",
      "backlog_id": "<primary task id>",
      "delivery_pipeline": "<governed | standard — from backlog primary delivery_pipeline>",
      "target_layer": "<M1 | infrastructure | … — from backlog primary target_layer>"
    }
    ```

    **Governed delivery (mechanical):** If the primary item has `delivery_pipeline: governed` **or**
    `target_layer: M1`, the PreToolUse hook **blocks Write/Edit** until
    `.azoth/pipeline-gate.json` exists (see `/deliver-full`, `/auto`, or `/deliver` **Stage 0**).
    After scope approval, remind the human: for governed work, invoke the appropriate
    pipeline command first; the orchestrator must run Stage 0 before other writes.

    Confirm: "scope-gate.json written — Read/Plan unblocked; governed scopes still require pipeline-gate.json after Stage 0 of a delivery pipeline."

## Scope Card Format

```markdown
## Scope Card — {YYYY-MM-DD}

**Phase:** P{current_phase:02d} — {current_phase_title}  ·  v{active_version}

**Primary:** [{id}] {title} ({target_layer}, {delivery_pipeline})
**Secondary:** [{id}] {title} ({target_layer})        ← omit if none
**Secondary:** [{id}] {title} ({target_layer})        ← omit if none

**Why:** {decision_ref} — {one-line decision summary from DECISIONS_INDEX.md}
**Episode context:** ep-{NNN}: {one-line summary}    ← omit if no relevant episode

**Architecture proposal (read-only, informational only):** `{backlog_id}` — {title} — status {status}    ← only if step 8b matches exactly one file

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

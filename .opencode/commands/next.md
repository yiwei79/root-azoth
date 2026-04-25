---
description: Show the next priority task from the roadmap and suggest how to proceed
agent: orchestrator
---

# /next — What Should I Work On?

Read the backlog and roadmap, produce a scope card, and write scope-gate.json on approval.

## Steps

0. **Refuse when another scope is still live**: Read `.azoth/scope-gate.json`.
    - If it is approved, unexpired, and already names an active `session_id`, **STOP**.
    - Do **not** silently overwrite the active scope by selecting new work.
    - If another active scope exists, route to `/resume`, `/park`, or `/session-closeout` instead.

0b. **Cross-check run-ledger for in-flight sessions**: Read `.azoth/run-ledger.local.yaml`.
    - If the file is absent or unreadable, skip this step (treat as no in-flight sessions).
    - Parse the `sessions` list. Collect entries where `status` is `active` or `parked`
      and `backlog_id` is a non-empty string.
    - Build an **excluded-ids set** from those `backlog_id` values.
    - Any backlog item whose `id` appears in this set must **not** be surfaced as a candidate
      in Step 3, even if its `backlog.yaml` status has not yet been flipped to `active`
      (lag window between write-claim and write-back).
    - If the excluded-ids set is non-empty, note it in the scope card footer:
      e.g. "N item(s) excluded — claimed by another session".

1. **Load backlog**: Read `.azoth/backlog.yaml`
2. **Load roadmap context**: Read `.azoth/roadmap.yaml` — use `active_version` to find the
   active version entry under `versions:`. Use `goal` and `phase_scope` for phase context.
   Also read `current_phase` and `current_phase_title` for display in the scope card header.
   (The legacy `tasks:` field is deprecated — do not use it for candidate task sourcing.)
3. **Find candidate tasks**: From backlog `items`, collect all where:
   - `status` is not `complete`, not `deferred`, and not `active`
     (`active` items are already claimed by a running session — skip them; `deferred` items target a future `target_version`)
   - `blocked_by` is null/absent, or every referenced id has `status: complete` in the backlog
   Sort by `priority` ascending (lower = higher priority).
3b. **Planning-bank fallback when no candidate tasks exist**: If Step 3 finds no
   claimable backlog candidates, read tracked planning banks before falling back to
   the next roadmap-version preview.
   - Read only `.azoth/design-banks/*.yaml` and `.azoth/initiative-banks/*.yaml`.
   - Do **not** read `.azoth/proposals/` as a candidate source. Proposal paths may be
     shown only when a tracked bank cites them as provenance.
   - Summarize up to three active planning seeds, preferring banks with
     `readiness.human_decision`, `readiness.candidate_first_slice`,
     `readiness.hydration_recommendation`, `routing_candidates`, or open questions.
   - Treat these as **read-only discovery seeds**, not scope authority. Do not write
     `scope-gate.json`, claim a run, or mutate backlog/roadmap/spec state from a
     bank seed alone.
   - Route the operator to `/plan`, research/refinement, proposal refinement, or an
     explicit hydration/scaffold step before any future `/next` scope approval.
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

10b. **Acquire write claim**: After writing `scope-gate.json`, acquire the write claim so
    competing sessions are mechanically blocked. Call `acquire_write_claim` from `run_ledger.py`
    or run:
    ```
    python3 scripts/run_ledger.py claim <session_id> <expires_at>
    ```
    This registers the write claim in `.azoth/run-ledger.local.yaml`. At session closeout,
    release the claim via `release_write_claim` or:
    ```
    python3 scripts/run_ledger.py release-claim <session_id>
    ```
    If a competing session holds an unexpired claim, the PreToolUse hook will deny
    Write/Edit until the claim is released or expires (and `resolve_stale_claims` clears it).

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

    **Pipeline selection after scope approval (all scopes):** Writing `.azoth/scope-gate.json`
    declares intent; it does **not** authorize direct implementation. After scope approval,
    the next step is delivery pipeline selection. If the human did **not** explicitly choose a
    pipeline, `/auto` is the default (D23) and must run **Stage 0 goal clarification**
    before implementation begins.

    **Governed delivery (mechanical):** If the primary item has `delivery_pipeline: governed` **or**
    `target_layer: M1`, the PreToolUse hook **blocks Write/Edit** until
    `.azoth/pipeline-gate.json` exists (see `/deliver-full`, `/auto`, or `/deliver` **Stage 0**).
    For standard scopes, Stage 0 / pipeline selection still applies even though
    `pipeline-gate.json` is not required.

    Confirm: "scope-gate.json written — intent declared; select a delivery pipeline next. If none was specified, use /auto and run Stage 0 before implementation. Governed scopes still require pipeline-gate.json after Stage 0 of the chosen delivery pipeline."

10c. **Mark backlog item as active**: After the write claim is successfully acquired,
    update `.azoth/backlog.yaml`: find the item whose `id` matches `backlog_id` from
    scope-gate.json and set its `status` field to `active`.

    - **How**: Targeted in-place YAML edit — locate the item by `id:` key, change its
      `status:` line to `status: active`. Do not alter any other field or reformat the file.
    - **If item not found**: log a warning in the confirmation message
      ("Warning: backlog item `<id>` not found in backlog.yaml — status not updated") and
      continue; do not abort scope approval.
    - **If item is already `active`**: no-op — note "already active" in the confirmation
      message and continue.
    - **If write claim was denied** (competing session holds an unexpired claim): do not
      update backlog status; surface the denial to the human and stop.
    - **Recovery (abandoned scope):** If a session ends without `/session-closeout` (crash
      or manual abort), the item remains `active` in `backlog.yaml`. Clear it by running
      `/session-closeout` (even with no deliverables) or by manually setting `status` back
      to the prior value and running `python3 scripts/run_ledger.py release-claim <session_id>`.

## Scope Card Format

```markdown
## Scope Card — {YYYY-MM-DD}

**Phase:** P{current_phase:02d} — {current_phase_title}  ·  v{active_version}

**Primary:** [{id}] {title} ({target_layer}, {delivery_pipeline})
**Secondary:** [{id}] {title} ({target_layer})        ← omit if none
**Secondary:** [{id}] {title} ({target_layer})        ← omit if none

**Why:** {decision_ref} — {one-line decision summary from DECISIONS_INDEX.md}
**Episode context:** ep-{NNN}: {one-line summary}    ← omit if no relevant episode
**Excluded:** {N} item(s) skipped — claimed by another session ({id}, …)    ← omit if excluded-ids set is empty (Step 0b)
**Planning-bank seeds:** {bank_id or initiative_id}: {readiness/human decision/candidate/readiness gate}    ← only when Step 3 has no candidate tasks and Step 3b finds tracked banks

**Architecture proposal (read-only, informational only):** `{backlog_id}` — {title} — status {status}    ← only if step 8b matches exactly one file

---
Type `approved` to write scope-gate.json (valid 2h) and unblock Write/Edit.
Type `skip` to skip primary and show next candidate.
```

## Rules

- **Never auto-start work** — output the scope card and wait for `approved`
- **`/next` is for new work** — do not use it to reopen parked sessions or continue an active scope
- **`active` means claimed** — a backlog item with `status: active` is owned by a running
  session; `/next` skips it. The status is set by Step 10c on scope approval and cleared by
  `/session-closeout` when the session ends
- **If a live scope already exists**, stop and route to `/resume`, `/park`, or `/session-closeout`
- **Never mix M1 and non-M1** in a single scope card (D51: M1 requires dedicated session)
- **Skip completed items** — if all backlog items are complete, congratulate, surface any
  tracked planning-bank seeds as read-only discovery context, then show the next version
  entry from `roadmap.yaml versions:` as a preview
- **Planning banks are seeds, not scopes** — design and initiative banks can make
  research/refinement or hydration candidates discoverable, but they do not authorize
  scope-gate writes until a concrete backlog/roadmap/spec boundary is approved
- **If backlog.yaml is missing**, suggest running `/bootstrap` to initialize
- **Scope card validator**: if a mixed card would result, show the conflict and propose
  the primary-only card instead
- **On `skip`**: remove primary from consideration for this run and repeat from step 4

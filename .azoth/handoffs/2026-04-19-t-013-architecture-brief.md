# T-013 Architecture Brief

## Goal

Define a deterministic reconciliation pass that runs inside the temporary sandbox
worktree after `git merge` succeeds and before verification/promotion, so shared
Azoth state is resolved by semantic policy instead of raw line merges.

## Scope

This slice covers reconciliation policy for shared Azoth state after the real
integrate-run execution lane exists.

Focus areas:
- governed contract for reconciliation inside the integrate-run path
- explicit human design-gate evidence for governed replay paths
- backlog/roadmap identity handling under explicit allowlists
- final-delivery approval event-log preservation
- episode collision guards
- derived counter recomputation

Non-goals:
- lifecycle/closeout UX redesign (`T-014`)
- broader multi-writer claim infrastructure
- external evidence refresh (`BL-065`)
- auto-resolving ambiguous roadmap/backlog identity conflicts
- unapproved reconciliation of arbitrary roadmap/backlog rows

## Target Model

Introduce a dedicated reconciliation helper, likely under `scripts/`, that runs
against the sandbox repo root and the selected handoff metadata before verification.
This helper operates in two explicit modes:

1. **Mechanical reconcile mode**
   - safe for transient and append-only shared state
   - usable from `/worktree-sync` without widening governance semantics

2. **Governed shared-state reconcile mode**
   - required for backlog/roadmap reconciliation
   - only active when the handoff record carries explicit governed metadata produced
     by an approved scope/pipeline
   - `/worktree-sync` command text must be updated to state that integrate runs may
     invoke this pre-approved governed reconciliation substep when such metadata exists
   - reviewer replays and planner handoffs must receive a recorded human design-approval
     artifact, not only a chat-only acknowledgement

Classify shared files into policy buckets:

1. `keep-target`
   - `.azoth/scope-gate.json`
   - `.azoth/pipeline-gate.json`
   - `.azoth/run-ledger.local.yaml`
   - `.azoth/session-state.md`
   - `.azoth/bootloader-state.md`

2. `append-with-dedupe`
   - `.azoth/memory/episodes.jsonl`
   - `.azoth/final-delivery-approvals.jsonl`

3. `identity-merge-or-block`
   - `.azoth/backlog.yaml`
   - `.azoth/roadmap.yaml`

4. `recompute-derived`
   - `azoth.yaml` counters and other manifest-style derived totals

## Human Design-Gate Approval Evidence

The architect revision loop must produce a repo-local approval artifact so downstream
replays can prove the required human design gate was actually consumed. For this session,
the replay artifact is:

- `.azoth/handoffs/2026-04-19-t-013-design-approval-loop-3.yaml`

General rule:

- every governed architect revision that is replayed into `deliver_full_s3` must carry a
  design-approval record with `session_id`, `stage_id`, `actor_type: human`, `approved: true`,
  `approved_at`, and the applicable loop metadata
- this repo-local design-gate artifact proves pipeline replay approval only; it is not the
  artifact referenced by integrate-run queue metadata
- reviewer and planner inputs must include that approval artifact path alongside the
  revised architect stage summary

## Proposed Rules

### Keep-target

Treat transient session/control-plane files as target-branch authority during an
integrate pass. Producer-side values are not merged into the live target state.

### Append-with-dedupe

- `episodes.jsonl`: union by episode `id`; if the same `id` has different payloads,
  fail closed.
- `final-delivery-approvals.jsonl`: treat as an append-only event log. Preserve every
  distinct approval event, including repeated approvals for the same session. Only
  suppress exact-record duplicates (or an explicit immutable event id, if the log gains
  one later). Never dedupe by business fields such as `session_id`, `gate`, `decision`,
  or `approved` alone.

### Identity-merge-or-block

Backlog and roadmap reconciliation are governed surfaces. They are only eligible for
reconciliation when the selected producer handoff carries explicit allowlist metadata plus
verifiable approval provenance.

Tracked governed approval capsule:

- governed replay evidence must live in a tracked file committed on the queued producer
  branch, not in the repo-local stage handoff directory
- required location: `.azoth/governed-state-approvals/<session_id>-<backlog_id>.yaml`
- queue-record `approval_evidence_path` and `approval_evidence_sha256` refer to this
  tracked governed approval capsule, never to `.azoth/handoffs/*.yaml`
- the governed approval capsule must include:
  - `schema_version: 1`
  - `artifact_kind: governed-shared-state-approval`
  - `session_id`
  - `backlog_id`
  - `goal`
  - `pipeline`
  - `approved_stage_id`
  - `actor_type: human`
  - `decision: approved`
  - `approved_at`
  - `allowlist_unit`
  - `whole_initiative_approved`
  - `shared_state_allowlist.backlog_ids`
  - `shared_state_allowlist.roadmap_task_refs`
  - optional `shared_state_allowlist.initiative_refs`
  - `scope_fingerprint`

Required queue-record provenance fields:

- `scope_session_id`
- `scope_backlog_id`
- `scope_goal`
- `scope_fingerprint`
- `approval_evidence_path`
- `approval_evidence_sha256`
- `allowlist_unit`
- `shared_state_allowlist.backlog_ids`
- `shared_state_allowlist.roadmap_task_refs`

Optional only for explicitly whole-initiative approvals:

- `shared_state_allowlist.initiative_refs`
- `whole_initiative_approved: true`

Default rule:

- default to task/row-level scope only
- initiative-wide scope is forbidden unless the tracked governed approval capsule
  explicitly states that the whole initiative was approved for reconciliation

Canonical `scope_fingerprint` contract:

- the integrator must recompute `scope_fingerprint` from the governed approval capsule,
  not from queue metadata supplied by the producer handoff alone
- the hash input is the UTF-8 encoding of canonical JSON with sorted keys, no extra
  whitespace, and list values sorted ascending after de-duplication for this exact object:

```json
{
  "session_id": "<session_id>",
  "backlog_id": "<backlog_id>",
  "goal": "<goal>",
  "allowlist_unit": "<allowlist_unit>",
  "whole_initiative_approved": true,
  "shared_state_allowlist": {
    "backlog_ids": ["<sorted unique backlog ids>"],
    "roadmap_task_refs": ["<sorted unique roadmap task refs>"],
    "initiative_refs": ["<sorted unique initiative refs>"]
  }
}
```

- `scope_fingerprint` is `sha256` of that canonical JSON payload
- any queue record whose mirrored scope fields do not exactly match the capsule-derived
  payload must fail closed

Verifier source:

- the integrator reads the tracked governed approval capsule at `approval_evidence_path`
  from the queued producer commit
- hashes it and matches `approval_evidence_sha256`
- validates that the capsule's `session_id`, `backlog_id`, `goal`, `pipeline`,
  `approved_stage_id`, and scope unit match the governed queue record
- recomputes `scope_fingerprint` from the exact canonical payload above and matches it
  against both the capsule value and the queue record value
- rejects queue metadata that widens the allowlist beyond the capsule, including any
  extra backlog rows, roadmap task refs, or initiative refs

If any provenance field is absent, mismatched, or wider than the approved scope, the
integrator must fail closed and skip backlog/roadmap reconciliation entirely.

- `backlog.yaml`: merge only rows whose ids are in the explicit task-level allowlist;
  allow monotonic status progression for those approved rows; block on divergent
  identity-bearing fields such as title, target layer, initiative reference, or
  delivery pipeline.
- `roadmap.yaml`: reconcile only the explicitly allowed initiative/task refs; preserve
  target-branch authority for global selectors like `active_version`, `current_phase`,
  and milestone-wide summary state unless both sides already agree; block on any extra or
  ambiguous identity drift outside the allowlist.

### Recompute-derived

- `azoth.yaml`: do not text-merge counters from both sides.
- Recompute `decisions`, `memory.episodes`, and similar derived counts from canonical
  source files after reconciliation completes.
- Keep recomputation downstream of successful reconcile only; if reconciliation fails,
  the live target branch and its manifest stay untouched.

## Execution Flow

1. Sandbox merge succeeds in `scripts/worktree_sync.py`.
2. Reconciliation helper runs over the shared-state surface set.
3. Mechanical reconcile mode always applies to transient, append-only, and derived files.
4. Governed shared-state reconcile mode applies to backlog/roadmap only when the selected
   handoff carries explicit allowlist metadata plus approval provenance from an approved
   governed session.
5. If reconciliation fails, stop, preserve the sandbox, keep the queue unresolved, and
   leave the live target branch unchanged.
6. If reconciliation succeeds, run verification commands in the reconciled sandbox.
7. Promote the tested merge.

## Risks

- Ambiguous backlog/roadmap identity collisions could silently corrupt the control plane
  if the helper guesses instead of blocking.
- A metadata allowlist that is too broad or missing entirely would let unrelated governance
  rows piggyback through an otherwise safe integration.
- Recomputing derived counters must use canonical sources consistently or it will create
  new drift.
- This slice touches shared M1 state and must stay bounded; lifecycle and UX concerns
  should remain deferred to `T-014`.

## Acceptance Shape

- Deterministic unit tests for each policy bucket
- Queue-record tests proving governed handoffs can carry allowlist metadata and that
  missing or extra planning-surface rows fail closed
- Queue-record tests proving approval provenance is verified from a tracked approval artifact
  and that mismatched hashes/session ids/backlog ids fail closed
- Queue-record tests proving `.azoth/handoffs/*.yaml` cannot satisfy `approval_evidence_path`
  and that only tracked governed approval capsules are replayable from the queued producer commit
- Queue-record tests proving `scope_fingerprint` is recomputed from the canonical capsule
  payload and that widened queue metadata is rejected even when a producer supplies its own hash
- Command/contract updates proving `/worktree-sync` explicitly describes the governed
  reconciliation substep instead of claiming all integrate behavior is non-governance
- Integration tests proving:
  - append-only files union correctly without collapsing distinct approval events
  - target-owned transient files are preserved
  - ambiguous backlog/roadmap identity collisions fail closed
  - extra non-allowlisted backlog/roadmap rows fail closed
  - initiative-wide allowlists are rejected unless a whole-initiative approval artifact is present
  - derived manifest counters are recomputed instead of line-merged
  - reconciliation failure leaves the live target branch unchanged
  - reconciliation failure leaves the handoff queue unresolved
  - rerunning the same `handoff_id` still preserves the existing T-012 repair/rerun path

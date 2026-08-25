# Gate Protocol — Mechanical Enforcement Steps

This document is the canonical reference for session-gate, scope-gate, and pipeline-gate
enforcement in `/auto`, `/deliver`, and `/deliver-full`. All three commands reference this file.

## Session-gate layer

`.azoth/session-gate.json` is the lightweight session envelope for exploratory chat,
research, planning, and other no-scope work. It is **not** delivery authorization.

Required fields:

- `session_id`
- `goal`
- `session_mode: exploratory | delivery`
- `opened_at`
- `updated_at`
- `status: active | closed`
- `approved_by: system | human`

When an active exploratory session exists without an approved scope gate, Write/Edit is
still restricted. The only allowed lifecycle writes are:

- `.azoth/session-gate.json`
- `.azoth/run-ledger.local.yaml`
- `.azoth/session-state.md`
- `.azoth/bootloader-state.md`
- `.azoth/memory/episodes.jsonl`

Any other write must stop and escalate into `/auto` so `.azoth/scope-gate.json` is opened.

## Scope-gate check

Before any pipeline stage begins work, the orchestrator reads `.azoth/scope-gate.json`
and verifies:

- `approved: true`
- `expires_at` is in the future
- `session_id` matches the active session

If the scope-gate is missing, expired, or unapproved, **stop** and ask the human to
run `/next` or `/auto` to declare delivery intent and receive an approved scope card.

### Scope-gate exemptions

The scope-gate layer may explicitly allow a write before the repo-wide gate stack continues.
These are **administrative/bootstrap** writes, not normal implementation writes:

- writing or editing `.azoth/scope-gate.json` itself (scope bootstrap)
- writing `.azoth/pipeline-gate.json` itself (pipeline bootstrap for governed work)
- writing bounded exploratory lifecycle files while `.azoth/session-gate.json` is active

When a write is classified as one of these exemptions, downstream alignment, write-claim,
and entropy gates must short-circuit and allow it.

## Pipeline-gate write (governed work only)

**Before the first Write/Edit** to the repo in this run: `Read` `.azoth/scope-gate.json`.
If any governed signal is present, `Write` `.azoth/pipeline-gate.json` so the
PreToolUse hook allows subsequent edits:

```json
{
  "session_id": "<must match scope-gate.session_id>",
  "pipeline": "deliver-full | deliver | auto",
  "approved": true,
  "expires_at": "<same as scope-gate.expires_at>",
  "opened_at": "<ISO 8601 now, +00:00>"
}
```

Set `"pipeline"` to the delivery command you will actually run (`"auto"` | `"deliver"` |
`"deliver-full"`). Do **not** assume `"auto"` if the handoff is `/deliver` or
`/deliver-full`.

Treat the scope as governed when **any** of the following is true:

- `governance_mode == governed`
- legacy `delivery_pipeline == governed`
- fused `/auto` scope-gates record the chosen pipeline as `delivery_pipeline == deliver-full`
- `target_layer == M1`

If none of those governed signals are present, **omit** this file unless it
already exists from a prior step. This bridge wording matters because `/next`
still emits legacy governed/standard scope cards, while fused `/auto`
declarations may record the chosen pipeline name directly.

If `pipeline-gate.json` already exists with the same `session_id`, update `opened_at`
only.

Validity requirements for a live `pipeline-gate.json`:

- `pipeline` or `pipeline_command` is present and names a real delivery command:
  `auto`, `dynamic-full-auto`, `deliver`, or `deliver-full`
- `opened_at` is parseable ISO-8601
- `expires_at` is parseable ISO-8601 and still in the future
- `opened_at <= expires_at`
- `session_id` matches `scope-gate.json.session_id`
- `expires_at` matches `scope-gate.json.expires_at`
- if the scope already records an exact selected pipeline command, the pipeline-gate command must match it

## Governed approval consumption

For governed runs, human approval is not complete when the gate files validate. The
same run must consume that approval into execution state through
`scripts/run_ledger.py` by advancing the paused human-gate checkpoint to the next
executable stage.

Required paused checkpoint shape before approval consumption:

- `status: paused`
- `pause_reason: human-gate`
- `active_stage_id` names the gate-owning stage that just completed
- `pending_stage_ids[0]` names the next executable downstream stage

Required same-run mutation after approval consumption:

- append the prior `active_stage_id` to `stages_completed`
- promote `pending_stage_ids[0]` into `active_stage_id`
- remove the promoted stage from `pending_stage_ids`
- clear `pause_reason`
- set `status: active`
- rewrite `next_action` to the promoted executable stage

Updating only narration or a status/declaration card is insufficient. If the next
stage cannot be promoted mechanically, fail closed and stop.

Reviewer/evaluator-driven revise-and-continue loops now use the same fail-closed
runtime discipline:

- require lineage proof from the active run entry (`stages_completed[-1]`,
  `active_stage_id`, `pending_stage_ids`)
- rewrite the queue as `[revision_stage, gate_stage, *downstream]`
- keep the current review stage as the gate-owning `active_stage_id`
- set `status: paused` and `pause_reason: human-gate`
- require the same human approval consumption path to promote the replay target

If lineage proof is missing, ambiguous, or already rewritten, fail closed and stop.

## Ledger-backed staged delegation evidence

For `/auto`, `dynamic-full-auto`, `/deliver`, and `/deliver-full`, protected downstream
progress also requires paired run-ledger evidence for every delegated stage. The
orchestrator records:

- `stage_spawns[]` when a subagent is spawned
- `stage_summaries[]` when that subagent returns a typed stage summary

Both entries bind `run_id`, `stage_id`, `subagent_type`, `trigger`, `role_hint`, and
`dependency_summary_refs`. `stage_spawns[]` carries `spawned_at`; `stage_summaries[]`
carries `summary_recorded_at`, `summary_status`, and `summary_disposition`.

Before spawning a protected downstream stage, run:

```bash
python3 scripts/run_ledger.py require-stage-evidence \
  --run-id <run_id> \
  --stage-id <upstream_stage_id>
```

The helper uses the latest matching spawn and summary evidence. Missing records,
metadata mismatch, blocked/needs-input status, or request-changes style dispositions
fail closed. A status card or declaration does not substitute for ledger evidence.

## Governed closeout approval evidence

Before `scripts/do_closeout.py` performs any governed W1–W4 mutation, it must read
`.azoth/final-delivery-approvals.jsonl` and find the **latest** matching record for the
active `scope-gate.json.session_id` with:

```json
{
  "session_id": "<must match scope-gate.session_id>",
  "gate": "final-delivery",
  "actor_type": "human",
  "approved": true,
  "decision": "approved"
}
```

`approved: true` is mandatory; `decision: "approved"` is the canonical human-readable
mirror field. The file is **consume-only** during closeout: read it, validate it, and
leave it unchanged. Missing files, malformed JSONL, missing matching records, agent-only
records, or a later denial for the same session must all fail closed before W1.

After approval evidence passes and still before W1, closeout checks matching live/paused
governed runs for unresolved stage evidence. It blocks only runs for the same
`scope-gate.json.session_id`; unrelated historical, complete, failed, or non-governed runs
do not block closeout.

## Why this gate exists

This stage wires **Claude Code's delivery pipeline** to mechanical enforcement: governed
work cannot bypass `/deliver-full` (or `/auto` / `/deliver`) and inline-only
implementation. The PreToolUse hook in `.claude/settings.json` reads both gate files
before allowing any Write/Edit tool call. Without a valid pipeline-gate, writes to
governed artifacts are blocked at the tool layer — not just by convention.

## Cursor parity

Cursor does not run PreToolUse hooks. Simulate the same check manually before every
Write/Edit: read both gate files, confirm `approved: true` and unexpired `expires_at`,
and confirm `session_id` consistency. See `.cursor/rules/claude-code-parity.mdc` for
the behavioral parity rules.

Cross-platform validation: run `python3 scripts/check_gates.py --session-id <session_id>`
(optionally `--require-pipeline-gate` to force the check even for non-governed sessions).
This script validates both gate files, derives governed pipeline-gate requirements from the
active scope, and cross-checks session_id consistency, timestamp freshness, and
pipeline-command validity. It imports from `scripts/scope_gate_check.py` and extends it
with pipeline-gate and field-completeness checks.

## Fused Declaration flow (`/auto`)

When `/auto` is invoked, the orchestrator presents a **fused Declaration** combining
scope card and pipeline composition in a single approval. On approval, the orchestrator
writes `.azoth/scope-gate.json` with 7 core required fields
(`session_id`, `goal`, `approved`, `approved_by`, `expires_at`, `backlog_id`,
`target_layer`) plus one mode field (`delivery_pipeline` during the bridge, or
`governance_mode` on the normalized path), and optionally `.azoth/pipeline-gate.json`
(for governed work). When `/auto` uses `delivery_pipeline`, that field may carry
the chosen pipeline name (`auto | deliver | deliver-full`) instead of the legacy
`governed | standard` scope classification. This replaces the separate
`/next` → `/auto` two-step flow.

The fused Declaration eliminates one human gate (scope approval) from the `/auto` happy
path without reducing governance surface: all mandatory gates (kernel, governance, M2→M1,
final delivery) remain unconditionally enforced.

If a matching exploratory `.azoth/session-gate.json` is already active for the same goal,
the delivery declaration must reuse that `session_id` when writing `.azoth/scope-gate.json`.
Escalation into delivery does not mint a second session identity.

After a governed human gate is approved, `/auto`, `/deliver`, and `/deliver-full`
must advance to the next executable stage in the same run via the shared
`scripts/run_ledger.py` approval-consumption helper. Emitting only another
declaration or status card after approval counts as failure.

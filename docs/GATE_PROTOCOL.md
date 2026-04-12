# Gate Protocol — Mechanical Enforcement Steps

This document is the canonical reference for scope-gate and pipeline-gate enforcement
in `/auto`, `/deliver`, and `/deliver-full`. All three commands reference this file.

## Scope-gate check

Before any pipeline stage begins work, the orchestrator reads `.azoth/scope-gate.json`
and verifies:

- `approved: true`
- `expires_at` is in the future
- `session_id` matches the active session

If the scope-gate is missing, expired, or unapproved, **stop** and ask the human to
run `/next` to declare intent and receive an approved scope card.

## Pipeline-gate write (governed work only)

**Before the first Write/Edit** to the repo in this run: `Read` `.azoth/scope-gate.json`.
If `delivery_pipeline` is `governed` **or** `target_layer` is `M1`, `Write`
`.azoth/pipeline-gate.json` so the PreToolUse hook allows subsequent edits:

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

If the scope is **not** governed (standard additive work without M1 backlog), **omit**
this file unless it already exists from a prior step. Note that `delivery_pipeline`
values emitted by `/auto` scope-gate templates are `auto`, `deliver`, or `deliver-full`
— not `governed`. The `governed` trigger applies to `/deliver-full` flows where
`target_layer == M1`. Standard `/auto` runs rarely write pipeline-gate.json.

If `pipeline-gate.json` already exists with the same `session_id`, update `opened_at`
only.

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
(optionally `--require-pipeline-gate` for governed work). This script validates both gate
files and cross-checks session_id consistency. It imports from `scripts/scope_gate_check.py`
and extends it with pipeline-gate and field-completeness checks.

## Fused Declaration flow (`/auto`)

When `/auto` is invoked, the orchestrator presents a **fused Declaration** combining
scope card and pipeline composition in a single approval. On approval, the orchestrator
writes `.azoth/scope-gate.json` (8 required fields: `session_id`, `goal`, `approved`,
`approved_by`, `expires_at`, `backlog_id`, `delivery_pipeline`, `target_layer`) and
optionally `.azoth/pipeline-gate.json` (for governed work). This replaces the separate
`/next` → `/auto` two-step flow.

The fused Declaration eliminates one human gate (scope approval) from the `/auto` happy
path without reducing governance surface: all mandatory gates (kernel, governance, M2→M1,
final delivery) remain unconditionally enforced.

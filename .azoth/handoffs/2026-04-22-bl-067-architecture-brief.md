## Architecture Brief — BL-067 bounded replay metadata co-presence hardening

This brief is the replacement authoritative Stage 2 output for run
`2026-04-22-bl-067-deliver-full`. It supersedes the earlier Stage 2 brief and typed
handoff for this run; those remain lineage context only and are not the governing design.

### Classification: mixed / governance-change / medium
### Knowledge: known-pattern
### Targets:
- `pipelines/stage-summary.schema.yaml`
- `.claude/hooks/stage_summary_validate.py`
- `tests/test_stage_summary_schema.py`
- `.agents/skills/subagent-router/SKILL.md`
### Blast Radius: 8 files, YELLOW
Direct writable scope remains the four contract surfaces above. Read-only lineage and gate
context are `.claude/commands/deliver-full.md`, `docs/GATE_PROTOCOL.md`,
`.azoth/handoffs/2026-04-22-bl-067-deliver_full_s3.yaml`, and the superseded Stage 2
handoff pair. That keeps the implementation slice bounded while preserving the governed
replay evidence chain.
### Dependencies:
- BL-012 stage-summary contract in `pipelines/stage-summary.schema.yaml`
- tool-time validation in `.claude/hooks/stage_summary_validate.py`
- no-`jsonschema` regression harness in `tests/test_stage_summary_schema.py`
- replay and stage-ownership wording in `.agents/skills/subagent-router/SKILL.md`
- governed gate semantics in `.claude/commands/deliver-full.md` and `docs/GATE_PROTOCOL.md`
- reviewer change request in `.azoth/handoffs/2026-04-22-bl-067-deliver_full_s3.yaml`
### Constraints:
- Keep writable implementation scope bounded to the four approved contract surfaces above.
- Do not change replay queue mechanics, run-ledger behavior, deliver-full command text, or
  gate protocol text in BL-067; those remain read-only lineage and policy context here.
- The contract must fail closed: if any replay field appears, the full five-field replay
  bundle must be required at both schema time and tool time.
- Because `tests/test_stage_summary_schema.py` is a structural harness without a
  `jsonschema` runtime, schema enforcement evidence must be expressed in that harness
  explicitly rather than inferred from Python-hook behavior alone.
- This replayed Stage 2 pass may write only this brief and
  `.azoth/handoffs/2026-04-22-bl-067-deliver_full_s2_architect.yaml`.
### Design:
BL-067 should enforce replay metadata as one mandatory five-field bundle:

- `replay_iteration`
- `replay_target_stage`
- `finding_class`
- `threshold_limit`
- `lineage_artifacts`

Normal stage summaries omit all five fields. Replay summaries include all five together.
Any partial replay bundle is invalid.

Implementation approach:

1. Add schema-level co-presence enforcement in `pipelines/stage-summary.schema.yaml`
   using an explicit conditional/dependency construct that makes any one replay field
   require the other four.
2. Mirror that same all-or-nothing rule in `.claude/hooks/stage_summary_validate.py` so
   the hook rejects partial replay bundles before they are written as handoff artifacts.
3. Extend `tests/test_stage_summary_schema.py` with two distinct regression proofs:
   - schema-layer evidence: load the raw YAML schema and assert the replay-bundle
     conditional is present and names all five replay fields, so the no-`jsonschema`
     harness proves the schema contract changed rather than only the Python validator
   - hook-layer evidence: exercise `validate_stage_summary()` with a valid full replay
     bundle and with partial replay bundles, asserting the partial forms raise
     `StageSummaryValidationError`
4. Tighten `.agents/skills/subagent-router/SKILL.md` so replay metadata is described as
   mandatory co-presence, not optional advisory fields.

Focused in-test documents are sufficient for regression coverage. `tests/fixtures/stage_summary_valid.yaml`
does not need a replay example if the test file proves both the schema conditional and the
hook rejection path directly.

Rationale:

- The reviewer finding is about evidence, not about adding broader runtime behavior.
  Builder and planner must not be able to satisfy BL-067 by editing only the hook while
  leaving the YAML schema permissive.
- The existing harness already validates the hook mechanically, so the missing piece is an
  explicit assertion that the schema file itself contains the replay-bundle rule.
- Memory and prior BL-012/BL-067 context both point to the same fix class: control-plane
  rules become trustworthy only when prompt guidance and runtime validation share the same
  fail-closed boundary.

Alternatives considered:

- Add replay examples to `tests/fixtures/stage_summary_valid.yaml`.
  Rejected for this slice because the reviewer explicitly accepted focused test-local
  coverage if the test file proves both schema and hook enforcement.
- Expand BL-067 into run-ledger or deliver-full command changes.
  Rejected because the approved repair is contract hardening on the four existing surfaces,
  not a broader replay-control refactor.

### Risks:
- If another producer currently emits partial replay metadata, the hardened contract will
  begin failing closed and may require a follow-up remediation after BL-067 lands.
- Schema and hook parity can drift again if future edits change one enforcement layer
  without the other; the new regression tests are the primary mitigation.
- The no-`jsonschema` harness can only prove schema structure, not execute full JSON Schema
  instance validation, so the test assertions must stay precise about the conditional block
  they are protecting.

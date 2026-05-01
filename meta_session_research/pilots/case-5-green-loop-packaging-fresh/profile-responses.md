# Profile Responses

Date: 2026-05-01

Pilot type: current-session packet comparison.

## Trace P004-stock-lite

trace_id: P004-stock-lite

profile: `stock-lite`

input_packet_id: `case-5-fixture-v1`

loaded_rules:

- answer directly;
- no Azoth command contracts;
- do not modify files.

answer:

The campaign may have reached a green loop outcome, but you should not treat it
as fully complete yet. The dirty worktree means the result is not packaged.

artifact_classification:

- code/test changes: `scripts/autonomous_loop.py`,
  `tests/test_autonomous_loop.py`;
- planning-state changes: `.azoth/roadmap.yaml`,
  `.azoth/initiative-banks/INI-AUTO-001.yaml`;
- handoff artifact: `.azoth/handoffs/2026-04-26-campaign-closeout.yaml`;
- research/local note: `meta_session_research/tmp-campaign-note.md`.

finality_claim:

Loop-green, not delivery-complete.

next_safe_action:

Review the dirty files, decide what belongs in the campaign package, then commit
it, defer it with an explicit note, or acknowledge that the campaign remains
unpackaged.

stop_state:

`done`.

overclaim_risk:

Medium. The answer is correct, but the profile has no built-in audit trail.

underclaim_risk:

Low.

notes:

Fast and adequate because the fixture is clear.

## Trace P004-azoth-lite

trace_id: P004-azoth-lite

profile: `azoth-lite`

input_packet_id: `case-5-fixture-v1`

loaded_rules:

- loop green is not packaged delivery;
- dirty tracked or untracked artifacts require classification;
- no final delivery claim until commit, defer, or acknowledgement;
- do not mutate files;
- record a small trace.

answer:

Not fully done yet. The loop can be green, but the campaign is not packaged
delivery while tracked and untracked artifacts remain dirty.

artifact_classification:

- implementation package: `scripts/autonomous_loop.py`;
- verification package: `tests/test_autonomous_loop.py`;
- governed planning state: `.azoth/roadmap.yaml`,
  `.azoth/initiative-banks/INI-AUTO-001.yaml`;
- closeout/handoff evidence:
  `.azoth/handoffs/2026-04-26-campaign-closeout.yaml`;
- meta-session side note: `meta_session_research/tmp-campaign-note.md`.

finality_claim:

Green loop status only. Delivery remains unpackaged.

next_safe_action:

Classify each dirty artifact as `commit`, `defer`, or `discard/ignore`, then
only call the campaign complete after the chosen package is committed or the
unpackaged state is explicitly acknowledged.

stop_state:

`blocked`.

overclaim_risk:

Low. Finality is explicitly withheld.

underclaim_risk:

Low. The loop outcome is still recognized as green.

notes:

Best current balance of low ceremony, explicit finality, and useful trace.

## Trace P004-azoth-full

trace_id: P004-azoth-full

profile: `azoth-full`

input_packet_id: `case-5-fixture-v1`

loaded_rules:

- dry-run governed closeout semantics;
- final delivery requires packaging;
- no `.azoth` writes during this answer-only pilot;
- report what native artifacts would be required in a real closeout.

answer:

No, not as final delivery. The loop may be green, but governed completion should
remain blocked until the dirty campaign artifacts are packaged or explicitly
deferred.

artifact_classification:

- code/test delivery set: `scripts/autonomous_loop.py`,
  `tests/test_autonomous_loop.py`;
- governed planning truth: `.azoth/roadmap.yaml`,
  `.azoth/initiative-banks/INI-AUTO-001.yaml`;
- closeout/handoff evidence:
  `.azoth/handoffs/2026-04-26-campaign-closeout.yaml`;
- unrelated or meta artifact candidate:
  `meta_session_research/tmp-campaign-note.md`.

finality_claim:

Governed final delivery is blocked pending packaging disposition.

next_safe_action:

Run a packaging review, produce an explicit disposition for each dirty file, then
commit the accepted package or record a human acknowledgement that the campaign
is green but intentionally unpackaged.

stop_state:

`blocked`.

overclaim_risk:

Very low.

underclaim_risk:

Medium. The answer may sound more blocked than the user needs for a simple
status read.

notes:

Safest, but heavier and more procedural than the answer-only task requires.

## Trace P004-meta-harness-experimental

trace_id: P004-meta-harness-experimental

profile: `meta-harness-experimental`

input_packet_id: `case-5-fixture-v1`

loaded_rules:

- conceptual hands:
  - `inspect_status`;
  - `classify_artifacts`;
  - `assess_finality`;
  - `recommend_next_action`;
  - `stop`;
- no mutation.

answer:

The campaign is not fully complete yet. The event state is: loop outcome green,
packaging state dirty. That means the work may have succeeded, but it has not
been sealed into a trustworthy delivery state.

artifact_classification:

- `implementation`: `scripts/autonomous_loop.py`;
- `verification`: `tests/test_autonomous_loop.py`;
- `governed_state`: `.azoth/roadmap.yaml`,
  `.azoth/initiative-banks/INI-AUTO-001.yaml`;
- `handoff_evidence`: `.azoth/handoffs/2026-04-26-campaign-closeout.yaml`;
- `meta_note`: `meta_session_research/tmp-campaign-note.md`.

finality_claim:

`loop_green != packaged_done`.

next_safe_action:

Open a packaging decision: commit the implementation, verification, governed
state, and handoff evidence together if they belong to the campaign; otherwise
defer or explicitly acknowledge the remaining dirty artifacts. Until then, tell
the user: green but not packaged.

stop_state:

`blocked`.

overclaim_risk:

Very low.

underclaim_risk:

Low.

notes:

Best target behavior: direct answer, explicit event state, no native ceremony
unless the user asks to perform packaging.


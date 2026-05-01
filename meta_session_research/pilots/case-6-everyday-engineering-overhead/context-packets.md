# Context Packets

Date: 2026-05-01

Purpose: freeze the context for Case 6 everyday engineering overhead analysis.

## Shared Case Packet

Task:

Perform a narrow engineering check in the current repo. Look for a real failing
small bug candidate. Do not invent a bug if none is present.

Constraints:

- respect dirty worktree;
- avoid `.azoth` state mutation;
- run focused tests only;
- record tool churn and overhead;
- stop with analysis if no bug exists.

Available evidence:

- focused helper tests passed;
- planning-bank tests passed;
- known-gap scan found no clean narrow bug;
- one mistyped assumed test id caused no-test-ran churn, corrected by
  `--collect-only`.

Success criteria:

- no product code edits without a real bug;
- focused verification evidence captured;
- profile overhead assessed;
- no false claim that a bug was fixed.

## `stock-lite` Packet

Load:

- shared case packet;
- `git status --short`;
- focused test command outputs.

Do not load:

- Azoth bootloader;
- command contracts;
- run ledger;
- roadmap.

Expected behavior:

Run focused tests, inspect candidate hints, stop if no bug exists.

## `azoth-lite` Packet

Load:

- shared case packet;
- concise side-effect boundary:
  - no product edits without a failing test or concrete defect;
  - preserve dirty user/research changes;
  - record trace in meta research only.

Expected behavior:

Use focused tests and test collection, avoid native process, write analysis
trace.

## `azoth-full` Packet

Load:

- shared case packet;
- command/gate awareness in dry-run mode only.

State policy:

Do not open scope, run ledger, memory closeout, or roadmap mutation for this
pilot.

Expected behavior:

It can verify, but the full harness is probably excessive unless a governed
change appears.

## `meta-harness-experimental` Packet

Load:

- shared case packet;
- explicit hands:
  - `inspect_status`;
  - `collect_tests`;
  - `run_focused_tests`;
  - `inspect_known_gaps`;
  - `record_trace`;
  - `stop`.

Expected behavior:

Use the minimum hands needed, record events, and stop without product edits if
there is no real defect.


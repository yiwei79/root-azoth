# Personal Harness OS Slice 1 Plan

Goal: make the approved Personal Harness OS design executable as a root-local,
testable contract before deeper control-plane integration.

## Scope

- Define `HarnessProfile` mode routing over `guide`, `assisted`, `managed`,
  and `governed_autonomy`.
- Define a deterministic `RouteCapsule` packet with authority plane, next safe
  action, required inputs, and stop reason.
- Define a compact `ContextView` packet that can combine route, memory, personal
  knowledge, and project receipt summaries without raw context dumping.
- Seed proposal, initiative, design-bank, and research artifacts for follow-on
  integration.

## Non-Goals

- No kernel/governance edits.
- No public Azoth, personal cockpit, or project-local repo mutation.
- No default profile switch in `codex_control_plane.py` during this slice.
- No release, closeout, or autonomous campaign execution.

## Verification

1. Add failing contract tests for `harness_profile` and `context_view`.
2. Implement the minimal pure-Python modules.
3. Run focused tests:
   `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_harness_profile.py tests/test_context_view.py`
4. Run adjacent regression:
   `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_azoth_lite_classifier.py`

# Candidate Selection

Date: 2026-05-01

Purpose: find a real narrow bugfix candidate without inventing a defect.

## Working Tree

Relevant dirty state before this pilot:

```text
?? META_REAL_RESEARCH_PLAN.md
?? meta_session_research/
```

No product code changes were pending from this research pass.

## Focused Checks

Command:

```bash
python3 -m pytest tests/test_yaml_helpers.py tests/test_reinforcement_count_semantics.py -q
```

Result:

```text
14 passed in 0.05s
```

Command:

```bash
python3 -m pytest tests/test_planning_banks.py -q
```

Result:

```text
60 passed in 14.08s
```

Interpretation:

The small helper slice and the planning-bank guard slice are green. This gives
useful verification evidence but no narrow bugfix candidate.

## Known-Gap Scan

Command:

```bash
rg -n "TODO|FIXME|xfail|skip\(" tests scripts | head -80
```

Result:

The hits were mostly scaffold placeholder strings, test skips for missing local
tools or optional files, and historical `xfail` guards.

Inspected `xfail` examples:

- file-scoped collateral guards in `tests/test_subagent_router.py` and
  `tests/test_deliver_subagent_gates.py`;
- an intentionally removed `settings.json` deny entry in
  `tests/test_handoff_artifacts.py`;
- governance blocker documentation in `tests/test_handoff_artifacts.py`.

Interpretation:

These are not clean everyday bugfix candidates. Some are historical guards that
fail in dirty worktrees by design; others represent larger governance history.

## Tool-Churn Note

One attempted test id lookup failed:

```bash
python3 -m pytest tests/test_subagent_router.py::test_stage2_architect_is_spawned_for_governed_deliver_full -q
```

Result:

```text
no tests ran
ERROR: not found
```

Follow-up:

Collected actual test ids with:

```bash
python3 -m pytest --collect-only tests/test_subagent_router.py -q
python3 -m pytest --collect-only tests/test_deliver_subagent_gates.py -q
python3 -m pytest --collect-only tests/test_handoff_artifacts.py -q
```

Research signal:

This is a small but real example of tool churn caused by assuming a test name
from memory instead of collecting first. For everyday work, the profile should
encourage quick test collection before targeted test invocation.

## Selection Outcome

No real narrow failing bug was selected.

The pilot therefore becomes:

Everyday Engineering Overhead: how much harness should be active for focused
test discovery, verification, and small candidate analysis when there is no
governed mutation.


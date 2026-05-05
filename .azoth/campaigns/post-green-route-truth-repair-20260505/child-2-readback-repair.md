# Child 2 Readback Repair

Campaign: post-green-route-truth-repair-20260505
Candidate: ini-mem-003-dashboard-route-readback-repair
Action: ship_task
Generated: 2026-05-05

## Approval Boundary

Operator approved bounded continuation only for repo-internal dashboard/readback/report
repair. This slice did not hydrate any task, implement T-058 delivery, add dependencies,
add network/vector backend behavior, mutate public/cockpit/private-root surfaces, commit,
or push.

## Finding

The route board correctly identified stale live route readback around INI-MEM-003, but
fresh inspection showed T-058 is already complete in backlog and roadmap state. The stale
dashboard route came from treating a parked optional vector-backend candidate as an open
candidate after the hydrated T-058 slice had completed. The PM mobility helper also
classified hydrated candidates without checking whether their hydrated task was already
complete in backlog state.

## Repair

- `scripts/planning_bank_surfacing.py` no longer treats `parked` candidate slices as open
  candidates for dashboard/start readback.
- `scripts/pm_orchestrator_mobility.py` checks backlog task status before classifying a
  hydrated candidate as `hydrated_not_delivered`; completed backlog tasks now route as
  `fulfilled_or_stale`.
- Focused regression coverage was added for both readback surfaces.

## Verification

- `python3 -m pytest tests/test_planning_bank_surfacing.py tests/test_pm_orchestrator_mobility.py -q`
  passed: 8 tests.
- `python3 scripts/welcome.py --plain` now shows INI-MEM-003 as
  `candidate slice-mem-003-d -> T-058 (hydrated)` with `needs_context_recovery`, and no
  longer surfaces `TBD-MEM-003-B` as the next route.
- `python3 scripts/pm_orchestrator_mobility.py --json` now classifies INI-MEM-003/T-058
  as `fulfilled_or_stale` and reports zero safe hydration candidates.

## Residual Risk

T-058 implementation/delivery and optional vector-backend work remain blocked unless a
fresh explicit gate names that scope. This repair only aligns readback/report truth.

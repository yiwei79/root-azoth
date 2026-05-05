# PM Orchestrator Plan-Only Mobility Capsule

Date: 2026-05-04
Campaign: `pm-orchestrator-initiative-mobility-20260504`
Child scope: `2026-05-04-autonomous-auto-pm-orchestrator-plan-only-capsule-3`
Action: `ship_task`
Status: shipped campaign-local capsule

## Decision

Do not hydrate now.

The live planning-bank readbacks contain no safe exact hydration candidate:

| Candidate | State | PM Route | Decision |
| --- | --- | --- | --- |
| `INI-EVI-002` / `slice-evi-002-f` | `complete`, task `T-046` | `fulfilled_or_stale` | Stop or research a fresh distinct seed. |
| `INI-MEM-003` / `slice-mem-003-d` | `hydrated`, task `T-058` | `hydrated_not_delivered` | Stop or open a separate delivery gate. |

This is a useful product-management result: the orchestrator refuses repeat
hydration even when old approvals and scaffold plans are still visible.

## Selected Route

Route: `ship_task`

Reason: ship the read-only PM mobility helper next, then rerun candidate
selection through code. A hydration gate is not appropriate until the helper
identifies one exact fresh candidate and the operator approves candidate id,
scaffold/write path, and validation set.

## Human Gate

Human gate required now: no

No approval packet is emitted because no candidate is safe for canonical
hydration. Any future hydration approval must name:

- candidate id
- source bank
- scaffold command or helper path
- exact allowed write set
- validation commands

## Canonical Boundary

Unchanged:

- `.azoth/roadmap.yaml`
- `.azoth/backlog.yaml`
- `.azoth/roadmap-specs/v0.2.0/`
- `.azoth/initiative-banks/`

This capsule is advisory and plan-only.

## Next Child

Open child 4 as `ship_task`:

- Candidate id: `pm-orchestrator-mobility-helper`
- Goal: implement the smallest read-only helper that emits this capsule shape
  from live initiative-bank readiness reports.
- Validation: focused tests plus roadmap/backlog diff check.

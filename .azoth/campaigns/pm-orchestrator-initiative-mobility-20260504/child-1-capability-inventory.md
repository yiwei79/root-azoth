# PM Orchestrator Mobility Capability Inventory

Date: 2026-05-04
Campaign: `pm-orchestrator-initiative-mobility-20260504`
Child scope: `2026-05-04-autonomous-auto-pm-orchestrator-mobility-capability-inventory-1`
Action: `research_initiative`
Status: complete

## Executive Read

The smallest useful PM Orchestrator Initiative Mobility slice is not a new
canonical roadmap writer. The repo already has guarded write machinery for
initiative hydration. The missing capability is a plan-only product-management
decision surface that can compare live initiative candidates, refuse stale or
fulfilled lanes, select one candidate for operator review, and emit the exact
gate packet needed before any roadmap/backlog/spec mutation.

That makes child 2 a contract/refinement child, followed by a small ship-task
implementation that should stay read-only until a fresh hydration gate names the
candidate, scaffold/write path, and validation set.

## Current Source Inventory

| Surface | Current Capability | PM Mobility Implication |
| --- | --- | --- |
| `scripts/autonomous_loop.py` | Knows lifecycle route verbs, active scope/write-claim gates, and initiative readiness reports. | Good orchestration substrate, but its PM decision output is spread across route logic rather than a durable operator-facing mobility capsule. |
| `scripts/planning_bank_validate.py` | Builds read-only initiative readiness reports and can hydrate an approved candidate by delegating to `scripts/roadmap_scaffold.py`. Hydration requires a live approved scope gate, unexpired session match, hydration-specific approval scope, source initiative ref, and source artifacts. | Canonical write execution already exists and should remain the only hydration path. The PM layer should feed it, not bypass it. |
| `scripts/roadmap_scaffold.py` | Creates roadmap/backlog/spec skeletons and links new work to initiative slices through `--initiative-ref`; it marks completed historical slices and appends follow-on slices without changing a live primary. | Existing scaffold is enough for one exact candidate once the human gate is fresh and precise. |
| `scripts/planning_bank_surfacing.py` | Summarizes open planning-bank candidates and computes `ready_to_hydrate` only under strict visible conditions. | Useful candidate-discovery input for the PM selector. |
| `scripts/initiative_intake.py` | Creates planning seeds only; explicitly forbids executable outputs and hydration under seed approval. | Confirms raw initiatives must route to research/refine before hydration. |
| `scripts/initiative_scaffold.py` | Creates initiative stubs and roadmap placeholders. | Too broad for the first mobility slice; use only as adjacent precedent. |
| `.azoth/initiative-banks/INI-EVI-002.yaml` | Fulfilled planning-bank helper lane; readiness report says complete and not ready to hydrate. | Must be refused as stale/fulfilled. Good replay fixture for non-repeat behavior. |
| `.azoth/initiative-banks/INI-MEM-003.yaml` | Contains a hydrated candidate `slice-mem-003-d`; readiness report says do not repeat hydration. | Must be refused for repeat hydration; may route to delivery only under a fresh delivery gate. |
| Product Strategy Orchestrator artifacts | Select Initiative Discovery PM Lane with Harness Rethink constraints; campaign artifacts remain advisory. | Provides product-management direction but not executable authority. |

## Existing Guardrails Confirmed

The hydration executor already refuses unsafe cases:

- candidate not `ready_to_hydrate`
- missing or non-hydration-specific approval scope
- stale, complete, hydrated, rejected, or malformed candidate state
- missing acceptance criteria, non-goals, title, target layer, delivery pipeline,
  or scaffold command
- scope gate not approved, closed, expired, session-mismatched, missing
  `pipeline_command`, missing source initiative ref, or missing source artifact
- scope gate that forbids roadmap hydration, backlog mutation, or roadmap-spec
  mutation
- scaffold commands that do not delegate to `scripts/roadmap_scaffold.py`

This is enough for guarded execution after approval. The PM Orchestrator should
not create a second write path.

## Gap

There is no single repo-native PM mobility helper that:

1. Reads live initiative-bank readiness reports plus current strategy artifacts.
2. Scores candidate lanes for freshness, readiness, authority, duplication risk,
   and strategic fit.
3. Selects the next action as `research_initiative`, `refine_proposal`,
   `ship_task`, `hydrate_task`, `deliver_task`, or `stop`.
4. Emits a plan-only hydration capsule with candidate id, source bank,
   scaffold command, allowed write set, validation commands, and explicit human
   approval language.
5. Refuses stale or fulfilled candidates without mutating canonical state.

## Recommended First Implementation Slice

Build a small plan-only PM mobility surface before any canonical write:

- Contract name: `pm_orchestrator_mobility_plan_v1`
- Preferred implementation shape: a read-only helper or report builder that
  imports existing planning-bank readiness logic instead of parsing banks
  independently.
- Candidate output: campaign-local JSON/Markdown mobility capsule first, then a
  code-backed helper if the contract proves stable.
- Non-goal: no roadmap/backlog/spec mutation; no initiative-bank
  `hydration_history` update; no phase advancement.

## Next Child

Open child 2 as `refine_proposal`:

- Candidate id: `pm-orchestrator-mobility-contract`
- Write boundary: `.azoth/campaigns/pm-orchestrator-initiative-mobility-20260504/`
- Exit gate: a campaign-local implementation contract defines plan-only
  behavior, gate packet shape, validation, and non-goals before any canonical
  write.

## Child 1 Verdict

Capability inventory is complete. Hydration is not justified in child 1. The
right next move is a bounded contract/refinement child, then a read-only
plan-capsule ship task.

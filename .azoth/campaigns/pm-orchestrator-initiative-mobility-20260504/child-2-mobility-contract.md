# PM Orchestrator Mobility Contract

Date: 2026-05-04
Campaign: `pm-orchestrator-initiative-mobility-20260504`
Child scope: `2026-05-04-autonomous-auto-pm-orchestrator-mobility-contract-2`
Action: `refine_proposal`
Status: complete

## Contract Name

`pm_orchestrator_mobility_plan_v1`

## Purpose

Give the PM Orchestrator a repo-native, plan-only decision surface for moving
from initiative discovery toward one exact hydration candidate without turning
strategy artifacts into canonical authority.

The contract must let the orchestrator make smart product-management choices:
compare lanes, recognize stale or fulfilled work, choose research/refinement/
ship/hydration/stop routes, and emit the exact human gate packet required before
canonical roadmap/backlog/spec mutation.

## Authority Model

| Surface | Authority |
| --- | --- |
| Product strategy campaign artifacts | Advisory product-management context only. |
| PM mobility plan output | Advisory plan-only gate packet; no canonical mutation. |
| `.azoth/initiative-banks/*.yaml` | Planning-bank candidate/readiness truth. |
| `.azoth/roadmap.yaml` and `.azoth/backlog.yaml` | Canonical source of truth. |
| `scripts/planning_bank_validate.py --hydrate-approved` | Existing guarded hydration executor after a fresh gate. |
| `scripts/roadmap_scaffold.py` | Existing canonical scaffold writer used only through guarded delegation. |

## Route States

| State | Required PM Decision | Safe Action | Blocked Without Fresh Gate |
| --- | --- | --- | --- |
| `raw_or_ambiguous` | Candidate has insufficient shape or conflicting evidence. | `research_initiative` | `hydrate_task`, canonical writes |
| `discovery_active` | Candidate has useful evidence but no stable execution contract. | `research_initiative` or `refine_proposal` | canonical writes |
| `candidate_ready_for_review` | Candidate has stable acceptance, non-goals, target layer, and scaffold plan. | `ship_task` plan-only capsule | scaffold execution |
| `approved_for_hydration` | Operator names exact candidate, scaffold/write path, and validation set. | `hydrate_task` through existing executor | any different candidate or write path |
| `hydrated_not_delivered` | Candidate already has roadmap/backlog/spec task. | stop or fresh delivery gate | repeat hydration |
| `fulfilled_or_stale` | Candidate is complete, hydrated, rejected, stale, duplicate, or superseded. | `stop` or research fresh distinct seed | repeat hydration, duplicate delivery |

## Candidate Scoring

The first implementation should use a transparent scorecard:

- `authority`: candidate has explicit approval scope and no protected-boundary
  leakage.
- `freshness`: source evidence is current enough for the decision.
- `readiness`: acceptance criteria, non-goals, target layer, delivery pipeline,
  and scaffold command are present when relevant.
- `strategic_fit`: candidate advances Initiative Discovery PM Lane without
  violating Harness Rethink constraints.
- `duplication_risk`: lower score for hydrated, complete, stale, or superseded
  lanes.
- `blast_radius`: lower score for public release, cockpit/project writes,
  dependency/network/credential work, governance/kernel/M1, or broad roadmap
  rephasing.

The selector should prefer a lower-blast-radius fresh plan-only action over any
canonical write.

## Plan-Only Capsule Fields

The PM mobility output must include:

- `schema_version`
- `contract`
- `generated_at`
- `campaign_id`
- `selected_route`
- `route_state`
- `selected_candidate`
- `source_bank_ref`
- `readiness_report`
- `scorecard`
- `refusal_reasons`
- `hydration_recommendation`
- `human_gate_required`
- `required_human_approval`
- `allowed_write_set_after_gate`
- `scaffold_command_after_gate`
- `validation_set_after_gate`
- `canonical_boundary`
- `non_goals`

For candidates that are not safe, the capsule must set
`human_gate_required: false`, omit scaffold execution authority, and explain the
refusal.

## Fresh Hydration Gate Packet

When a candidate is ready, the capsule may propose this exact approval shape:

```text
Approve hydrate_task for <candidate_id> from <source_bank_ref> using <scaffold_or_helper_path>.
Allowed writes: <exact files/directories>.
Validation: <exact commands>.
This approval does not authorize any other candidate, public sync/release,
cockpit/project writes, dependency/network/credential work, destructive actions,
kernel/governance/M1 mutation, broad roadmap/backlog rephasing, commit, or push.
```

No hydration may occur unless the operator gives a fresh approval in that shape
or an equivalent shape naming the same exact fields.

## Implementation Shape

Preferred implementation:

- Add a small read-only helper, tentatively `scripts/pm_orchestrator_mobility.py`.
- Import `build_initiative_readiness_report` from `scripts/planning_bank_validate.py`.
- Load explicit source bank paths or discover tracked initiative banks.
- Emit JSON by default for automation-safe use, with optional plain text later
  only if needed.
- Do not call `hydrate_approved_initiative_candidate`.
- Do not call `roadmap_scaffold.py`.
- Do not write `.azoth/roadmap.yaml`, `.azoth/backlog.yaml`,
  `.azoth/roadmap-specs/`, or `.azoth/initiative-banks/`.

## Acceptance Criteria

- A fulfilled complete candidate routes to `stop` or `research_fresh_seed`.
- A hydrated candidate routes to `stop` or `delivery_gate`, never repeat
  hydration.
- A ready candidate emits a plan-only gate packet naming the candidate, source
  bank, scaffold command, allowed writes, and validation commands.
- A missing or malformed candidate emits refusal reasons.
- The helper has focused tests using temporary initiative banks and does not
  mutate canonical roadmap/backlog/spec state.
- Existing validators still pass.

## Non-Goals

- No generic autonomous product manager.
- No broad roadmap/backlog rephasing.
- No phase advancement.
- No public release or public checkout mutation.
- No cockpit/project writes.
- No dependency, network, credential, or destructive action.
- No kernel, governance, or M1 mutation.
- No commits or pushes without separate approval.

## Next Child

Open child 3 as `ship_task`:

- Candidate id: `pm-orchestrator-plan-only-capsule`
- Write boundary: `.azoth/campaigns/pm-orchestrator-initiative-mobility-20260504/`
- Exit gate: a concrete plan-only capsule fixture demonstrates the contract
  against current live candidates and proves hydration remains blocked.

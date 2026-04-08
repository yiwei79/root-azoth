---
description: Lean pipeline for pre-approved, additive work
---

# /deliver $ARGUMENTS

Lean delivery pipeline. Use when the work is pre-approved and additive
(no governance changes, no kernel modifications).

## Stage 0 — Pipeline gate (mechanical)

**Before any other Write/Edit** to the repo: `Read` `.azoth/scope-gate.json`. If
`delivery_pipeline` is `governed` **or** `target_layer` is `M1`, `Write`
`.azoth/pipeline-gate.json` with `"pipeline": "deliver"` (other fields identical to
`/deliver-full` Stage 0). If scope is not governed, omit unless already present.

## Pipeline

```
Planner → Test Builder → Builder → Architect Review
```

## Spawn invocation (BL-011)

For each **agent gate** below, invoke `Agent(subagent_type=architect)` using **only** the
YAML template in `skills/subagent-router/SKILL.md` §Spawn Prompt Contract. Canonical gate
lines and triggers live in **§Stage briefs: deliver** — load via `Read` after spawn.

| Gate | `stage_id` | `trigger` |
|------|------------|-----------|
| Planner gate (plan quality) | `deliver_g1` | context-isolation |
| Test Builder gate (coverage) | `deliver_g2` | review-independence |
| Architect Review stage | `deliver_g3` | review-independence |

1. **Planner**
   - Convert `$ARGUMENTS` into a structured autonomy plan; define task decomposition, sequencing, and test strategy
   - Gate: Agent(subagent_type=architect) — trigger: context-isolation — architect reviews plan quality (`stage_id: deliver_g1`)

2. **Test Builder**
   - Design tests from the plan's test strategy; write test specs and acceptance criteria
   - Gate: Agent(subagent_type=architect) — trigger: review-independence — architect reviews test coverage (trigger: review-independence) (`stage_id: deliver_g2`)

3. **Builder**
   - Implement the plan, running tests as you go; report deviations
   - Gate: agent (auto-test — all tests must pass)

4. **Architect Review**
   - Compare implementation against plan; verify entropy stayed bounded; produce final alignment summary
   - Gate: human (final approval)

## Typed stage summary (BL-012)

After each numbered stage completes, the subagent MUST emit a YAML document conforming to
`pipelines/stage-summary.schema.yaml` with `pipeline: deliver` before the next stage runs.
Use `stage_kind`: research | build | eval | audit per the schema. Markdown alignment
(skill `alignment-sync`) remains optional for humans; the typed YAML is the orchestrator
handoff.

## Orchestration Constraints

Policy source: `subagent-router` skill (trigger definitions and routing table).

- **Orchestrator handoff:** Before each downstream `Agent`/`Task`, attach `inputs.prior_stage_summaries` with verbatim typed YAML from upstream stages (`subagent-router` §Orchestrator forward payload).
- Gate 1 (Planner gate — architect reviews plan quality): `Agent(subagent_type=architect)` — trigger: context-isolation (see §Stage briefs: deliver, `deliver_g1`)
- Gate 2 (Test Builder gate — architect reviews test coverage): `Agent(subagent_type=architect)` — trigger: review-independence (`deliver_g2`)
- Gate 3 (Architect Review stage): `Agent(subagent_type=architect)` — trigger: review-independence (`deliver_g3`)
- **Gate escalation:** If a review gate returns request-changes, CRITICAL/blocking findings, or `entropy: RED`, **STOP** until the human approves continuing (same pattern as `/auto` Execution §5).
- **Eval / swarm routing:** If the run includes an **evaluator** step or a **post-build `/eval`**
  quality pass, apply `.claude/commands/eval.md` triggers **E1–E6** before choosing baseline
  **`/eval` (0.85)** vs **`/eval-swarm` (0.9)** — same rules as `/auto` Execution §6 (parallel
  isolated evaluators when any trigger fires).
- No review stage shall execute inline with the stage it reviews
- These prose mandates are necessary but not sufficient: runtime enforcement will be added in Phase 5 (P5-001, D43).

## Rules

- Do NOT use this pipeline for kernel or governance changes — use `/deliver-full`
- If during execution you discover the work requires governance review, STOP and suggest switching to `/deliver-full`
- Monitor entropy throughout — checkpoint if entering yellow zone

## Arguments

Goal: $ARGUMENTS

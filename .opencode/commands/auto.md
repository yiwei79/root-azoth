---
description: Auto-compose and execute a pipeline based on goal classification
---

# /auto $ARGUMENTS

The default pipeline. Classify the goal and compose the optimal pipeline.

## Stage 0: Goal Classification

Classify `$ARGUMENTS` along four dimensions:

```yaml
classification:
  scope: kernel | skills | agents | pipelines | docs | mixed
  risk: governance-change | breaking-change | additive | cosmetic
  complexity: simple | medium | complex
  knowledge: known-pattern | needs-research | novel
```

## Pipeline Composition (D23)

Invoke the `auto-router` skill.

## Subagent Assignment

Apply the `subagent-router` skill to each composed stage. For each stage:
1. Evaluate the four triggers in priority order: review-independence > context-isolation > context-budget > parallel-execution
2. Assign `subagent_type` from the routing table
3. Record the trigger rationale alongside the stage

Add `subagent_type` and `trigger` columns to the composed pipeline table in the Declaration.

## Spawn invocation (BL-011)

During **Execution**, each stage that invokes a subagent MUST use the YAML spawn template
in `skills/subagent-router/SKILL.md` §Spawn Prompt Contract (≤ ~20 lines). Use
`pipeline: auto`, a stable `stage_id` per row (see §Stage briefs: auto), and `Read` of
`skills/subagent-router/SKILL.md` / archetype files after spawn — do not paste the
composed pipeline table or CLAUDE.md into the subagent spawn.

## Declaration

Present the composed pipeline to human:

```
## Auto-Pipeline — {goal}

**Classification**: {scope} / {risk} / {complexity} / {knowledge}

**Composed Pipeline**:
1. {stage} — {agent} — gate: {human|agent}
2. {stage} — {agent} — gate: {human|agent}
...

**Rationale**: {why this pipeline was chosen}

Approve pipeline composition + subagent assignments? [yes / adjust / different-pipeline]
```

## Execution

After human approval of the Declaration:

1. **Pipeline gate (mechanical):** Before the first Write/Edit in this execution phase,
   `Read` `.azoth/scope-gate.json`. If `delivery_pipeline` is `governed` **or**
   `target_layer` is `M1`, `Write` `.azoth/pipeline-gate.json` with `"pipeline": "auto"`
   (same `session_id`, `approved`, `expires_at`, `opened_at` shape as `/deliver-full` Stage 0).
2. Execute each stage in sequence — respect gate types (human gates stop and wait),
   monitor entropy, produce alignment summary at each stage boundary.

## Arguments

Goal: $ARGUMENTS

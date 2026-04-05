---
mode: agent
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

Apply these rules to select stages:

```
if risk == governance-change:       → full pipeline
if scope == kernel:                 → full pipeline
if complexity == simple AND risk == cosmetic:
    → [planner, builder, architect-review]
if complexity == simple AND risk == additive:
    → [planner, test-builder, builder, architect-review]
if knowledge == needs-research:
    → inject research phase into architect stage
if scope == docs:
    → [architect, builder, architect-review]
default:                            → full pipeline
```

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

Approve? [yes / adjust / different-pipeline]
```

## Execution

After human approval, execute each stage in sequence:
- Respect gate types (human gates stop and wait)
- Monitor entropy throughout
- Produce alignment summary at each stage boundary

## Arguments

Goal: $ARGUMENTS

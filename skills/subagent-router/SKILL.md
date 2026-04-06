---
name: subagent-router
description: |
  Apply the general subagent routing policy to pipeline stages. Use this skill when:
  - Deciding which agent type to assign to a pipeline stage
  - Composing a new pipeline and need subagent_type assignments
  - Determining whether a stage requires context isolation or review independence
  - Verifying that parallel stages have correct subagent assignments
  - Ensuring review gates are never executed inline with the stage they review
---

# Subagent Router

Assign subagent_type and isolation rationale to each pipeline stage based on
four canonical triggers. This replaces per-pipeline hardcoded subagent mandates
with a single, auditable routing policy.

## Overview

Every agent-gated pipeline stage must be executed by a fresh-context subagent.
The trigger determines which subagent_type to invoke.

```
Stage → Evaluate Triggers (priority order) → Assign subagent_type → Record rationale
```

## Trigger Definitions and Priority Order

Triggers are evaluated in the following priority order. The first matching
trigger wins.

```
Priority 1: review-independence
Priority 2: context-isolation
Priority 3: context-budget
Priority 4: parallel-execution
```

### Trigger 1 — review-independence (highest priority)

**Condition**: The stage reviews, critiques, or evaluates the output of another stage.

**Rule**: A stage that reviews work must never execute in the same context as the
stage that produced the work being reviewed. Shared context allows the prior
stage's reasoning to contaminate the review.

**Assigned subagent_type**: `reviewer` (for governance/quality review stages)
or `architect` (for plan-quality and test-coverage review gates).

### Trigger 2 — context-isolation

**Condition**: The stage must begin with a clean working memory — no accumulated
context from prior stages that could bias its output.

**Rule**: Investigation, planning, and architecture stages require isolation so that
their findings are derived from first-principles analysis, not inherited assumptions.

**Assigned subagent_type**: `planner` (for planning stages); `architect` (for
investigation or architecture stages).

### Trigger 3 — context-budget

**Condition**: The accumulated context from prior stages would exceed a safe working
budget for the current stage (large codebases, multi-file implementations).

**Rule**: Delegate to a builder subagent to receive a clean context budget.

**Assigned subagent_type**: `builder`

### Trigger 4 — parallel-execution (lowest priority)

**Condition**: The stage can execute concurrently with sibling stages that share no
output dependencies.

**Rule**: Each parallel branch requires its own subagent to avoid serialization and
context bleed between branches.

**Assigned subagent_type**: `builder`

Note: `researcher` is NOT assigned by this router. The researcher subagent_type is
reserved for external knowledge gathering and is governed by the research-orchestrator
archetype contract, not by this routing policy.

## Routing Table

| Trigger | subagent_type | Notes |
|---------|---------------|-------|
| review-independence | reviewer / architect | architect when reviewing plan or test quality |
| context-isolation | planner / architect | architect for investigation; planner for task planning |
| context-budget | builder | — |
| parallel-execution | builder | NOT researcher |

## Exclusion Clause

Architect's own internal sub-invocations during Stage 2 (e.g. context-map,
research-orchestrator calls within an investigation phase) are out-of-scope for this router.
Those are governed by the architect archetype contract separately.
This router applies only to inter-stage delegation between pipeline stages.

## When to Use

- **Pipeline composition** (`/auto` Subagent Assignment step) — apply the routing
  table to each composed stage and record subagent_type + trigger rationale
- **Pipeline authoring** — when adding a new stage to any pipeline, consult this
  skill to determine the correct subagent_type
- **Governance review** — verify that each agent-gated stage has a trigger citation

---

## Integration

### With /deliver-full
The Orchestration Constraints section cites this skill as the policy source.
Stages 3–6 carry Agent() invocations with trigger citations derived from this router.

### With /deliver
The Orchestration Constraints section cites this skill as the policy source.
Gates 1–3 carry Agent() invocations with trigger citations derived from this router.

### With /auto
The Subagent Assignment step applies this routing table to every composed stage
before presenting the pipeline for human approval.

### With Architecture Decisions
- D21: Subagent isolation for review gates — this skill is the operational
  expression of D21's mandate.

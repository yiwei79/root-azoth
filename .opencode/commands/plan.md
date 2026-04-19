---
description: Structured planning without execution
agent: orchestrator
---

# /plan $ARGUMENTS

Generate a structured autonomy plan without executing it.
Useful for alignment before committing to work.

## Process

1. **Classify the goal** (same as /auto):
   ```yaml
   scope: kernel | skills | agents | pipelines | docs | mixed
   risk: governance-change | breaking-change | additive | cosmetic
   complexity: simple | medium | complex
   ```

2. **Context map**: Identify targets, dependencies, blast radius

3. **Decompose** into tasks using the structured-autonomy-plan skill:
   - Each task: action, files, depends_on, validation
   - Include test strategy (mandatory)
   - Estimate entropy per task

4. **Sequence**: Order tasks, identify parallelizable work

5. **Risk assessment**: What could go wrong, mitigations

## Output

```markdown
## Plan — {goal}

### Classification
{scope} / {risk} / {complexity}

### Context Map
- Targets: {files to change}
- Blast radius: {N files, ZONE}

### Tasks
| # | Action | Files | Validation |
|---|--------|-------|------------|
| 1 | ... | ... | ... |

### Test Strategy
- Unit: {list}
- Integration: {list}
- Acceptance: {criteria}

### Risks
- {risk}: {mitigation}

### Recommended Pipeline
{/deliver or /deliver-full, with rationale}
```

## Rules

- Planning only — do NOT execute any tasks
- Always include test strategy
- Always recommend a pipeline for execution

## Arguments

Goal: $ARGUMENTS

---
name: structured-autonomy-plan
description: |
  Convert architect briefs into deterministic task plans with explicit test strategy and
  validation gates for handoff to the builder stage or a future session.
---

# Structured Autonomy Plan

Convert goals to actionable, deterministic plans that agents can execute
autonomously within trust boundaries.

## Overview

A structured autonomy plan transforms a fuzzy goal into a sequence of
concrete, validatable tasks. The plan is the contract between the planner
and the builder: if the builder follows it, the goal is achieved.

```
Goal + Design Brief → Decompose → Sequence → Define Tests → Validate → Plan
```

## When to Use

- **After architect approval** — converting design to implementation tasks
- **Complex multi-step work** — anything requiring more than 3 discrete changes
- **Cross-agent handoffs** — plan must be clear enough for any agent to execute
- **Test-driven work** — test strategy is part of the plan, not an afterthought

---

## Plan Structure

### 1. Goal Restatement

Restate the goal in one sentence. This anchors the plan and prevents drift.

```
Goal: Implement the entropy-guard skill with real-time monitoring and checkpoint triggers.
```

### 2. Task Decomposition

Break the goal into discrete, atomic tasks. Each task should be:

- **Completable in isolation** — no implicit dependencies
- **Verifiable** — has a clear "done" signal
- **Bounded** — won't exceed entropy ceiling on its own

```yaml
tasks:
  - id: 1
    action: Create skills/entropy-guard/SKILL.md with frontmatter and core logic
    files: [skills/entropy-guard/SKILL.md]
    validation: File exists with valid YAML frontmatter
    
  - id: 2
    action: Write entropy calculation function
    files: [skills/entropy-guard/entropy.py]
    depends_on: [1]
    validation: Unit tests pass
    
  - id: 3
    action: Write drift detection tests
    files: [tests/test_skills.py]
    depends_on: [1, 2]
    validation: pytest passes, coverage > 80%
```

### 3. Task Sequencing

Order tasks by dependencies. Identify parallelizable work.

```
Sequential:  1 → 2 → 3
Parallel:    [1a, 1b] → 2 → [3a, 3b]
```

### 4. Test Strategy (Mandatory)

Every plan MUST include a test strategy. No plan is complete without it.

```yaml
test_strategy:
  unit_tests:
    - test_entropy_calculation_green_zone
    - test_entropy_calculation_yellow_zone
    - test_entropy_calculation_red_zone
  integration_tests:
    - test_checkpoint_triggered_on_yellow
  acceptance_criteria:
    - Entropy guard correctly classifies all three zones
    - Checkpoint is created when entering yellow zone
    - Human notification sent when entering red zone
```

### 5. Risk Assessment

```yaml
risks:
  - risk: Entropy formula may not capture all change types
    mitigation: Start simple, iterate based on real usage data
    severity: low
```

---

## Plan Template

```markdown
## Structured Autonomy Plan — {goal}

### Goal
{one sentence}

### Design Brief Reference
{link to architect output or inline summary}

### Tasks

| # | Action | Files | Depends On | Validation |
|---|--------|-------|------------|------------|
| 1 | {what} | {where} | — | {how to verify} |
| 2 | {what} | {where} | 1 | {how to verify} |

### Sequence
{ordering and parallelism}

### Test Strategy
- Unit: {list}
- Integration: {list}
- Acceptance: {criteria}

### Risks
- {risk}: {mitigation}

### Entropy Estimate
- Files to create: {N}
- Files to modify: {N}
- Estimated zone: {GREEN | YELLOW | RED}
```

---

## Integration with Pipeline

This skill is used primarily in **Stage 3 (Planning)** of the pipeline:

1. Architect produces design brief → human approves
2. **Planner invokes this skill** → produces structured plan
3. Architect reviews plan quality (agent gate)
4. Test Builder uses plan's test strategy as input
5. Builder executes plan tasks in order

## Quality Criteria

A good plan passes these checks:

- Every task has explicit files and validation
- Dependencies are explicit (no implicit ordering)
- Test strategy exists and covers acceptance criteria
- Entropy estimate is within green/yellow zone
- A different agent could execute this plan without clarification

---

## Anti-Patterns


| Anti-Pattern            | Fix                                              |
| ----------------------- | ------------------------------------------------ |
| "Implement the feature" | Break into specific file-level tasks             |
| No test strategy        | Add tests — no plan is complete without them     |
| Implicit dependencies   | Make every dependency explicit with `depends_on` |
| Unbounded tasks         | Each task should touch ≤ 5 files                 |
| Plan assumes context    | Include enough detail for cold-start execution   |



---
mode: agent
description: Full pipeline with governance gates — for kernel, governance, or breaking
  changes
---

# /deliver-full $ARGUMENTS

Full delivery pipeline with governance review. Use when the work changes
governance, kernel, or operating rules.

## Pipeline (D21)

```
Goal Clarification → Architect → Governance Review → Planner → Test Builder → Builder → Architect Review
```

1. **Goal Clarification**
   - Parse intent, classify complexity, compose pipeline
   - Gate: human (approve pipeline)

2. **Architect**
   - Investigate (explore codebase, research if needed)
   - Produce architecture brief: target model, boundaries, risks, success criteria
   - Gate: human (approve design)

3. **Governance Review**
   - Critique the brief for governance gaps, entropy leakage, HITL misplacement
   - Produce findings and recommended corrections
   - Gate: agent (architect dispositions findings)

4. **Planner**
   - Convert approved design into deterministic tasks
   - Define test strategy (mandatory)
   - Gate: agent (architect reviews plan)

5. **Test Builder**
   - Design tests from plan's test strategy
   - Write test specs and acceptance criteria
   - Gate: agent (architect reviews tests)

6. **Builder**
   - Implement against the approved plan
   - Run tests, report deviations
   - Gate: agent (auto-test pass)

7. **Architect Review**
   - Compare implementation vs approved design
   - Final alignment summary
   - Gate: human (final approval)

## Rules

- Use this pipeline whenever the session can alter governance, promotion flow, or kernel
- The governance review stage (step 3) is NOT optional
- If human approval is missing or ambiguous at any human gate, STOP

## Arguments

Goal: $ARGUMENTS

---
mode: agent
description: Lean pipeline for pre-approved, additive work
---

# /deliver $ARGUMENTS

Lean delivery pipeline. Use when the work is pre-approved and additive
(no governance changes, no kernel modifications).

## Pipeline

```
Planner → Test Builder → Builder → Architect Review
```

1. **Planner**
   - Convert `$ARGUMENTS` into a structured autonomy plan
   - Define task decomposition, sequencing, and test strategy
   - Gate: agent (architect reviews plan quality)

2. **Test Builder**
   - Design tests from the plan's test strategy
   - Write test specs and acceptance criteria
   - Gate: agent (architect reviews test coverage)

3. **Builder**
   - Implement the plan, running tests as you go
   - Report any deviation from the plan
   - Gate: agent (auto-test — all tests must pass)

4. **Architect Review**
   - Compare implementation against plan
   - Verify entropy stayed bounded
   - Produce final alignment summary
   - Gate: human (final approval)

## Rules

- Do NOT use this pipeline for kernel or governance changes — use `/deliver-full`
- If during execution you discover the work requires governance review, STOP and suggest switching to `/deliver-full`
- Monitor entropy throughout — checkpoint if entering yellow zone

## Arguments

Goal: $ARGUMENTS

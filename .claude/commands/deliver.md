---
description: "Lean pipeline for pre-approved, additive work"
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
   - Gate: Agent(subagent_type=architect) — architect reviews plan quality (trigger: context-isolation)

2. **Test Builder**
   - Design tests from the plan's test strategy
   - Write test specs and acceptance criteria
   - Gate: Agent(subagent_type=architect) — architect reviews test coverage (trigger: review-independence)

3. **Builder**
   - Implement the plan, running tests as you go
   - Report any deviation from the plan
   - Gate: agent (auto-test — all tests must pass)

4. **Architect Review**
   - Compare implementation against plan
   - Verify entropy stayed bounded
   - Produce final alignment summary
   - Gate: human (final approval)

## Orchestration Constraints

Policy source: `subagent-router` skill (trigger definitions and routing table).

- Gate 1 (Planner gate — architect reviews plan quality): Agent(subagent_type=architect) — trigger: context-isolation
- Gate 2 (Test Builder gate — architect reviews test coverage): Agent(subagent_type=architect) — trigger: review-independence
- Gate 3 (Architect Review stage): `Agent(subagent_type=architect)` — trigger: review-independence
- No review stage shall execute inline with the stage it reviews
- These prose mandates are necessary but not sufficient: runtime enforcement will be added in Phase 5 (P5-001, D43).

## Rules

- Do NOT use this pipeline for kernel or governance changes — use `/deliver-full`
- If during execution you discover the work requires governance review, STOP and suggest switching to `/deliver-full`
- Monitor entropy throughout — checkpoint if entering yellow zone

## Arguments

Goal: $ARGUMENTS

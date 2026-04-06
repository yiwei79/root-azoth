---
description: "Full pipeline with governance gates — for kernel, governance, or breaking changes"
---

# /deliver-full $ARGUMENTS

Full delivery pipeline with governance review. Use when the work changes
governance, kernel, or operating rules.

## Pipeline (D21)

```
Goal Clarification → Architect → Governance Review → Planner → Test Builder → Builder → Architect Review
```

## Orchestration Constraints

- Policy source: `subagent-router` skill (trigger definitions and routing table)
- Each agent gate (stages 3–6) mandates a fresh-context subagent invocation via `Agent(subagent_type=...)`
- The Architect (orchestrator) remains the final speaker for all human gates
- Subagents return findings; Architect disposes and escalates to human if needed
- No review stage shall execute inline with the stage it reviews
- These prose mandates are necessary but not sufficient: runtime enforcement will be added in Phase 5 (P5-001, D43). Residual risk: an orchestrator that ignores this text can still run stages inline.
- Isolation constraint applies to agent-gated review stages (3–6). Architect's own internal sub-invocations during Stage 2 (e.g. context-map, research-orchestrator) are governed by the architect archetype contract separately.

1. **Goal Clarification**
   - Parse intent, classify complexity, compose pipeline
   - Gate: human (approve pipeline)

2. **Architect**
   - Investigate (explore codebase, research if needed)
   - Produce architecture brief: target model, boundaries, risks, success criteria
   - Gate: human (approve design)

3. **Governance Review**
   - Agent(subagent_type=reviewer): Critique the brief for governance gaps, entropy leakage, HITL misplacement — trigger: review-independence
   - Produce findings and recommended corrections
   - Gate: agent (architect receives reviewer findings; if findings touch kernel, governance changes, or M2→M1 promotion, escalate to human — present compressed decision request per Trust Contract §2)

4. **Planner**
   - Agent(subagent_type=planner): Convert approved design into deterministic tasks — trigger: context-isolation
   - Define test strategy (mandatory)
   - Gate: agent (architect reviews plan quality and completeness)

5. **Test Builder**
   - Agent(subagent_type=builder): Design tests from plan's test strategy — trigger: review-independence
   - Write test specs and acceptance criteria
   - Gate: agent (architect reviews test coverage against plan)

6. **Builder**
   - Agent(subagent_type=builder): Implement against the approved plan — trigger: context-budget
   - Run tests, report deviations
   - Gate: agent (auto-test pass — all tests must pass before hand-off to architect review)

7. **Architect Review**
   - Compare implementation vs approved design
   - Final alignment summary
   - Gate: human (final approval)
   - After human final approval passes: run `python scripts/version-bump.py --patch`
   - Log: `Stage 7 ✓ version bumped X → Y`

## Rules

- Use this pipeline whenever the session can alter governance, promotion flow, or kernel
- The governance review stage (step 3) is NOT optional
- If human approval is missing or ambiguous at any human gate, STOP

## Arguments

Goal: $ARGUMENTS

---
mode: agent
description: Full pipeline with governance gates — for kernel, governance, or breaking
  changes
---

# /deliver-full $ARGUMENTS

Full delivery pipeline with governance review. Use when the work changes
governance, kernel, or operating rules.

## Stage 0 — Pipeline gate (mechanical)

**Before any other Write/Edit** to the repo in this run: `Read` `.azoth/scope-gate.json`.
If `delivery_pipeline` is `governed` **or** `target_layer` is `M1`, `Write`
`.azoth/pipeline-gate.json` so the PreToolUse hook allows subsequent edits:

```json
{
  "session_id": "<must match scope-gate.session_id>",
  "pipeline": "deliver-full",
  "approved": true,
  "expires_at": "<same as scope-gate.expires_at>",
  "opened_at": "<ISO 8601 now, +00:00>"
}
```

If the scope is **not** governed (standard additive work without M1 backlog), **omit** this
file unless you already use it from a prior step. If `pipeline-gate.json` already exists with
the same `session_id`, update `opened_at` only.

This stage wires **Claude Code’s delivery pipeline** to mechanical enforcement: governed
work cannot bypass `/deliver-full` (or `/auto` / `/deliver`) and inline-only implementation.

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

## Spawn invocation (BL-011)

For stages **3–6**, invoke subagents with **only** the YAML spawn template in
`skills/subagent-router/SKILL.md` §Spawn Prompt Contract (≤ ~20 lines). Stage semantics,
canonical D21 `role_hint` strings, and gate wording live in **§Stage briefs: deliver-full**
in that skill — load via `Read` after spawn; do not paste them into the spawn body.

| Step | Stage | `subagent_type` | `stage_id` | `trigger` |
|------|-------|-----------------|------------|-----------|
| 3 | Governance Review | reviewer | `deliver_full_s3` | review-independence |
| 4 | Planner | planner | `deliver_full_s4` | context-isolation |
| 5 | Test Builder | builder | `deliver_full_s5` | review-independence |
| 6 | Builder | builder | `deliver_full_s6` | context-budget |

1. **Goal Clarification**
   - Parse intent, classify complexity, compose pipeline
   - Gate: human (approve pipeline)

2. **Architect**
   - Investigate (explore codebase, research if needed)
   - Produce architecture brief: target model, boundaries, risks, success criteria
   - Gate: human (approve design)

3. **Governance Review** — spawn per table; findings and recommended corrections per §Stage briefs: deliver-full
   - Gate: agent (architect receives reviewer findings; if findings touch kernel, governance changes, or M2→M1 promotion, escalate to human — present compressed decision request per Trust Contract §2)

4. **Planner** — spawn per table; test strategy mandatory per §Stage briefs: deliver-full
   - Gate: agent (architect reviews plan quality and completeness)

5. **Test Builder** — spawn per table
   - Gate: agent (architect reviews test coverage against plan)

6. **Builder** — spawn per table
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

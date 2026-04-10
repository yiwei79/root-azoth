---
description: Full pipeline with governance gates — for kernel, governance, or breaking
  changes
---

# /deliver-full $ARGUMENTS

Full delivery pipeline with governance review. Use when the work changes
governance, kernel, or operating rules.

## Stage 0 — Pipeline gate (mechanical)

Apply the canonical procedure in `docs/GATE_PROTOCOL.md`. If this command writes
`.azoth/pipeline-gate.json`, set `"pipeline": "deliver-full"`.

## Typed stage summary (BL-012)

After each pipeline step completes (architect through builder), emit YAML per
`skills/subagent-router/SKILL.md` §Stage summary output and `pipelines/stage-summary.schema.yaml`
with `pipeline: deliver-full` and a stable `stage_id` (see `subagent-router` §Stage briefs:
deliver-full). The orchestrator forwards this summary to the next stage; optional markdown
alignment (`alignment-sync`) remains human-facing only.

## Pipeline (D21)

```
Goal Clarification → Architect → Governance Review → Planner → Test Builder → Builder → Architect Review
```

## Orchestration Constraints

- Policy source: `subagent-router` skill (trigger definitions and routing table)
- Each agent gate (stages 3–6) mandates a fresh-context subagent invocation via `Agent(subagent_type=...)`
- The Architect (orchestrator) remains the final speaker for all human gates
- Subagents return findings; Architect disposes and escalates to human if needed
- **Orchestrator handoff:** Before each downstream `Agent`/`Task`, attach `inputs.prior_stage_summaries` with verbatim typed YAML from upstream stages (`subagent-router` §Orchestrator forward payload). Evaluator and review stages are not valid without this.
- **Review escalation:** If Governance Review returns request-changes, CRITICAL/blocking findings, `entropy: RED`, or `status: needs-input`, **STOP** — do not run Planner until the human approves continuation (same human-gate pattern as `/auto` Execution §5).
- **Eval / swarm routing:** When the pipeline reaches an **evaluator** stage or a **final `/eval`**
  pass after Builder / Architect Review, apply `.claude/commands/eval.md` triggers **E1–E6**
  (governed scope and multi-stage summaries often satisfy **E2**/**E3**). If any trigger
  fires → **`/eval-swarm`** semantics (`/auto` Execution §6). Governed work must not skip
  this check before declaring delivery complete.
- No review stage shall execute inline with the stage it reviews
- These prose mandates are necessary but not sufficient: runtime enforcement will be added in Phase 5 (P5-001, D43). Residual risk: an orchestrator that ignores this text can still run stages inline.
- Isolation constraint applies to agent-gated review stages (3–6). Architect's own internal sub-invocations during Stage 2 (e.g. context-map, research-orchestrator) are governed by the architect archetype contract separately.

## Spawn invocation (BL-011)

For stages **3–6**, invoke subagents with **only** the YAML spawn template in
`skills/subagent-router/SKILL.md` §Spawn Prompt Contract (≤ ~20 lines). Stage semantics,
canonical D21 `role_hint` strings, BL-012 handoffs, and gate wording live in that skill —
load **§Stage briefs: deliver-full** via `Read` after spawn; do not paste them into the
spawn body.

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

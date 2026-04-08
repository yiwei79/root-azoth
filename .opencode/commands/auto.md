---
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

Invoke the `auto-router` skill.

## Subagent Assignment

Apply the `subagent-router` skill to each composed stage. For each stage:
1. Evaluate the four triggers in priority order: review-independence > context-isolation > context-budget > parallel-execution
2. Assign `subagent_type` from the routing table
3. Record the trigger rationale alongside the stage

Add `subagent_type` and `trigger` columns to the composed pipeline table in the Declaration.

## Spawn invocation (BL-011)

During **Execution**, each stage that invokes a subagent MUST use the YAML spawn template
in `skills/subagent-router/SKILL.md` §Spawn Prompt Contract (≤ ~20 lines). Use
`pipeline: auto`, a stable `stage_id` per row (see §Stage briefs: auto), and `Read` of
`skills/subagent-router/SKILL.md` / archetype files after spawn — do not paste the
composed pipeline table or CLAUDE.md into the subagent spawn.

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

Approve pipeline composition + subagent assignments? [yes / adjust / different-pipeline]
```

## Execution

After human approval of the Declaration:

1. **Pipeline gate (mechanical):** Before the first Write/Edit in this execution phase,
   `Read` `.azoth/scope-gate.json`. If `delivery_pipeline` is `governed` **or**
   `target_layer` is `M1`, `Write` `.azoth/pipeline-gate.json` with `"pipeline": "auto"`
   (same `session_id`, `approved`, `expires_at`, `opened_at` shape as `/deliver-full` Stage 0).
2. Execute each stage in sequence — respect gate types (human gates stop and wait),
   monitor entropy, produce alignment summary at each stage boundary.
3. **Typed stage summary (BL-012):** When a stage completes (before the next stage consumes
   context), the subagent MUST emit a YAML document that conforms to
   `pipelines/stage-summary.schema.yaml` (`stage_id` must match the spawn for that stage).
   The orchestrator passes that document forward as the machine-readable handoff. Optional
   markdown alignment (`alignment-sync` skill) is for human pull-review only — it does not
   replace the typed summary for inter-stage context.
4. **Orchestrator handoff (mandatory):** Before spawning the **next** subagent (`Task` /
   `Agent`), the orchestrator MUST attach every **upstream typed stage summary** the next
   stage needs under `inputs.prior_stage_summaries` per `skills/subagent-router/SKILL.md`
   §Orchestrator forward payload. **Evaluators** MUST receive the full YAML for the stage
   they evaluate (e.g. planner). Subagents do not share chat context; omitting this payload
   is an orchestrator error and invalidates the evaluator gate.
5. **Review disposition & human escalation:** After **reviewer** (or any audit stage that
   critiques upstream work), parse the return for disposition. **STOP** and **do not** spawn
   planner, evaluator, or builder for the rest of the composed pipeline until the human
   explicitly continues if **any** of these hold:
   - Explicit **request-changes** / **request changes** / **BLOCKED** / **blocked**
   - Any **CRITICAL** finding that requires scope or design revision
   - Typed summary has `status: needs-input` or `entropy: RED`
   Present a short **Human gate — review** card: findings, severity, and options (revise
   design / adjust scope / abort). Wait for a human signal such as **proceed**,
   **revise-then-continue**, or **abort** before continuing. **Do not** treat “pipeline
   started” as overriding a failed review gate.

6. **Evaluator stage — `/eval` routing (E1–E6):** When the **composed pipeline** includes an
   **evaluator** stage (or the orchestrator runs a **final quality gate** equivalent to
   `/eval` before declaring success), **before** spawning evaluator work:
   - `Read` `.claude/commands/eval.md` and evaluate triggers **E1–E6** using the active
     scope (`.azoth/scope-gate.json`), pipeline row count / branch count, file-change
     footprint, `prior_stage_summaries`, and any reviewer disposition.
   - If **any** trigger fires → follow **`/eval-swarm`** (`.claude/commands/eval-swarm.md`)
     and `.claude/workflows/enterprise/e2e-swarm-eval-loop.md`: **N** parallel
     `Task(subagent_type=evaluator, readonly=true)` with **`threshold: 0.9`**, one orchestrator
     message per wave — **not** a single collapsed 0.85 eval in the orchestrator thread.
   - If **none** fire → a **single** `Task(evaluator)` at **0.85** is valid.
   - If triggers are borderline, **prefer escalation** (see `/eval` § ambiguity).
   - This applies whether the caller is human or agent; skipping the table is an
     orchestrator error for evaluator-sized work.

## Arguments

Goal: $ARGUMENTS

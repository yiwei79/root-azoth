---
mode: agent
description: Auto-compose and execute a pipeline based on goal classification
agent: orchestrator
---

# /auto $ARGUMENTS

The default pipeline. Classify the goal and compose the optimal pipeline.

## Preconditions

<!-- P1-016: Antigravity compliance -->
- Verify `.azoth/scope-gate.json` exists and is approved before write work.
- If `target_layer: M1` or governance surface detected, redirect to `/deliver-full`.
- See `docs/antigravity-compliance-matrix.md` for platform parity gaps.

## Stage 0: Goal Classification

Classify `$ARGUMENTS` along four dimensions:

```yaml
classification:
  scope: kernel | skills | agents | pipelines | docs | mixed
  risk: governance-change | breaking-change | additive | cosmetic
  complexity: simple | medium | complex
  knowledge: known-pattern | needs-research | novel | instruction-refinement
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

During **Execution**, each stage that invokes a subagent MUST use the minimal YAML
contract in `skills/subagent-router/SKILL.md` §§Spawn Prompt Contract, Stage summary output,
and Orchestrator forward payload. Use `pipeline: auto`, a stable `stage_id` per row (see
§Stage briefs: auto), and keep the spawn body to the compact YAML plus required handoff data.

## Declaration

Present the composed pipeline to human as a **fused Declaration** combining scope card
and pipeline composition in a single approval:

```
## Auto-Pipeline — {goal}

**Classification**: {scope} / {risk} / {complexity} / {knowledge}
**Scope**: session: {session_id} | TTL: 2h | layer: {target_layer} | pipeline: auto

**Composed Pipeline**:
1. {stage} — {agent} — {subagent_type} — gate: {human|agent}
2. {stage} — {agent} — {subagent_type} — gate: {human|agent}
...

**Rationale**: {why this pipeline was chosen}

Approve scope + pipeline? [yes / adjust / abort]
> On approval: orchestrator writes `.azoth/scope-gate.json` and `.azoth/pipeline-gate.json`
> (governed only). No separate /next step required for /auto.
```

## Declaration Mode Selection

Before presenting the Declaration, evaluate the composed pipeline condition to choose
between the full interactive Declaration and the lightweight informational path:

**Informational Declaration** (present as a compact card, auto-proceed unless human
intervenes) — applies when **all** of the following hold:

1. `knowledge == known-pattern`
2. `risk != governance-change`
3. `scope != kernel`
4. The composed pipeline condition matches a lightweight route:
   - `scope == docs`
   - `complexity == simple AND risk == cosmetic`
   - `complexity == simple AND risk == additive`
   - `complexity == medium AND risk == additive AND knowledge == known-pattern`

> **Note**: Rule 9 (`complexity == medium AND risk == additive` without `known-pattern`)
> always uses the full Declaration because it only fires when `knowledge != known-pattern`
> (Rule 8 would have matched first otherwise). Constraint 1 above excludes it by definition.

When all conditions are met, present the Informational Declaration:

```
## Auto-Pipeline — {goal} [INFORMATIONAL]

**Classification**: {scope} / {risk} / {complexity} / known-pattern
**Scope**: session: {session_id} | TTL: 2h | layer: {target_layer} | pipeline: auto
**Composed Pipeline**: {stages}
**Rationale**: lightweight known-pattern path — auto-proceeding unless you intervene.

Type `stop` or `abort` to halt. Otherwise auto-proceeding.
```

**Proceed logic:**
- If the human's next message contains `stop`, `abort`, or `no` → halt, do not write scope-gate.json.
- If the human's next message contains `proceed`, `yes`, `ok`, or any other signal → write scope-gate.json and continue.
- If no explicit stop signal → treat as approval and continue.

**Full Declaration** (present with explicit yes/adjust/abort prompt) — all other cases,
including `risk == governance-change`, `scope == kernel`, `knowledge == needs-research`,
`knowledge == instruction-refinement`, and `default`.

**L2 evidence monitoring**: After sessions using the informational auto-proceed path,
capture any observations about missed or skipped informational cards in M3 episodes.
Run `/intake` periodically to surface adoption patterns. If agents consistently fail
to present the informational card, promote to M2 as a pattern requiring explicit
enforcement.

## Execution

After human approval of the Declaration:

1. **Post-Approval Gate-Write (fused):** After human approves the Declaration (or
   informational Declaration auto-proceeds), write gate files in this exact order:

   **Step 1 — Write `.azoth/scope-gate.json`** (always):
   ```json
   {
     "session_id": "<active session ID>",
     "goal": "<$ARGUMENTS verbatim>",
     "approved": true,
     "approved_by": "human",
     "expires_at": "<ISO 8601, UTC, now + 2 hours>",
     "backlog_id": "<matched backlog item ID or 'ad-hoc'>",
     "delivery_pipeline": "<auto | deliver | deliver-full>",
     "target_layer": "<M1 | M2 | M3 | mineral — from classification>"
   }
   ```

   **Step 2 — Conditionally write `.azoth/pipeline-gate.json`** (only if
   `delivery_pipeline == governed` OR `target_layer == M1`):
   ```json
   {
     "session_id": "<must match scope-gate.json>",
     "pipeline": "auto",
     "approved": true,
     "expires_at": "<copy from scope-gate.json>",
     "opened_at": "<ISO 8601, UTC, now>"
   }
   ```

   **Step 3 — Verify:** Run `python3 scripts/check_gates.py --session-id <session_id>`.
   Must exit 0. If exit 1: stop and surface the error.

   No separate `/next` step is required — the fused Declaration replaces it for `/auto`.
2. Execute each stage in sequence — respect gate types (human gates stop and wait),
   monitor entropy, produce alignment summary at each stage boundary.
3. **Typed stage summary (BL-012):** When a stage completes, the subagent MUST emit YAML
  that conforms to `pipelines/stage-summary.schema.yaml`; `stage_id` must match the spawn
  and the orchestrator treats that YAML as the machine-readable handoff.
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

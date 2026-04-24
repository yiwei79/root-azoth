# /auto $ARGUMENTS

The default pipeline. Classify the goal and compose the optimal pipeline.

## Preconditions

<!-- P1-016: Antigravity compliance -->
- Verify `.azoth/scope-gate.json` exists and is approved before write work.
- See `docs/antigravity-compliance-matrix.md` for platform parity gaps.

## Stage 0: Goal Classification

Stage 0 is intake plus classification. Before composing the pipeline, load the
latest context the run depends on:

1. read back relevant memory when the goal is pipeline-improvement,
   instruction-refinement, or a replay after a failed quality gate
2. inspect the latest repo-state evidence for the touched surfaces
3. include known platform/runtime constraints in the composition decision

Then classify `$ARGUMENTS` along four dimensions:

```yaml
classification:
  scope: kernel | skills | agents | pipelines | docs | mixed
  risk: governance-change | breaking-change | additive | cosmetic
  complexity: simple | medium | complex
  knowledge: known-pattern | needs-research | novel | instruction-refinement
```

## Stage 0 Assumption Checkpoint

Using the evidence loaded above, emit a Stage 0 Assumption Checkpoint before final classification, auto-router composition, and Declaration. The checkpoint is the canonical handoff from intake evidence to routing judgment.

```yaml
stage0_assumption_checkpoint:
  interpreted_goal: "<what the user is asking Azoth to accomplish>"
  inputs_and_scope_source: "<explicit inputs, current scope/gate, backlog id, or ad-hoc>"
  assumptions:
    - claim: "<assumption>"
      confidence: high|medium|low
      evidence: "<memory/repo/user evidence>"
  uncertainty_missing_facts:
    - "<unknown that could change routing or gate posture>"
  owned_surfaces:
    - "<files/modules/governed surfaces in scope>"
  out_of_scope_deferrals:
    - "<nearby work deliberately deferred>"
  classification_rationale: "<scope/risk/complexity/knowledge reasoning>"
  gate_implications: "<human, governance, freshness, or entropy gates>"
  routing_implications: "<auto-router base row plus subagent/delegation effects>"
```

Fail closed if a dimension is unclear, latest/current external facts are material,
or the request may expand into kernel/governance policy: ask one focused question,
insert official-source research, or require the relevant human gate before final
classification.

## Pipeline Composition (D23)

Invoke the `auto-router` skill. Treat the selected row as the conservative base
composition, then compose from the shared stage-family vocabulary:

- `context-recall`
- optional `discovery / evidence / research`
- `architect / design`
- `review`
- `plan`
- `execute`
- `quality gate`
- `closeout`

`/auto` remains the owning pipeline. Governed or high-risk work may cause
`/auto` to choose the heaviest internal path, but the command does not force a
redirect to `/deliver-full`.

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

Before spawning a protected downstream stage, the orchestrator MUST record the upstream
spawn and summary evidence in `.azoth/run-ledger.local.yaml`:

1. record the subagent spawn with `scripts/run_ledger.py record-spawn`
2. record the returned typed stage summary with `scripts/run_ledger.py record-summary`
3. require paired evidence with `scripts/run_ledger.py require-stage-evidence`

Evidence binds stage identity, routing metadata, dependency refs, timestamps, status, and disposition.
Missing, mismatched, blocked, or needs-input evidence is a fail-closed condition.

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
**Adaptive Controls**: discovery insertion: {enabled|not needed} | replay threshold: {2|3}

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

   If the routed Codex input already includes `session_id=<id>`, treat that id as
   authoritative for this declaration. When `.azoth/session-gate.json` is active for the
   same goal, the scope bootstrap must reuse that exploratory `session_id` instead of
   minting a new one.

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

   **Step 2 — Conditionally write `.azoth/pipeline-gate.json`** (only if the scope
   is governed via `governance_mode == governed`, legacy
   `delivery_pipeline == governed`, fused `/auto` selection
   `delivery_pipeline == deliver-full`, or `target_layer == M1`):
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
  and the orchestrator treats that YAML as the machine-readable handoff. The orchestrator
  records the summary in the run ledger before any protected downstream spawn.
4. **Orchestrator handoff (mandatory):** Before spawning the **next** subagent (`Task` /
   `Agent`), the orchestrator MUST attach every **upstream typed stage summary** the next
   stage needs under `inputs.prior_stage_summaries` per `skills/subagent-router/SKILL.md`
   §Orchestrator forward payload. **Evaluators** MUST receive the full YAML for the stage
   they evaluate (e.g. planner). Subagents do not share chat context; omitting this payload
   is an orchestrator error and invalidates the evaluator gate. The run ledger must contain
   matching `stage_spawns` and `stage_summaries` evidence for each forwarded dependency.
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
   When the human does approve continuation on a governed run, consume that approval in the
   same run through `scripts/run_ledger.py` by promoting the next executable stage from the
   paused human-gate checkpoint. Another declaration/status card by itself is not valid
   downstream progress.
   When the finding is a valid revise-and-continue case, rewrite the active run queue
   fail-closed so the approved upstream revision stage is inserted ahead of the current
   gate-owning review stage. If lineage proof is missing, ambiguous, or already rewritten,
   stop and escalate instead of narrating progress.
6. **Self-iterative quality (bounded replay):** Route failed findings to the lowest
   legitimate upstream corrective stage instead of improvising inline revisions:
   - architecture / scope / governance / contract → replay `architect`
   - planning / test-strategy / handoff completeness → replay `planner`
   - implementation / failing acceptance → replay `builder`
   - evidence insufficiency → insert discovery / evidence before replaying design or planning

   Default replay thresholds are `2` for non-governed runs and `3` for governed or
   high-stakes runs. When the threshold is exhausted, stop replay and present a
   recomposition decision rather than continuing an ad hoc loop.

7. **Evaluator stage — `/eval` routing (E1–E6):** When the **composed pipeline** includes an
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

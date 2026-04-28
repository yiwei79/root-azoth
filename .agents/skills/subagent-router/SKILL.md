---
name: subagent-router
description: |
  Assign `subagent_type` and isolation triggers to `/auto`, `/deliver`, and `/deliver-full`
  stages; defines the spawn-prompt contract (BL-011) and forward payload for typed summaries.
---

# Subagent Router

Assign subagent_type and isolation rationale to each pipeline stage based on
four canonical triggers. This replaces per-pipeline hardcoded subagent mandates
with a single, auditable routing policy.

## Overview

Every agent-gated pipeline stage must be executed by a fresh-context subagent.
The trigger determines which subagent_type to invoke.

```
Stage → Evaluate Triggers (priority order) → Assign subagent_type → Record rationale
```

## Trigger Definitions and Priority Order

Triggers are evaluated in the following priority order. The first matching
trigger wins.

```
Priority 1: review-independence
Priority 2: context-isolation
Priority 3: context-budget
Priority 4: parallel-execution
```

### Trigger 1 — review-independence (highest priority)

**Condition**: The stage reviews, critiques, or evaluates the output of another stage.

**Rule**: A stage that reviews work must never execute in the same context as the
stage that produced the work being reviewed. Shared context allows the prior
stage's reasoning to contaminate the review.

**Assigned subagent_type**: `reviewer` (for governance/quality review stages)
or `architect` (for plan-quality and test-coverage review gates).

### Trigger 2 — context-isolation

**Condition**: The stage must begin with a clean working memory — no accumulated
context from prior stages that could bias its output.

**Rule**: Investigation, planning, and architecture stages require isolation so that
their findings are derived from first-principles analysis, not inherited assumptions.

**Assigned subagent_type**: `planner` (for planning stages); `architect` (for
investigation or architecture stages).

### Trigger 3 — context-budget

**Condition**: The accumulated context from prior stages would exceed a safe working
budget for the current stage (large codebases, multi-file implementations).

**Rule**: Delegate to a builder subagent to receive a clean context budget.

**Assigned subagent_type**: `builder`

### Trigger 4 — parallel-execution (lowest priority)

**Condition**: The stage can execute concurrently with sibling stages that share no
output dependencies.

**Rule**: Each parallel branch requires its own subagent to avoid serialization and
context bleed between branches.

**Assigned subagent_type**: `builder`

Note: `researcher` is NOT assigned by this router. The researcher subagent_type is
reserved for external knowledge gathering and is governed by the research-orchestrator
archetype contract, not by this routing policy.

## Routing Table


| Trigger             | subagent_type        | Notes                                                  |
| ------------------- | -------------------- | ------------------------------------------------------ |
| review-independence | reviewer / architect | architect when reviewing plan or test quality          |
| context-isolation   | planner / architect  | architect for investigation; planner for task planning |
| context-budget      | builder              | —                                                      |
| parallel-execution  | builder              | NOT researcher                                         |


## Exclusion Clause

Architect's own internal sub-invocations during Stage 2 (e.g. context-map,
research-orchestrator calls within an investigation phase) are out-of-scope for this router.
Those are governed by the architect archetype contract separately.

However, the governed **Stage 2 architect-design stage itself is in scope** for this router.
When a pipeline requires `deliver_full_s2_architect`, the orchestrator must spawn the
architect next or fail closed before any inline architect brief is produced.

This router applies only to inter-stage delegation between pipeline stages.

## Spawn Prompt Contract (BL-011)

**Problem:** Passing a 100–300 line paste of pipeline prose into every `Agent()` or
`Task()` call duplicates orchestrator context into the subagent and burns tokens on
every spawn.

**Rule:** The subagent message body is **only** a short YAML block (≤ ~20 lines) plus
optional `Read` targets. Role behavior, routing tables, and stage briefs live in
`skills/subagent-router/SKILL.md` (this file) and `agents/**/*.agent.md`; load them
**after** spawn with `Read` if needed — do not embed them in the spawn.

### Required template

```yaml
pipeline: autonomous-auto | deliver-full | deliver | auto
stage_id: <string>   # e.g. deliver_full_s3 — see §Stage briefs
subagent_type: <architect|planner|builder|reviewer|evaluator|...>
trigger: <review-independence|context-isolation|context-budget|parallel-execution>
model_tier: premium | standard | fast  # optional — set by orchestrator, resolved by router
execution_budget:               # optional — omit for leaf-only execution
  child_fanout_cap: <int>       # only for designated queen agents
  depth_remaining: <int>        # decrement before spawning children
goal: |
  <one paragraph: what the user asked for>
inputs:
  artifacts: []  # paths or descriptions of upstream outputs to read first
```

Optional: one line `role_hint:` repeating the canonical D21 audit string for that stage
(see §Stage briefs) so logs stay grep-friendly.

**`model_tier` resolution**: the orchestrator sets `model_tier` based on risk and complexity
(see orchestrator agent `§ Model Tiering`). The subagent-router resolves tier to a concrete
model identifier at spawn time. If omitted, defaults to `standard`.

## Codex Model Selector Contract (T-025)

For Codex-hosted spawns, `model_tier` is portable intent, not the final runtime
payload. Before spawning a Codex subagent, the orchestrator must resolve the tier
through `scripts/codex_model_selector.py`, using `.azoth/codex-model-selector-policy.yaml`
as policy input and appending selector evidence to
`.azoth/codex-model-selector-traces.local.jsonl`.

The resolved spawn payload must include explicit runtime fields:

```yaml
model_tier: premium | standard | fast
model: <resolved-model>
reasoning_effort: <low|medium|high|xhigh>
```

Do not omit `model` or `reasoning_effort` on Codex subagent spawns. Parent `xhigh` reasoning must not leak into leaf workers by omission; `xhigh` is allowed only when
the selector policy, an explicit operator override, or evaluator-backed escalation
chooses it for that stage.

**`execution_budget` resolution**: if omitted, the spawned agent is leaf-only. Only
`orchestrator`, `research-orchestrator`, and `architect` may receive a non-leaf budget.
The root orchestrator owns the global execution budget and should reserve capacity for queen
children instead of saturating all slots with direct leaf tasks.

### Orchestrator forward payload (mandatory)

BL-011 limits **role metadata** in the spawn (goal, `stage_id`, triggers) — it does **not**
mean downstream stages receive **zero** context from upstream work.

- **The orchestrator** (main chat in Cursor; Architect in Claude Code) **must** attach the
**verbatim typed stage summary YAML** from each dependency stage before spawning the next
subagent. Put it under `inputs.prior_stage_summaries` in the same spawn YAML, for example:

```yaml
inputs:
  prior_stage_summaries:
    auto_s3_planner: |
      stage_summary_version: 1
      pipeline: auto
      stage_id: auto_s3_planner
      ...
```

- **Evaluator**, **builder**, and any stage that **judges** prior work **must** receive the
full summary YAML for the stage being evaluated (not a prose summary of the summary).
- If the orchestrator skips this forward, evaluators correctly report **CONCERNS** — missing
handoff is an **orchestrator failure**, not an evaluator failure.

### Before / after (illustrative)


|                           | Approximate subagent spawn body                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------------------ |
| **Before (anti-pattern)** | 1.5–3K tokens: full pipeline markdown + stage bullets + CLAUDE.md excerpts copied into the spawn |
| **After (contract)**      | 120–400 tokens: YAML block above + `Read` of this skill + archetype file                         |


**After** is the only approved pattern for `/auto`, `/autonomous-auto`, `/deliver`, and
`/deliver-full` execution.

### Static-prefix-friendly ordering (P1-011)

Keep spawn YAML keys in this order whenever practical:

1. `pipeline`
2. `stage_id`
3. `subagent_type`
4. `trigger`
5. optional `role_hint`
6. `goal`
7. `inputs`

Put high-variance text (`goal`, large artifact lists, `prior_stage_summaries`) later so the
prefix stays stable for provider-side prompt caching.

## Stage summary output (BL-012)

When the stage finishes (before returning control to the orchestrator), emit a **YAML**
document that validates against `pipelines/stage-summary.schema.yaml`:

- Set `pipeline` to `auto`, `autonomous-auto`, `deliver`, or `deliver-full` to match the active command.
- Set `stage_id` to the same value used in the spawn template for this stage.
- Set `stage_kind` to one of `research` | `build` | `eval` | `audit` (semantic bucket for the handoff).
- Keep `done`, `decisions`, and `open` within schema array limits (max 5 bullets each).

The orchestrator passes this file forward; do not rely on long prose alone at stage boundaries.

When the stage is part of a bounded replay / revise-and-continue loop, also include:

- `replay_iteration`
- `replay_target_stage`
- `finding_class`
- `threshold_limit`
- `lineage_artifacts`

## Stage briefs: deliver-full

Use `stage_id` with `pipeline: deliver-full`.


| stage_id          | subagent_type | trigger             | Canonical `role_hint` (D21 audit)                                                                                                          |
| ----------------- | ------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `deliver_full_s2_architect` | architect | context-isolation | `Agent(subagent_type=architect): Produce the governed design brief as a fresh-context stage — trigger: context-isolation` |
| `deliver_full_s3` | reviewer      | review-independence | `Agent(subagent_type=reviewer): Critique the brief for governance gaps, entropy leakage, HITL misplacement — trigger: review-independence` |
| `deliver_full_s4` | planner       | context-isolation   | `Agent(subagent_type=planner): Convert approved design into deterministic tasks — trigger: context-isolation`                              |
| `deliver_full_s5` | builder       | review-independence | `Agent(subagent_type=builder): Design tests from plan's test strategy — trigger: review-independence`                                      |
| `deliver_full_s6` | builder       | context-budget      | `Agent(subagent_type=builder): Implement against the approved plan — trigger: context-budget`                                              |


**Stage 3 — Governance Review:** Gate: agent (orchestrator receives reviewer findings; if findings touch kernel, governance changes, or M2→M1 promotion, escalate to human — compressed decision request per Trust Contract §2).

**Stage 4 — Planner:** Define test strategy (mandatory). Gate: agent (orchestrator reviews plan quality and completeness).

**Stage 5 — Test Builder:** Write test specs and acceptance criteria. Gate: agent (orchestrator reviews test coverage against plan).

**Stage 6 — Builder:** Run tests; report deviations. Gate: agent (auto-test pass — all tests must pass before hand-off to architect review).

## Stage briefs: deliver

Use `pipeline: deliver` and `stage_id` from this table.


| stage_id     | subagent_type | trigger             | Canonical `role_hint` (D21 audit)                                                                                         |
| ------------ | ------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `deliver_g1` | architect     | context-isolation   | Planner gate — `Agent(subagent_type=architect)` reviews plan quality (trigger: context-isolation)                         |
| `deliver_g2` | architect     | review-independence | Test Builder gate — `Agent(subagent_type=architect)` reviews test coverage (trigger: review-independence)                 |
| `deliver_g3` | architect     | review-independence | Architect Review stage — `Gate 3 (Architect Review stage): Agent(subagent_type=architect)` — trigger: review-independence |


## Stage briefs: auto

For `pipeline: auto`, set `stage_id` to a stable identifier per composed stage (e.g.
`auto_s1_architect`, `auto_s2_reviewer`) and fill `subagent_type` + `trigger` from the
routing table above. Full composition rules remain in `skills/auto-router/SKILL.md` and
`pipelines/auto.pipeline.yaml`.

## Stage briefs: autonomous-auto

For `pipeline: autonomous-auto`, use the same stage-family routing as `auto`, with
stable loop-aware stage ids (for example `autonomous_auto_s1_architect`,
`autonomous_auto_s2_reviewer`, or `loop_governor_s5_planner`). The active loop budget and
`approval_basis` are scope inputs; they do not replace BL-011 spawn payloads or BL-012
typed summaries.

### Agent Crafter meta-loop (governed M1)

When the goal involves **Agent Crafter** or meta-agent definition work (`agents/tier3-meta/agent-crafter.agent.md`):

- Use **fresh-context** spawns for **evaluator**, **prompt-engineer**, **reviewer**, and **builder** stages per the trigger table; do not collapse these into the orchestrator thread when `**Task`** / `Agent` is available.
- The orchestrator **must** attach **prior_stage_summaries** (BL-012 YAML) at every handoff — especially into **evaluator** and **reviewer**.
- For **governed** M1 scopes, treat **governance-review** as **default-on** after crafter integration; a **human-declared waiver** in the `/auto` Declaration is the only supported skip, and should be mirrored in alignment notes.

### L2 evidence → prompt-engineer (P6-002)

When the human or orchestrator runs the **L2 refinement** branch, **do not** paste evaluator/reviewer transcripts into the prompt-engineer spawn. Append a typed record to `.azoth/memory/l2-refinement-evidence.jsonl` using **`scripts/l2_evidence_append.py`** (gated), then spawn **prompt-engineer** with **review-independence** (fresh context) and `Read` of the JSONL tail (or session-filtered lines) plus `target_surfaces` from the record.

## Cursor Note

Cursor uses `Task` instead of Claude Code `Agent()`. The main chat remains the
orchestrator, each isolated stage is a separate `Task` with the same `subagent_type`
this router assigns, and downstream spawns still need verbatim `prior_stage_summaries`.
If reviewer output returns request-changes, blocked, CRITICAL findings, `entropy: RED`,
or `status: needs-input`, stop until the human explicitly continues.

## Evaluator Note

DYNAMIC-FULL-AUTO+ and normal delivery pipelines use the same evaluator escalation rule:
compute **E1-E6** from `.claude/commands/eval.md` at evaluator boundaries, then choose
`/eval-swarm` versus a single evaluator pass from that result.

## When to Use

- **Pipeline composition** (`/auto` Subagent Assignment step) — apply the routing
table to each composed stage and record subagent_type + trigger rationale
- **Pipeline authoring** — when adding a new stage to any pipeline, consult this
skill to determine the correct subagent_type
- **Governance review** — verify that each agent-gated stage has a trigger citation

D21 remains the architecture anchor for the isolation rules in this router.

---
description: Governance quality gate — evaluate artifacts; auto-escalates to swarm
  eval when warranted
agent: orchestrator
---

# /eval $ARGUMENTS

Apply agentic-eval to the specified artifacts or current session output.

**Intelligent routing:** Before treating this as a **single** baseline review (PASS **≥ 0.85**), assess **workflow + work content** below. If **any escalation trigger** fires, you **must** follow **`/eval-swarm`** semantics (threshold **0.90**, isolated parallel **`Task(evaluator)`** per wave, minimal prompts) — whether the caller is a **human** or an **agent orchestrating a pipeline**. Do not substitute a lone inline 0.85 pass for a swarm-sized problem. If you **decline** escalation, state **which triggers fired** and **why** a baseline `/eval` is still sufficient (short audit line).

## When `/eval` escalates to swarm eval (`/eval-swarm`)

Evaluate this list from the **current goal, scope card, pipeline preset, and artifacts** (including `$ARGUMENTS` and session churn):

| # | Trigger | Rationale |
|---|---------|-----------|
| E1 | **≥ 2 independent deliverables** or branches to judge (e.g. multiple backlog slices, parallel file groups, or separate acceptance criteria) | Parallel work needs **parallel isolated evaluators**; one thread inherits author bias. |
| E2 | **Composed pipeline** (`/auto`, `/dynamic-full-auto`, `/deliver`, `/deliver-full`) and this is the **evaluator stage** after **multi-file**, **governance-touching**, or **cross-layer** changes | Same as E1; aligns with **review-independence** (`skills/subagent-router/SKILL.md`). |
| E3 | Active scope has **`governance_mode: governed`**, legacy **`delivery_pipeline: governed`**, fused `/auto` **`delivery_pipeline: deliver-full`**, and/or **`target_layer: M1`** | Higher stakes; mechanical gates expect **strict** quality. |
| E4 | **Entropy / blast radius** high for this session (e.g. approaches or exceeds **Trust Contract** file ceiling, or touches **kernel templates**, **commands**, **skills** deploy paths) | Drift risk warrants **0.90** + isolated passes. |
| E5 | **Prior** review or eval on the same deliverable returned **CONDITIONAL** or **FAIL**, or **reviewer request-changes** is open | Re-check with **fresh** evaluators; prefer swarm wave over repeating inline critique. |
| E6 | **Explicit human or scope signal** (“parallel”, “swarm”, multiple **prior_stage_summaries**, or stacked backlog IDs in the goal) | Intent is already multi-branch. |

**Rule:** If **any** of **E1–E6** is **true** → run **`/eval-swarm`** (see `.claude/commands/eval-swarm.md` + `.claude/workflows/enterprise/e2e-swarm-eval-loop.md`). If **none** are true → a **single** evaluator pass at **0.85** is appropriate.
If `.claude/commands/` is not present in your install, use the equivalent prompt under `.github/prompts/` (or your platform-specific mirror).

**Orchestrator (agents):** When the composed pipeline reaches an evaluation step, **compute triggers from the table** using the same inputs the human would see (scope-gate, pipeline table, file list, prior stage summaries). If escalated, spawn **one message** with **N** parallel `Task` evaluators (`subagent_type: evaluator`, `readonly: true`, `threshold: 0.9`) per independent branch — **not** one collapsed eval in the orchestrator thread. If not escalated, a **single** `Task(evaluator)` (or equivalent) at **0.85** is valid.

**Ambiguity:** If unsure whether **E1** or **E4** applies, **prefer escalation** — false positives cost extra compute; false negatives leak bias.

**Consumer reference:** `skills/dynamic-full-auto/SKILL.md` (PRE_DELIVERY_EVAL / Wave C) uses this same E1–E6 table for orchestrator decisions before writes; normative text stays here — do not fork trigger definitions into other files.

## Evaluation Criteria

1. Architecture alignment — decisions respect all decisions in docs/DECISIONS_INDEX.md
2. Kernel integrity — no unauthorized kernel changes
3. Governance compliance — HITL gates respected, promotion rules followed
4. Test coverage — new functionality has tests
5. Entropy bounds — changes stay within Trust Contract limits
6. Anti-slop — output adds real value, not filler

## Process

1. Identify artifacts to evaluate:
   - If `$ARGUMENTS` specifies files: evaluate those
   - If `$ARGUMENTS` is empty: evaluate this session's output

2. For each artifact, score against criteria:
   ```
   - artifact:
   - strengths:
   - gaps:
   - boundary risk:
   - entropy or drift:
   - human decision needed:
   - recommended action:
   ```

3. Produce overall assessment (when using 0.0–1.0 rubric weights, align with **evaluator** agent):
   - **PASS:** overall **≥ 0.85** and no dimension below **0.5**, proceed
   - **CONDITIONAL:** overall **≥ 0.70 and < 0.85** (or pass line met but max one dimension below 0.5 per evaluator protocol), proceed with noted caveats
   - **FAIL:** overall **< 0.70** or **2+** dimensions below 0.5, address before proceeding

Manual override: humans may still invoke **`/eval-swarm`** directly when the table above did not fire but they want the **0.90** bar.

## Rules

- If governance, HITL placement, or ownership boundaries are unclear, flag them
- Be specific about gaps — "needs improvement" is not actionable
- Score honestly — passing everything defeats the purpose

## L2 follow-on (optional, P6-002)

`/eval` stays **read-only** for repo files. If the human wants delivery evidence preserved for a later **prompt-engineer** pass, map this command’s structured output to an L2 evidence record (`skills/agentic-eval/SKILL.md` — L2 mapping) and append with `python3 scripts/l2_evidence_append.py --session-id <active scope session_id>` — only when scope (and pipeline, if M1/governed) gates are valid.

## Arguments

Target: $ARGUMENTS

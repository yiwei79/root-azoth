---
description: Strict swarm evaluation — 0.90 bar, isolated evaluators, multi-wave iteration
agent: orchestrator
---

# /eval-swarm $ARGUMENTS

**Higher bar than `/eval`:** use this command when you need **end-to-end parallel swarm** quality gates — **overall ≥ 0.90** (not 0.85), **fresh evaluator context per wave**, and **minimal prompts** (artifact paths + acceptance criteria only) so judges are not biased by author narrative.

**Baseline gate:** For **simple** single-artifact reviews with **no** escalation triggers, use **`/eval`** (PASS at **≥ 0.85**). **`/eval`** is **smart**: it instructs callers to **escalate here** when workflow/content matches the trigger table (see `.claude/commands/eval.md` § “When `/eval` escalates to swarm eval”).
If `.claude/commands/` is not present in your install, use the equivalent prompt under `.github/prompts/` (or your platform-specific mirror).

## When to use `/eval-swarm`

- Multiple branches or deliverables evaluated **in parallel** (`Task` evaluators in **one** orchestrator message).
- **Iterate** eval → fix → re-eval until thresholds clear (see max rounds in workflow).
- **Anti-bias:** Evaluators must **not** receive builder chat logs or long intent prose — only **paths**, **rubric**, and **`threshold: 0.9`**.

## Threshold and disposition

Align with **`agents/tier3-meta/evaluator.agent.md`** weights.

| Outcome | Rule |
|---------|------|
| **PASS** | **overall ≥ 0.90** and **no dimension &lt; 0.5** |
| **FAIL** | Otherwise — schedule **Wave D** (fixes) and **new** evaluator `Task`s (never reuse the same eval thread after edits) |

Do **not** map `/eval`’s **CONDITIONAL** band (0.70–0.85) to a passing swarm gate here — this command is intentionally stricter.

## Process

1. Read **`.claude/workflows/enterprise/e2e-swarm-eval-loop.md`** — waves, fan-out limits, isolation rules, spawn YAML.
2. If `$ARGUMENTS` lists files or globs, treat them as the **artifact set** for Wave C; if empty, evaluate **this session’s** stated deliverables (queen lists paths explicitly in evaluator spawns).
3. Spawn **`Task`** with `subagent_type: evaluator`, **`readonly: true`**, body = short YAML + `Read` targets + `threshold: 0.9` + `acceptance:` bullets — **parallel** independent evals in **one** message when branches are independent.
4. **Aggregate** scores in the orchestrator only; evaluators do not read each other’s reports.
5. If any branch **FAIL**s, pass **gap summaries** (not full prior eval dumps) to planner/builder `Task`s, then re-run Wave C with **new** evaluators.

## Rules

- **Never** conflate this with **`/eval`** — different numeric gate and process.
- **Never** paste author reasoning into an evaluator spawn — **review-independence** (see `skills/subagent-router/SKILL.md`).
- **L2 evidence:** Same as `/eval` — optional `l2_evidence_append.py` when scope (and pipeline, if governed) gates allow; this command stays **read-only** for repo files.

## Arguments

Target: $ARGUMENTS

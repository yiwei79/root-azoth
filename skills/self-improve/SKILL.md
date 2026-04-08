---
name: self-improve
description: |
  Run L1–L2 reflexion: mine episodes for friction, propose evidence-backed instruction
  changes, and iterate auto-refinement on skills or agent text.
---

# Self-Improve

Systematic improvement through reflexion, evidence gathering, and
instruction refinement. The engine that makes Azoth better over time.

## Overview

Self-improvement in Azoth follows a maturity ladder:

```
L1: In-context learning (reflexion, eval, remember)     — Day 1
L2: Prompt optimization (auto-refine from evidence)     — Month 1-2
L3: Architecture search (Agent Crafter, human-gated)    — Month 3+
```

This skill operates at L1 and L2. L3 is the Agent Crafter (Phase 6).

## When to Use

- **After session close** — review episodes for improvement signals
- **After repeated failures** — pattern in M3 suggests process change
- **After 5+ sessions** — enough data for L2 optimization proposals
- **When friction is noticed** — "this keeps being harder than it should be"
- **Explicitly** — human asks "how can we improve X?"

### Backlog work is not exempt from delivery pipelines (D21)

If the active goal maps to `**.azoth/backlog.yaml`** (`delivery_pipeline: standard` → `**/deliver**`, governed or `target_layer: M1` → `**/deliver-full**`), the orchestrator must **not** implement the full outcome inline in one thread. Use **staged pipelines** with `**Task`** (Cursor) / `**Agent(subagent_type=...)**` (Claude Code): **one spawn per stage**, spawn prompt per `**skills/subagent-router/SKILL.md`** (BL-011), and **typed YAML handoffs** between stages (BL-012). Same rule applies to **docs and README** when they are the deliverable — skipping planner / test-design / builder / review to “save time” is an **architecture bypass**, not a shortcut.

**Recovery:** If the bypass already happened, capture the miss in **M3**, then **re-run** the appropriate pipeline stages (or an explicit review `Task`) before treating the work as closed.

---

## L1: Reflexion Loop

In-context learning within a single session. The agent reflects on its
own performance and adjusts behavior.

### Process

```
1. Complete a task
2. Evaluate the result (via agentic-eval)
3. Reflect: What worked? What didn't? Why?
4. Adjust approach for next task
5. Capture lesson as episode (via remember)
```

### Reflexion Template

```markdown
## Reflexion — {task}

### What I did
{brief description of approach}

### Result
{outcome + evaluation score if available}

### What worked
- {specific thing that helped}

### What didn't
- {specific thing that hindered}

### Adjustment
{what I'll do differently next time}

### Episode
{captured via remember skill}
```

### L1 is Always Active

Reflexion doesn't need explicit invocation. Every agent should:

- Notice when something takes longer than expected
- Notice when a plan step fails and needs retry
- Notice when the human corrects or adjusts
- Record these observations as episodes

### Ordinal reuse across menus (ep-081)

**Failure mode:** The human chooses **option 2** from an early branching list (e.g. phase-close vs other paths). Later, the assistant lists **“what you should do next”** as **option 1 / option 2 / …** using the **same ordinal scheme**. The human says **“option 2”** meaning the **second follow-up**, not the **original** option 2 — routing error.

**Practice:** After a numbered branch, use **named** follow-ups (**Session closeout**, **Seed backlog**, **Run /intake**) or a **different** label scheme (**Next A/B/C**, **Step 1…**). If the human says **option N** without context, **confirm which list** before acting.

---

## L2: Evidence-Based Refinement

Systematic instruction improvement based on accumulated evidence.

### Prerequisites

- 5+ episodes in M3 covering the target area
- Identifiable pattern (not a one-off)
- Specific instruction or skill to improve
- Evaluation criteria that can measure improvement

**P6-002 — structured evidence:** For pipeline-originated signals (evaluator scores, reviewer findings), prefer normalizing into `.azoth/memory/l2-refinement-evidence.jsonl` via `scripts/l2_evidence_append.py` under valid gates, then handing **prompt-engineer** filtered `Read` windows — see `skills/prompt-engineer/SKILL.md` §L2 evidence consumption.

### L2 Refinement Process

```
1. IDENTIFY — Find recurring friction/failure pattern in M3 episodes
2. ANALYZE  — Root-cause the pattern (is it instruction quality? missing context? wrong approach?)
3. HYPOTHESIZE — Propose specific instruction change
4. VARIANT  — Generate A/B variants of the instruction
5. EVALUATE — Score variants against historical evidence
6. PROPOSE  — Present winning variant to human for approval
```

### Step 1: Identify

```markdown
## Pattern Identified

**Signal**: 3 of last 5 sessions had entropy alerts during auth module changes
**Episodes**: [ep-001, ep-003, ep-005]
**Common factor**: Context map didn't account for test file dependencies
```

### Step 2: Analyze

```markdown
## Root Cause Analysis

The context-map skill doesn't explicitly prompt for test file discovery
when mapping dependencies. Agents map source dependencies but miss that
test files import from the same modules.

**Not the cause**: Agent laziness, entropy ceiling too low, or scope creep
**Is the cause**: Incomplete dependency scanning instruction
```

### Step 3-4: Hypothesize + Variant

```markdown
## Proposed Refinement

**Target**: skills/context-map/SKILL.md, Step 2 (Map Dependencies)
**Current**: "What depends on the targets? What do the targets depend on?"
**Variant A**: Add explicit test discovery step: "For each target, find
  all test files that import from it"
**Variant B**: Add "Downstream" category that includes test files
```

### Step 5: Evaluate

```markdown
## Variant Evaluation

Replayed against episodes [ep-001, ep-003, ep-005]:
- Variant A: Would have caught test deps in 3/3 cases
- Variant B: Would have caught test deps in 2/3 cases (missed indirect import)

**Winner**: Variant A (explicit test discovery step)
```

### Step 6: Propose

```markdown
## Refinement Proposal

**Skill**: context-map
**Change**: Add "Step 2.5: Discover Test Dependencies" after dependency mapping
**Evidence**: 3 episodes where test deps were missed
**Expected improvement**: Prevent entropy alerts from uncovered test breakage
**Variant score**: 3/3 historical cases would have been caught

⏳ Awaiting human approval to apply refinement
```

---

## Improvement Signals

What to look for in M3 episodes:


| Signal                              | Implication               | Action                            |
| ----------------------------------- | ------------------------- | --------------------------------- |
| Same failure 3+ times               | Process gap               | L2 refinement                     |
| Entropy alerts clustering           | Scope estimation issue    | Refine context-map or planning    |
| Human corrections repeating         | Instruction unclear       | Refine the instruction            |
| Evaluation scores plateauing        | Ceiling reached           | Consider L3 (architecture change) |
| Friction in specific pipeline stage | Stage instruction quality | Refine stage prompt               |


---

## Governance

Self-improvement has strict governance:

1. **L1 reflexion** is always-do (agents reflect without permission)
2. **L2 proposals** require human approval before applying
3. **L2 never modifies kernel** — kernel changes are L3 (governance pipeline)
4. **All variants are logged** — no silent instruction changes
5. **Evidence is required** — "I think this would be better" is not enough

---

## Integration

### With Remember

- Episodes are the raw data for improvement signals
- Reinforcement counts indicate pattern strength

### With Agentic-Eval

- Evaluation scores are the measurement tool
- Variant scoring uses eval patterns

### With Prompt-Engineer

- L2 refinements are instruction changes — prompt-engineer crafts them
- Quality checklist applies to all variants

### With Entropy Guard

- Entropy patterns are a key improvement signal
- Clustering of yellow/red zones indicates process issues

### With Promotion Rubric

- L2 refinements that prove durable become M2 → M1 promotion candidates
- The rubric determines where improvements land


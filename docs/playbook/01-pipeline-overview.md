# Pipeline Overview

> How Azoth pipelines work — from goal to delivery.

## What is a Pipeline?

A pipeline is a **sequence of agent stages** that takes your goal from idea to
delivered code. Each stage is handled by a specialized agent (architect, planner,
builder, etc.), and gates between stages ensure quality without requiring you to
babysit every step.

```
  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
  │  YOUR    │────▶│ AZOTH   │────▶│ AGENTS  │────▶│ DELIVERED│
  │  GOAL    │     │ CLASSIFIES    │ EXECUTE │     │ CODE    │
  └─────────┘     └─────────┘     └─────────┘     └─────────┘
```

## The Four Pipelines

Azoth has four pipeline commands. Think of them as **gear ratios** — use the
lightest gear that fits your work:

```
                        ┌──────────────────────────────────────────┐
  Lightest ◀────────────┤                                          ├──────────▶ Heaviest
                        └──────────────────────────────────────────┘

  /auto                /deliver              /deliver-full         /dynamic-full-auto
  ─────                ────────              ─────────────         ──────────────────
  Smart default.       Pre-approved          Full governance.      Explore first,
  Classifies your      additive work.        For kernel,           then auto-route
  goal, picks the      Fixed 5-stage         governance, or        to the right
  right stages.        structure.            breaking changes.     pipeline.
  1 human gate.        1 human gate.         3 human gates.        1-2 human gates.
```

### When to Use Which

| Pipeline | Use when... | Human gates |
|----------|-------------|-------------|
| **`/auto`** | You have a clear goal and want Azoth to figure out the right stages | 1 (fused Declaration) |
| **`/deliver`** | Work is pre-approved, additive, non-governance | 1 (final approval) |
| **`/deliver-full`** | Touching kernel, governance, or breaking changes | 3 (goal, design, delivery) |
| **`/dynamic-full-auto`** | Complex/unknown — need research swarms before delivery | 1-2 (checkpoint Γ + delivery) |

---

## How `/auto` Works (The Default)

`/auto` is the smart default. You tell it what you want, it figures out how to
get there.

### Step 1 — Classification

Your goal is classified along 4 dimensions:

```
┌─────────────────────────────────────────────────────┐
│              GOAL CLASSIFICATION                     │
├──────────────┬──────────────────────────────────────┤
│ scope        │ kernel · skills · agents · docs · …  │
│ risk         │ governance · breaking · additive · …  │
│ complexity   │ simple · medium · complex             │
│ knowledge    │ known-pattern · needs-research · …    │
└──────────────┴──────────────────────────────────────┘
```

### Step 2 — Auto-Router Selects Stages

The classification maps to a pipeline via 10 priority-ordered rules:

```
Rule  Condition                              Pipeline
────  ─────────────────────────────────────  ──────────────────────────────────
 1    risk == governance-change              architect→reviewer→planner→eval→builder→architect
 2    scope == kernel                        architect→reviewer→planner→eval→builder→architect
 3    knowledge == needs-research            architect→planner→eval→builder→architect
 4    knowledge == instruction-refinement    architect→reviewer→planner→eval→builder→architect
 5    scope == docs                          architect→builder→architect
 6    simple + cosmetic                      planner→builder→architect
 7    simple + additive                      planner→eval→builder→architect
 8    medium + additive + known-pattern      planner→eval→builder→architect
 9    medium + additive                      architect→planner→eval→builder→architect
 10   default (everything else)              architect→reviewer→planner→eval→builder→architect
```

**Key insight**: Rules 1-4 catch all governance/kernel/research work and force
full oversight. Rules 5-9 progressively lighten the pipeline for safer work.
Rule 10 is the conservative fallback.

### Step 3 — Fused Declaration (1 human gate)

Instead of separate scope approval + pipeline approval, `/auto` presents
everything in **one card**:

```
┌────────────────────────────────────────────────────────┐
│  Auto-Pipeline — fix the login validation bug          │
│                                                        │
│  Classification: skills / additive / simple / known    │
│  Scope: session: abc123 | TTL: 2h | layer: mineral    │
│  Model tier: standard                                  │
│                                                        │
│  Composed Pipeline:                                    │
│    1. planner    — standard — gate: agent              │
│    2. evaluator  — standard — gate: agent              │
│    3. builder    — standard — gate: agent              │
│    4. architect  — standard — gate: agent (review)     │
│                                                        │
│  Approve scope + pipeline? [yes / adjust / abort]      │
└────────────────────────────────────────────────────────┘
```

For **lightweight known-pattern** work (docs, simple cosmetic/additive), this
becomes an **informational card** that auto-proceeds:

```
┌────────────────────────────────────────────────────────┐
│  Auto-Pipeline — fix typo in README [INFORMATIONAL]    │
│                                                        │
│  Classification: docs / cosmetic / simple / known      │
│  Pipeline: planner→builder→architect                   │
│  Auto-proceeding unless you type `stop`.               │
└────────────────────────────────────────────────────────┘
```

### Step 4 — Agents Execute

After approval, agents run in sequence. Each agent:
1. Receives a typed handoff from the previous stage
2. Does its work in an isolated context
3. Produces a typed summary for the next stage

```
 ┌──────────┐    handoff    ┌───────────┐    handoff    ┌──────────┐    handoff    ┌──────────┐
 │ PLANNER  │──────────────▶│ EVALUATOR │──────────────▶│ BUILDER  │──────────────▶│ ARCHITECT│
 │          │    (YAML)     │           │    (YAML)     │          │    (YAML)     │ (review) │
 │ Plan the │               │ Score the │               │ Write    │               │ Verify   │
 │ work     │               │ plan      │               │ code     │               │ quality  │
 └──────────┘               └───────────┘               └──────────┘               └──────────┘
      │                          │                           │                          │
   agent gate                agent gate                  test gate                  agent gate
   (auto-pass)               (≥0.85?)                   (tests pass?)             (APPROVED?)
```

**If any gate fails**, the pipeline stops and escalates to you.

### Mid-Pipeline Adaptation (v2)

The orchestrator no longer rigidly follows the original pipeline. After each
stage, it checks for **deviation signals**:

```
  After Stage N completes:
  ┌─────────────────────────────────────────────────────────┐
  │ ✓ Complexity upgraded?    → Re-scope Card to human      │
  │ ✓ Kernel surface found?   → Halt, present human gate    │
  │ ✓ Entropy spiking?        → Offer: narrow / split / go  │
  │ ✓ Eval < 0.80?            → Insert architect review     │
  │ ✓ Tests missing?          → Insert builder test stage    │
  └─────────────────────────────────────────────────────────┘
```

If a deviation is found, the orchestrator can **insert**, **skip**, or
**reorder** stages — then surfaces the change to you for approval.
The pipeline adapts to what it discovers, not just what was planned.

### Step 5 — Done

The architect review closes the pipeline. Your code is delivered.

---

## How `/deliver-full` Works (Governed)

For high-stakes work (kernel, governance, breaking changes):

```
 YOU                         AZOTH
 ───                         ─────
  │                            │
  │  "change governance rule"  │
  │───────────────────────────▶│
  │                            │
  │   ┌─ Stage 1 ─────────┐   │
  │   │ Goal Clarification │   │
  │◀──│ "Here's my plan…"  │   │
  │   └────────────────────┘   │
  │                            │
  │  "yes, approved" ──────────│──▶ 🔒 HUMAN GATE 1
  │                            │
  │   ┌─ Stage 2 ─────────┐   │
  │   │ Architect Design   │   │
  │◀──│ "Architecture…"    │   │
  │   └────────────────────┘   │
  │                            │
  │  "design approved" ───────│──▶ 🔒 HUMAN GATE 2
  │                            │
  │   ┌─ Stages 3-6 ──────┐   │
  │   │ Review → Plan →    │   │
  │   │ Test → Build       │   │
  │   │ (agent gates)      │   │
  │   └────────────────────┘   │
  │                            │
  │   ┌─ Stage 7 ─────────┐   │
  │   │ Architect Review   │   │
  │◀──│ "Here's delivery…" │   │
  │   └────────────────────┘   │
  │                            │
  │  "approved" ──────────────│──▶ 🔒 HUMAN GATE 3
  │                            │
  │   ✅ Delivered + versioned │
  │                            │
```

Three mandatory human gates ensure you stay in control of high-risk changes.

---

## How `/dynamic-full-auto` Works (DFA)

For complex, exploratory work where you don't know the solution yet:

```
┌─────────────────────────────────────────────────────┐
│                  DISCOVERY PHASE                     │
│                                                      │
│   Wave A: Researcher swarms (Sonnet)                │
│     ├── researcher-1: external patterns             │
│     └── researcher-2: domain analysis               │
│                                                      │
│   Wave B: Explore swarms (Haiku)                    │
│     ├── explore-1: codebase mapping                 │
│     ├── explore-2: gate analysis                    │
│     └── explore-3: platform audit                   │
│                                                      │
│   Queen Merge: → SWARM_RESEARCH_DIGEST.yaml         │
│                                                      │
│   Architect Synthesis (Opus): root causes + solutions│
└────────────────────────┬────────────────────────────┘
                         │
                   Checkpoint Γ
                  (re-classify)
                         │
                    ┌────┴────┐
                    │ /auto   │  ← auto-routes to the right
                    │ /deliver│    delivery pipeline
                    │ /full   │
                    └─────────┘
```

DFA uses **model tiering** for cost efficiency:
- **Premium**: architect synthesis, governance review (heavy reasoning)
- **Standard**: research, planning, evaluation, building (default)
- **Fast**: explore swarms, docs, cosmetic fixes (quick scanning)

> Model tiering now applies to **all** pipelines, not just DFA. The
> orchestrator sets `model_tier: premium | standard | fast` on every spawn
> based on risk and complexity. See the orchestrator's Model Tiering section.

---

## Gate Types

Every stage boundary has a gate. Three types:

| Gate | Who decides | What happens on failure |
|------|-------------|------------------------|
| 🔒 **Human** | You | Pipeline stops, waits for your input |
| 🤖 **Agent** | AI reviewer | Auto-passes if clean; escalates to human if issues found |
| 🧪 **Auto-test** | Test suite | All tests must pass; failure blocks the pipeline |

**Governance-critical gates** (kernel, governance changes, final delivery)
are **always human** — no exceptions, no auto-proceed.

---

## The Memory System

Pipelines feed into a 3-layer memory that makes future sessions smarter:

```
┌─────────────────────────────────────────────────┐
│  M3: EPISODIC                                    │
│  .azoth/memory/episodes.jsonl                    │
│  Auto-appended at session closeout.              │
│  "What happened, what we learned."               │
├─────────────────────────────────────────────────┤
│  M2: SEMANTIC                                    │
│  .azoth/memory/patterns.yaml                     │
│  Promoted from M3 (human-approved).              │
│  "Recurring patterns and conventions."           │
├─────────────────────────────────────────────────┤
│  M1: PROCEDURAL                                  │
│  kernel/ + skills/ + agents/                     │
│  The rules themselves. Immutable without          │
│  human-approved promotion.                       │
└─────────────────────────────────────────────────┘
```

Each `/session-closeout` captures an episode (M3). Over time, patterns emerge
and get promoted to M2, then eventually to M1 — making the toolkit better at
handling similar work in the future.

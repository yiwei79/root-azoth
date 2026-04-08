---
description: 'DYNAMIC-FULL-AUTO+ session: adaptive research/explore swarms, digest,
  Checkpoint Γ, optional eval-swarm, then /auto-style delivery'
---

# /dynamic-full-auto $ARGUMENTS

**Primary specification:** `Read` **`skills/dynamic-full-auto/SKILL.md`** and execute it end-to-end for the goal in `$ARGUMENTS`. This command is the slash entry for that session mode; do not improvise a parallel workflow.

## Role

Orchestrator-only in main chat: run **adaptive** discovery waves (research + explore), queen merge into **`SWARM_RESEARCH_DIGEST.yaml`**, **`scripts/swarm_research_digest.py validate`**, **Checkpoint Γ** (re-classify + `auto-router`), optional **`/eval-swarm`**, then hand off to **`/auto`**, **`/deliver`**, or **`/deliver-full`** for gated implementation — per the skill.

## Iron laws (non-negotiable)

Follow **`.agents/skills/swarm-coordination/SKILL.md`**: single-message fan-out, queen aggregation, no worker-to-worker chatter. Subagent work uses **`skills/subagent-router/SKILL.md`** **BL-011** spawn contract and **BL-012** typed handoffs.

## Gates

- **Scope / pipeline:** Same rules as **`/auto`** (see `.claude/commands/auto.md` **Execution**): before the first **Write/Edit** in a governed or M1 delivery tail, satisfy **`.azoth/scope-gate.json`** and, when required, **`.azoth/pipeline-gate.json`**. When you **write** `pipeline-gate.json`, set **`"pipeline"`** to the delivery command you actually run next — exactly one of **`"auto"`** (see `.claude/commands/auto.md`), **`"deliver"`** (see `.claude/commands/deliver.md` Stage 0), or **`"deliver-full"`** (see `.claude/commands/deliver-full.md` Stage 0). Do **not** default to **`auto`** when the handoff is **`/deliver`** or **`/deliver-full`**.
- **`azoth_effect: write`:** Discovery waves are **read/analysis** unless scope already permits writes; **writes** (digest append, implementation) require the same gates as **`/auto`** for governed/M1 work.
- **Review failure:** If any review / audit stage returns request-changes, CRITICAL blockers, **`entropy: RED`**, or **`status: needs-input`**, **STOP** and wait for explicit human approval before continuing — same as **`/auto`**.

## Evaluator routing

When the composed delivery pipeline includes an evaluator (or you run a pre-delivery eval gate), follow **`.claude/commands/eval.md`** **E1–E6** and the skill’s **PRE_DELIVERY_EVAL** section (including **`/eval-swarm`** when triggers fire).

## Cursor / other IDEs

This command is defined for **Claude Code** (`.claude/commands/`). Other tools consume the same sources via their compatibility layers; behavior is specified by **`skills/dynamic-full-auto/SKILL.md`**, not duplicated here.

## Arguments

Goal / session intent: **$ARGUMENTS**

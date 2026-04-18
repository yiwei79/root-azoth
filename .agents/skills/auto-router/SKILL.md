---
name: auto-router
description: |
  Map Stage 0 classification to the ordered stage list for `/auto` (D23); use after
  goal classification, before human approval of the composed pipeline.
version: "1.0"
layer: mineral
governance_anchor: D23
---

## Overview

The auto-router skill is the decision engine for dynamic pipeline composition
(D23). After the Architect completes Stage 0 goal classification, this skill
maps the four classification dimensions — scope, risk, complexity, and knowledge
— onto a concrete stage sequence from `pipelines/auto.pipeline.yaml`.

Rules are evaluated **top-to-bottom**. The first matching condition wins.
The resulting pipeline is presented to the human for approval before execution.

Without this skill, the Architect has no canonical reference and must guess
at stage sequences. This causes ad-hoc pipeline selection that bypasses the
governed composition rules in `auto.pipeline.yaml`.

## When to Use

Use this skill immediately after Stage 0 (goal-clarification) completes and
the classification YAML is available. Do NOT compose a pipeline before
classification is complete.

Trigger: `$GOAL has been classified; compose the pipeline.`

This skill is invoked by `/auto` before the Declaration step.

## Routing Rules

Rules are evaluated in the order below. **Stop at the first match.**


| Priority | Condition                                   | Pipeline Stages                                                 | Notes                                                                |
| -------- | ------------------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------- |
| 1        | `risk == governance-change`                 | `[architect, reviewer, planner, evaluator, builder, architect]` | Full pipeline — any governance mutation requires maximum oversight   |
| 2        | `scope == kernel`                           | `[architect, reviewer, planner, evaluator, builder, architect]` | Full pipeline — kernel is immutable without human-approved promotion |
| 3        | `knowledge == needs-research`               | `[architect, planner, evaluator, builder, architect]`           | Inject research-phase into architect stage before planner            |
| 4        | `knowledge == instruction-refinement AND complexity == simple AND risk == additive` | `[architect, planner, evaluator, builder, architect]` | Lightweight instruction-refinement — keeps l2 evidence review but drops reviewer for bounded additive work |
| 5        | `knowledge == instruction-refinement`       | `[architect, reviewer, planner, evaluator, builder, architect]` | Full fallback — ambiguous, governed, kernel-adjacent, or otherwise non-qualifying refinement stays conservative |
| 6        | `scope == docs`                             | `[architect, builder, architect]`                               | Lightweight — docs carry low risk and need no review or evaluation   |
| 7        | `complexity == simple AND risk == cosmetic` | `[planner, builder, architect]`                                 | Minimal pipeline — no review or evaluation needed                    |
| 8        | `complexity == simple AND risk == additive` | `[planner, evaluator, builder, architect]`                      | Additive changes need evaluation even when simple                    |
| 9        | `complexity == medium AND risk == additive AND knowledge == known-pattern` | `[planner, evaluator, builder, architect]`    | Medium additive known-pattern — reviewer eliminated; evaluator retains correctness gate |
| 10       | `complexity == medium AND risk == additive` | `[architect, planner, evaluator, builder, architect]`           | Medium additive — architect scopes design; reviewer eliminated       |
| 11       | `default`                                   | `[architect, reviewer, planner, evaluator, builder, architect]` | Full pipeline — when in doubt, use maximum coverage                  |


### Rule Rationale

**Rule 1 (governance-change)** — Any change to kernel, governance, or the trust
contract requires the full review cycle. Risk dimension takes priority over all
other dimensions because governance mutations are irreversible without human
approval.

**Rule 2 (kernel scope)** — Kernel scope triggers full pipeline independently
of risk rating. A "cosmetic" change to kernel/ is still a kernel change and
must pass through reviewer and evaluator.

**Rule 3 (needs-research)** — When the knowledge dimension signals that the
solution space is not yet understood, a research phase must be injected into
the Architect stage before planning proceeds. The evaluator remains in the
pipeline because research outputs need quality validation.

**Rule 4 (lightweight instruction-refinement)** — When the knowledge dimension
indicates instruction-refinement and the work is both `simple` and `additive`,
the router may use a lighter path that still begins in the Architect stage with
L2 evidence loaded. This branch is only for low-risk refinement of existing
instruction surfaces where the intended change is decision-complete, bounded to
known authored router surfaces, and does not touch kernel, governance, or any
human-gate contract. The reviewer is removed only for this narrow subset; the
planner and evaluator remain so correctness is still checked before builder work.

**Rule 5 (instruction-refinement fallback)** — All other instruction-refinement
goals stay on the current full path. Ambiguous, governance-touching,
kernel-adjacent, medium/complex, or otherwise non-qualifying refinement work
must fall through immediately to the full reviewer-inclusive route rather than
trying to infer a lighter lane from intent alone.

The **l2-evidence-review** phase is defined as the following sequence of steps,
executed by the Architect at the start of the stage, before any planning brief
is produced:

1. **Read M3 episodes** — load `.azoth/memory/episodes.jsonl` and filter for
   entries tagged `instruction-refinement`; extract friction signals, failed
   patterns, and improvement candidates recorded in prior sessions.
2. **Load M2 patterns** — scan `.azoth/memory/patterns.yaml` (or equivalent
   promoted patterns store) for any patterns that bear on the target instruction
   surface; note convergence or divergence with the current surface.
3. **Surface L2 evidence** — produce a concise evidence summary (≤ 10 bullet
   points) listing: candidate instructions to change, supporting episode count,
   and severity (friction / regression / gap).
4. **Anchor the architect brief** — the evidence summary is attached as the
   first section of the architect's planning output so the reviewer and planner
   receive grounded L2 context, not a blank-slate design.

**Rule 6 (docs)** — Documentation changes are low-risk by definition. An
abbreviated pipeline eliminates unnecessary review and evaluation overhead
while preserving the architect-close gate.

**Rule 7 (simple + cosmetic)** — Trivially small and zero-risk changes (typo
fixes, formatting, comment updates) do not require an evaluator pass. Planner
scopes the work; builder executes; architect closes.

**Rule 8 (simple + additive)** — Simple additive changes (new config keys,
small utility functions) are low-complexity but add surface area. The evaluator
is retained to verify correctness before the architect approves.

**Rule 9 (medium + additive + known-pattern)** — Medium-complexity additive work
on known patterns (e.g., adding a new rule to an existing table, extending a
tested utility) does not need governance review because Rules 1–4 have already
filtered out governance-change, kernel, needs-research, and both instruction-refinement
branches.
The reviewer is eliminated; the evaluator retains the correctness gate. No architect
opening stage is needed because known-pattern work has a well-understood design.

**Rule 10 (medium + additive)** — Medium-complexity additive work where the knowledge
dimension is not known-pattern (e.g., novel but low-risk feature work). The architect
opens the pipeline to scope the design, but the reviewer is eliminated because the
risk is additive (no governance surface). The evaluator validates quality.

**Rule 11 (default)** — Any goal that does not match conditions 1–10 uses the
full pipeline. The default is conservative: prefer more oversight over less.


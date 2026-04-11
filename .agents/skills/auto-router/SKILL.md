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
| 4        | `knowledge == instruction-refinement`       | `[architect, reviewer, planner, evaluator, builder, architect]` | Full pipeline — L2 evidence refinement; inject l2-evidence-review into architect |
| 5        | `scope == docs`                             | `[architect, builder, architect]`                               | Lightweight — docs carry low risk and need no review or evaluation   |
| 6        | `complexity == simple AND risk == cosmetic` | `[planner, builder, architect]`                                 | Minimal pipeline — no review or evaluation needed                    |
| 7        | `complexity == simple AND risk == additive` | `[planner, evaluator, builder, architect]`                      | Additive changes need evaluation even when simple                    |
| 8        | `complexity == medium AND risk == additive AND knowledge == known-pattern` | `[planner, evaluator, builder, architect]`    | Medium additive known-pattern — reviewer eliminated; evaluator retains correctness gate |
| 9        | `complexity == medium AND risk == additive` | `[architect, planner, evaluator, builder, architect]`           | Medium additive — architect scopes design; reviewer eliminated       |
| 10       | `default`                                   | `[architect, reviewer, planner, evaluator, builder, architect]` | Full pipeline — when in doubt, use maximum coverage                  |


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

**Rule 4 (instruction-refinement)** — When the knowledge dimension indicates
instruction-refinement, the goal involves improving existing instruction surfaces
(skills, agent definitions, commands) using accumulated L2 evidence. The full
pipeline ensures reviewer validation and evaluator quality gates on instruction
changes. An l2-evidence-review phase is injected into the architect stage so
evidence is analyzed before planning begins.

**Rule 5 (docs)** — Documentation changes are low-risk by definition. An
abbreviated pipeline eliminates unnecessary review and evaluation overhead
while preserving the architect-close gate.

**Rule 6 (simple + cosmetic)** — Trivially small and zero-risk changes (typo
fixes, formatting, comment updates) do not require an evaluator pass. Planner
scopes the work; builder executes; architect closes.

**Rule 7 (simple + additive)** — Simple additive changes (new config keys,
small utility functions) are low-complexity but add surface area. The evaluator
is retained to verify correctness before the architect approves.

**Rule 8 (medium + additive + known-pattern)** — Medium-complexity additive work
on known patterns (e.g., adding a new rule to an existing table, extending a
tested utility) does not need governance review because Rules 1–4 have already
filtered out governance-change, kernel, needs-research, and instruction-refinement.
The reviewer is eliminated; the evaluator retains the correctness gate. No architect
opening stage is needed because known-pattern work has a well-understood design.

**Rule 9 (medium + additive)** — Medium-complexity additive work where the knowledge
dimension is not known-pattern (e.g., novel but low-risk feature work). The architect
opens the pipeline to scope the design, but the reviewer is eliminated because the
risk is additive (no governance surface). The evaluator validates quality.

**Rule 10 (default)** — Any goal that does not match conditions 1–9 uses the
full pipeline. The default is conservative: prefer more oversight over less.



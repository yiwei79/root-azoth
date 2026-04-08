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
| 4        | `scope == docs`                             | `[architect, builder, architect]`                               | Lightweight — docs carry low risk and need no review or evaluation   |
| 5        | `complexity == simple AND risk == cosmetic` | `[planner, builder, architect]`                                 | Minimal pipeline — no review or evaluation needed                    |
| 6        | `complexity == simple AND risk == additive` | `[planner, evaluator, builder, architect]`                      | Additive changes need evaluation even when simple                    |
| 7        | `default`                                   | `[architect, reviewer, planner, evaluator, builder, architect]` | Full pipeline — when in doubt, use maximum coverage                  |


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

**Rule 4 (docs)** — Documentation changes are low-risk by definition. An
abbreviated pipeline eliminates unnecessary review and evaluation overhead
while preserving the architect-close gate.

**Rule 5 (simple + cosmetic)** — Trivially small and zero-risk changes (typo
fixes, formatting, comment updates) do not require an evaluator pass. Planner
scopes the work; builder executes; architect closes.

**Rule 6 (simple + additive)** — Simple additive changes (new config keys,
small utility functions) are low-complexity but add surface area. The evaluator
is retained to verify correctness before the architect approves.

**Rule 7 (default)** — Any goal that does not match conditions 1–6 uses the
full pipeline. The default is conservative: prefer more oversight over less.

## Integration

### How the Architect uses this skill

```
1. Complete Stage 0 classification.
2. Invoke the `auto-router` skill with the classification YAML.
3. Match the classification against the routing table top-to-bottom.
4. Record the matched condition and resulting pipeline.
5. Emit the Declaration block (pipeline + rationale + approval prompt).
6. Wait for human approval before executing.
```

### Cross-file consistency

This skill is the single source of truth for routing logic. The condition
strings and pipeline arrays in this file MUST match `pipelines/auto.pipeline.yaml`
exactly. If you need to add or modify a rule, update BOTH files in the same
change and update the tests in `tests/test_auto_router.py`.

### Subagent assignment

After composing the pipeline, apply the `subagent-router` skill to assign
a `subagent_type` to each stage. Add `subagent_type` and `trigger` columns
to the Declaration table before presenting for approval.

At **execution** time, each subagent spawn must follow `subagent-router`
§Spawn Prompt Contract (BL-011): YAML goal + parameters only, not pasted pipeline prose.

### L2 / instruction-rubric goals (P6-002, v1 inject-only)

The Stage 0 classification tuple (`scope`, `risk`, `complexity`, `knowledge`) does not yet include an explicit “instruction refinement” flag, so **v1** does **not** add a new `composition_rules` row to `pipelines/auto.pipeline.yaml`. For goals that should feed **prompt-engineer** after delivery evidence exists, the **orchestrator** documents and runs an **inject-only** branch: append an L2 evidence record (`scripts/l2_evidence_append.py`), then spawn **prompt-engineer** with fresh context. When classification is extended (future task), a single new auto-router rule may reference that flag.

### Related files

- `pipelines/auto.pipeline.yaml` — YAML representation of these rules
- `skills/subagent-router/SKILL.md` — stage-level subagent assignment
- `.claude/commands/auto.md` — the `/auto` command that invokes this skill
- `docs/DECISIONS_INDEX.md` D23 — governance anchor


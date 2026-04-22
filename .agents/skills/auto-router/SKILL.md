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
(D23). After Stage 0 intake and goal classification, this skill maps the four
classification dimensions — scope, risk, complexity, and knowledge — onto a
conservative routing row from `pipelines/auto.pipeline.yaml`.

Rules are evaluated **top-to-bottom**. The first matching condition wins for
the **base composition**, which is now expressed as:

- a `reference_preset`
- an ordered list of `stage_families`
- a `discovery_policy`

The orchestrator still reasons over the latest context before execution:

- `context-recall` is mandatory for pipeline-improvement, instruction-refinement,
  and replay-after-gate-failure work.
- latest repo-state evidence and platform constraints are part of composition,
  not post-hoc cleanup.
- discovery / evidence / research is a **cross-cutting insertion capability**
  that `/auto` may add when confidence is low or evidence is missing.
- the selected row is a **reference composition / conservative template**, not
  permission to skip gates or collapse required staged ownership into inline
  orchestration. In `/auto` and `dynamic-full-auto`, the orchestrator may keep
  a bounded non-agent-gated slice inline only when it explicitly records why
  inline is more beneficial than spawning and what signal would force a return
  to staged delegation.

Without this skill, the Architect has no canonical reference and must guess at
pipeline shape. This causes ad-hoc selection that bypasses the governed rules in
`auto.pipeline.yaml`.

## When to Use

Use this skill immediately after Stage 0 (goal-clarification) completes and
the classification YAML is available. Do NOT compose a pipeline before
classification is complete.

Trigger: `$GOAL has been classified; compose the pipeline.`

This skill is invoked by `/auto` before the Declaration step.

## Shared Stage Families

Every `/auto` run reasons from the same stage-family vocabulary:

1. `intake + classification` — owned by Stage 0
2. `context-recall`
3. `discovery-evidence-research`
4. `architect-design`
5. `review`
6. `plan`
7. `execute`
8. `quality-gate`
9. `closeout`

The shared discovery trigger vocabulary in `auto.pipeline.yaml` is:

- `low-solution-confidence`
- `conflicting-memory-or-pattern-evidence`
- `cross-surface-drift`
- `latest-context-dependency`
- `gate-finding-evidence-insufficient`

The routing table below selects the conservative base shape. The orchestrator
then applies the mandatory read-back and insertion rules above so the composed
pipeline reflects current context rather than a frozen preset.

## Routing Rules

Rules are evaluated in the order below. **Stop at the first match.**

| Priority | Condition | Reference Preset | Stage Families | Discovery Policy | Notes |
| -------- | --------- | ---------------- | -------------- | ---------------- | ----- |
| 1 | `risk == governance-change` | `full` | `architect-design`, `review`, `plan`, `execute`, `quality-gate`, `closeout` | `conditional` | Full lane — any governance mutation requires maximum oversight |
| 2 | `scope == kernel` | `full` | `architect-design`, `review`, `plan`, `execute`, `quality-gate`, `closeout` | `conditional` | Full lane — kernel is immutable without human-approved promotion |
| 3 | `knowledge == needs-research` | `research` | `discovery-evidence-research`, `architect-design`, `plan`, `execute`, `quality-gate`, `closeout` | `required` | Discovery-first delivery lane — the shared research family must run before design locks |
| 4 | `knowledge == instruction-refinement AND complexity == simple AND risk == additive` | `refactor` | `context-recall`, `architect-design`, `plan`, `execute`, `quality-gate`, `closeout` | `conditional` | Lightweight instruction-refinement — keeps L2 evidence loading but drops reviewer for bounded additive work |
| 5 | `knowledge == instruction-refinement` | `full` | `context-recall`, `architect-design`, `review`, `plan`, `execute`, `quality-gate`, `closeout` | `conditional` | Full fallback — ambiguous, governed, kernel-adjacent, or otherwise non-qualifying refinement stays conservative |
| 6 | `scope == docs` | `docs` | `architect-design`, `execute`, `closeout` | `conditional` | Lightweight — docs carry low risk and usually need no review or separate quality gate |
| 7 | `complexity == simple AND risk == cosmetic` | `hotfix` | `plan`, `execute`, `closeout` | `conditional` | Minimal lane — no dedicated review or quality gate by default |
| 8 | `complexity == simple AND risk == additive` | `deliver` | `plan`, `execute`, `quality-gate`, `closeout` | `conditional` | Additive changes keep a correctness gate even when simple |
| 9 | `complexity == medium AND risk == additive AND knowledge == known-pattern` | `deliver` | `plan`, `execute`, `quality-gate`, `closeout` | `conditional` | Medium additive known-pattern — reviewer eliminated; quality gate retained |
| 10 | `complexity == medium AND risk == additive` | `refactor` | `architect-design`, `plan`, `execute`, `quality-gate`, `closeout` | `conditional` | Medium additive novel work — architect scopes the design while staying below the full review lane |
| 11 | `default` | `full` | `architect-design`, `review`, `plan`, `execute`, `quality-gate`, `closeout` | `conditional` | Full lane — when in doubt, use maximum coverage |


### Rule Rationale

**Rule 1 (governance-change)** — Any change to kernel, governance, or the trust
contract requires the full review cycle. Risk dimension takes priority over all
other dimensions because governance mutations are irreversible without human
approval. `/auto` does **not** forcibly redirect these cases to `/deliver-full`;
it composes the conservative full path while keeping orchestrator ownership
unless the human explicitly chose another command. The `full` reference preset
anchors the heaviest oversight shape, while the stage-family list keeps the
declarative contract aligned with the shared auto-family vocabulary.

**Rule 2 (kernel scope)** — Kernel scope triggers full pipeline independently
of risk rating. A "cosmetic" change to kernel/ is still a kernel change and
must pass through review and quality gates.

**Rule 3 (needs-research)** — When the knowledge dimension signals that the
solution space is not yet understood, discovery / evidence gathering must be
inserted before planning proceeds. This insertion is not unique to one mode:
it is part of the shared auto-family control plane. The evaluator remains in
the pipeline because research outputs need quality validation. This is the only
rule with `discovery_policy: required`.

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
executed inside the `context-recall` family before the `architect-design` stage
produces any planning brief:

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

## Bounded Replay

Self-iterative quality inside `/auto` is a bounded replay contract, not a
manual prompt loop.

- architecture / scope / governance / contract findings replay `architect`
- planning / test-strategy / handoff-completeness findings replay `planner`
- implementation / failing-acceptance findings replay `builder`
- evidence-insufficient findings insert discovery / evidence before replaying
  design or planning

Default thresholds are `2` replays for non-governed runs and `3` for governed
or high-stakes runs. When the threshold is exhausted, the orchestrator stops
replay and enters recomposition: narrow the slice, change the pipeline shape,
or escalate to the human for a pipeline decision.

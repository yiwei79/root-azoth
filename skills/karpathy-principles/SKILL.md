---
name: karpathy-principles
description: |
  Injectable discipline slot for coding, review, planning, or refactoring stages that need
  explicit assumption surfacing, simplicity pressure, surgical diffs, and stage6-rubric-verifiable
  success criteria without expanding the root CLAUDE.md instruction layer.
version: "1.0"
layer: mineral
governance_anchor: D44
---

# Karpathy Principles

An on-demand Azoth skill for applying four Karpathy-inspired engineering disciplines:
Think Before Coding, Simplicity First, Surgical Changes, and Goal-Driven Execution.

This skill is deliberately injectable. It strengthens a specific stage or artifact when
the work benefits from extra reasoning discipline, but it does not become always-on root
architecture text and it does not rewrite builder, orchestrator, or structured-autonomy
behavior reserved for later KRP slices.

## Overview

Use this skill to slow down just enough to avoid the expensive mistake: building the
wrong thing, widening a change because the code is interesting, or declaring completion
without crisp evidence. The output should be practical: a small working theory, a
minimal implementation path, a constrained diff, and verification that maps to the
actual goal.

The skill is not a separate pipeline. It is a discipline layer that can be loaded by a
builder, planner, reviewer, or architect stage when the current task has enough ambiguity
or blast radius to justify more explicit thinking. When invoked for M1 skill work,
`stage6-rubric` can evaluate the result for a falsifiable invocation cue, governance
anchor, concrete usage pattern, and integration clarity.

## When to Use

- Before editing code in a `/deliver-full` or governed M1 task where the goal is compact
  but the implementation route is not yet obvious.
- During code review when a proposed patch looks larger than the acceptance criteria, or
  when the reviewer needs to separate real risk from preference.
- During planning when the next action depends on assumptions about existing architecture,
  test surfaces, generated mirrors, or governance gates.
- During refactoring when the safest path is likely a narrow behavior-preserving change
  instead of a broad cleanup pass.
- During recovery after a failed test or gate when the agent needs to re-state the target
  and avoid cascading unrelated edits.

Do not use this skill to bypass required Azoth gates, to expand root instructions, or to
fold follow-on work into T-KRP-B. Builder posture changes belong to T-KRP-C. Orchestrator
assumption-classification changes belong to T-KRP-D. Structured-autonomy success-criteria
gating belongs to T-KRP-E.

## Principles

### Think Before Coding

State the goal, the observed constraints, and the smallest hypothesis that would explain
the next change. Identify the files that should move and the files that should stay still.
If the current evidence is thin, gather the missing context before editing.

Good output is not a long essay. It is a short preflight that names what will be changed,
why that change is sufficient, and what would falsify the plan.

### Simplicity First

Prefer the repo's existing helpers, naming, data formats, and test style. Add abstraction
only when it removes real complexity or matches an established local pattern.

If two approaches both satisfy the acceptance criteria, choose the one with fewer moving
parts, fewer files, and fewer future obligations. Simplicity here means lower cognitive
load for the next maintainer, not clever compression.

### Surgical Changes

Keep the diff aligned to the approved scope. Preserve unrelated dirty work, generated
artifacts, local config, and user edits. If a generator owns a mirror, edit the canonical
source and rerun the generator rather than hand-patching the mirror.

When an adjacent issue appears, decide whether it blocks the goal. Fix it only if the
cost is tiny and the ownership is clear; otherwise name it as follow-up and keep moving.

### Goal-Driven Execution

Tie every edit and every test to the user's requested outcome. The completion standard is
not "I changed the file"; it is "the stated behavior is implemented and the relevant
checks pass or have an honest blocker."

Before delivery, restate the evidence: changed paths, commands run, outcomes, and any
residual risk. If the stage produces a summary artifact, make the goal, verification,
and deferrals explicit enough for the next agent to continue without guessing.

## Usage Pattern

Use this pattern when injecting the skill into a stage:

1. Restate the target in one sentence and list the owned surfaces.
2. Name the assumptions that could make the chosen implementation wrong.
3. Pick the smallest source-of-truth edit set that satisfies the goal.
4. Run the narrowest meaningful test first, then the required stage checks.
5. Report deferrals explicitly, especially T-KRP-C, T-KRP-D, and T-KRP-E boundaries.

Example invocation:

```yaml
skill: karpathy-principles
stage: deliver_full_s6
goal: Add one injectable M1 skill and generated mirrors without expanding root CLAUDE.md.
owned_surfaces:
  - skills/karpathy-principles/SKILL.md
  - skills/index.yaml
  - azoth.yaml
verification:
  - python3 scripts/azoth-deploy.py --check
  - PYTHONPATH=scripts python3 -m pytest tests/test_skills.py tests/test_azoth_deploy.py -q
```

Expected output:

- a brief preflight,
- a minimal diff against canonical sources,
- generated mirrors refreshed by the deploy script,
- tests or gate results tied to the acceptance criteria,
- explicit follow-on boundaries for any deferred KRP work.

## Integration

- `stage6-rubric`: evaluates this M1 skill when it is created or materially revised,
  including governance anchor, falsifiable trigger, concrete usage pattern, and caller
  integration clarity.
- `structured-autonomy-plan`: may reference this skill when a plan needs explicit
  success criteria and assumption checks before a builder handoff.
- `dynamic-full-auto` and `/deliver-full`: may inject this skill into build, review, or
  replay stages when adaptive routing detects ambiguity, high blast radius, or repeated
  verification failure.

This integration is opt-in. T-KRP-B provides the skill surface and registration only; it
does not change root CLAUDE.md, builder defaults, orchestrator classification policy, or
structured-autonomy gates.

## Boundaries

This skill is the T-KRP-B slice of the Karpathy Principles initiative. It gives agents a
loadable discipline surface, but it does not make the discipline always-on and it does not
change pipeline routing by itself.

Keep these follow-ons separate:

- T-KRP-C owns builder-agent posture changes for surgical changes and simplicity-first
  enforcement.
- T-KRP-D owns orchestrator assumption-surfacing at goal classification.
- T-KRP-E owns structured-autonomy success-criteria gating.

If a caller needs one of those behaviors, name it as follow-on scope instead of expanding
this skill during T-KRP-B.

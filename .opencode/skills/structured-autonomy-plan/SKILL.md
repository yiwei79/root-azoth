---
name: structured-autonomy-plan
description: |
  Convert architect briefs into deterministic task plans with explicit test strategy and
  validation gates for handoff to the builder stage or a future session.
---

# Structured Autonomy Plan

Convert goals to actionable, deterministic plans that agents can execute
autonomously within trust boundaries.

## Overview

A structured autonomy plan transforms a fuzzy goal into a sequence of
concrete, validatable tasks. The plan is the contract between the planner
and the builder: if the builder follows it, the goal is achieved.

```
Goal + Design Brief → Success Criteria → Decompose → Sequence → Map Validation → Plan
```

## When to Use

- **After architect approval** — converting design to implementation tasks
- **Complex multi-step work** — anything requiring more than 3 discrete changes
- **Cross-agent handoffs** — plan must be clear enough for any agent to execute
- **Test-driven work** — test strategy is part of the plan, not an afterthought

---

## Plan Structure

### 1. Goal Restatement

Restate the goal in one sentence. This anchors the plan and prevents drift.

```
Goal: Implement the entropy-guard skill with real-time monitoring and checkpoint triggers.
```

### 2. Success Criteria

Before decomposing work, derive falsifiable success criteria from the goal and
design brief. These criteria define what must be true for the plan to count as
complete, independent of the tasks chosen to get there.

Each success criterion MUST be:

- **Falsifiable** — a reviewer can prove it passed or failed
- **Outcome-focused** — describes the desired system behavior or artifact state
- **Traceable** — maps back to the goal or an architect decision
- **Validation-bound** — names the test, check, human review, or deferral that will verify it

Each success criterion MUST map to exactly one validation disposition:

- **automated_test** — verified by a named unit, integration, lint, parity, or regression test
- **manual_validation** — verified by a deterministic command, inspection, or artifact check
- **human_review** — requires an explicit human judgment or approval gate
- **deferred** — intentionally left out of scope with a concrete follow-up owner or artifact

```yaml
success_criteria:
  - id: SC-1
    criterion: Entropy guard classifies green, yellow, and red zones from changed-file counts.
    source: architect_decision:entropy-zone-classification
    validation_disposition: automated_test
    validation_ref: tests/test_entropy_guard.py::test_classifies_all_zones

  - id: SC-2
    criterion: Yellow-zone entry produces an auditable checkpoint artifact.
    source: goal:checkpoint-triggers
    validation_disposition: manual_validation
    validation_ref: python3 scripts/check_entropy_guard.py --fixture yellow-zone

  - id: SC-3
    criterion: Red-zone notifications match operator escalation expectations.
    source: architect_decision:human-escalation
    validation_disposition: human_review
    validation_ref: reviewer confirms escalation copy and gate behavior
```

#### Non-Goals and Deferrals Checkpoint

Before builder handoff, the planner MUST name work that is intentionally out of
scope. This checkpoint prevents the builder from treating a silent omission as
approved implementation scope.

```yaml
non_goals:
  - Production telemetry ingestion is not part of this slice.
  - Kernel or governance contract edits are excluded unless explicitly approved.
deferrals:
  - id: DEF-1
    item: Add production telemetry trend analysis after baseline event capture ships.
    owner: backlog
    follow_up_artifact: BL-123
    linked_success_criteria: [SC-4]
```

The checkpoint MUST appear before task decomposition and MUST be carried into the
builder handoff when any success criterion uses `deferred`.

#### Lineage Boundary Markers

Structured autonomy planning is the T-KRP-E slice: it adds falsifiable success
criteria and validation dispositions to planner output. It must not blur these
adjacent boundaries:

- **T-KRP-A root behavior** — validates root session and continuity behavior; do
  not use this skill to redefine start, next, resume, or root-routing semantics.
- **T-KRP-B injectable skill** — owns the Karpathy-principles discipline as an
  injectable skill; this skill may reference that discipline but must not absorb
  or rewrite its contract.
- **T-KRP-C Builder posture** — owns Builder scope discipline, owned surfaces,
  and final delivery reporting; this skill hands the builder a plan, not a new
  builder operating contract.
- **T-KRP-D Orchestrator assumption surfacing** — owns Stage 0 assumption
  checkpoints and routing implications; this skill consumes an approved brief
  after those assumptions are surfaced.
- **T-KRP-E structured success criteria** — owns success criteria, non-goals,
  deferrals, and validation mapping inside the structured autonomy plan.
- **T-006 stable criteria for replay routing** — replay decisions must cite
  stable acceptance criteria and the lowest legitimate corrective stage instead
  of reinterpreting broad roadmap intent.

### 3. Task Decomposition

Break the goal into discrete, atomic tasks. Each task should be:

- **Completable in isolation** — no implicit dependencies
- **Verifiable** — has a clear "done" signal
- **Bounded** — won't exceed entropy ceiling on its own

```yaml
tasks:
  - id: 1
    success_criteria: [SC-1]
    action: Create skills/entropy-guard/SKILL.md with frontmatter and core logic
    files: [skills/entropy-guard/SKILL.md]
    validation: File exists with valid YAML frontmatter
    
  - id: 2
    success_criteria: [SC-1]
    action: Write entropy calculation function
    files: [skills/entropy-guard/entropy.py]
    depends_on: [1]
    validation: Unit tests pass
    
  - id: 3
    success_criteria: [SC-2, SC-3]
    action: Write drift detection tests
    files: [tests/test_skills.py]
    depends_on: [1, 2]
    validation: pytest passes, coverage > 80%
```

### 4. Task Sequencing

Order tasks by dependencies. Identify parallelizable work.

```
Sequential:  1 → 2 → 3
Parallel:    [1a, 1b] → 2 → [3a, 3b]
```

### 5. Test Strategy and Validation Map (Mandatory)

Every plan MUST include a test strategy and validation map. No plan is complete
without evidence for each success criterion, or an explicit deferred disposition
when evidence is intentionally out of scope.

```yaml
test_strategy:
  unit_tests:
    - test_entropy_calculation_green_zone
    - test_entropy_calculation_yellow_zone
    - test_entropy_calculation_red_zone
  integration_tests:
    - test_checkpoint_triggered_on_yellow
  acceptance_criteria:
    - Entropy guard correctly classifies all three zones
    - Checkpoint is created when entering yellow zone
    - Human notification sent when entering red zone
validation_map:
  - criteria_id: SC-1
    validation_disposition: automated_test
    validation_ref: tests/test_entropy_guard.py::test_classifies_all_zones
  - criteria_id: SC-2
    validation_disposition: manual_validation
    validation_ref: python3 scripts/check_entropy_guard.py --fixture yellow-zone
  - criteria_id: SC-3
    validation_disposition: human_review
    validation_ref: reviewer approval of escalation copy and gate behavior
  - criteria_id: SC-4
    validation_disposition: deferred
    validation_ref: backlog:BL-123 tracks production telemetry follow-up
```

### 6. Risk Assessment

```yaml
risks:
  - risk: Entropy formula may not capture all change types
    mitigation: Start simple, iterate based on real usage data
    severity: low
```

---

## Plan Template

```markdown
## Structured Autonomy Plan — {goal}

### Goal
{one sentence}

### Design Brief Reference
{link to architect output or inline summary}

### Success Criteria

| ID | Criterion | Source | Validation Disposition | Validation Ref |
|----|-----------|--------|------------------------|----------------|
| SC-1 | {falsifiable outcome} | {goal or decision} | {automated_test | manual_validation | human_review | deferred} | {test, command, reviewer gate, or follow-up} |

### Non-Goals and Deferrals
- Non-goal: {explicitly excluded work}
- Deferral: {follow-up id, owner, and linked success criteria}

### Tasks

| # | Success Criteria | Action | Files | Depends On | Validation |
|---|------------------|--------|-------|------------|------------|
| 1 | {SC-ids} | {what} | {where} | — | {how to verify} |
| 2 | {SC-ids} | {what} | {where} | 1 | {how to verify} |

### Sequence
{ordering and parallelism}

### Test Strategy
- Unit: {list}
- Integration: {list}
- Acceptance: {criteria}

### Validation Map
- SC-1: {automated_test | manual_validation | human_review | deferred} — {validation ref}

### Risks
- {risk}: {mitigation}

### Entropy Estimate
- Files to create: {N}
- Files to modify: {N}
- Estimated zone: {GREEN | YELLOW | RED}
```

In pipeline terms, this artifact is usually produced after architect approval and then
consumed by the test-builder and builder stages, so file lists, dependencies, and
validation steps must stay cold-start clear.

## Quality Criteria

A good plan passes these checks:

- Falsifiable success criteria appear before task decomposition
- Every success criterion maps to validation or a named deferral
- Every task has explicit files and validation
- Every task references one or more success criteria
- Dependencies are explicit (no implicit ordering)
- Test strategy exists and covers acceptance criteria
- Entropy estimate is within green/yellow zone
- A different agent could execute this plan without clarification

---

## Anti-Patterns


| Anti-Pattern            | Fix                                              |
| ----------------------- | ------------------------------------------------ |
| "Implement the feature" | Break into specific file-level tasks             |
| Tasks before criteria   | Define falsifiable success criteria first        |
| Unmapped criteria       | Map each criterion to validation or deferral     |
| No test strategy        | Add tests — no plan is complete without them     |
| Implicit dependencies   | Make every dependency explicit with `depends_on` |
| Unbounded tasks         | Each task should touch ≤ 5 files                 |
| Plan assumes context    | Include enough detail for cold-start execution   |

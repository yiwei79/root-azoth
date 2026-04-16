---
name: stage6-rubric
description: |
  Architect gate for `/deliver-full` Stage 6/7: PASS/FAIL structured content (agents,
  skills, pipeline YAML) before human approval — implements D44 shallow-output checks.
version: "1.0"
layer: mineral
governance_anchor: D44
---

# Stage 6 Quality Rubric

Concrete PASS/FAIL criteria for structured content reviewed at the Architect Review
stage of the full delivery pipeline. Prevents shallow first-pass output (ep-021)
from reaching human approval.

## Overview

The full pipeline's Stage 6 (Architect Review) has historically passed structured
content that was under-specified — requiring a second enrichment pass after delivery.
D44 was created to close this gap by giving the reviewing architect a rubric with
explicit thresholds, not vague quality intuitions.

Three axes apply in sequence. A fail on any axis in any fail condition blocks
Stage 6 approval and escalates to the human gate (Stage 7).

```
Content artifact → Axis 1 (Depth) → Axis 2 (Governance) → Axis 3 (Patterns) → PASS
                                                                               ↓ FAIL
                                                             Escalate to Stage 7 human gate
```

## When to Use

Invoke this skill when acting as architect at Stage 6/7 of `/deliver-full`, before
approving any of these content types:

- Agent archetype files (`agents/*/AGENT.md`)
- Skill definition files (`skills/*/SKILL.md`)
- Pipeline YAML files (`pipelines/*.yaml` or `pipelines/*.pipeline.yaml`)

Do NOT apply to prose documentation, ADRs, or scripts — this rubric is for
structured deliverables only.

## Axis 1 — Minimum Depth

### Agent Archetypes (`AGENT.md`)

Required sections — each must contain ≥ 3 substantive items (not placeholder text):

| Section | Minimum content |
|---------|----------------|
| Role | 3 substantive sentences describing the archetype's purpose and domain |
| When to Use | 3 specific trigger conditions (not "when you need X" generics) |
| Tools | 3 named tools or tool categories with rationale |
| Interaction Patterns | 3 example sequences (trigger → action → output) |
| Boundaries | 3 explicit constraints (what this agent does NOT do) |

### Skills (`SKILL.md`)

Required frontmatter fields:
- `name` — matches directory name
- `description` — includes at least one **falsifiable invocation cue** (named artifact
  type, pipeline stage, slash command, or tool surface). Pure generic phrasing with no
  such cue fails Axis 1 (BL-015: descriptions may be 1–2 sentences instead of bullet lists).
- `layer` — one of: `mineral`, `wave`, `current`, `molecule` (when the field is present)
- `governance_anchor` — decision ref (required for M1 skills)

Required sections:
- `## Overview` — purpose and problem solved, ≥ 2 sentences
- `## When to Use` — ≥ 1 trigger condition specific enough to be testable
- At least one concrete usage pattern with example input/output or invocation

### Pipeline YAML

Required fields:
- `name` — pipeline identifier
- `description` — ≥ 1 sentence
- All stages must have: `name`, `agent`, and `gate` with declared `type`
- No stage may have empty `outputs:` list
- No untyped gates (every gate must have `type: human` or `type: agent`)

## Axis 2 — Governance Constraint Coverage

For any M1 artifact (target_layer: M1 or layer: mineral), verify:

1. **Decision ref present** — `governance_anchor` or `decision_ref` field exists and
   the referenced decision ID is present in `docs/DECISIONS_INDEX.md`
2. **Gate type declared** — every stage interaction declares `type: human` or
   `type: agent`; ambiguous gate language (e.g. "approval needed") fails this check
3. **HITL implications noted** — if the artifact removes, weakens, or bypasses a
   human gate, the Trust Contract implications are documented in the artifact
4. **Mechanical enforcement path cited** — behavioral rules expressed only in prose
   (not backed by a hook, gate, or scope check) fail this criterion; cite the
   enforcement mechanism or explicitly note it is pending (with a Phase ref)

## Axis 3 — Interaction Pattern Completeness

### Agent Archetypes

- ≥ 1 complete example interaction sequence in the format: trigger → action → output
- Escalation path defined: when does this agent stop and escalate to a human?
- Integration points listed: which other agents or skills does this archetype use?

### Skills

- ≥ 1 `## When to Use` condition specific enough to be testable (falsifiable trigger)
- If the skill is invoked by another skill or pipeline, an `## Integration` section
  must be present listing each caller and the invocation context

## Fail Conditions

Any of the following blocks Stage 6 approval (agent gate). If the reviewing
architect reaches Stage 7 with any unresolved fail condition, escalate to
the human final-approval gate with the specific condition cited.

1. Any required section contains only a single sentence where ≥ 3 substantive
   items are required (Axis 1 depth threshold not met)
2. `governance_anchor` or `decision_ref` is absent on any M1-targeted artifact
   (Axis 2, criterion 1)
3. A gate or interaction point exists with no declared type (`type: human` or
   `type: agent`) — gate type ambiguity violates D24 (Axis 2, criterion 2)
4. An agent archetype is missing the Interaction Patterns section entirely
   (Axis 3 completeness threshold not met)
5. A skill's `description` or `## When to Use` content is generic only — no falsifiable
   invocation cue (named artifact type, pipeline stage, slash command, or tool surface).
   Examples of failing text: "when you need evaluation", "for quality checks", "when reviewing"
   with no concrete routing hook.


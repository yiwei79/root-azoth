---
name: remember
description: |
  Append structured episodes to `.azoth/memory/episodes.jsonl` and classify lessons for
  M3→M2 promotion; use at session closeout or when capturing durable decisions or patterns.
---

# Remember

Capture durable lessons from experience. Every session produces knowledge —
this skill ensures it's not lost.

## Overview

The remember skill is the write interface to Azoth's 3-layer memory system.
It captures episodes (M3), surfaces patterns for promotion to M2, and
ultimately contributes to procedural knowledge (M1) in kernel/skills/agents.

```
Experience → Capture Episode → Auto-Classify → Surface in Future → Propose Promotion
```

## When to Use

- **Session close** (HARDEN phase) — always capture an episode
- **After significant decisions** — record the reasoning
- **After failures** — record what went wrong and why
- **When patterns emerge** — "this is the third time I've seen this"
- **Explicitly** — when the human says "remember this"

---

## Episode Capture

### Episode Schema

```json
{
  "id": "uuid-v4",
  "timestamp": "2026-04-04T12:00:00Z",
  "session_id": "uuid-v4",
  "type": "success | failure | decision | pattern | observation",
  "goal": "What the session was trying to achieve",
  "summary": "What happened (2-3 sentences)",
  "lessons": [
    "Specific, actionable lesson 1",
    "Specific, actionable lesson 2"
  ],
  "tags": ["skill-development", "governance", "testing"],
  "reinforcement_count": 0,
  "context": {
    "phase": "2",
    "pipeline": "deliver",
    "files_changed": 5
  }
}
```

### When to increment reinforcement_count

`reinforcement_count` starts at `0` on every new episode. Increment it by `1`
each time a **subsequent** session surfaces the same lesson and it still holds
true — i.e., when you would write the same lesson again but an identical or
near-identical episode already exists. Do **not** increment on the initial
capture; do **not** increment more than once per session.

### Capture Rules

1. **One episode per session minimum** — the HARDEN phase always produces one
2. **Episodes are append-only** — never edit, never delete (M3 governance rule)
3. **Be specific** — "tests helped catch a regression" not "testing is good"
4. **Include the why** — decisions without reasoning are useless later
5. **Tag for retrieval** — tags enable efficient future surfacing

### Supersession and Contradiction Rules

Append-only means correction happens by addition, not mutation.

- If a lesson changes, create a **new episode linked to the older one**; never rewrite the old
  episode to make history look cleaner than it was.
- If new evidence contradicts an older lesson, capture a new episode and link it to the older one
  via context such as `related_episode_id` or `supersedes_episode_id`.
- Use explicit status tags so later recall can reason about episode state:
  - `stale` — the lesson is historical background only because the workflow, toolchain, or repo
    shape changed.
  - `superseded` — a newer episode replaces the actionable guidance from an older one for the same
    tag set.
  - `contradicted` — evidence conflicts and there is not yet a clear winner, so both episodes stay
    visible until more evidence or human review resolves it.
- Contradictions do not authorize deletion. They create a new episode linked to the older one and
  preserve both sides of the evidence trail.

### Episode Types


| Type          | When                          | Example                                                 |
| ------------- | ----------------------------- | ------------------------------------------------------- |
| `success`     | Something worked well         | "TDD approach caught 3 edge cases early"                |
| `failure`     | Something went wrong          | "Skipped context map, broke downstream API"             |
| `decision`    | A non-obvious choice was made | "Chose YAML over JSON for pipeline format"              |
| `pattern`     | A recurring theme noticed     | "Third time blast radius > 10 files in auth module"     |
| `observation` | Something worth noting        | "OpenCode reads CLAUDE.md differently than Claude Code" |


---

## Episode Surfacing

At session start (SURVEY phase), surface relevant episodes:

### Relevance Scoring

```
relevance = recency_weight * recency_score
           + tag_match_weight * tag_overlap
           + reinforcement_weight * reinforcement_count
```

**Canonical read path**: The context-recall skill is the canonical read path
for this step; if context-recall is available, invoke it instead of running
this section manually.

### Surfacing Format

```
📝 Relevant episodes from recent sessions:

1. [2026-04-03] (pattern) "Context mapping before cross-module changes
   prevents cascade failures" — reinforced 3x

2. [2026-04-02] (decision) "Entropy guard formula: files + creates +
   3*deletes + lines/100 — working well in practice"
```

---

## Auto-Classification

When an episode is captured, auto-classify using the Promotion Rubric's
four questions:

```yaml
classification:
  scope: generic | repo-local | personal
  reuse_potential: high | medium | low
  maturity: single-episode | reinforced | proven
  recommended_home: toolkit | repo | personal | not-yet
```

Classification is recorded with the episode but does NOT trigger automatic
promotion. Promotion always requires human approval.

---

## Promotion Proposal

When a pattern has been reinforced across 2+ episodes:

```markdown
## Promotion Proposal

**Pattern**: {description}
**Evidence**:
- Episode {id1} ({date}): {summary}
- Episode {id2} ({date}): {summary}

**Rubric Assessment**:
- A. Scope: {generic / repo-local}
- B. Reuse: {yes / no}
- C. Preference: {no — this is objective}
- D. Maturity: {reinforced across N sessions}

**Recommended Home**: {skills/ | agents/ | repo-local}
**Proposed Action**: {create skill | update instruction | add to patterns.yaml}

⏳ Awaiting human approval
```

---

## When Not to Add a Pattern

Do not add a pattern to the promotion path just because an episode feels important.
Prefer keeping the lesson in M3 only when any of the following are true:

- The lesson is based on a single event and has not been reinforced across sessions.
- The behavior is highly repo-local, temporary, or tied to one branch, one incident, or one
  short-lived tool version.
- The lesson captures a personal preference rather than an objective, reusable rule.
- The evidence set is contradictory or stale and needs more observation before promotion.
- The tags are unstable or too specific, which would turn M2 into a junk drawer of narrow cases.

If unsure, keep the episode in M3, improve the tags, and wait for reinforcement before proposing
promotion. Human approval remains the final gate for M2 changes.

---

## Best Practices


| Practice                                 | Rationale                                             |
| ---------------------------------------- | ----------------------------------------------------- |
| **Capture failures, not just successes** | Failures teach more — don't filter them out           |
| **Be specific, not generic**             | "Ruff caught type error in auth.py" > "linting helps" |
| **Tag consistently**                     | Use a small, stable tag vocabulary                    |
| **Don't force promotions**               | Let patterns prove themselves over 3+ sessions        |
| **Review episodes periodically**         | Stale episodes decay — that's fine                    |

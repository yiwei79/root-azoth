---
name: context-recall
description: |
  Read M3 episodes and M2 patterns by goal tags before architect planning or SURVEY
  session start (D45 memory read path).
version: "1.0"
layer: mineral
governance_anchor: D45
---

# Context Recall

Read relevant episodes and patterns from Azoth memory before planning begins.
Closes the write-only memory sink problem — M3/M2 accumulate but nothing reads
them back into session behavior without this skill.

## Overview

The Azoth memory system writes reliably (M3 episodes via `remember`, M2 patterns
via `/promote`) but has no automatic read-back path. Without this skill, every
session starts cold regardless of how much relevant prior context exists.

Context-recall extracts tags from the current goal, scores M3 episodes and M2
patterns against those tags, and surfaces the top 1-3 most relevant items before
the architect begins planning. This bridges the write-only sink into an actionable
feedback loop.

```
Current goal → Extract tags → Score M3 + M2 → Rank → Surface top 1-3 → Architect plans
```

## When to Use

Invoke this skill in the following contexts:

- **SURVEY phase** (session start) — before declaring a goal or opening a scope card.
  Surface what prior sessions learned about the domain before committing to a plan.
- **Stage 2 entry** (pipeline Architect stage) — before reading the codebase or
  composing a design. Recall what prior deliveries in this area produced or failed.
- **Explicit recall** — when the human or orchestrator says "recall context for X"
  or "what do we know about Y from prior sessions."

## Scoring Algorithm

Execute the following steps in order. The result is a ranked list of top 1-3
candidates (episodes and/or patterns combined).

```
Step 1 — Extract tags
  Extract 3-5 tags from the current session goal.
  Tags are noun phrases: topic, type, domain, artifact name.
  Example: goal "Build context-recall skill" → tags: ["context-recall", "skill", "memory", "read-path"]

Step 2 — Score M3 episodes
  For each episode in .azoth/memory/episodes.jsonl:
    tag_overlap_count    = count of goal tags that appear in episode["tags"]
    days_since_timestamp = (today - episode["timestamp"].date()).days
    score = tag_overlap_count * 2
          + (1 / max(days_since_timestamp, 0.5))
          + reinforcement_count * 0.5
  Note: max(days_since_timestamp, 0.5) prevents division-by-zero for same-day episodes.

Step 3 — Score M2 patterns
  M2 read authorization: patterns in .azoth/memory/patterns.yaml are human-approved
  knowledge. Reading them is permitted and not restricted by GOVERNANCE.md (which
  governs writes to M2 via the promotion protocol, not reads). If patterns.yaml is
  absent, skip this step gracefully and proceed with M3 results only.

  For each pattern in .azoth/memory/patterns.yaml:
    trigger_match    = 1 if any goal tag appears in pattern["trigger"], else 0
    reinforcements   = len(pattern["reinforced_by"])
    score = trigger_match * 3
          + reinforcements * 0.5

Step 4 — Tiebreaker
  When two candidates share equal scores, the most recent timestamp wins.

Step 5 — Surface top 1-3
  Collect all scored candidates (episodes + patterns), sort descending by score,
  return the top 1-3. If no candidates score above 0, return empty (no forced output).
```

## Output Format

Surface results using this format. Omit sections with no matches.

```markdown
## Context Recall

**Relevant context for: {goal-summary}**

1. [ep-NNN] ({date}) — {type}: {one-line summary}
   Lessons: {first lesson from lessons array}

2. [pattern: {pattern-id}] — {trigger phrase}: {one-line summary}
   Apply: {how_to_apply — first sentence only}
```

If no episodes or patterns score above zero, output:

```markdown
## Context Recall

No prior context found for: {goal-summary}
```

## Integration

### With `remember` skill

`remember` is the write path for M3 episodes. `context-recall` is the canonical
read path. They are complementary: `remember` captures at session close;
`context-recall` surfaces at session open. Do not use the Episode Surfacing section
in `remember` directly — invoke `context-recall` instead for consistency.

### With `full.pipeline.yaml`

`context-recall` is an optional tool in the `architect-design` stage. Invoke it
before reading the codebase to prime the architect with relevant prior session
knowledge.

### With `.azoth/memory/`

Reads from:
- `.azoth/memory/episodes.jsonl` — M3 append-only episode log
- `.azoth/memory/patterns.yaml` — M2 human-approved patterns (read-only; absence
  handled gracefully)

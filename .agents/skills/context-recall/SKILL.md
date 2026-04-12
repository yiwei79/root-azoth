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

## Tag Vocabulary Guidance

Recall quality depends on a small, stable tag vocabulary. Prefer 3-5 reusable noun
phrases that map to actual retrieval needs rather than ad hoc prose copied from the
current prompt.

- Prefer durable artifact/domain tags such as `context-recall`, `memory`, `pipeline`,
  `deliver-full`, or a concrete file/skill name.
- Reuse existing tags when an episode already names the same topic; do not create near
  synonyms like `recall`, `context-recall-skill`, and `memory-read-path` for one idea.
- Keep tags broad enough to match future sessions, but not so broad that every episode
  matches everything.
- If a goal includes a new term, pair it with at least one established tag so recall can
  bridge old and new vocabulary.

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

Step 5 — Contradiction, stale, and supersession handling
  Before final output, review the top candidates for conflict:
  - contradiction: two recalled items recommend incompatible actions
  - stale: an older item no longer reflects the current toolchain, governance, or repo shape
  - supersede: a newer item explicitly replaces an older lesson for the same tag set

  Policy:
  - Keep M3 append-only; never rewrite old episodes during recall.
  - If a newer candidate replaces an older one, treat the older item as archive context and
    mark the newer lesson as the one that supersedes it.
  - If two items contradict each other and no clear winner exists, surface both and flag the
    contradiction instead of collapsing them into a fake consensus.
  - If an item is only historical background, label it archive/stale and rank it below the
    fresher lesson even if the tag overlap is similar.

Step 6 — Surface top 1-3
  Collect all scored candidates (episodes + patterns), sort descending by score,
  return the top 1-3. If no candidates score above 0, return empty (no forced output).
```

## Conflict Handling Notes

Use explicit recall notes when a recalled item is risky to apply as-is.

- **Contradiction** — say which items disagree and what decision axis changed.
- **Stale episode** — call out why the lesson may be stale (old workflow, renamed file,
  replaced governance rule, outdated install path).
- **Archive vs supersede** — archived items remain readable background; supersede means a
  newer lesson should be preferred for action under the same tags.

## Output Format

Surface results using this format. Omit sections with no matches.

```markdown
## Context Recall

**Relevant context for: {goal-summary}**

1. [ep-NNN] ({date}) — {type}: {one-line summary}
   Lessons: {first lesson from lessons array}
   Status: active | archive | superseded | contradiction

2. [pattern: {pattern-id}] — {trigger phrase}: {one-line summary}
   Apply: {how_to_apply — first sentence only}
```

If no episodes or patterns score above zero, output:

```markdown
## Context Recall

No prior context found for: {goal-summary}
```

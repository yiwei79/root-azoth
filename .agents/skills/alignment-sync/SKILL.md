---
name: alignment-sync
description: |
  Produce pull-based alignment summaries (phone-friendly) at pipeline stage boundaries,
  human gates, entropy zone shifts, session closeout, or when the human asks for status.
---

# Alignment Sync

Generate concise, phone-friendly alignment summaries. The human reviews
when ready — agents never block waiting for attention.

## Overview

Alignment is PULL-based in Azoth. Agents complete work, produce summaries,
and the human reviews on their own schedule. Summaries must be optimized
for quick comprehension — often on a phone screen.

```
Work Complete → Generate Summary → Human Pulls When Ready → Signal Received → Continue
```

### Machine-readable handoff (BL-012)

For `/auto`, `/deliver`, and `/deliver-full`, the **canonical** inter-stage artifact is a YAML
document validated by `pipelines/stage-summary.schema.yaml`. Markdown summaries in this skill
remain valuable for **human** pull review (phone-friendly, narrative context); they do
**not** replace the typed stage summary for orchestrator forwarding.

## When to Use

- **Pipeline stage completion** — every stage produces a summary
- **Human gate reached** — summary + decision options
- **Entropy escalation** — yellow/red zone triggers immediate summary
- **Session close** — comprehensive session summary
- **On demand** — when human asks "what's the status?"

---

## Summary Format

### Standard Alignment Summary

```markdown
## Alignment Summary — {stage_name}

**Status**: {complete | blocked | needs-input}
**Entropy**: {GREEN | YELLOW | RED} (delta: {N})

### Done
- {what was completed, 1-3 bullets}

### Decisions
- {non-obvious decisions with reasoning}

### Open
- {questions or blockers, numbered for easy response}

### Next
{what happens next, or what signal is needed}
```

### Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Max words | 500 | Phone screen readability |
| Max bullets per section | 5 | Scannability |
| Questions numbered | Always | Easy to respond "approve 1, adjust 2" |
| Status + entropy first | Always | Most important info above the fold |
| Jargon | Minimal | Define if unavoidable |

---

## Summary Types

### Stage Completion Summary

Used after completing a pipeline stage.

```markdown
## Alignment — Planning Complete

**Status**: complete
**Entropy**: GREEN (delta: 0 — planning only)

### Done
- Decomposed "add entropy-guard skill" into 4 tasks
- Defined test strategy: 5 unit tests, 2 integration

### Decisions
- Chose formula: files + creates + 3*deletes + lines/100 (matches Trust Contract)

### Next
Ready for Test Design stage. Awaiting architect review (agent gate).
```

### Human Gate Summary

Used when a human decision is needed.

```markdown
## Alignment — Design Review Required

**Status**: needs-input
**Entropy**: GREEN (delta: 2.1)

### Done
- Architect produced design brief for auth refactor
- Blast radius: 8 files across 2 modules

### Decisions Needed
1. Approach A (modify existing) vs B (rewrite) — recommend A (lower risk)
2. Include migration script? (adds 3 files to scope)

### Options
- `approve` — proceed with recommended approach (A, no migration)
- `approve 1, adjust 2: yes include migration`
- `stop` — pause for discussion
```

### Entropy Alert Summary

Used when entering yellow or red zone.

```markdown
## ⚠️ Entropy Alert — YELLOW Zone

**Status**: checkpoint-recommended
**Entropy**: YELLOW (delta: 7.3, session: 12.1)

### Recent Changes
- Modified 5 files in auth/ module
- Created 2 new test files
- 280 lines changed

### Checkpoint
Created: `azoth-checkpoint-1712188800`

### Options
- `continue` — proceed (approaching red at 10)
- `scope-down` — split remaining work into next session
- `rollback` — restore to checkpoint
```

### Session Close Summary

Used during HARDEN phase.

```markdown
## Session Summary — 2026-04-04

**Status**: complete
**Session entropy**: 8.4 (YELLOW peak, GREEN average)
**Duration**: ~45 minutes

### Accomplished
- Created entropy-guard skill (SKILL.md + integration)
- Added 5 drift detection tests — all passing
- Updated azoth.yaml manifest

### Episode Captured
- Type: success
- Lesson: "Entropy formula works well for file-centric changes, may need
  tuning for large refactors"

### Promotions Proposed
- None this session (too early for pattern reinforcement)

### Next Session
- Continue Phase 2: alignment-sync and self-improve skills remaining
- Then: skill drift detection test suite
```

---

## Human Signal Reference

| Signal | Meaning | Agent Response |
|--------|---------|---------------|
| `continue` / `approve` / `yes` | Proceed | Advance pipeline |
| `approve N` | Approve specific numbered item | Apply selective approval |
| `adjust: {feedback}` | Modify and retry | Re-execute with feedback |
| `stop` / `hold` | Halt pipeline | Preserve state, await |
| `rollback` | Revert to checkpoint | Restore and report |
| `status` | Request summary | Generate fresh summary |

---

## Best Practices

| Practice | Rationale |
|----------|-----------|
| **Lead with status + entropy** | Human needs these two facts first |
| **Number all questions** | Enables terse responses ("approve 1, 3") |
| **500 word max** | Phone readability — respect human attention |
| **No filler** | Anti-slop: every word must carry information |
| **Include options** | Don't make human figure out what to say next |

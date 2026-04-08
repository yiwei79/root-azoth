---
name: entropy-guard
description: |
  Track session entropy, blast radius, and Trust Contract ceilings during pipelines; decide
  when to checkpoint or escalate before thresholds are exceeded.
---

# Entropy Guard

Monitor and bound session entropy. Prevent any single turn or stage from
creating unrecoverable damage.

## Overview

Entropy is the measure of how much a session has changed. The entropy guard
tracks changes in real-time and triggers checkpoints or human escalation
when thresholds are approached.

```
Action → Measure Delta → Accumulate → Check Zone → Respond
                                         │
                              GREEN: proceed
                              YELLOW: checkpoint recommended
                              RED: checkpoint required + notify human
```

## When to Use

- **Continuously** during the OPERATE phase — entropy is always monitored
- **Before risky operations** — calculate expected entropy before acting
- **At pipeline stage boundaries** — report cumulative entropy
- **When scope creep is suspected** — entropy spike = scope expansion

---

## Entropy Calculation

### Per-Turn Delta

```
entropy_delta = files_changed + files_created + (files_deleted * 3) + (lines_changed / 100)
```

**Why this formula:**

- File changes and creates are weighted equally (1 each)
- Deletions are weighted 3x because they're harder to recover
- Line changes are normalized (100 lines ≈ 1 unit of entropy)

### Cumulative Session Entropy

```
session_entropy = sum(entropy_delta for each turn)
```

### Zone Classification


| Zone   | Threshold      | Meaning              | Response                          |
| ------ | -------------- | -------------------- | --------------------------------- |
| GREEN  | delta < 5      | Normal operation     | Proceed freely                    |
| YELLOW | 5 ≤ delta < 10 | Elevated change rate | Checkpoint recommended            |
| RED    | delta ≥ 10     | High change rate     | Checkpoint required, notify human |


### Per-Turn Limits (from Trust Contract)


| Resource         | Limit | On Exceed                   |
| ---------------- | ----- | --------------------------- |
| Files modified   | 10    | Checkpoint + human approval |
| Files created    | 10    | Checkpoint + human approval |
| Files deleted    | 0     | Always human approval       |
| Lines changed    | 500   | Checkpoint + human approval |
| New dependencies | 0     | Always human approval       |
| Kernel files     | 0     | Always human approval       |


---

## Checkpoint Protocol

When entropy threshold is approached or exceeded:

### 1. Create Checkpoint

Prefer the mechanical helper (repo root): `python3 scripts/azoth_checkpoint.py create`
(stash) or `python3 scripts/azoth_checkpoint.py tag` (lightweight tag on `HEAD`). Same naming
convention as below; see `--help` for `git stash apply` vs `git stash pop`.

```bash
# For uncommitted work:
git stash push -m "azoth-checkpoint-$(date +%s)"

# For committed work:
git tag "azoth/checkpoint/$(date +%s)"
```

### 2. Generate Entropy Report

```markdown
## Entropy Report — Turn {N}

**Zone**: {GREEN | YELLOW | RED}
**Turn delta**: {N} (files: {M} changed, {C} created, {D} deleted; lines: {L})
**Session cumulative**: {N}

### Changes This Turn
- {file}: {created | modified | deleted} ({lines} lines)

### Checkpoint
- Type: {git stash | git tag}
- Reference: {stash ref or tag name}

### Recommendation
- {continue | scope-down | human-approval-needed}
```

### 3. Present to Human (if RED zone)

Include the entropy report in the alignment summary with clear options:

- Continue with current scope
- Scope down to reduce entropy
- Rollback to checkpoint

---

## Proactive Entropy Monitoring

The entropy guard operates at **always-do** posture tier. It should:

1. **Pre-calculate** entropy before executing a plan step
2. **Warn early** when approaching yellow zone (at 80% of threshold)
3. **Suggest scope splits** when a single task would exceed red zone
4. **Track trends** — if entropy is accelerating, flag it

### Pre-Execution Check

Before executing a planned change:

```
Planned changes: 7 files, ~300 lines
Current session entropy: 4.2
Expected delta: 7 + 3.0 = 10.0
Expected zone after: RED

⚠️ This operation would push session entropy into RED zone.
Recommendation: Checkpoint first, or split into 2 smaller operations.
```

---

## Integration

### With Bootloader

- **OPERATE**: Entropy guard is active throughout
- **HARDEN**: Final entropy report included in session summary

### With Pipeline

- Stage boundaries trigger entropy reports
- Gate evaluations consider entropy zone

### With Trust Contract

- Entropy guard ENFORCES the Trust Contract's entropy ceiling
- Per-turn limits are the Trust Contract's rules, not the guard's

### With Alignment-Sync

- Entropy zone is always included in alignment summaries
- RED zone triggers immediate alignment summary

### With Remember

- Entropy events (yellow/red zone entries) are recorded as episodes
- Patterns in entropy can drive process improvements

---

## Telemetry Record

**D14 / P5-004:** Durable audit lines are appended by `.claude/hooks/session_telemetry.py`
(PreToolUse orchestrator + optional session events). See `kernel/GOVERNANCE.md` §6 and
`docs/AZOTH_ARCHITECTURE.md` §9 for canonical **`outcome`** values (`allowed` / `denied` vs `success`).

The JSON below is an **illustrative** entropy-oriented record; actual lines may include
`source`, `denial_stage`, `entropy_delta`, `cumulative_entropy`, `entropy_zone`, etc.

```json
{
  "session_id": "uuid",
  "turn": 3,
  "entropy_delta": 4.2,
  "cumulative": 8.7,
  "zone": "yellow",
  "files_changed": 3,
  "files_created": 1,
  "lines_changed": 120,
  "checkpoint_created": true,
  "timestamp": "ISO-8601"
}
```

Stored in `.azoth/telemetry/session-log.jsonl`.
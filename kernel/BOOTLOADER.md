# Azoth Bootloader

> The boot sequence every Azoth-powered session executes.
> This file is Layer 0 (Molecule) — immutable without human approval.

---

## Boot Sequence

Every session follows four phases. The agent reads this file (via CLAUDE.md)
and executes each phase in order. No phase may be skipped.

```
ACTIVATE → SURVEY → OPERATE → HARDEN
```

---

## Phase 1: ACTIVATE

**Purpose**: Load identity, constraints, and trust boundaries.

1. Read `CLAUDE.md` — project instructions, routing table, current phase
2. **Resolve governance path `G` (D42 path duality):**
   - If `kernel/TRUST_CONTRACT.md` exists at the repo root → **`G` := `kernel`**
   - Else if `.azoth/kernel/TRUST_CONTRACT.md` exists → **`G` := `.azoth/kernel`**
   - Else → STOP; report missing governance files to the human (neither scaffold nor consumer layout detected).
3. Read `G/TRUST_CONTRACT.md` — entropy ceiling, alignment protocol
4. Read `G/GOVERNANCE.md` — HITL gates, promotion rules, **Section 2** for typed gate catalog (D24) and mandatory human gates
5. Load bootloader state (`.azoth/bootloader-state.md` if present)
6. Validate kernel integrity:
   - Hash the deployed governance files against `.azoth/kernel-checksums.sha256` (see checksum manifest under `.azoth/`)
   - If drift detected → STOP, report to human, await signal

**Output**: Agent identity loaded, trust boundaries active.

**Failure mode**: If any kernel file is missing or corrupted, halt and report.
Do not proceed with degraded governance.

---

## Phase 2: SURVEY

**Purpose**: Understand the current project and session context.

1. Read project structure (key directories, languages, frameworks)
2. Load memory state:
   - M3: `.azoth/memory/episodes.jsonl` — recent episodes
   - M2: `.azoth/memory/patterns.yaml` — proven patterns
3. Check git state: branch, recent commits, uncommitted changes
4. Identify current phase from `azoth.yaml` manifest
5. Load development roadmap (`.azoth/roadmap.yaml`):
   - Current phase and phase title
   - Next priority task (first unblocked `pending` task)
   - Report: "Phase {N}: {title} — Next: [{task_id}] {task_title}"
6. Surface relevant patterns from memory:
   - "Last session worked on X"
   - "Known issue: Y"
   - "Pattern Z applies here"
7. Check insight inbox (`.azoth/inbox/*.jsonl`):
   - If files present → report count to human
   - Suggest running `/intake` to process queued insights

**Preflight gate**: Before proceeding to OPERATE, confirm readiness:
- ✅ Kernel integrity verified (ACTIVATE passed)
- ✅ Memory files loaded (or bootstrapping from zero)
- ✅ Git state understood
- ✅ Current phase and next task identified
- If any check FAILED → report to human, await signal before OPERATE

**Output**: Context map — what exists, what's in progress, what matters.

**Failure mode**: If memory files are absent (first session), note it and
proceed. Memory bootstraps from zero — this is expected.

---

## Phase 3: OPERATE

**Purpose**: Execute the session's goal within trust boundaries.

1. Receive goal from human
2. Classify goal (via auto-pipeline, D23):
   - Scope: kernel | skills | agents | pipelines | docs | mixed
   - Risk: governance-change | breaking-change | additive | cosmetic
   - Complexity: simple | medium | complex
   - Knowledge: known-pattern | needs-research | novel
3. Compose pipeline from classification (or accept explicit pipeline choice)
4. Present pipeline to human for approval
5. Execute pipeline stages, respecting gate types in `GOVERNANCE.md` Section 2 of the governance copy loaded in ACTIVATE (`G/GOVERNANCE.md`) — `human` vs `agent` approvers, mandatory human gates.
6. Monitor entropy throughout:
   - Track files changed, scope of modifications
   - If approaching entropy ceiling → checkpoint and report

**Output**: Delivered work product, passing tests, alignment summary.

**Failure mode**: If entropy ceiling is breached, checkpoint immediately
and present alignment summary. Do not continue without human signal.

---

## Phase 4: HARDEN

**Purpose**: Capture learnings, verify integrity, prepare for next session.

1. Capture episode in M3 (`.azoth/memory/episodes.jsonl`):
   - What was the goal?
   - What pipeline was used?
   - What worked? What didn't?
   - What patterns emerged?
2. Run drift detection:
   - Re-hash kernel files
   - Compare against session-start checksums
   - Report any unexpected changes
3. Generate alignment summary (<500 words, phone-friendly):
   - Work completed
   - Decisions made
   - Open questions
   - Suggested next steps
4. Update bootloader state (`.azoth/bootloader-state.md`):
   - Session count
   - Last goal
   - Active phase
   - Pending promotions
5. Propose M3 → M2 promotions if patterns are mature enough

**Output**: Session closed, state persisted, human can review asynchronously.

**Failure mode**: If episode capture fails, warn human but do not block
session close. Memory is important but not worth losing work over.

---

## Bootloader State Schema

The file `.azoth/bootloader-state.md` tracks cross-session state:

```yaml
session_count: 0
last_session:
  date: null
  goal: null
  pipeline: null
  outcome: null
active_phase: 1
pending_promotions: []
kernel_checksum: null
```

This file is runtime state (gitignored) — it is NOT part of the kernel.

---

## Integration Points

| Phase | Reads | Writes |
|-------|-------|--------|
| ACTIVATE | CLAUDE.md, `G/*` governance files (see ACTIVATE step 2), `.azoth/bootloader-state.md` | — |
| SURVEY | Project files, .azoth/memory/*, azoth.yaml, .azoth/roadmap.yaml, .azoth/inbox/*.jsonl | — |
| OPERATE | Pipeline definitions, agent configs | Source files, tests |
| HARDEN | Kernel checksums | .azoth/memory/*, .azoth/bootloader-state.md |

---

## Invariants

These hold true across ALL sessions, ALL projects:

1. **Kernel files are never modified without human approval** — Phase 1 (ACTIVATE) enforces this via integrity checks
2. **Every session produces an episode** — Phase 4 (HARDEN) captures it in M3
3. **Entropy is bounded** — Phase 3 (OPERATE) monitors and checkpoints
4. **Human alignment is PULL-based** — agent produces summaries, human reviews when ready
5. **Boot sequence is deterministic** — same inputs produce same agent state

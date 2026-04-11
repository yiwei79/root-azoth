# Session Lifecycle

> The full flow from opening a session to closing it.

## The Three Phases

Every Azoth session follows three phases:

```
┌───────────┐         ┌───────────┐         ┌───────────┐
│  ORIENT   │────────▶│  EXECUTE  │────────▶│  CLOSE    │
│           │         │           │         │           │
│  /start   │         │  /auto    │         │ /session- │
│  /next    │         │  /deliver │         │  closeout │
│           │         │  /deliver │         │           │
│           │         │   -full   │         │           │
└───────────┘         └───────────┘         └───────────┘
   5 min                 30-120 min             5 min
```

---

## Phase 1: Orient (`/start`)

```
You: /start
```

The welcome dashboard shows you:

```
┌─────────────────────────────────────────────────┐
│  🧪 AZOTH v0.1.1.32                             │
│  Phase: v0.2.0-p1 │ Branch: patch/v0.2.0-p1-…  │
├─────────────────────────────────────────────────┤
│  Top Backlog:                                    │
│    P1-001  Closeout script (priority 1)         │
│    P1-009  Memory M3→M2 promotion (priority 2)  │
│    P1-010  Entropy tracker (priority 3)          │
├─────────────────────────────────────────────────┤
│  Last Session: ep-127                            │
│  Pipeline UX friction reduction (S1-S4)          │
├─────────────────────────────────────────────────┤
│  What next?                                      │
│    • next    — pick top backlog item              │
│    • resume  — continue prior session             │
│    • intake  — process queued insights            │
│    • /auto   — freeform goal                      │
└─────────────────────────────────────────────────┘
```

### Routing options

| Command | When to use |
|---------|-------------|
| `next` | Pick the highest-priority backlog item |
| `resume <id>` | Continue an interrupted session |
| `intake` | Process insight files from `.azoth/inbox/` |
| `/auto <goal>` | Start with a specific goal |

---

## Phase 2: Execute (Pipeline)

Once you have a goal, execute it through a pipeline.

### Scope Gate

Before any work begins, a **scope gate** records what was approved:

```json
{
  "session_id": "abc-123",
  "goal": "add retry mechanism",
  "approved": true,
  "approved_by": "human",
  "expires_at": "2026-04-12T01:00:00Z",
  "backlog_id": "ad-hoc",
  "delivery_pipeline": "auto",
  "target_layer": "mineral"
}
```

This file (`.azoth/scope-gate.json`) acts as a **lock** — agents can only
write code when the scope gate is approved and unexpired.

### Agent Stages Run

Each stage runs in sequence with typed handoffs:

```
                    Typed YAML Handoff
                    ─────────────────
  Stage N ──────────────────────────────▶ Stage N+1

  Contains:
  • stage_id: what stage produced this
  • status: completed | needs-input | blocked
  • summary: what was done
  • artifacts: files created/modified
  • entropy: GREEN | YELLOW | RED
  • concerns: issues for next stage
```

### Entropy Tracking

Azoth tracks how many files you've changed to prevent scope creep:

```
  GREEN  (0-11 files)   ──  Safe. Keep going.
  YELLOW (12-24 files)  ──  Checkpoint recommended.
  RED    (25+ files)    ──  Stop. Split the work.
```

---

## Phase 3: Close (`/session-closeout`)

```
You: /session-closeout
```

Closeout performs 4 write phases:

```
┌───────────────────────────────────────────────────────┐
│  W1: EPISODE                                          │
│  Append to .azoth/memory/episodes.jsonl               │
│  What happened, what was learned, tags for recall.     │
├───────────────────────────────────────────────────────┤
│  W2: STATE                                            │
│  Update bootloader-state.md, close scope gate,        │
│  refresh session-state.md for cross-IDE handoff.       │
├───────────────────────────────────────────────────────┤
│  W3: MEMORY MIRROR                                    │
│  Sync to ~/.claude/projects/.../memory/ so Claude     │
│  Code sessions can read Copilot-authored state.        │
├───────────────────────────────────────────────────────┤
│  W4: VERSION                                          │
│  Bump patch version (e.g., 0.1.1.31 → 0.1.1.32).     │
│  Git commit the closeout.                              │
└───────────────────────────────────────────────────────┘
```

### Why closeout matters

- **Memory**: Future sessions read past episodes to avoid repeating mistakes
- **Continuity**: `bootloader-state.md` tells the next session exactly where
  things left off
- **Cross-IDE**: If you switch from Copilot to Claude Code (or vice versa),
  the handoff state travels with you
- **Versioning**: Every session bumps the patch version — you always know
  what changed when

---

## Full Session Example

```
You: /start                                    ← Orient
     → Dashboard shows P1-001 as top priority

You: /auto implement the closeout script       ← Declare + Execute
     → Classification: skills / additive / medium / known-pattern
     → Pipeline: planner → evaluator → builder → architect
     → "Approve? [yes / adjust / abort]"

You: yes                                       ← Approve
     → Scope gate written
     → Planner: 6 tasks, TDD approach
     → Evaluator: 0.89 (PASS)
     → Builder: 4 files created, 12 tests pass
     → Architect: APPROVED

You: /session-closeout                         ← Close
     → ep-128 saved
     → Version bumped to 0.1.1.33
     → Git committed
```

Total human interaction: **3 messages** (start, approve, closeout).

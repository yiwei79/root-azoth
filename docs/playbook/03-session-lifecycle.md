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

Codex note: the same lifecycle is start-centered. Use `$azoth-start`, `$azoth-start next`, `$azoth-start pipeline_command=<...> <goal>`, and `$azoth-start closeout`. `$azoth-session-closeout` remains a direct wrapper, while literal slash tokens are compatibility fallback in Codex, not the primary daily path.

---

## Phase 1: Orient (`/start`, or `$azoth-start` in Codex)

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
│    • resume  — reopen parked current session      │
│    • resume <id> — reopen another parked session  │
│    • intake  — process queued insights            │
│    • /auto   — freeform goal                      │
└─────────────────────────────────────────────────┘
```

### Routing options

| Command | When to use |
|---------|-------------|
| `next` | Pick the highest-priority backlog item |
| `resume` | Reopen the parked session for this thread without a second scope approval |
| `resume <id>` | Reopen an interrupted parked session from another thread |
| `intake` | Process insight files from `.azoth/inbox/` |
| `/auto <goal>` | Start with a specific goal |

In Codex, route those same choices through `$azoth-start ...` instead of splitting the daily path into `/start -> /next -> /auto`.

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

### TTL Management (v2)

The scope gate has a **2-hour TTL**. The orchestrator now manages this actively:

```
  TTL Status           Action
  ──────────           ──────
  > 15 min remaining   Keep going normally.
  < 15 min remaining   TTL card: extend / checkpoint / abort.
  Expired              Pipeline halts. Re-scope with /next or /resume.
```

**In-place extension**: the orchestrator can extend TTL by 1 hour mid-pipeline
without full re-scoping — it updates `expires_at` directly and surfaces a card
so you always know.

### Agent Stages Run

Each stage runs in sequence with typed handoffs:

```

### Stage-aware resume

When a session is parked, Azoth separates three concerns:

- Scope restoration via `.azoth/scope-gate.json`
- Pipeline checkpoint restoration via `.azoth/run-ledger.local.yaml`
- Cross-IDE mirror state via `.azoth/session-state.md`

`/resume` restores the approved scope directly; it does not ask for a second
scope-approval card. If a saved run checkpoint exists, Azoth restores the saved
pipeline gate and resumes from the stored stage or human gate. If no checkpoint
exists, `/resume` restores scope only and routes back to pipeline selection,
with `/auto` Stage 0 as the default recommendation.

Only live approved scopes and parked sessions are resumable. A session that is
closed or administratively finalized is non-resumable: open a fresh scope with
`/next` instead of trying to reopen it with `/resume`.

Checkpoint mirror shape:

```yaml
session_id: abc-123
state: parked
pipeline: auto
pipeline_position: 2
current_stage_id: architect_review
completed_stages: [planner]
pending_stages: [builder_apply, reviewer_gate]
pause_reason: human-gate
active_run_id: run-123
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
│  refresh session-state.md for cross-IDE handoff,       │
│  preserving any stage-aware resume checkpoint fields   │
│  only for a parked handoff. Closed or administratively │
│  finalized closeout clears the saved checkpoint so     │
│  `/resume` cannot reopen finished work.                │
│  For roadmap/planning sessions, also sync initiative   │
│  and backlog continuity so the next action is a real   │
│  queued item, not only a spec or stale pointer.        │
├───────────────────────────────────────────────────────┤
│  W3: MEMORY MIRROR                                    │
│  Best-effort sync to ~/.claude/projects/.../memory/   │
│  and log `W3 deferred` when the path is unavailable.  │
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
- **Cross-IDE**: If you switch between Codex, Claude Code, Copilot, or another
  supported adapter, the repo-local handoff state and any saved pipeline checkpoint
  travel with you; W3 is a best-effort Claude memory mirror
- **Versioning**: Every session bumps the patch version — you always know
  what changed when

In Codex, W3 is supplemental: W2 repo-local state wins if W2 and W3 diverge, and W3 deferral must never block W4.

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

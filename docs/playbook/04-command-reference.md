# Command Reference

> Quick reference for Azoth commands across slash-native and skill-routed surfaces.

Claude/Cursor/OpenCode can use slash-style command text directly. In Codex, calm
flow prefers `/skills` with `$azoth-start` as the daily entry surface; compatibility
wrappers and raw slash tokens still work, but routed workflow commands normalize
back through the same start-centered control plane.

## Pipeline Commands

### `/auto <goal>`
**The smart default.** Classifies your goal and composes the optimal pipeline.

```
/auto add input validation to the signup form
```

- **Gates**: 1 fused Declaration (scope + pipeline in one approval)
- **Lightweight path**: known-pattern + non-governance → informational auto-proceed
- **Stages**: 3-6 depending on classification (see auto-router rules)
- **Codex canonical route**: `$azoth-start pipeline_command=auto <goal>`

---

### `/deliver <goal>`
**Lean pipeline for pre-approved, additive work.** Fixed 5-stage structure.

```
/deliver implement the caching layer per approved design
```

- **Gates**: 1 human gate (final approval)
- **Stages**: pipeline-gate → planner → test-builder → builder → architect-review
- **Use when**: Work is already scoped and approved, non-governance
- **Codex canonical route**: `$azoth-start pipeline_command=deliver <goal>`

---

### `/deliver-full <goal>`
**Full governance pipeline.** For kernel, governance, or breaking changes.

```
/deliver-full update the trust contract for new agent tier
```

- **Gates**: 3 human gates (goal, design, delivery)
- **Stages**: goal-clarify → architect → governance-review → planner → test-builder → builder → architect-review
- **Use when**: Touching kernel/, governance rules, or making breaking changes
- **Codex canonical route**: `$azoth-start pipeline_command=deliver-full <goal>`

---

### `/dynamic-full-auto <goal>`
**Adaptive discovery + delivery.** Research swarms explore first, then routes to the right delivery pipeline.

```
/dynamic-full-auto investigate why pipeline latency increased 3x
```

- **Gates**: 1-2 human gates (checkpoint Γ + delivery)
- **Stages**: discovery waves → queen merge → checkpoint Γ → auto-route to delivery
- **Use when**: You don't know the solution yet and need exploration

---

## Session Commands

### `/start`
**Session welcome dashboard.** Shows repo state, backlog, and routing options.
**Agent**: orchestrator (preserved across all platforms).

```
/start
```

Routes to: `next`, `resume`, `intake`, `promote`, `eval`, `roadmap`, or custom goal.

In Codex calm flow, prefer `$azoth-start`, `$azoth-start next`, `$azoth-start closeout`,
or `$azoth-start <goal>` for the same routes.

---

### `/next`
**Scope card builder.** Picks the highest-priority backlog item and opens a scope gate.
**Agent**: orchestrator (preserved across all platforms).

```
/next
```

Writes `.azoth/scope-gate.json` after human approval. Not needed when using `/auto` (fused Declaration handles it).
In Codex, the canonical daily equivalent is `$azoth-start next`.

---

### `/session-closeout`
**Unified eval + close + sync.** Run at the end of every session.

```
/session-closeout
```

Performs W1-W4: episode capture, state update, memory mirror, version bump.
In Codex calm flow, prefer `$azoth-start closeout` or use `$azoth-session-closeout`
directly. W3 is best-effort and may log `W3 deferred`; repo-local W1/W2/W4 remain
authoritative.

---

## Utility Commands

### `/intake`
**Process queued insights** from `.azoth/inbox/*.jsonl` through the governed intake protocol.

### `/promote`
**Review M3→M2 promotion candidates.** Surfaces recurring patterns from episodes for human-approved promotion to semantic memory.

### `/eval <artifact>`
**Quality gate.** Evaluate artifacts against rubrics. Auto-escalates to swarm evaluation when triggers fire.

### `/plan <goal>`
**Structured planning without execution.** Produces a plan that can later be executed via `/deliver` or `/auto`.

### `/roadmap`
**Roadmap dashboard.** Shows versioned phases and upcoming work.

### `/hookmode [status|calm|verbose|verbo]`
**Codex hook profile switcher.** Inspect or change the local Codex hook mode.

- **Default**: no argument shows the current mode and sync state
- **`calm`**: restore the low-noise Codex default
- **`verbose` / `verbo`**: enable the fuller automatic Codex hook profile locally

---

## Pipeline Selection Cheat Sheet

```
                    Is it governance / kernel?
                    ─────────────────────────
                           │
                    YES    │    NO
                     │     │     │
                     ▼     │     ▼
              /deliver-full│   Do you know the solution?
                           │   ──────────────────────────
                           │          │
                           │   YES    │    NO
                           │    │     │     │
                           │    ▼     │     ▼
                           │  /auto   │  /dynamic-full-auto
                           │          │
                           │   Is it pre-approved
                           │   with a fixed plan?
                           │   ─────────────────
                           │          │
                           │   YES    │    NO
                           │    │     │     │
                           │    ▼     │     ▼
                           │ /deliver │   /auto
```

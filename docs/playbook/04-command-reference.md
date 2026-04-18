# Command Reference

> Quick reference for all Azoth slash commands.

Codex note: `$azoth-start` is the canonical daily entry surface in Codex. Compatibility wrappers like `$azoth-auto` and literal slash tokens still work, but routed workflow commands normalize back through the same calm-flow start controller.

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
In Codex, use `$azoth-start` for the same surface; `$azoth-start next` and `$azoth-start pipeline_command=<...> <goal>` stay inside the same calm-flow route.

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
In Codex, `$azoth-session-closeout` is the primary entry and W3 is best-effort/deferred by default.

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

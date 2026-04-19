# Your First `/auto`

> A step-by-step walkthrough of running your first pipeline.

Codex note: the canonical Codex daily route is `$azoth-start`. Use `$azoth-start pipeline_command=auto <goal>` for the start-centered calm-flow path, or `$azoth-auto <goal>` as a compatibility wrapper. Literal `/auto` text in Codex is compatibility fallback, not the primary UX surface.

## Before You Start

Make sure Azoth is installed. You should see a welcome dashboard when starting
a new session:

```
You: /start
```

If the dashboard appears, you're ready. In Codex, that same daily route starts at
`$azoth-start`; raw slash tokens stay in compatibility-fallback territory there.

---

## Step 1: Tell Azoth What You Want

Type `/auto` followed by your goal in plain language:

```
You: /auto add a retry mechanism to the API client
```

In Codex, the equivalent canonical entry is:

```
You: $azoth-start pipeline_command=auto add a retry mechanism to the API client
```

That's it. Azoth handles the rest.

---

## Step 2: Review the Declaration

Azoth classifies your goal and presents a **fused Declaration** — one card
combining scope and pipeline:

```
┌────────────────────────────────────────────────────────────┐
│  Auto-Pipeline — add retry mechanism to API client         │
│                                                            │
│  Classification: skills / additive / medium / known-pattern│
│  Scope: session: a1b2c3 | TTL: 2h | layer: mineral        │
│  Model tier: standard                                      │
│                                                            │
│  Composed Pipeline:                                        │
│    1. planner    — standard — gate: agent                  │
│    2. evaluator  — standard — gate: agent                  │
│    3. builder    — standard — gate: agent                  │
│    4. architect  — standard — gate: agent (review)         │
│                                                            │
│  Rationale: medium + additive + known-pattern (Rule 8)     │
│             — reviewer skipped, evaluator retains quality.  │
│                                                            │
│  Approve scope + pipeline? [yes / adjust / abort]          │
└────────────────────────────────────────────────────────────┘
```

You have three choices:

| Response | What happens |
|----------|-------------|
| **yes** | Pipeline starts executing |
| **adjust** | Change scope, stages, or classification |
| **abort** | Cancel entirely |

```
You: yes
```

---

## Step 3: Watch It Run

After approval, Azoth writes the scope gate and starts executing stages.
You'll see progress at each stage boundary:

```
Azoth: ✅ Scope gate written. Starting pipeline...

       ── Stage 1: Planner ──
       Decomposed into 4 tasks with test strategy.
       Agent gate: PASS

       ── Stage 2: Evaluator ──
       Plan scored 0.91 (threshold: 0.85). PASS.
       Agent gate: PASS

       ── Stage 3: Builder ──
       Created retry_client.py, test_retry.py.
       3 tests pass. Auto-test gate: PASS

       ── Stage 4: Architect Review ──
       Implementation matches plan. Entropy: GREEN (3 files).
       Agent gate: APPROVED
```

### What if something fails?

If an agent gate fails (e.g., evaluator scores below threshold), the pipeline
**stops and asks you**:

```
Azoth: ⚠️ Evaluator scored 0.72 (below 0.85 threshold).
       Concerns:
         - Missing error handling for network timeouts
         - Test coverage incomplete for edge cases

       Options: [iterate / adjust-scope / abort]
```

You decide how to proceed. The pipeline never silently pushes past a failure.

---

## Step 4: Close the Session

When the pipeline completes, close out the session to capture learnings:

```
You: /session-closeout
```

This:
1. **Saves an episode** to memory (what you did, what was learned)
2. **Bumps the version** (0.1.1.31 → 0.1.1.32)
3. **Updates state files** for the next session
4. **Commits changes** to git

In Codex, prefer `$azoth-start closeout` for the daily route. `$azoth-session-closeout`
still works as a direct wrapper, while W1/W2/W4 stay authoritative and W3 remains
best-effort/deferred unless you explicitly request a Claude memory mirror refresh.

---

## Common Patterns

### Simple docs fix (auto-proceeds)

```
You: /auto fix typo in README.md

Azoth: Auto-Pipeline — fix typo [INFORMATIONAL]
       docs / cosmetic / simple / known-pattern
       Pipeline: planner→builder→architect
       Auto-proceeding unless you type `stop`.

       ... (runs without waiting) ...

       ✅ Done. 1 file changed.
```

### Complex feature (full pipeline)

```
You: /auto redesign the authentication system

Azoth: Auto-Pipeline — redesign auth
       Classification: mixed / breaking-change / complex / needs-research
       Pipeline: architect→reviewer→planner→eval→builder→architect
       6 stages, 2 human gates possible.

       Approve? [yes / adjust / abort]
```

### "I don't know the solution yet" (use DFA)

```
You: /dynamic-full-auto investigate performance bottleneck

Azoth: Launching discovery swarms...
       Wave A: 2 researchers analyzing patterns
       Wave B: 3 explore agents scanning codebase
       ... (converges on root causes) ...

       Checkpoint Γ: Re-classified as medium/additive.
       Routing to /auto with [planner→eval→builder→architect].
```

---

## Tips

1. **Start with `/auto`** — or `$azoth-start pipeline_command=auto <goal>` in Codex calm flow — it picks the right pipeline 90% of the time
2. **Say `adjust`** if the classification seems wrong — you can override
3. **Use `/dynamic-full-auto`** when you're exploring, not building
4. **Always `/session-closeout`** — it's how Azoth learns and improves
5. **Trust the gates** — they catch problems before they become expensive

## What's New (Orchestrator v2)

| Feature | What it does |
|---------|-------------|
| **Decision table** | Clear inline vs pipeline routing — no ambiguity on what gets a pipeline |
| **Mid-pipeline adaptation** | Orchestrator detects deviations and can insert/skip/reorder stages |
| **Model tiering** | `premium` / `standard` / `fast` on every spawn — cost matches complexity |
| **Token budget** | Tracks context consumption, auto-compresses at 80%, checkpoints at 95% |
| **TTL management** | Active TTL monitoring with in-place extension (no full re-scope mid-pipeline) |
| **Memory consultation** | Checks M3 episodes before classification — suggests prior pipelines for similar goals |
| **Error recovery** | Retry policy + circuit breaker (3 failures → halt + diagnostic card) |
| **Evaluator dispatch** | E1-E6 triggers decide single eval (0.85) vs swarm eval (0.90) automatically |
| **Agent binding** | `/start`, `/next`, and Codex calm-flow `$azoth-start ...` now keep orchestrator agent context across all platforms |

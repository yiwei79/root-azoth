---
name: swarm-coordination
description: Multi-agent swarm coordination patterns. Orchestrates parallel agent execution, manages agent communication, handles task distribution, and coordinates results aggregation.
version: 1.0.0
model: sonnet
invoked_by: both
user_invocable: true
tools: [Read, Write, Edit, Bash, Glob, Grep]
best_practices:
  - Spawn independent agents in parallel
  - Use structured handoff formats
  - Aggregate results systematically
  - Handle partial failures gracefully
error_handling: graceful
streaming: supported
verified: true
lastVerifiedAt: 2026-02-22T00:00:00.000Z
---

# Swarm Coordination Skill

Swarm Coordination Skill - Orchestrates parallel agent execution, manages inter-agent communication, handles task distribution, and coordinates results aggregation for complex multi-agent workflows.

- Parallel agent spawning - Task distribution strategies - Results aggregation - Inter-agent communication - Failure handling and recovery

### Step 1: Analyze Task for Parallelization

Identify parallelizable work:


| Pattern           | Example                        | Strategy               |
| ----------------- | ------------------------------ | ---------------------- |
| Independent tasks | Review multiple files          | Spawn in parallel      |
| Dependent tasks   | Design → Implement             | Sequential spawn       |
| Fan-out/Fan-in    | Multiple reviews → Consolidate | Parallel + Aggregation |
| Pipeline          | Parse → Transform → Validate   | Sequential handoff     |


### Step 2: Spawn Agents in Parallel

Use the Task tool to spawn multiple agents in a single message:

```javascript
// Spawn multiple agents in ONE message for parallel execution
Task({
  task_id: 'task-1',
  subagent_type: 'general-purpose',
  description: 'Architect reviewing design',
  prompt: 'Review architecture...',
});

Task({
  task_id: 'task-2',
  subagent_type: 'general-purpose',
  description: 'Security reviewing design',
  prompt: 'Review security...',
});
```

**Key**: Both Task calls must be in the SAME message for true parallelism.

### Step 3: Define Handoff Format

Use structured formats for agent communication:

```markdown
## Agent Handoff: [Source] → [Target]

### Context

- Task: [What was done]
- Files: [Files touched]

### Findings

- [Key finding 1]
- [Key finding 2]

### Recommendations

- [Action item 1]
- [Action item 2]

### Artifacts

- [Path to artifact 1]
- [Path to artifact 2]
```

### Step 4: Aggregate Results

Combine outputs from parallel agents:

```markdown
## Swarm Results Aggregation

### Participating Agents

- Architect: Completed ✅
- Security: Completed ✅
- DevOps: Completed ✅

### Consensus Points

- [Point all agents agree on]

### Conflicts

- [Point agents disagree on]
- Resolution: [How to resolve]

### Combined Recommendations

1. [Prioritized recommendation]
2. [Prioritized recommendation]
```

### Step 5: Handle Failures

Strategies for partial failures:


| Scenario                | Strategy                        |
| ----------------------- | ------------------------------- |
| Agent timeout           | Retry with simpler prompt       |
| Agent error             | Continue with available results |
| Conflicting results     | Use consensus-voting skill      |
| Missing critical result | Block and retry                 |


1. **Parallelize Aggressively**: Independent work should run in parallel
2. **Structured Handoffs**: Use consistent formats for communication
3. **Graceful Degradation**: Continue with partial results when safe
4. **Clear Aggregation**: Combine results systematically
5. **Track Provenance**: Know which agent produced each result

**Parallel Review Request**:

```
Get architecture, security, and performance reviews for the new API design
```

**Swarm Coordination**:

```javascript
// Spawn 3 reviewers in parallel (single message)
Task({ task_id: 'task-3', description: 'Architect reviewing API', prompt: '...' });
Task({ task_id: 'task-4', description: 'Security reviewing API', prompt: '...' });
Task({ task_id: 'task-5', description: 'Performance reviewing API', prompt: '...' });
```

**Aggregated Results**:

```markdown
## API Design Review (3 agents)

### Consensus

- RESTful design is appropriate
- Need authentication on all endpoints

### Recommendations by Priority

1. [HIGH] Add rate limiting (Security)
2. [HIGH] Use connection pooling (Performance)
3. [MED] Add versioning to URLs (Architect)
```

## Rules

- Always spawn independent agents in parallel
- Use structured handoff formats
- Handle partial failures gracefully

## Related Workflow

This skill has corresponding workflows under `.claude/workflows/enterprise/`:

- **Index**: `.claude/workflows/enterprise/swarm-coordination-skill-workflow.md`
- **E2E eval iteration (threshold 0.9, isolated evaluators)**: `.claude/workflows/enterprise/e2e-swarm-eval-loop.md` — multi-wave swarm, **iterate** until every branch passes **overall ≥ 0.9**; **fresh `Task(evaluator)` per wave** with **minimal spawn payload** (artifacts + criteria only) to avoid author–evaluator bias. Invoked via slash command **`/eval-swarm`** (not **`/eval`**).
- **When to use E2E workflow**: Quality-critical multi-branch delivery, or when baseline **`/eval` (0.85)** is too loose for the swarm gate.
- **When to use skill only**: Simple parallel spawn without iteration loop.

## Workflow Integration

This skill powers multi-agent orchestration patterns across the framework:

**Router Decision:** `.claude/workflows/core/router-decision.md`

- Router uses swarm patterns for parallel agent spawning
- Planning Orchestration Matrix defines when to use swarm coordination

**Artifact Lifecycle:** `.claude/workflows/core/skill-lifecycle.md`

- Swarm patterns apply to artifact creation at scale
- Parallel validation of multiple artifacts

**Related Workflows:**

- `consensus-voting` skill for resolving conflicting agent outputs
- `context-compressor` skill for aggregating parallel results
- Enterprise workflows in `.claude/workflows/enterprise/` use swarm patterns

---

## Advanced parallelism (orchestrator contract)

Use this when fanning out work that must stay fast and auditable:

1. **Single-message dispatch** — Put every independent `Task` (or `Agent`) for the same wave in **one** orchestrator turn. Spawning workers one turn after another **serializes** execution and is not a swarm.
2. **Queen aggregation** — Workers do not read each other’s scratch space. The orchestrator collects structured handoffs, resolves conflicts, and forwards only what the next stage needs (same idea as BL-011 / `prior_stage_summaries` in governed pipelines).
3. **Wave layering** — If you need more than **7** parallel workers, split into **waves**: wave A fan-out → aggregate → wave B fan-out. Do not raise a single fan-out without bound.
4. **Pipeline vs swarm** — `/auto` and `/deliver-full` stages are **often sequential** (architect → planner → builder → reviewer) because outputs depend on prior typed summaries. **Swarm** applies to **sibling** tasks with **no** upstream dependency (e.g. three independent backlog blueprints, three independent file reviews). Never parallelize a stage that must consume the previous stage’s YAML verbatim without passing that payload.

### End-to-end eval loop (strict — 0.9)

Use **`e2e-swarm-eval-loop.md`** when the orchestrator must **loop** Wave C (parallel evals) → Wave D (fixes) until thresholds clear:

| Rule | Why |
|------|-----|
| **Threshold 0.9** | Use **`/eval-swarm`**, not **`/eval`**; document disposition explicitly. |
| **New evaluator `Task` each wave** | Prevents “sticky” PASS from prior turn; aligns with **review-independence**. |
| **Spawn body = paths + criteria** | Do not inject builder narrative into eval prompts. |
| **Max 3 rounds** | Avoid infinite micro-tweak loops; queen escalates to human. |

## Iron Laws

1. **NEVER** spawn workers sequentially — all independent agents must be dispatched in a single message
2. **ALWAYS** implement failure detection; never let a hung worker block the swarm indefinitely
3. **NEVER** allow cross-worker communication — all coordination must flow through the Queen
4. **ALWAYS** use structured handoff format for worker reports to enable programmatic aggregation
5. **NEVER** spawn more than 7 workers in a single fan-out — coordination overhead dominates beyond that

## Anti-Patterns


| Anti-Pattern               | Why It Fails                                           | Correct Approach                                           |
| -------------------------- | ------------------------------------------------------ | ---------------------------------------------------------- |
| Sequential spawning        | No parallelism; swarm executes like a queue            | Spawn all independent workers in a single message          |
| Cross-worker communication | O(N²) coordination chaos                               | All worker-to-worker communication flows through the Queen |
| No failure handling        | One worker crash stalls the swarm                      | Detect hung/failed workers and re-spawn with fresh state   |
| Unbounded parallelism      | Coordination overhead exceeds speedup beyond 7 workers | Limit to 5-7 workers per fan-out for optimal throughput    |
| Free-form worker reports   | Cannot aggregate results programmatically              | Require all workers to use the structured handoff template |


## Memory Protocol (MANDATORY)

**Azoth workshop (this repo):** durable capture is **`.azoth/memory/episodes.jsonl`** (M3) and, when promoted, **`.azoth/memory/patterns.yaml`** (M2). Reference swarm lessons there so Cursor/Claude Code parity stays in-repo.

**Optional Claude Code project path (consumer installs):**

```bash
cat .claude/context/memory/learnings.md
```

**After completing:**

- New pattern → `.azoth/memory/episodes.jsonl` (and optional `.claude/context/memory/learnings.md` if using that layout)
- Issue found → `.azoth/inbox/` or episodes; optional `issues.md` in project memory
- Decision made → episodes + `docs/DECISIONS_INDEX.md` when architectural

> ASSUME INTERRUPTION: Your context may reset. If it's not in memory, it didn't happen.


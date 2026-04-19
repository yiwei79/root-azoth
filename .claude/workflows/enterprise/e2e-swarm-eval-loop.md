# End-to-end advanced agent swarm — eval iteration (threshold 0.9)

**Purpose:** Run **multi-wave** parallel work with **strict evaluator isolation**, then **iterate** until every branch meets **overall ≥ 0.9** on the standard weighted rubric (see `agents/tier3-meta/evaluator.agent.md`).

**When to use:** Multiple independent deliverables (or symmetric review/eval passes on the same artifact set), quality-critical gates, and you want **no** author–evaluator context bleed.

---

## Constants

| Constant | Value |
|----------|--------|
| **Eval threshold** | **0.90** (use slash command **`/eval-swarm`** — not default **`/eval`** **0.85**) |
| **PASS** | `overall_score >= 0.90` **and** no dimension **< 0.5** |
| **CONDITIONAL** | Reserved for human override only — **do not** auto-proceed below 0.90 in this workflow |
| **Max iteration rounds** | **3** (then stop; queen reports and asks for human steering) |

---

## Context isolation (anti-bias) — mandatory

These rules prevent the evaluator from inheriting the author’s framing, missed edge cases, or premature “PASS” narratives.

1. **Fresh `Task` per eval wave** — Each evaluation run uses a **new** `Task` with `subagent_type: evaluator` and **no** access to the builder/planner chat transcript.
2. **Spawn payload is minimal** — Body = BL-011 YAML block + **`Read` targets** (paths) + **acceptance criteria bullets** + `threshold: 0.9`. Do **not** paste the builder’s full reasoning, draft text, or prior eval prose into the evaluator prompt.
3. **No peer eval** — Evaluators in the same wave do not read each other’s outputs; the **queen** (orchestrator) aggregates scores only **after** all eval Tasks return.
4. **Rebuild loop isolation** — If a branch fails &lt; 0.9, the **next** builder/planner fix uses a **fresh** `Task`; the **next** eval is again a **fresh** evaluator `Task`. Never “continue the same thread” for eval after author edits.
5. **Review-independence alignment** — Same trigger as `skills/subagent-router/SKILL.md` Priority 1: anything that **judges** prior work must not share the author’s context window.

---

## Wave topology (queen orchestration)

```
[Queen: define branches + acceptance criteria]

Wave A — parallel implementation (optional)
  └─ Task(builder) × N  in ONE message  (independent files only)

Wave B — parallel review (optional)
  └─ Task(reviewer) × N  in ONE message  (fresh contexts)

Wave C — parallel evaluation  ← threshold 0.9, isolated
  └─ Task(evaluator) × N  in ONE message
        each: readonly, threshold 0.9, artifacts only

[Queen: aggregate — any overall < 0.9 ?]

Wave D — targeted fix (sequential per failed branch, or parallel if fixes independent)
  └─ Task(planner|builder) with gap list from queen only (not full prior eval dumps)

→ repeat Wave C–D until all ≥ 0.9 or max rounds
```

- **Fan-out cap:** default to **`≤ 7 Tasks per wave`** for stable cost and predictability, and never exceed the active platform execution budget. On Codex, the default is `10` threads at depth `2`; evaluator waves are normally leaf-only, so treat that budget as a hard upper bound and keep the working cap at `7` unless the human explicitly authorizes a larger wave.
- **Dependencies:** If branch B needs branch A’s output, **do not** parallelize A and B in Wave A; sequence them and run parallel eval only when artifacts exist.

---

## Evaluator spawn contract (copy into each `Task`)

Use only this shape; keep under ~25 lines:

```yaml
pipeline: e2e-swarm-eval
stage_id: eval_branch_<id>
subagent_type: evaluator
trigger: review-independence
goal: |
  Weighted rubric evaluation; PASS only if overall >= 0.9 and no dimension < 0.5.
inputs:
  artifacts:
    - <path>
threshold: 0.9
acceptance:
  - <bullet>
```

**Forbidden in evaluator prompt:** builder chat logs, “here is what we intended,” screenshots of reasoning, or another evaluator’s full report (queen may pass **numeric scores + gap labels** to builders only).

---

## Iteration exit criteria

| Outcome | Action |
|---------|--------|
| All branches **PASS** (≥ 0.9) | Queen merges summary; optional L2 evidence append if gates allow |
| Any branch **FAIL** after 3 rounds | Stop; human decides scope cut or manual fix |
| **Tie-break** | Human reads queen aggregation only; do not average evaluator scores across branches for “truth” |

---

## Relation to `/auto`, `/eval`, and `/eval-swarm`

- **`/eval`** — baseline gate (**≥ 0.85**) for **simple** reviews; also defines **when to escalate** to swarm eval (triggers **E1–E6** in `.claude/commands/eval.md`). Pipelines and humans should **not** ignore those triggers.
- **`/eval-swarm`** — command surface for **≥ 0.90**, isolated evaluators, and the process below (invoked directly or **required** after `/eval` routing when triggers fire).
- Governed pipelines (`delivery_pipeline: governed`) still require **scope + pipeline gates** before writes (`claude-code-parity.mdc`).

---

## References

- `skills/subagent-router/SKILL.md` — spawn contract, `review-independence`
- `agents/tier3-meta/evaluator.agent.md` — weights, disposition math
- `.claude/commands/eval.md` — baseline **0.85** thresholds
- `.claude/commands/eval-swarm.md` — **0.90** swarm eval process
- `.agents/skills/swarm-coordination/SKILL.md` — parallelism and Iron Laws
- `pipelines/swarm-eval-wave.example.yaml` — canonical wave-topology data validated against `pipelines/swarm-eval-wave.schema.yaml`
- `pipelines/swarm-build-review.example.yaml` — two-wave (A+B only) preset for build+review runs that do not require eval/fix waves (BL-034)

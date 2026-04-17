---
name: dynamic-full-auto
description: |
  DYNAMIC-FULL-AUTO+ with queen-controlled adaptive routing: situational extra waves, pivots,
  post-digest re-classification via `skills/auto-router/SKILL.md` (D23), optional `/eval-swarm`
  (≥0.90) before writes, merge to `SWARM_RESEARCH_DIGEST.yaml`, `scripts/swarm_research_digest.py`.
  BL-011 spawns; scope/pipeline gates unchanged (D50).
---

# Dynamic Full Auto (DYNAMIC-FULL-AUTO+)

Optional **session mode** for high-throughput, read-mostly discovery: parallel online research,
parallel repo exploration, one machine-readable aggregate digest, then hand off to normal
`/auto`, `/deliver`, or `/deliver-full` for gated implementation.

This is **not** a replacement for `/auto` governance. It **compresses** the research and
reconnaissance phases using the same **swarm-coordination** iron laws (single-message fan-out,
queen aggregation, no worker-to-worker chatter).

The orchestrator is **not** bound to a single A→B→merge line: it **observes signals** after each
wave and **re-routes** (repeat, skip, insert eval, re-classify, or abort). That is the
**dynamic** in the name.

## Overview

```
Human opt-in
  → [Wave A*] parallel researcher (repeat/partial/skip per signals below)
  → [Wave B*] parallel explore   (repeat/partial/skip per signals below)
  → Queen merge + validate digest
  → [Checkpoint Γ] Re-run Stage 0 classification + auto-router (D23) — may change pipeline
  → [Optional Wave C] /eval-swarm — parallel Task(evaluator), threshold 0.9, anti-bias spawns
  → Delivery: /auto | /deliver | /deliver-full under approved scope + gates
```

`*` Waves are **elastic**: the queen may run **Wave A2**, **B-only**, **A-only**, or **short-circuit**
to merge when the situation warrants (see decision table).

**Digest artifact (canonical path):**

`.azoth/roadmap-specs/<active_roadmap_version>/SWARM_RESEARCH_DIGEST.yaml`

Align `<active_roadmap_version>` with `.azoth/roadmap.yaml` top-level `active_version` (D48).

## Prerequisites

Before running DYNAMIC-FULL-AUTO+ end-to-end:

- **Scope** — A valid `.azoth/scope-gate.json` (and `.azoth/pipeline-gate.json` when delivery is governed or `target_layer: M1`) before **any** `Write/Edit`, including digest updates (`append-pack` outcomes committed to disk). Discovery waves are read-mostly, but mutating the digest file is a write.
- **Roadmap alignment** — Digest path matches `active_version` in `.azoth/roadmap.yaml` (D48).
- **Orchestration** — Ability to spawn parallel `Task` / `Agent` workers per wave (BL-011); queen merges in the orchestrator thread.
- **Human** — Available for **Checkpoint Γ** pipeline declaration and for any review stop; for **delivery** after handoff, same gates as `/auto` / `/deliver` / `/deliver-full`.
- **Cursor** — Third-party rules/skills toggle enabled where applicable; **no** PreToolUse hooks — simulate scope-gate / pipeline-gate checks before every write (`.cursor/rules/claude-code-parity.mdc`).

## Non-goals (this skill / P1-012 slice)

- **No full P1-001 run ledger** in the same delivery slice as a friction/doc pass (ledger is a separate backlog item).
- **No `kernel/**` promotion** or consumer-kernel edits without human-approved scope.
- **No P1-002 declarative wave schema** folded in here without its **own** scope card.
- **No claim** that Cursor gains mechanical SessionStart or PreToolUse — only documented **behavioral** parity paths.

## Friction map (P1-012)

Canonical problem statement (from `.azoth/roadmap-specs/v0.2.0/P1-012.yaml`): documented DFA+ implies a smooth path from goal through digest to gated delivery, but **scope/pipeline gates**, **IDE asymmetry** (hooks vs simulated parity), **manual queen merge / append-pack / validate**, uneven `Task` fan-out, and **handoff to `/auto` | `/deliver` often needing a fresh scope approval** make the flow feel discontinuous. **P1-001 / P1-002** (durable run state, declarative waves) are deferred and widen the honesty gap until delivered.

| Friction | Blast radius (surfaces) | Decisions |
| -------- | ------------------------ | --------- |
| Gates interrupt a single narrative of “one session to shipped” | `.azoth/scope-gate.json`, `.azoth/pipeline-gate.json`, `/auto` Execution, `.cursor/rules/claude-code-parity.mdc` | **D50** scope card; **D21** typed stages / handoffs |
| Cursor lacks SessionStart / PreToolUse | This skill, `.claude/commands/dynamic-full-auto.md`, `CLAUDE.md`, Cursor rules | **D52** orientation; parity is behavioral in Cursor |
| Manual digest ops (merge, append-pack, validate) | `scripts/swarm_research_digest.py`, `SWARM_RESEARCH_DIGEST.yaml` | **D48** versioned roadmap paths |
| Re-classification and delivery composition | `skills/auto-router/SKILL.md`, `pipelines/auto.pipeline.yaml` | **D23** LLM-as-router composition |
| Second scope between digest work and implementation tail | `/next`, scope TTL, long-running checklist | **D50** + **P1-005** (see architecture doc) |

**Scope TTL and multi-wave runs:** See `docs/AZOTH_ARCHITECTURE.md` **Long-running sessions (P1-005)** for refresh, chunking, and gate policy alongside this skill.

**Mechanical helper:**

```bash
python3 scripts/swarm_research_digest.py validate .azoth/roadmap-specs/v0.2.0/SWARM_RESEARCH_DIGEST.yaml
python3 scripts/swarm_research_digest.py init PATH --roadmap-version v0.2.0
# append one pack: YAML mapping with id, topic, sources[], implications_for_azoth[], risks[]
python3 scripts/swarm_research_digest.py append-pack PATH --pack new_pack.yaml
```

Use `**append-pack**` after each researcher Task returns a pack (idempotent on `id`: duplicate
`id` is rejected). Run `**validate**` before commit and after manual edits.

Optional top-level `**meta**` mapping (e.g. `session_id`, `updated_at`) is allowed if present.

## Adaptive session graph (queen-controlled)

Treat the run as a **state machine**; the queen advances edges using **evidence**, not a fixed script.


| Phase                 | Purpose                                                  | Typical exit                                                                   |
| --------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **DISCOVER_R**        | Wave A research packs                                    | Enough cited packs + themes stable **or** max A repeats                        |
| **DISCOVER_X**        | Wave B explore findings                                  | Critical paths mapped **or** max B repeats                                     |
| **SYNTHESIZE**        | Merge digest, `consensus_themes`, `mapped_roadmap_tasks` | `swarm_research_digest.py validate` **OK**                                     |
| **RECLASSIFY**        | Stage 0 YAML + `auto-router`                             | New `classification` + composed pipeline table (may differ from session start) |
| **PRE_DELIVERY_EVAL** | Optional `/eval-swarm`                                   | All branches ≥ **0.90** or budget exhausted per e2e doc                        |
| **DELIVERY_HANDOFF**  | Spawn delivery pipeline via `/auto` mechanics            | Scope + pipeline gates satisfied                                               |


**Loops (dynamic):** DISCOVER_* can repeat; SYNTHESIZE can fail validation and force another A/B
micro-wave on a **narrowed** topic; RECLASSIFY can send you back to SYNTHESIZE if classification
implies missing digest coverage.

## Situational signals → routing

After **each** wave, the queen checks signals and **chooses the next edge** (document the choice
in `meta` or a one-line orchestrator log).


| Signal                                                                                                                                                            | Adaptive action                                                                                                                         |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Packs thin on citations or single-source dominance                                                                                                                | **Wave A′**: spawn 2–4 more `researcher` Tasks on under-covered topics only                                                             |
| Contradictory packs on the same claim                                                                                                                             | Spawn **one** `architect` or `researcher` “adjudication” pass **or** record conflict in `risks` + `consensus_themes` and continue       |
| `validate` fails on digest                                                                                                                                        | Fix YAML locally **or** re-merge; **do not** treat broken digest as canonical                                                           |
| Explore reports a **blocker** (missing file, test failure, governance landmine)                                                                                   | **Pivot**: narrow explore swarm to that blast radius **or** stop delivery handoff until scoped                                          |
| Goal was wrong after reading repo                                                                                                                                 | **RECLASSIFY** immediately; may skip further A if knowledge flips to `known-pattern`                                                    |
| Entropy / file-change pressure high before writes                                                                                                                 | Shrink scope card **or** split into two sessions (digest vs delivery)                                                                   |
| **Boolean OR over E1–E6** per `.claude/commands/eval.md` (compute from scope, pipeline, file list, prior summaries — same algorithm as `/eval` orchestrator rule) | If **any** trigger true → insert **PRE_DELIVERY_EVAL** (`/eval-swarm`); if **none** true, Wave C is optional unless human asks for 0.90 |


**Skip rules:** If `knowledge: known-pattern` **and** explore confirms no unknowns, queen may **skip
Wave A** or run a **single** researcher pack for confirmation. **Exception:** if the task depends on
latest/current external facts (platform behavior, APIs, policies, enums, specs), Wave A is mandatory
and must use official sources before Checkpoint Γ or delivery. If research is exhaustive but repo is
tiny, **skip Wave B** with explicit justification in `explore_swarm_summary.findings`.

## In-between pipeline routing (post-digest → delivery)

1. **Checkpoint Γ — Re-classify (mandatory before composing delivery)**
  Emit fresh Stage 0 `classification` YAML (`scope`, `risk`, `complexity`, `knowledge`).  
   `**Read` `skills/auto-router/SKILL.md`** and map to the pipeline stage list from
   `pipelines/auto.pipeline.yaml` (D23). The post-digest classification **may differ** from the
   session opener: e.g. `knowledge: needs-research` → `known-pattern` after the digest.
2. **Compose delivery** using the **new** table — same human declaration semantics as `/auto`
  (present pipeline to human unless session contract says otherwise). Subagent assignments still
   follow `skills/subagent-router/SKILL.md`.
3. **Optional `/eval-swarm` insertion (Wave C)**
  Only when Wave C is actually selected because the quality bar needs **≥ 0.90**, parallel
  independent work is present, or **eval.md** escalation triggers fire:
  - `**Read` `.claude/workflows/enterprise/e2e-swarm-eval-loop.md`** and `**.claude/commands/eval-swarm.md`**.  
  - Spawn **one message**, **≤7** `Task(subagent_type=evaluator, readonly=true)` with **minimal**
  YAML: `pipeline: e2e-swarm-eval`, `stage_id`, `artifacts` paths, `threshold: 0.9`,
  `acceptance:` bullets — **no** builder chat log, **no** author narrative (anti-bias).  
  - Queen aggregates scores; **FAIL** → Wave D fix with **fresh** planner/builder Tasks, then
  **new** evaluators (never reuse eval thread after edits). **Max rounds** per e2e doc (default 3).
   **E1–E6 trigger digest** (normative detail + orchestrator algorithm: `**Read` `.claude/commands/eval.md`**
   § “When `/eval` escalates to swarm eval”). If **any** row applies, prefer `/eval-swarm` (0.90) over a
   single-thread 0.85 pass. Ambiguity between E1/E4 → **prefer escalation**.

  | ID     | Mnemonic                                                                                                 |
  | ------ | -------------------------------------------------------------------------------------------------------- |
  | **E1** | ≥2 independent deliverables/branches to judge in parallel                                                |
  | **E2** | Composed pipeline **evaluator stage** after multi-file / governance-touching / cross-layer work          |
  | **E3** | Scope `**delivery_pipeline: governed`** and/or `**target_layer: M1`**                                    |
  | **E4** | High entropy / blast radius (Trust Contract ceiling, kernel templates, commands, skills deploy surfaces) |
  | **E5** | Prior eval **CONDITIONAL/FAIL** or reviewer **request-changes** still relevant                           |
  | **E6** | Human/scope signal: “parallel”, “swarm”, multiple `**prior_stage_summaries`**, stacked backlog IDs       |

   **Spawn contract:** Wave C evaluators follow **e2e-swarm-eval-loop** minimal payload (paths +
   `acceptance` + `threshold: 0.9`) — **not** a dump of BL-012 prose into the spawn; delivery stages
   after handoff still use **BL-012** `prior_stage_summaries` per `subagent-router`.
4. **Handoff** to builder stages only with valid **scope-gate** (+ **pipeline-gate** if governed).

## When to Use

- Roadmap or architecture work needing **cited external** signal (papers, vendor docs, patterns)
faster than a single-thread web pass.
- Large or unfamiliar repo surfaces where **disjoint explore** Tasks reduce blind spots before design.
- You will produce or extend `**SWARM_RESEARCH_DIGEST.yaml`** and may **reference** it from
`roadmap.yaml` `note:` or per-task specs under `roadmap-specs/<ver>/`.

## When Not to Use

- Governed **M1** or **kernel** delivery as the primary goal → use `**/deliver-full`** and normal gates.
- Narrow bugfixes, single-file edits, or **known-pattern** work → `**/auto`** or direct builder path.
- Skipping **scope-gate** / **pipeline-gate** for writes in Cursor parity → **never**; this skill does
not override mechanical PreToolUse in Claude Code or simulated gates in Cursor.

## Wave A — Online Research Swarm

1. Partition topics (e.g. durability, supervisor YAML, multi-eval independence, memory elasticity).
2. In **one orchestrator message**, spawn **4–7** `Task(subagent_type=researcher)` (or
  `research-orchestrator` fan-out if you centralize briefing) with **disjoint** briefs.
3. Each worker returns **structured YAML** (or markdown containing a YAML block) with:
  `id` or `research_pack_id`, `topic`, `sources: [{title, url}]`, `implications_for_azoth`,
   `risks`.
4. Queen normalizes `**research_pack_id` → `id`** (matches `append-pack` / script).
5. **Adaptive:** If signals say under-coverage, spawn **Wave A2+** in a **new** message with **narrower**
  briefs (no duplicate pack `id`). If research is sufficient, proceed.

## Wave B — Explore Swarm

1. Partition repo questions (welcome/gates, pipelines/eval wiring, session-closeout/memory, etc.).
2. In **one message**, spawn **3–5** `Task(subagent_type=explore)` with **read-only** scope.
3. Queen merges into `**explore_swarm_summary`** (`wave`, `findings[]`) inside the digest, or appends
  bullets manually then `**validate`**.
4. **Adaptive:** A **second** explore wave targets only high-uncertainty paths from wave 1. If there are
  no unknowns, record that explicitly and continue.

## Queen Merge + Digest Pattern (mandatory convention)

After Waves A and B:

1. **Update** `consensus_themes` (short `id` + `summary`) if new cross-cutting themes emerged.
2. **Merge** packs into `research_packs` (dedupe URLs; flag disagreements in `risks` or themes).
3. Set `**mapped_roadmap_tasks`** to the roadmap task ids informed by this run.
4. Run `**python3 scripts/swarm_research_digest.py validate …`** — **must pass** before treating
  the digest as canonical.
5. For **incremental** sessions: `**append-pack`** each new pack; never duplicate `**id`**.

## BL-011 / BL-012

- **BL-011:** Spawns use the compact contract in `skills/subagent-router/SKILL.md` — goal,
`stage_id`, `Read` targets; do not paste full slash-command markdown into `Task` bodies.
- **BL-012:** When this mode hands off to **delivery** `/auto`, forward typed `**stage-summary`**
YAML as required; the digest is an **aggregate artifact**, not a substitute for per-stage
summaries inside governed pipelines.

## Relation to Default `/auto`


| Aspect      | DYNAMIC-FULL-AUTO+                               | `/auto`                                  |
| ----------- | ------------------------------------------------ | ---------------------------------------- |
| Goal        | Digest + reconnaissance                          | Composed delivery + gated writes         |
| Parallelism | Research + explore swarms first                  | Stage-isolated `Task` per pipeline row   |
| Human       | Opt-in once for **this mode**; **during discovery/digest** there is **no extra** human pipeline-declaration step *until* Checkpoint Γ — **not** “no gates for the whole session.” After Γ, same declaration + review semantics as `/auto` for the **delivery** pipeline. | Declaration + review stops as documented for the composed delivery table |
| Outputs     | `SWARM_RESEARCH_DIGEST.yaml`                     | Merged code/config under scope           |


**Writes vs “mid-run”:** Any **Write/Edit** (including mutating the digest on disk) still requires valid **`.azoth/scope-gate.json`** (and **`.azoth/pipeline-gate.json`** when governed, with **`pipeline`** set to the delivery command you will actually run: `"auto"` \| `"deliver"` \| `"deliver-full"` — **do not** assume `auto` if the handoff is `/deliver` or `/deliver-full` per `.claude/commands/dynamic-full-auto.md` **Gates**). *Mode contract* means the **discovery/digest phases** do not add a **second** `/auto`-style pipeline table **before** Γ; it does **not** exempt tool writes from D50.

## Happy path — Claude Code

1. Human opts in (e.g. `/dynamic-full-auto` with a goal); orchestrator `Read`s this skill.
2. **Waves A/B** — One message per wave; parallel `Task(researcher)` / `Task(explore)` with BL-011 payloads; queen merges; `append-pack` / validate as needed.
3. **Checkpoint Γ** — Fresh Stage 0 `classification` + `skills/auto-router/SKILL.md`; present composed delivery table for human approval (same idea as `/auto` Declaration).
4. **Optional PRE_DELIVERY_EVAL** — If **E1–E6** in `.claude/commands/eval.md` fire, run `/eval-swarm` (0.90) per skill § In-between pipeline routing.
5. **Delivery** — Run `/auto`, `/deliver`, or `/deliver-full`; PreToolUse can **mechanically** enforce scope-gate / pipeline-gate before writes when configured.
6. **SessionStart / welcome** — May run via hooks (D52); see `CLAUDE.md` for plain vs Rich orientation.

## Happy path — Cursor

1. Same command/skill text may load via adapters; **PreToolUse and SessionStart do not run** — the orchestrator **simulates** the same checks as `claude-code-parity.mdc` before **every** Write/Edit.
2. **Orientation** — Plain snapshot: `Read` `.azoth/session-orientation.txt` or `python3 scripts/welcome.py --plain`; **Rich** dashboard: run `python3 scripts/welcome.py` in the **integrated terminal** (ANSI), not assumed in agent chat output.
3. **Waves A/B** — Same BL-011 `Task` pattern when **`Task`** is available; if unavailable, **sequential** stages with explicit warning — **not** equivalent isolation (state this in the session log).
4. **Digest writes** — `append-pack` / file edits to the digest are **writes**; scope-gate must **approve** that work (often the same card as discovery; if TTL expires, **`/next`** before continuing).
5. **Checkpoint Γ + delivery** — Same logical flow as Claude Code; **`pipeline-gate.json`** must set `"pipeline"` to match the **next** delivery command (`"auto"` \| `"deliver"` \| `"deliver-full"`).
6. **`/next`** — Use before gated implementation if scope is missing or expired; do not invent parallel workflows — see `.claude/commands/next.md`.

## Happy path — Codex

1. Codex now has **mechanical Bash hooks**: `PreToolUse` can block supported Bash commands, and `PostToolUse` / `Stop` / `UserPromptSubmit` are real hook surfaces. Scope-gate and entropy enforcement for non-Bash `Write`/`Edit` still rely on `developer_instructions` in `.codex/config.toml`.
2. **Network is disabled** in `workspace-write` sandbox (`network_access = false`). **Wave A researcher tasks cannot fetch external URLs.** Research must use pre-seeded context, local files, or be delegated to a platform with network access (Claude Code, Copilot).
3. **Waves A/B** — Use `$azoth-dynamic-full-auto` or literal `/dynamic-full-auto` in prompt. Codex multi-agent (`max_threads: 6, max_depth: 1`) enables parallel researcher/explore tasks within the sandbox, but without external fetches.
4. **Digest writes** — Same scope-gate contract: validate `.azoth/scope-gate.json` before any write, including `append-pack` to the digest.
5. **Checkpoint Γ + delivery** — Same logical flow; `pipeline-gate.json` must match the delivery command.
6. **Stop hook** — `scripts/kernel-integrity.py` runs at session end to flag kernel drift.

## Lazy Eval Loading

Do not pre-load `.claude/commands/eval.md`, `.claude/commands/eval-swarm.md`, or
`.claude/workflows/enterprise/e2e-swarm-eval-loop.md` during discovery-only work. Read them
only if the delivery tail reaches an evaluator boundary or Wave C is actually inserted.

## Operator Checklist

- `active_version` in `roadmap.yaml` matches digest directory name.
- `validate` exits 0; no duplicate `research_packs[].id`.
- Sources are real URLs; contradictions called out in `risks` or `consensus_themes`.
- **Checkpoint Γ:** Stage 0 classification + `auto-router` re-run logged; pipeline table matches
post-digest reality.
- Eval docs are loaded only if PRE_DELIVERY_EVAL or another evaluator boundary is actually used.
- If PRE_DELIVERY_EVAL ran: `/eval-swarm` rules respected (fresh evaluators, minimal spawns, 0.9).
- **E1–E6 audit:** logged which triggers fired (or “none — Wave C skipped by policy”) using the same
table as `.claude/commands/eval.md`.
- Transition to `**/auto`** (or `/deliver-full`) with a **fresh** scope for implementation work.

After editing this skill, run `python3 scripts/azoth-deploy.py` (D46).

## Future refinement

Architecture will evolve (run ledger P1-001, declarative wave YAML P1-002). Keep **digest schema_version**
int; extend fields only with backward-compatible keys or bump schema.

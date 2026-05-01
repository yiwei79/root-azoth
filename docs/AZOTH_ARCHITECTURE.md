# AZOTH Architecture Plan v0.1.0

> Finalized: 2026-04-03 | Session: SupplyGrowth Architect Session
> Status: APPROVED — ready for Phase 1 implementation
>
> Strategic follow-up: see `docs/CO_PRIMARY_PLATFORM_BLUEPRINT.md` for the
> protocol-first platform model that treats **Claude Code** and **Codex** as
> co-primary command surfaces while preserving the adapter pattern for the
> remaining target platforms.

---

## 1. Problem Statement

Extract proven governance patterns, bootloader philosophy, and self-improvement
loops from a production agentic framework into a standalone, portable,
"drop-and-start" personal toolkit that:

- Works natively with the co-primary hosts Claude Code and Codex, while remaining compatible with OpenCode + GitHub Copilot
- Embodies "be water" philosophy: minimal invariant kernel → emergent structure
- Enables trusted autonomous agent swarms with single human alignment point
- Self-improves from experience (L1 → L2 → L3 maturity ladder)
- Installs in under 2 minutes into any repo
- Meta-recursive: can build, improve, and compose coded agent swarms
- Sync-extractable: ongoing pattern absorption from source framework

## 2. Name: Azoth

In alchemy, Azoth is the universal solvent — it dissolves into anything and
transforms what it touches. The word encodes A-to-Z (beginning and end, the
complete essence). Paracelsus called it the "animating spirit."

| Philosophy | Metaphor |
|---|---|
| Be water | Universal solvent — takes shape of any container |
| Drop and start | Dissolves into any repo, catalyzes transformation |
| Secret sauce | The alchemist's personal formula |
| Mutatable | Transforms everything it touches |
| Signature | An alchemist's mark — personal, recognizable |

---

## 3. Architecture: The Water Molecule Model

### Design Principle

"Be water" requires TWO things: shapelessness (no rigid structure) AND cohesion
(water molecules hold together). The toolkit needs:
1. A **kernel** so small it cannot drift (the molecule)
2. **Emergence protocols** that grow structure from goals (the flow)
3. **Entropy bounds** that prevent structure from calcifying (the cycle)

### Four-Layer Model

```
┌─────────────────────────────────────────────────────────┐
│ Layer 3: CURRENT (Orchestration & Delivery)             │
│ Pipeline definitions, swarm coordination, delivery      │
│ flows. Fully emergent — created per-goal, dissolved     │
│ after delivery.                                         │
├─────────────────────────────────────────────────────────┤
│ Layer 2: WAVE (Agents & Capabilities)                   │
│ Agent archetypes, skills, domain-specific agents.       │
│ Semi-stable — emerge from goals, persist if proven,     │
│ dissolve if unused.                                     │
├─────────────────────────────────────────────────────────┤
│ Layer 1: MINERAL (Portable Knowledge & Tools)           │
│ Core skills, episodic memory, prompt library,           │
│ evaluation rubrics. Stable but refinable —              │
│ improved via L1-L2 self-improvement loops.              │
├─────────────────────────────────────────────────────────┤
│ Layer 0: MOLECULE (Invariant Kernel)                    │
│ CLAUDE.md template, bootloader, governance kernel,      │
│ trust contract, promotion rubric. IMMUTABLE —           │
│ changes only via human-approved promotion.              │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Layer 0: The Molecule (Invariant Kernel)

The absolute minimum that makes Azoth Azoth. ~10 files, ~2000 lines total.

| File | Purpose | Size Target |
|------|---------|-------------|
| `CLAUDE.md` (template) | Single source of truth for consumer projects | ~100 lines |
| `azoth.yaml` | Toolkit manifest: version, state, installed layers | ~30 lines |
| `kernel/BOOTLOADER.md` | Boot sequence: Activate → Survey → Operate → Harden | ~100 lines |
| `kernel/PROMOTION_RUBRIC.md` | 4-question decision tree for pattern placement | ~120 lines |
| `kernel/TRUST_CONTRACT.md` | Entropy bounds, alignment protocol, HITL gates | ~200 lines |
| `kernel/GOVERNANCE.md` | Append-only memory rules, drift detection contract | ~100 lines |

### Trust Contract

The formal contract that enables "walk away without anxiety":

1. **Entropy Ceiling**: Every agent action has a bounded blast radius
   - File changes: max N files per session without human approval
   - Governance files: NEVER without human approval
   - New dependencies: NEVER without human approval

2. **Alignment Protocol**: PULL-based (human checks when ready)
   - Agent completes turn → produces alignment summary
   - Human reviews summary (phone-friendly: <500 words)
   - Human sends alignment signal: ✅ continue / 🔄 adjust / ⛔ stop

3. **Drift Detection**: Automatic entropy measurement
   - Session start: validate kernel integrity (checksums)
   - Session end: measure delta from approved state
   - If drift > threshold: block next action, require alignment

4. **Recovery Protocol**: Git-based checkpoints
   - Auto-snapshot before risky operations
   - Rollback to last approved state on failure

5. **Sustainable Velocity Principle**
   - Optimizes for SUSTAINED quality delivery over time, not sprint speed
   - "Fast but wrong" creates negative compounding

---

## 5. Layer 1: Minerals (Portable Knowledge)

### Core Skills (8 total)

**Extracted from source framework (5):**

| Skill | Purpose |
|-------|---------|
| `context-map` | Map blast radius before action |
| `structured-autonomy-plan` | Convert goals to actionable plans |
| `agentic-eval` | Quality gate (coverage, correctness, risk) |
| `remember` | Capture durable lessons |
| `prompt-engineer` | Shape prompts and instructions |

**New for Azoth (3):**

| Skill | Purpose |
|-------|---------|
| `entropy-guard` | Monitor and bound session entropy |
| `alignment-sync` | Generate phone-friendly alignment summaries |
| `self-improve` | L1-L2 reflexion and prompt refinement loop |

### Memory System (3-Layer, Auto-Improving)

```
M3: EPISODIC ── .azoth/memory/episodes.jsonl
    What happened, when, what worked/failed
    Append-only, auto-classified, decays unless reinforced

M2: SEMANTIC ── .azoth/memory/patterns.yaml
    Proven patterns, preferences, project facts
    Promoted from M3 via rubric, human-approved

M1: PROCEDURAL ── kernel/ + skills/ + agents/
    How to do things — encoded in instructions, agents, skills
    Promoted from M2 via governance
```

**Auto-improvement loop:**

```
Work → Episode (M3) → Auto-classify → Propose promotion → Human approves
→ Pattern (M2) → Prove durability → Promote → Instruction/Skill (M1)
→ Prompt Engineer auto-refines M1 content (L2 improvement)
```

**Context-sensitive retrieval (D45):**

Memory is write-AND-read. The auto-improvement loop above describes the write
path. The read path surfaces relevant episodes and patterns into the active
context window based on the current goal:

```
Goal → Extract tags (task_type, keywords, error_signature)
     → Grep M3/M2 by tags → Rank by promotion status, recency, relevance
     → Surface top 1-3 matches before planning begins
```

Retrieval is triggered at two points:

1. **BOOTLOADER SURVEY** (step 6): surface patterns relevant to the session goal
2. **Pipeline Stage 0** (Goal Clarification): surface episodes relevant to the specific task

Implementation: `skills/context-recall/` (Layer 1 skill, NOT a kernel component).
The `remember` skill handles writes to M3; `context-recall` handles reads from M3/M2.

### Instruction Library

| Instruction | Scope |
|-------------|-------|
| `agent-safety` | Governance guardrails |
| `bootloader-workflow` | Boot sequence |
| `context-engineering` | Copilot optimization |
| `spec-driven-workflow` | 6-phase ANALYZE→HANDOFF loop |
| `memory-bank` | 7-file memory architecture |

---

## 6. Layer 2: Waves (Emergent Agents)

### Agent Catalog (10 archetypes, 4 tiers)

**Tier 1: Core Pipeline**

| Archetype | Role |
|-----------|------|
| `Architect` | Design, constraints, alignment, pipeline orchestration |
| `Planner` | Task decomposition, sequencing, test strategy |
| `Builder` | Implementation, testing, code changes |
| `Reviewer` | Quality, governance, safety critique |

**Tier 2: Research**

| Archetype | Role |
|-----------|------|
| `Researcher` | Multi-source research with citations |
| `Research Orchestrator` | Coordinates research swarm |

**Tier 3: Self-Improvement (Meta-Recursive)**

| Archetype | Role |
|-----------|------|
| `Prompt Engineer` | Auto-refine prompts, instructions, rubrics |
| `Evaluator` | Quality gates, scoring |
| `Agent Crafter` | META: Builds/improves other agents (L3) |

**Tier 4: Utility**

| Archetype | Role |
|-----------|------|
| `Context Architect` | Maps dependencies, blast radius |

### The Meta-Recursive Pattern (Agent Crafter)

Operational loop (D21): each stage after the architect brief uses a **fresh subagent context** (e.g. Cursor **`Task`** per stage with the mapped archetype). The orchestrator forwards **BL-012** typed YAML via `inputs.prior_stage_summaries` so **evaluator** and **reviewer** never inherit the crafter’s scratch context.

```
Architect brief → Agent Crafter designs → Evaluator scores (isolated)
→ Prompt Engineer refines → Agent Crafter integrates
→ Reviewer (governance-review) default-on for governed M1 → Human approves
→ Canonical write under agents/ + tests + azoth-deploy (D46)

Meta-level: Agent Crafter improves itself (with human approval)
Entropy guard prevents unbounded self-modification; recursion depth = 1 by default
```

**Waiver:** For **governed** backlog work, the human may skip the post-integration **reviewer** only by recording a **one-line waiver rationale** in the pipeline Declaration; default remains reviewer-on.

### Proactive Agent Posture (D26)

Azoth agents default to proactive-within-boundaries: take initiative on low-risk
actions, escalate high-risk ones.

**Always-do (no permission needed):**
- Pre-action context mapping (explore before changing)
- Dependency pre-staging (fetch related files autonomously)
- Test discovery (find existing tests before writing new ones)
- Memory pattern surfacing ("This matches episode X — relevant?")
- Checkpoint suggestions ("Approaching entropy ceiling — checkpoint?")
- Adjacent bug identification ("Found 2 related issues nearby")

**Ask-first (identify but get approval):**
- Scope expansion ("Evidence suggests new sub-question")
- Agent capability routing ("This needs Context Architect, not just SWE")
- Refactoring opportunities ("This could be cleaner — want me to?")
- Cross-agent escalation ("Governance issue found — invoke reviewer?")
- Command intent resolution ("Compound instruction detected — which part first?")

**Never-auto (always require human signal):**
- Kernel modifications
- Governance changes
- Dependency additions
- Pipeline self-modification
- Memory M2→M1 promotion

Each agent's `.agent.md` defines which posture tier applies to its specific actions.
The Trust Contract defines the overall ceiling.

### Seed Commands (D25)

Core **seed** commands (D25) include at least the table below. **Additional** lifecycle and
orchestration commands ship in this scaffold (for example `/next`, `/intake`, `/start`,
`/roadmap`, and platform-specific aliases) and are not meant to replace the minimum seeded set.

| Command | Category | Purpose |
|---------|----------|---------|
| `/bootstrap` | Lifecycle | Day 0 guided kernel creation |
| `/session-closeout` | Lifecycle | Unified eval + close + sync |
| `/remember` | Lifecycle | Capture cross-session learning |
| `/auto` | Pipeline | Auto-compose and execute an explicit governed delivery pipeline |
| `/dynamic-full-auto` | Pipeline | DYNAMIC-FULL-AUTO+ discovery swarms, digest, Γ, then delivery handoff |
| `/deliver` | Pipeline | Lean pipeline (pre-approved work) |
| `/deliver-full` | Pipeline | Full pipeline with governance gates |
| `/plan` | Pipeline | Structured planning without execution |
| `/context-architect` | Pipeline | Dependency map and blast radius (read-only) |
| `/eval` | Quality | Governance quality gate |
| `/test` | Quality | Unit test generation |
| `/promote` | Governance | Review promotion candidates |
| `/sync` | Infrastructure | Pattern extraction from source framework |
| `/worktree-sync` | Infrastructure | Git checkpoint and sync |
| `/arch-proposal` | Governance | L3 human-gated architecture proposal YAML (P6-003) |

Project-specific commands (session-close, classify-learning, fill-bootloader)
are NOT seeded — they emerge naturally in each consumer project via the memory system.

### Coded Agent Scaffold

```
scaffold/
  coded-agent/          # Single agent template
    __init__.py, config.py, llm_client.py, models.py,
    pipeline.py, prompts.py, cli.py, requirements.txt
  coded-swarm/          # Multi-agent swarm template
    orchestrator.py, worker.py, aggregator.py
```

---

## 7. Layer 3: Currents (Orchestration)

### Pipeline Architecture (D21)

Azoth pipelines are YAML-declarative with typed gates. The full pipeline has 7 stages:

```
Stage 0: GOAL CLARIFICATION
  Parse intent → classify complexity → compose pipeline → human approves

Stage 1: ARCHITECT (with embedded investigation)
  Invoke explore/research agents → synthesize design → human approves

Stage 2: GOVERNANCE REVIEW
  Invoke governance-reviewer → architect disposition → human if needed

Stage 3: PLANNING
  Invoke planner → task plan + test strategy (mandatory) → architect reviews

Stage 4: TEST DESIGN (Test Builder)
  Invoke test-builder → test specs + acceptance criteria → architect reviews

Stage 5: IMPLEMENTATION
  Invoke SWE → implement against plan, run tests → auto-test gate

Stage 6: ARCHITECT REVIEW (Architect Review)
  Compare implementation vs design → final alignment summary → human approves
```

### Pipeline Format: YAML-Declarative (D6, D24)

YAML defines deterministic structure. Markdown defines flexible content.
Every gate is typed as `human` or `agent`.

```yaml
name: full-delivery
stages:
  - name: goal-clarification
    agent: architect
    gate: { type: human, action: approve-pipeline }
  - name: architect-design
    agent: architect
    tools: [explore, research]
    gate: { type: human, action: approve-design }
  - name: governance-review
    agent: governance-reviewer
    gate: { type: agent, action: architect-disposition }
  - name: planning
    agent: planner
    outputs: [task_plan, test_strategy]
    gate: { type: agent, action: architect-review }
  - name: test-design
    agent: test-builder
    outputs: [test_specs, acceptance_criteria]
    gate: { type: agent, action: architect-review }
  - name: implementation
    agent: builder
    gate: { type: agent, action: auto-test }
  - name: architect-review
    agent: architect
    role: post-delivery-review
    gate: { type: human, action: final-approval }
output: alignment-summary
```

### Explore/Research as Architect Tools (D27)

Investigation agents (explore, research, research-orchestrator) are invoked BY the
Architect within its stage — they are tools, not separate pipeline stages. This matches
Claude Code's internal pattern: `queryLoop()` invokes tools within a single agent loop.

```
Architect receives goal
  ├── needs codebase context? → invoke explore agent
  ├── needs external research? → invoke research agent
  ├── needs deep investigation? → invoke research-orchestrator
  └── synthesize findings → produce architecture brief
```

### Goal Clarification Protocol (D22)

Stage 0 runs before pipeline selection. Adaptive questioning with no hard cap:

```yaml
goal_clarification:
  max_cycles: 3
  max_questions_per_cycle: 5
  total_cap: null  # Quality > speed

  protocol:
    - Show understanding FIRST, then ask for corrections
    - "Based on [context], I believe [X]. Is that right?"
    - Only ask what cannot be inferred from context
    - Predict answers from memory/patterns before asking

  adaptive_rules:
    cycle_1: Broad scope (what, why, constraints)
    cycle_2: Code-aware (after initial exploration)
    cycle_3: Edge cases and confirmation
    skip_when: User provides comprehensive spec or says "just do it"

  completeness_check:
    after_each_cycle: Assess if enough to proceed
    present: Pipeline selection with visual rationale
```

### Auto-Pipeline (D23)

Default governed delivery behavior when the user explicitly invokes `/auto` or a lite/default
route escalates into azoth-full. Ordinary work starts in azoth-lite first. Once delivery is
explicit, the Orchestrator classifies the goal, reads the latest local context, and composes
a pipeline from a shared stage-family vocabulary. Presets remain conservative reference
compositions, not rigid output targets.

```yaml
auto_pipeline:
  trigger: Explicit /auto, $azoth-auto, or escalation from azoth-lite into azoth-full governed delivery

  classification:
    scope: kernel | skills | agents | pipelines | docs | mixed
    risk: governance-change | breaking-change | additive | cosmetic
    complexity: simple | medium | complex
    knowledge: known-pattern | needs-research | novel | instruction-refinement

  shared_stage_families:
    - context-recall
    - discovery-evidence-research
    - architect-design
    - review
    - plan
    - execute
    - quality-gate
    - closeout

  discovery_triggers:
    - low-solution-confidence
    - conflicting-memory-or-pattern-evidence
    - cross-surface-drift
    - latest-context-dependency
    - gate-finding-evidence-insufficient

  composition_rules:
    - if risk == governance-change:
        reference_preset: full
        stage_families: [architect-design, review, plan, execute, quality-gate, closeout]
        discovery_policy: conditional
    - if scope == kernel:
        reference_preset: full
        stage_families: [architect-design, review, plan, execute, quality-gate, closeout]
        discovery_policy: conditional
    - if knowledge == needs-research:
        reference_preset: research
        stage_families: [discovery-evidence-research, architect-design, plan, execute, quality-gate, closeout]
        discovery_policy: required
    - if knowledge == instruction-refinement:
        reference_preset: full
        stage_families: [context-recall, architect-design, review, plan, execute, quality-gate, closeout]
        discovery_policy: conditional
    - if scope == docs:
        reference_preset: docs
        stage_families: [architect-design, execute, closeout]
        discovery_policy: conditional
    - default:
        reference_preset: full
        stage_families: [architect-design, review, plan, execute, quality-gate, closeout]
        discovery_policy: conditional

  declaration:
    format: visual-ui
    shows: [goal, classification, composed-stages, rationale]
    gate: human-approve  # Human can override composition
```

Discovery / evidence / research is a **cross-cutting capability** that any auto-family
run may insert when the trigger vocabulary warrants it. `dynamic-full-auto` uses this
same engine in a stronger autonomy posture: it begins with an autonomy budget and may
continue end-to-end, but it is not a discovery wrapper or a forced handoff mode.

### Pipeline Presets (D28)

| Preset | Stages | When |
|--------|--------|------|
| `full` | Goal→Architect(+explore/research)→Governance→Planner→TestBuilder→SWE→ArchReview | Governance/kernel changes |
| `deliver` | Planner→TestBuilder→SWE→ArchReview | Pre-approved, additive work |
| `hotfix` | Planner→SWE→ArchReview | Urgent bug fixes |
| `docs` | Architect→Builder→ArchReview | Documentation only |
| `research` | Architect(+research-swarm)→ArchReview | Investigation/analysis |
| `review` | Architect→Governance→ArchReview | Code/governance review only |
| `refactor` | Architect(+explore)→Planner→TestBuilder→SWE→ArchReview | Structural changes, TDD |
| `auto` | *Composed dynamically via D23* | Explicit governed delivery default after `/auto`, `$azoth-auto`, scope approval, or lite escalation |

### Gate Typing (D24)

Every pipeline gate must declare its type:

| Type | Meaning | Required For |
|------|---------|-------------|
| `human` | Requires explicit human signal to proceed | Kernel changes, governance, design approval, final delivery |
| `agent` | Another agent validates (architect, evaluator) | Plan quality, test coverage, auto-test pass |

**Rule**: Gates involving `kernel/`, governance files, or M2→M1 promotion MUST be `type: human`.

### Swarm Patterns

| Pattern | When | Trust Level |
|---------|------|-------------|
| Sequential pipeline | Default — most predictable | High |
| Parallel exploration | Research, codebase analysis | Medium |
| Evaluator-optimizer | Quality-critical generation | High |
| Orchestrator-workers | Complex multi-file changes | Medium |

---

## 8. Platform Compatibility

### Universal Instruction File

```
CLAUDE.md (universal)
    ├── Claude Code ──── primary, full features
    ├── OpenCode ─────── reads CLAUDE.md natively (free compatibility)
  ├── GitHub Copilot ── reads CLAUDE.md + .github/prompts/ and can discover .claude/agents/
    └── AGENTS.md ──────── AAIF standard (Copilot, OpenCode, Codex, Cursor, Gemini)
```

`AGENTS.md` at the project root is co-governed by the Linux Foundation Agentic AI Foundation
(AAIF, formed Dec 2025 with Anthropic, Microsoft, Google, OpenAI). Every major AI coding tool
reads it natively. Azoth generates it as a cross-platform broadcast layer (D46).

### Platform Adapter Pattern

The installer generates platform-specific files at init time.
Azoth's kernel stays platform-agnostic.

```
azoth init / azoth-deploy.py
  ├─ ALWAYS: CLAUDE.md, AGENTS.md, kernel/, skills/, .azoth/
  ├─ Claude Code detected? → .claude/ (commands, agents, settings)
  ├─ Codex detected?       → .codex/ (agents, config, hooks) + `.agents/skills/azoth-*` command wrappers
  ├─ OpenCode detected?    → .opencode/ (agents/, commands/, opencode.json)
  ├─ Copilot detected?     → .github/ (prompts/, copilot-instructions.md) + .claude/agents/ by default
  └─ Cursor (always in dev-sync) → .cursor/rules/*.mdc (from kernel/templates/platform-adapters/cursor/)
```

### Compatibility Matrix

| Component | Claude Code | OpenCode | Copilot | Codex | Cursor |
|-----------|-------------|----------|---------|-------|--------|
| CLAUDE.md | ✅ Primary | ✅ Native | ✅ Reads | ✅ via AGENTS/config context | ✅ via toggle |
| AGENTS.md | ✅ Native | ✅ Native | ✅ Native | ✅ Native | ✅ Native |
| Skills (SKILL.md) | ✅ .claude/skills/ | ✅ .opencode/skills/{name}/ | ✅ .github/skills/ | ✅ `.agents/skills/` + `azoth-*` wrappers | ✅ .claude + repo (toggle) |
| Agents | .claude/agents/ | .opencode/agents/ | .claude/agents/ by default, optional .github/agents/ mirror | `.codex/agents/*.toml` | .claude/agents/ (toggle) |
| Commands | .claude/commands/ | .opencode/commands/ | .github/prompts/ | `/skills` wrappers (`azoth-*`; `$azoth-start` calm-flow default) + literal-token fallback | .claude/commands/ (toggle) |
| `.cursor/rules/*.mdc` | — | — | — | — | ✅ from `azoth-deploy --platforms cursor` |
| Config | .claude/settings.json | opencode.json | VS Code settings | `.codex/config.toml` | Cursor Settings + toggle |
| Hooks | ✅ Full hook system | ✅ Plugin system | ⚠️ Limited | ⚠️ Hooks-capable (`SessionStart`, `UserPromptSubmit`, Bash `PreToolUse`/`PostToolUse`, `Stop`; non-Bash interception still unavailable) | ❌ (use `.mdc` parity rules) |
| MCP | .mcp.json | opencode.json `mcp` key | VS Code MCP | `.codex/config.toml` / plugins / MCP | VS Code MCP |

### Cursor IDE (Claude) and Claude Code parity

Cursor can consume the **same** Azoth sources as Claude Code when **Settings → Rules → “Include third-party plugin skills and configs”** is enabled: `CLAUDE.md`, `.claude/commands/`, repo-level `agents/` and `skills/` (paths as laid out in this scaffold; consumer installs may mirror via `azoth-deploy`).

**Seamless parity** means: same slash-command semantics, same skills, same trust and pipeline **logic**. **Runtime parity** differs in one important way:

| Mechanism | Claude Code | Cursor (Claude) |
|-----------|-------------|-----------------|
| `CLAUDE.md` + commands + agents + skills | Loaded via product integration | Loaded via toggle above |
| **PreToolUse hooks** (`.claude/settings.json`) | Executed on every tool call | **Not executed** — Cursor does not run Claude Code’s hook binary |
| Scope / pipeline gate enforcement | **Mechanical** (deny Write/Edit) | **Behavioral** — enforced by always-applied **`.cursor/rules/*.mdc`** instructing the model to read `.azoth/scope-gate.json` and `.azoth/pipeline-gate.json` and refuse writes when invalid |
| **Subagent isolation (D21)** | `Agent(subagent_type=...)` | **`Task`** with matching `subagent_type` (Azoth archetypes) — orchestrator stays in main chat; **must not** inline all pipeline stages when `Task` is available (see `claude-code-parity.mdc`) |

**GitHub Copilot parity:** Copilot can load `.github/prompts/`, `.github/copilot-instructions.md`, and discover Azoth agents, but freeform chat is not guaranteed to mechanically switch into slash-command execution. Therefore Copilot must treat literal pipeline tokens (`/auto`, `/dynamic-full-auto`, `/deliver`, `/deliver-full`) as explicit pipeline-entry requests, keep the orchestrator in main chat, and use staged `Task` / subagent execution when available rather than inlining the full pipeline in one thread.

**Codex parity:** Codex does **not** currently document repo-defined custom slash-command registration. Therefore Azoth projects command semantics into Codex through a calm-flow control plane: `$azoth-start` is the canonical daily entry surface, generated `azoth-*` wrappers remain discoverable through `/skills`, and literal `/auto`-style prompt text remains a **compatibility fallback**, not the primary UX contract. Codex should be treated as **source-compatible, instruction-first, skill-routed**: `.codex/config.toml` and `.codex/agents/*.toml` provide the main control plane, `.codex/hooks/user_prompt_submit_router.py` remains as a narrow compatibility hook, and there is still no broad Claude-style `Write/Edit` interception. When a command still uses `body.mode: legacy_claude_markdown`, the Codex wrapper must state that it is bridging through the matching `.claude/commands/*.md` body rather than overstating independence from the legacy mirror.

**Codex hook protocol (confirmed via runtime errors):** Codex hooks have **strict stdout requirements** that differ from Claude Code:

| Hook type | Allowed stdout | Forbidden |
|-----------|---------------|-----------|
| SessionStart | Plain text (becomes session context) | — |
| UserPromptSubmit | `additionalContext`, `updatedInput`, `decision: block` | — |
| PreToolUse | Bash-only mechanical deny via `permissionDecision: deny` or legacy `decision: block` | Non-Bash interception (`Write`, `Edit`, MCP, web tools) |
| PostToolUse | Bash-only `additionalContext`; `decision: block` changes continuation behavior | Undoing side effects from a Bash command that already ran |
| Stop | Valid JSON **or** empty stdout | Plain text, emoji, human-readable messages |

**Rules for Codex hooks:** (1) The default Azoth Codex adapter keeps only a `UserPromptSubmit` compatibility hook because Codex surfaces hook activity prominently in the UI. (2) `additionalContext` remains advisory injection for `UserPromptSubmit`; it is routing help, not authorization. (3) Enforcement that requires non-Bash `Write/Edit` deny still lives in `developer_instructions` in `.codex/config.toml`. (4) If future Codex hooks are added back, re-validate the host protocol surface instead of assuming Claude-style semantics. `scripts/azoth-deploy.py` still lints `.codex/hooks.json` for protocol violations on every deploy/check run. See `docs/platform-guides/codex-guide.md` § Codex Hook Protocol Rules.

**PreToolUse hook commands** in `.claude/settings.json` should use **paths relative to the repository root** (for example `python3 .claude/hooks/edit_pretooluse_orchestrator.py`) so clones and CI do not embed machine-specific absolute paths. Claude Code runs hooks with the **project workspace as the current working directory**. If a hook fails to resolve, use an absolute path only for local debugging.

**Entropy (Write/Edit, P5-002):** `kernel/TRUST_CONTRACT.md` §1 defines **session-scoped** limits for agents. The **PreToolUse** entropy hook runs **once per tool call** and accumulates counters within the active `scope-gate.json` `session_id`, resetting when the scope card changes—mechanical alignment with an approved scope.

**Alignment summary (Write/Edit, P5-003):** `kernel/TRUST_CONTRACT.md` §2 defines the human-facing Alignment Summary. For **machine-comparable** handoffs, pipeline stages emit typed YAML per **BL-012** (`pipelines/stage-summary.schema.yaml`). The **PreToolUse orchestrator** (`.claude/hooks/edit_pretooluse_orchestrator.py`) runs **after** the scope gate and **before** entropy: for **Write** and **Edit** targeting `.azoth/handoffs/**/*.yaml|yml`, it validates **one YAML document** per call using shared structural checks (`.claude/hooks/stage_summary_validate.py`). Invalid **handoff content** → deny with `[alignment-summary]`; **malformed JSON on stdin** remains fail-open (same rationale as scope/entropy hooks). **Edit** resolves `old_string`/`new_string` to candidate text (single match), then applies the same validation as **Write**.

**Malformed stdin (fail-open):** If the hook process receives **invalid JSON** on stdin (PreToolUse payload), the scope and orchestrator hooks **allow** the tool call—same posture as `scope-gate.py` and `pip-install-guard.py`. Rationale: without a parseable payload there is no reliable `tool_name` / `tool_input` to enforce; denying would block **all** Write/Edit on environmental or platform glitches. For the strictest threat model (deny when stdin is corrupt), that would require a separate product or hook contract change—not Azoth-only policy.

**Architectural rule:** Treat Cursor as **source-compatible, hook-soft**. The **kernel/templates/platform-adapters/cursor/** templates (`azoth-memory.mdc`, `claude-code-parity.mdc`) are the **minimum viable guardrails** so sessions honor scope gates, pipeline gates, `/next`, delivery pipelines, and **Task-based** subagent routing **without** relying on hooks. Duplicated policy in M2 patterns + rules is intentional (mechanical enforcement in Claude Code, instruction enforcement in Cursor). **`scripts/azoth-deploy.py --platforms cursor`** copies `*.mdc.template` → `.cursor/rules/*.mdc` so consumer workspaces stay coupled to kernel templates.

**When to use which IDE:** Cursor is appropriate for exploration, edits, and multi-stage delivery **when** the agent uses **`Task`** per `subagent-router` (same isolation contract as Claude Code). Prefer **Claude Code** when you need **binary** PreToolUse enforcement, not for subagent isolation alone. See `kernel/templates/platform-adapters/cursor/README.md`.

#### Cross-IDE session memory parity (`/session-closeout` W1–W4)

Azoth treats **repo-local state** as the **authoritative** narrative every platform must converge on. **Claude Code project memory** (`~/.claude/projects/<project-key>/memory/`) is a **supplemental mirror**, not a second source of truth.

Canonical checkpoint contract lives in **`commands/session-closeout/command.yaml`** plus **`commands/session-closeout/body.md`**; deploy outputs mirror it to **`.claude/commands/session-closeout.md`**, **`.github/prompts/session-closeout.prompt.md`**, and **`.opencode/commands/session-closeout.md`**.

| Checkpoint | What it writes | Claude Code | Codex | Cursor | OpenCode | GitHub Copilot |
|------------|----------------|-------------|-------|--------|----------|----------------|
| **W1** | `.azoth/memory/episodes.jsonl` | ✅ | ✅ | ✅ | ✅ | ✅ (same repo path) |
| **W2** | `.azoth/bootloader-state.md`, `.azoth/run-ledger.local.yaml`, `.azoth/scope-gate.json` (`.azoth/session-state.md` when present) | ✅ | ✅ | ✅ | ✅ | ✅ (same repo paths) |
| **W3** | `~/.claude/projects/<project-key>/memory/` (`project_status.md`, `MEMORY.md` index, optional `feedback_*.md`) | ✅ native | ⚠️ **best-effort** with host FS access; else log `W3 deferred` | ⚠️ **attempt** with host FS access; else log `W3 deferred` | N/A | ⚠️ **attempt mirror write** so later Claude Code sessions can read the latest Copilot-authored closeout |
| **W4** | `python scripts/version-bump.py --patch` | ✅ | ✅ | ✅ | ✅ | ✅ |

**Session start (all IDEs):** **`azoth-memory.mdc`** (Cursor) / same paths in Claude Code — read **`.azoth/memory/patterns.yaml`**, **`.azoth/bootloader-state.md`**, **`.azoth/session-state.md`** when present. Handoff **`session-state.md`** is separate from the W2 bullets in `/session-closeout` (update it when you intentionally leave a cross-IDE capsule). Stage-aware continuity uses `.azoth/run-ledger.local.yaml` as the durable source of truth and mirrors `pipeline`, `pipeline_position`, `current_stage_id`, `completed_stages`, `pending_stages`, `pause_reason`, and `active_run_id` into `session-state.md` for cross-IDE resume.

**Parity rule:** **W1 + W2 + W4** are the **shared contract** — every tool edits or commits the **same files in the repo**. **W3** exists so Claude Code’s native project-memory layer stays aligned; **Codex**, **Cursor**, and **GitHub Copilot** should treat it as a best-effort mirror (attempt W3 or log deferral per the platform adapter rules) instead of a closeout blocker. **Codex**, **OpenCode**, and **GitHub Copilot** still do not **consume** `~/.claude/projects/.../memory/` as a native runtime surface; their parity is **committed W1/W2** (plus `azoth.yaml`). If W2 and W3 diverge, **W2 wins**; refresh W3 on the next closeout run from Claude Code or another host with access.

**Governed closeout rule:** before `scripts/do_closeout.py` performs any W1–W4 mutation for a governed scope or `target_layer: M1`, it must validate the latest matching human `final-delivery` approval for the active `session_id` in `.azoth/final-delivery-approvals.jsonl`. Approval evidence is consume-only during closeout: read it, validate it, and leave it unchanged. Missing, malformed, missing-match, or denied records fail closed before W1.

### Platform File Format Differences

Key structural differences the dev-sync script (D46) must handle:

| Azoth canonical field | Claude Code | Copilot `.agent.md` | OpenCode `.md` |
| --------------------- | ----------- | ------------------- | -------------- |
| `name` | `name` | `name` | filename (no frontmatter field) |
| `description` | `description` | `description` (required) | `description` (required) |
| `tier` | no equivalent | no equivalent | `mode: primary/subagent/all` (partial) |
| `tools` list | `tools` list | `tools` list | `permission` object (richer) |
| `posture.never_auto` | body text | body text | `permission: deny` (structural) |
| `posture.ask_first` | body text | body text | `permission: ask` (structural) |
| `model` | `model` | `model` (VS Code only) | `model` |
| `skills` | body reference | no equivalent | `.opencode/skills/` (separate) |

**posture → permission mapping** (OpenCode-specific, automatable):

```
posture.never_auto items  → permission: deny
posture.ask_first items   → permission: ask
implicitly allowed tools  → permission: allow
```

### Dev-Sync Script (D46)

`scripts/azoth-deploy.py` translates canonical sources into platform-specific deployed files.
This enables cross-platform workspace compatibility without waiting for the Phase 4 installer.

```
agents/**/*.agent.md            ─┬→ .claude/agents/<name>.md         (Claude Code + default Copilot path)
                                 ├→ .github/agents/<name>.agent.md   (optional Copilot compatibility mirror)
                                 ├→ .opencode/agents/<name>.md       (posture→permission, infer mode)
                                 └→ .codex/agents/<name>.toml        (Codex custom agents)

commands/<name>/command.yaml    ─┬→ .claude/commands/<name>.md       (deployed Claude mirror)
 + canonical body.md            ├→ .github/prompts/<name>.prompt.md (add agent binding)
                                 ├→ .opencode/commands/<name>.md     (add $ARGUMENTS support)
                                 └→ .agents/skills/azoth-<name>/     (Codex command-wrapper skills + UI metadata)

commands/<name>/command.yaml    ─┬→ same deployed outputs as above
 + legacy `.claude/commands/*.md`┘   while `body.mode: legacy_claude_markdown` remains live

skills/**/ ─────────────────────┬→ .opencode/skills/<name>/SKILL.md  (per-skill subdirectory)
                                 └→ .agents/skills/<name>/SKILL.md    (Codex / Antigravity shared skill path)
kernel/templates/platform-adapters/codex/*.template
                                 → .codex/*                            (Codex project adapter files)
kernel/templates/platform-adapters/cursor/*.mdc.template
                                 → .cursor/rules/<name>.mdc           (Cursor always-on rules)
                                   AGENTS.md                          (generated broadcast layer)
```

Prior art: Caliber (`caliber-ai-org/ai-setup`) uses a similar canonical→many approach
with a git pre-commit hook triggering regeneration.

---

## 9. Observability & Trust Enforcement

### Session Telemetry

Append-only **JSON Lines** at `.azoth/telemetry/session-log.jsonl` (gitignored). Writer:
`.claude/hooks/session_telemetry.py` (P5-004). Normative intent: `kernel/GOVERNANCE.md` §6.

**`outcome` vocabulary (canonical):**

| `source`   | Typical `outcome` | Meaning |
|------------|-------------------|---------|
| `pretooluse` | `allowed` \| `denied` | PreToolUse `Write`/`Edit` allowed or blocked after scope / alignment / entropy |
| `session`  | `success` | Session lifecycle (e.g. `session_orientation` after welcome) |

**Example lines (illustrative):**

```jsonl
{"session_id":"2026-04-08-p5-004","turn":2,"source":"pretooluse","tool_name":"Write","action":"write","target":"foo.py","outcome":"allowed","entropy_zone":"GREEN","timestamp":"2026-04-08T12:00:00+00:00"}
{"session_id":"","source":"session","action":"session_orientation","outcome":"success","timestamp":"2026-04-08T12:00:01+00:00"}
```

Parsers MUST accept `allowed`/`denied` — not only `"success"`.

### Error Recovery: Git-Based Checkpoints

```bash
# Before risky operations:
git stash push -m "azoth-checkpoint-$(date +%s)"
# OR
git tag azoth/checkpoint/$(date +%s)

# On failure:
git stash pop  # Restore to checkpoint
```

---

## 10. Distribution & Installation

### Primary: Git Clone + Installer

```bash
git clone https://github.com/[user]/azoth.git ~/.azoth
cd my-project && ~/.azoth/install.sh
```

### What `azoth init` Does

1. Detect platform (Claude Code / OpenCode / Copilot / multiple)
2. Detect existing project structure
3. Generate CLAUDE.md (adapted to project)
4. Deploy kernel files
5. Install skills to platform-appropriate directory
6. Deploy agent archetypes (T1 always, T2-4 on demand)
7. Generate platform-specific commands/agents
8. Set up permissions (settings.json / opencode.jsonc)
9. Initialize memory store (.azoth/memory/)
10. Run first boot sequence (Survey phase)
11. Print alignment summary

### Interactive Onboarding (Consumer Projects)

```
╔══════════════════════════════════════════════════╗
║           🧪 AZOTH — Project Setup              ║
╠══════════════════════════════════════════════════╣
║  Detected:                                       ║
║  • Platform: Claude Code + GitHub Copilot        ║
║  • Language: Python                              ║
║                                                  ║
║  Choose your setup:                              ║
║  [1] Minimal — Kernel only (bootloader + trust)  ║
║  [2] Standard — Kernel + core skills + agents    ║
║  [3] Full — Everything + research + meta agents  ║
╚══════════════════════════════════════════════════╝
```

---

## 11. Sync Extraction Mechanism

### `azoth sync --source <path>`

```
Phase 1: SCAN    → Read source framework, build inventory with hashes
Phase 2: DIFF    → Compare against Azoth's current state
Phase 3: PROPOSE → Apply Promotion Rubric to each delta
Phase 4: ALIGN   → Human approves/rejects each pattern
Phase 5: SANITIZE → Strip org-specific references
```

### Sanitization Rules (sync-config.yaml)

```yaml
sanitize:
  strip_patterns: ["OrgName", "InternalProject", "internal-url.com"]
  strip_paths: ["Projects/", "workspace/SESSION_MEMORY.md"]
```

---

## 12. Self-Improvement Roadmap

| Level | Mechanism | Timeline | Human Gate |
|-------|-----------|----------|------------|
| L1 | In-context learning (reflexion, eval, remember) | Day 1 | Per-session |
| L2 | Prompt optimization (auto-refine from evidence) | Month 1-2 | Per-batch |
| L3 | Human-gated architecture search (Agent Crafter) | Month 3+ | Per-proposal |

---

## 13. Repository Structure

```
azoth/
├── CLAUDE.md                     # Azoth development instructions
├── LICENSE                       # PolyForm Noncommercial 1.0.0 (see file)
├── azoth.yaml                    # Toolkit manifest
├── install.sh                    # macOS/Linux installer
├── install.ps1                   # Windows installer
│
├── kernel/                       # Layer 0: MOLECULE
│   ├── BOOTLOADER.md
│   ├── TRUST_CONTRACT.md
│   ├── GOVERNANCE.md
│   ├── PROMOTION_RUBRIC.md
│   └── templates/
│       ├── CLAUDE.md.template
│       ├── settings.json.template
│       ├── copilot-instructions.md.template
│       ├── bootloader-state.md.template
│       └── platform-adapters/
│           ├── claude/
│           ├── opencode/
│           └── copilot/
│
├── skills/                       # Layer 1: MINERAL
│   ├── context-map/SKILL.md
│   ├── structured-autonomy-plan/SKILL.md
│   ├── agentic-eval/SKILL.md
│   ├── remember/SKILL.md
│   ├── prompt-engineer/SKILL.md
│   ├── entropy-guard/SKILL.md
│   ├── alignment-sync/SKILL.md
│   └── self-improve/SKILL.md
│
├── agents/                       # Layer 2: WAVE
│   ├── tier1-core/
│   ├── tier2-research/
│   ├── tier3-meta/
│   └── tier4-utility/
│
├── instructions/                 # Portable instruction library
├── commands/                     # Neutral command contracts + authored bodies
│   ├── <name>/command.yaml
│   └── <name>/body.md            # when migrated; legacy_claude_markdown bridges still exist for some families
├── pipelines/                    # Layer 3: CURRENT
├── scaffold/                     # Coded agent templates
│   ├── coded-agent/
│   └── coded-swarm/
├── hooks/                        # Claude Code hooks
├── scripts/                      # Automation (sync, validate)
├── tests/                        # Drift detection, integrity
├── docs/                         # Architecture, ADRs
│
├── .claude/                      # Meta-dev: Claude Code config
│   ├── commands/
│   └── settings.json
├── .github/                      # Meta-dev: Copilot config
│   └── AGENTIC_BOOTLOADER.md
└── .azoth/                       # Runtime state (gitignored)
    ├── memory/
    ├── telemetry/
    └── sync-log.jsonl
```

**Developer preflight (P1-003):** When `scripts/pipeline_lint.py` exists, run it on `pipelines/*.pipeline.yaml` before relying on composed `/auto` output; CI/pytest should cover happy-path and one malformed fixture once the linter lands.

---

## 14. Risks & Mitigations

| Risk | Impact | Severity | Mitigation |
|------|--------|----------|------------|
| Kernel bloat beyond 2K LOC | Loses "be water" cohesion | High | Hard cap: 10 kernel files, 2000 LOC (D2) |
| Platform drift (Claude Code ↔ Copilot ↔ OpenCode) | Inconsistent behavior | Medium | Dual-write pattern, adapter templates (D19) |
| Sync leaks org-specific content | Privacy / IP violation | High | Sanitization script with explicit strip patterns (D9) |
| Meta-recursive loop diverges | Unbounded self-modification | Medium | Evaluator scoring + human gate + recursion depth=1 |
| Trust enforcement deferred to Phase 5 | Phases 1-4 built without enforcement | High | Move minimum viable trust (kernel checksums) to Phase 1 |
| Premature L3 self-modification | Architecture drift without guardrails | Medium | Human gate on ALL kernel changes, no agent self-approval |
| Installation complexity | Adoption barrier | Low | Single-command installer, sensible defaults |
| Platform adapter drift after init | Generated files diverge from templates | Medium | Manifest-based reconciliation (`azoth doctor`, Phase 4) |

---

## 15. Architecture Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Name: Azoth | Universal solvent metaphor, CLI ergonomics |
| D2 | Kernel: 10 files / 2000 LOC cap | Small enough to never drift |
| D3 | Trust Contract: entropy ceiling | Enables anxiety-free autonomy |
| D4 | Repo: isolated from org repos | No org contamination |
| D5 | Distribution: git clone + installer | Simple, v1 appropriate |
| D6 | Pipelines: YAML-declarative | Deterministic structure + flexible content |
| D7 | Agents: 10 archetypes, 4 tiers | Core + Research + Meta + Utility |
| D8 | Coded scaffold: included | Meta-recursive requires it |
| D9 | Sync extraction: Python script | Ongoing pattern absorption |
| D10 | Session scope: Phase 1 + Sync per session | Quality over quantity |
| D11 | Memory: 3-layer auto-improving | M3 episodic → M2 semantic → M1 procedural |
| D12 | Claude Code Extension: full compat | Dual-path deployment |
| D13 | Skills: shared between platforms | SKILL.md is universal format |
| D14 | Observability: session telemetry | Trust Contract enforcement |
| D15 | Rollback: git-based checkpoints | Simple, portable, understood |
| D16 | README: Phase 4 deliverable | Not Day 0 |
| D17 | Pipeline schema: Phase 3 deliverable | Not Day 0 |
| D18 | OpenCode: compatible via CLAUDE.md | Reads it natively, free |
| D19 | Platform adapter pattern | Complexity in installer, not kernel |
| D20 | No multi-platform layers in kernel | Kernel stays agnostic |
| D21 | Full pipeline: 7 stages with typed gates | Research-validated canonical pattern |
| D22 | Goal Clarification Protocol (Stage 0) | Adaptive questioning, no hard cap |
| D23 | Auto-pipeline: LLM-as-router composition | Explicit governed delivery behavior, 8 presets |
| D24 | Gate typing: human vs agent | Kernel/governance gates must be human |
| D25 | Seed slash commands: documented minimum set + scaffold extensions | Essential lifecycle + pipeline + quality; see § Seed Commands (D25) |
| D26 | Proactive Agent Posture: 3 tiers | always-do / ask-first / never-auto |
| D27 | Explore/Research as Architect tools | Not separate pipeline stages |
| D28 | 8 pipeline presets | full, deliver, hotfix, docs, research, review, refactor, auto |
| D29 | Inbox format: `.azoth/inbox/*.jsonl` | Append-only, machine-parseable, git-friendly |
| D30 | Trusted source registry | Governance boundary for external data |
| D31 | SURVEY auto-detect + `/intake` | Passive awareness + explicit processing |
| D32 | 12-field insight schema | Structured enough to triage, flexible enough to extend |
| D33 | 4-step intake protocol | Validate → Classify → Triage → Integrate/Archive |
| D34 | root-azoth = personal root scaffold | Private workshop, not consumer product |
| D35 | azoth = public deployable product | Extracted via sync, consumer-ready |
| D36 | `--scaffold` vs `--project` modes | Phase 4 product differentiation |
| D37 | root-azoth (private) / azoth (public) | Naming convention for clarity |
| D38 | Scaffold infra now, extraction later | Build the workshop, extract the product when ready |
| D39 | Roadmap tracking: `.azoth/roadmap.yaml` | Machine-readable task backlog for agent self-direction |
| D40 | Repo rename: root-azoth (private) | Clear distinction from azoth (public product) |
| D41 | Bootstrap loop: 4 artifacts | Roadmap + /next + preflight gate + decisions index |
| D42 | Path duality (scaffold `kernel/` vs consumer `.azoth/kernel/`) | Normative rules in §18 Path duality; installer deploys read-only copy |
| D43 | Commit-time governance enforcement hooks | Git `commit-msg` hook + `scripts/git_commit_policy.py` reject `Co-Authored-By:` trailers; `scripts/azoth_install_git_hooks.py` sets `core.hooksPath` — VCS-time complement to BL-002 PreToolUse scope-gate (write-time); further format rules optional |
| D44 | Pipeline Stage 6 quality rubric for structured content | Stage 6 (Architect Review) must score generated structured content against minimum depth thresholds before passing the delivery gate — prevents shallow first-pass output |
| D45 | Context-sensitive memory retrieval | Grep-by-tags read interface for M3/M2; dual trigger at SURVEY + Stage 0; implemented as Layer 1 skill (`context-recall`), not kernel |
| D46 | Dev-sync script: workspace self-installation to platform directories | `scripts/azoth-deploy.py` translates canonical agents/skills/commands into Claude Code, Copilot, OpenCode, Codex platform-specific files + AGENTS.md broadcast layer |
| D47 | Persistent backlog system: `.azoth/backlog.yaml` | Operational work queue; items carry `target_layer` (M1/M2/M3/infrastructure) and `delivery_pipeline` (governed/standard); active items cannot be silently dropped — deferral requires `target_version` |
| D48 | Versioned roadmap: `.azoth/ROADMAP.yaml` | Supersedes D39; multi-version structure (active/planned/backlog/complete); tasks reference backlog items; CLAUDE.md becomes rendered summary; explicit deferral with reason |
| D49 | Intake 3-axis triage | Extends D33 step 3: for each integrated insight, human simultaneously decides (1) M3 action, (2) M2 candidate flag, (3) backlog item needed — three independent axes, any combination valid |
| D50 | Session scope card | `/next` outputs a scope card (1 primary + max 2 secondary goals); human approves → writes `.azoth/scope-gate.json`; validator rejects mixed M1+runtime sessions |
| D51 | Formalized M2→M1 promotion path | M1 changes are a governed event: `target_layer: M1` backlog item + `/deliver-full` pipeline; M1 changes happen between sessions only; scope card validator enforces isolation |
| D52 | Session Welcome UX: `/start` + `scripts/welcome.py` | Rich-rendered terminal dashboard at session open; `scripts/welcome.py` reads `azoth.yaml`, `backlog.yaml`, `scope-gate.json`, recent episodes and renders via Python `rich` library — `box.HEAVY` identity header, `box.MINIMAL` phase progress strip, `Columns([health, backlog])` 2-column body with `box.ROUNDED` panels, last-session strip, START options panel; Rich handles all Unicode/emoji width via wcwidth internally — zero manual padding; context-sensitive option menu (resume if gate active, else /next); the canonical start contract now lives in `commands/start/command.yaml` + `commands/start/body.md`, with deployed mirrors for Claude/Cursor and calm-flow `$azoth-start` routing for Codex; UX entry point for D41 bootstrap loop; Phase 4 deliverable; Phase 5 (Claude Code): `hooks.SessionStart` → `.claude/hooks/session_start_welcome.py` runs `welcome.py --plain`, tees stdout to `.azoth/session-orientation.txt` (gitignored), injects same text into model context; matchers `startup|resume`; optional per-hook `timeout` (seconds, hooks doc); `CLAUDE.md` rule 9 — default trust injection, `Read` file for verbatim chat only; Cursor has no SessionStart — parity rules + manual script |

---

## 16. v0.1.0 Release Criteria

- [ ] Kernel passes integrity tests
- [ ] `azoth init` works on macOS + Windows
- [ ] All 8 skills functional
- [ ] 4 core pipeline agents (T1) working end-to-end
- [ ] Memory system captures and promotes episodes
- [ ] Trust Contract enforceable (telemetry + checkpoints)
- [ ] At least 1 consumer project successfully deployed

---

## 17. Development Phases

| Phase | Scope | Deliverables |
|-------|-------|-------------|
| **1** | Kernel Extraction | 4 kernel docs, templates, platform adapters, installer |
| **1.5** | Sync Infrastructure | azoth-sync.py, sync-config.yaml, /sync command |
| **2** | Core Skills | 5 extracted + 3 new skills, drift tests |
| **3** | Agent Archetypes | 10 agents, pipeline schema, dual-format |
| **4** | Distribution | Session Welcome UX (`/start` + `scripts/welcome.py`), README, `azoth init` onboarding, CI, publish |
| **5** | Trust Layer | Hooks (incl. P5-007 SessionStart → plain orientation + `.azoth/session-orientation.txt` on Claude Code), telemetry, checkpoints, phone-friendly output |
| **6** | Meta-Recursive | Agent Crafter, L2 optimization, L3 proposals |

---

## 18. Root Scaffold Architecture (D29–D38)

### Scaffold vs Product Identity (D34–D37)

| Attribute | Root Scaffold (this repo) | Deployable Product |
|-----------|---------------------------|-------------------|
| Repo name | **root-azoth** (private) | **azoth** (public) |
| Purpose | Development workshop, design lab | Consumer-ready toolkit |
| Contains | All experiments, audit trails, session history | Clean extracted artifacts |
| Audience | The alchemist (you) | Any developer |
| Mode | `scaffold` | `project` (Phase 4) |

### 3-Tier Product Flow

```
Tier 1: Source Framework (SupplyGrowth Agentic Framework)
  │ patterns extracted via azoth-sync.py
  ▼
Tier 2: Root Scaffold (root-azoth — this repo)
  │ product extracted via sync-config.yaml profiles
  ▼
Tier 3: Deployable Product (azoth — public repo)
  │ installed into consumer projects
  ▼
Consumer Projects
```

- **Tier 1 → Tier 2**: `azoth-sync.py` extracts proven patterns, sanitizes org content
- **Tier 2 → Tier 3**: Product extraction profiles strip scaffold-only artifacts
- **Tier 3 → Consumer**: `install.sh` deploys kernel + skills + agents

### 4-Plane Operating Model

The 3-tier product flow is the release/update supply chain. Daily authority now
uses a 4-plane operating model:

| Plane | Authority | Owns | Must not own |
| --- | --- | --- | --- |
| `root-azoth` development workshop | Toolkit source, roadmap, validation, extraction | Source scripts, tests, governance, release evidence, generated adapters | Personal cockpit state or project-local write authority |
| Public `azoth` product | Installable release authority | Clean extracted runtime, installers, public docs, tags, public CI | Private root history, cockpit memory, project secrets |
| `yiwei-azoth-cockpit` personal control plane | Operator routing, global pointers, release ledger, personal memory | Project pointers, cockpit receipts, personal/global context, safe-open command surface | Project source, project instructions, project-local gates |
| Controlled project repos | Project-local context and write authority | Code, project memory, project instructions, project gates, project receipts | Cockpit-global memory or public product release authority |

Project switching from the cockpit is handoff execution: the cockpit may print
the project path and a fresh project-session prompt, but project context becomes
authoritative only inside the project repo/session.

### Insight Inbox Protocol (D29–D33)

External insights (from Tier 1 audits, cross-project analysis, or other sources)
enter the scaffold through a governed channel:

- **D29**: `.azoth/inbox/*.jsonl` format with summary.md companion
- **D30**: Trusted source registry at `.azoth/trusted-sources.yaml`
- **D31**: SURVEY auto-detect + `/intake` command
- **D32**: Standardized insight schema (12 fields)
- **D33**: Validate → Classify → Human Triage → Integrate to M3 or Archive

See `kernel/GOVERNANCE.md` Section 7 for the full intake protocol.

### Product Extraction (D38)

Scaffold infrastructure is implemented NOW. Public repo extraction is a
mechanical step deferred to Phase 4:

1. Define extraction profiles in `sync-config.yaml`
2. Strip scaffold-only artifacts (session history, inbox, audit trails)
3. Generate clean product repo with consumer-facing README
4. Validate: fresh clone → install → tests pass

### Path duality (D42): `kernel/` vs `.azoth/kernel/`

Azoth uses **two legitimate locations** for the same four governance documents (`BOOTLOADER.md`, `TRUST_CONTRACT.md`, `GOVERNANCE.md`, `PROMOTION_RUBRIC.md`). Which path is correct depends on **workspace role**, not preference.

| Context | Authoritative path | Role |
|---------|-------------------|------|
| **Scaffold / toolkit development** (e.g. root-azoth clone, Tier 2) | Repo root **`kernel/`** | Source of truth. Edits happen here; changes promote via governance. |
| **Consumer project** (after `install.sh` / `install.ps1`, Tier 3 → consumer) | **`.azoth/kernel/`** | Read-only copy deployed by the installer. Not a second editable tree. |

**How to tell:** If the repository contains a top-level **`kernel/`** directory next to `scripts/` and `skills/`, you are in **scaffold** mode — use `kernel/` for Layer 0. If there is **no** repo root `kernel/` but `.azoth/kernel/*.md` exists, you are in **consumer** mode — treat `.azoth/kernel/` as the governance read path; do not create a parallel root `kernel/` for edits.

**Drift and integrity:** Consumer installs record checksums in **`.azoth/kernel-checksums.sha256`**. The integrity check is defined under **ACTIVATE** in `BOOTLOADER.md` (hashed files live under `.azoth/kernel/` after install). Resolve “where is GOVERNANCE?” using the table above before opening files.

**Related:** P4-006 aligns individual `kernel/*.md` files (including `BOOTLOADER.md` ACTIVATE) with this convention. D42 is the normative story; P4-006 is the mechanical pass.

### Architecture Decisions (D29–D38)

| # | Decision | Rationale |
|---|----------|-----------|
| D29 | Inbox format: `.azoth/inbox/*.jsonl` | Append-only, machine-parseable, git-friendly |
| D30 | Trusted source registry | Governance boundary for external data |
| D31 | SURVEY auto-detect + `/intake` | Passive awareness + explicit processing |
| D32 | 12-field insight schema | Structured enough to triage, flexible enough to extend |
| D33 | 4-step intake protocol | Validate → Classify → Human Triage → Integrate/Archive *(step 3 extended by D49)* |
| D34 | root-azoth = personal root scaffold | Private workshop, not consumer product |
| D35 | azoth = public deployable product | Extracted via sync, consumer-ready |
| D36 | `--scaffold` vs `--project` modes | Phase 4 product differentiation |
| D37 | root-azoth (private) / azoth (public) | Naming convention for clarity |
| D38 | Scaffold infra now, extraction later | Build the workshop, extract the product when ready |
| D39 | Roadmap tracking: `.azoth/roadmap.yaml` | Machine-readable task backlog for agent self-direction *(superseded by D48)* |
| D40 | Repo rename: root-azoth (private) | Clear distinction from azoth (public product) |
| D41 | Bootstrap loop: 4 artifacts | Roadmap + /next + preflight gate + decisions index |
| D42 | Path duality: `kernel/` (scaffold) vs `.azoth/kernel/` (consumer) | Same four governance files; role depends on install vs development — see §18 Path duality |

---

## 19. Closed Workflow Loop (D47–D51)

### Why This Section Exists

The intake → M3 → M2 pipeline (D29–D33, D11) was a one-way funnel: insights
went *in* through the inbox, accumulated in episodes and patterns, but had no
governed path *back out* into session planning. The result was ad-hoc scope
creep, ignored backlog items, and a monolithic roadmap that couldn't express
"valuable but not now."

This section formalizes the full closed loop:

```
session → closeout → inbox
          /intake (3-axis, D49) → M3 + M2-candidate flag + backlog draft
          /promote → M2 (for M2-candidate items)
          backlog.yaml (D47) ← operational source of truth
          ROADMAP.yaml (D48) ← versioned strategic plan
          /next → scope card (D50) → human approves
          scope-gate.json → PreToolUse hook (P3-008)
          session (scope-enforced)
          → M1 if governed (/deliver-full), infrastructure/M2/M3 if standard
          → loop
```

### D47: Persistent Backlog (`.azoth/backlog.yaml`)

The backlog is the operational work queue. Every insight-derived task, every
architecture decision that implies implementation, every deferred roadmap item
lands here.

**Schema fields:**

| Field | Values | Purpose |
|-------|--------|---------|
| `id` | BL-NNN | Stable identifier |
| `title` | string | Short description |
| `source` | episode id / decision | Origin traceability |
| `target_layer` | M1 / M2 / M3 / infrastructure | Routes delivery pipeline |
| `delivery_pipeline` | governed / standard | governed → /deliver-full |
| `status` | active / deferred / done | Active items cannot be silently dropped |
| `target_version` | v0.1.0 / v0.2.0 / ... | Required for deferral |
| `priority` | integer | Lower = higher priority |

**Enforcement:** `/next` reads `backlog.yaml` as primary input. Active items
persist until explicitly deferred (requires `target_version`) or done. There
is no silent drop path.

### D48: Versioned Roadmap (`.azoth/ROADMAP.yaml`)

Supersedes D39. The roadmap is now multi-version:

```yaml
versions:
  - id: v0.1.0
    status: active       # current release scope
  - id: v0.2.0
    status: planned      # deferred items + next phase
  - id: v0.3.0
    status: planned      # future phases
  - id: v0.4.0
    status: backlog      # long-horizon
```

Items deferred from the active version carry an explicit `deferred_reason`.
CLAUDE.md roadmap section becomes a rendered summary of `ROADMAP.yaml active`
— the machine-readable file is the source of truth.

`.azoth/roadmap.yaml` (D39) remains active until `/next` is updated to read
`ROADMAP.yaml + backlog.yaml` (BL-004).

### D49: Intake 3-Axis Triage (extends D33)

D33's step 3 (Human Triage) is extended from a single decision to three
independent axes presented simultaneously:

```
M3 action:      [ integrate | archive | defer ]
M2 candidate?   [ yes | no ]
Backlog item?   [ yes | no | draft ]
```

Any combination is valid. A single insight can be integrated into M3, flagged
as an M2 promotion candidate, AND generate a backlog item — or any subset.

**M2 candidate flag** is consumed by `/promote` (avoids re-scanning all M3).
**Backlog item draft** is proposed by the agent and written to `backlog.yaml`
on human approval.

### D50: Session Scope Card

`/next` outputs a scope card before the session begins:

```
Primary goal:    [exactly 1 task from active backlog/ROADMAP]
Secondary goals: [0-2 supporting tasks]
target_layer:    [M1 | infrastructure | mixed — mixed is REJECTED]
```

Human explicitly approves the scope card. Approval writes
`.azoth/scope-gate.json` with the approved goals and expiry. The PreToolUse
hook (P3-008) reads this file before allowing Write/Edit.

**Validator rule:** A scope card mixing M1-targeted items with runtime tasks
is rejected. M1 changes require a dedicated session.

### Long-running sessions (P1-005)

Multi-hour or multi-wave work (including DYNAMIC-FULL-AUTO+ discovery and `/eval-swarm`) must stay
compatible with **short-lived scope and pipeline gates** (D50) and the Trust Contract entropy ceiling.
Operator-visible friction (discovery narrative vs gates, Claude Code vs Cursor, digest handoffs) is
documented under **`skills/dynamic-full-auto/SKILL.md`** (roadmap **P1-012**).

**Checklist**

1. **Refresh scope before TTL expiry** — Run `/next` (or human-approved scope card) to write a new
   `.azoth/scope-gate.json` when the current `expires_at` is near; do not assume silent extension.
   **Lightweight alternative:** the orchestrator may extend `expires_at` in-place (by 1 hour) when
   a pipeline is mid-execution, provided it surfaces a TTL card to the human offering extend /
   checkpoint / abort. This avoids full re-scoping mid-pipeline while preserving human-in-the-loop.
   Explicit `/resume` restores the previously approved scope directly; it should not force a second
   scope-approval wall.
2. **Chunk delivery** — Keep each governed write batch within approved scope; split backlog slices
   rather than exceeding the per-session file ceiling.
3. **Run ledger (P1-001)** — Append wave outcomes to `.azoth/run-ledger.local.yaml` (gitignored)
   after each wave or stage; use `python3 scripts/run_ledger.py status` to resume without replaying prose. Schema: `pipelines/run-ledger.schema.yaml`.
4. **Digest merges** — After swarm append to `SWARM_RESEARCH_DIGEST.yaml`, run
   `python3 scripts/swarm_research_digest.py validate` on that path before commit.
5. **Never disable hooks** — Long runs do not bypass PreToolUse scope-gate or pipeline-gate; adjust
   scope instead.

**Risks:** Expired gates mid-run cause mechanical Write/Edit denies; stale scope cards mis-label M1
vs infrastructure work; unbounded parallel Task fan-out violates swarm Iron Laws (see
`.agents/skills/swarm-coordination/SKILL.md`).

### Context & token budget (P1-011)

**Goal:** Lower median tokens and latency per session **without** weakening D50 gates, **BL-012**
typed handoffs, or **`/eval-swarm`** quality bars.

**Principles (toolkit-level):**

1. **Compaction at stage boundaries** — Prefer machine-readable **`pipelines/stage-summary.schema.yaml`**
   payloads (`prior_stage_summaries`) over pasting full subagent prose into the orchestrator thread
   (extends completed **BL-012**).

2. **Static prefix, volatile suffix** — For provider **prompt caching**, keep **stable** system
   instructions, tool definitions, and rubrics **early**; put **session-specific** state (scope
   cards, file lists that churn every turn) **late**. Small tool or parameter toggles can
   **invalidate** large cached prefixes — document this when changing hooks or command bodies.

3. **Spawn hygiene** — Follow **`skills/subagent-router/SKILL.md`** **BL-011**: minimal YAML spawn +
   **`Read`** targets instead of embedding the whole pipeline table in every **Task**.

4. **Parallel eval economics** — **`/eval-swarm`** multiplies tokens vs a single evaluator; use it
   when **E1–E6** triggers fire (**`.claude/commands/eval.md`**). For **offline** scoring, vendor
   **batch** APIs trade latency for cost — not a substitute for interactive gates.

5. **Deploy stability** — **`scripts/azoth-deploy.py`** (**D46**) should keep mirrored command/agent
   text **deterministic** so repeated installs share long identical prefixes where the API layer
   repeats scaffold text.

**Research aggregate:** `.azoth/roadmap-specs/v0.2.0/SWARM_RESEARCH_DIGEST.yaml` pack **RP-E**
(sources: OpenAI / Anthropic / Gemini caching docs; ACON arXiv:2510.00615; Context Folding OpenReview;
JetBrains context-efficiency blog; PASTE arXiv:2603.18897; OpenAI Batch API).

### D51: Formalized M2→M1 Promotion Path

D11 noted "M2→M1 pending" as a partial status. D51 formalizes it.

**Trigger:** A backlog item with `target_layer: M1` + `/deliver-full` pipeline.

**Rules:**
- M1 changes happen *between* sessions, never during an active session
- The scope card validator (D50) enforces this: M1 items cannot be mixed with runtime tasks
- `/deliver-full` is the required pipeline for all M1-targeted backlog items
- This applies to kernel/, skills/, commands/ (plus their deployed mirrors), and agents/ equally

**Promotion chain:**

```
Observation (M3) --/promote--> Pattern (M2) --BL item + /deliver-full--> Procedure (M1)
    ^                              ^                                           ^
any insight                 reinforced >=2x                         governance-gated
m2_candidate=true flag      set at intake                           target_layer: M1
```

### Architecture Decisions (D47–D54)

| # | Decision | Rationale |
|---|----------|-----------|
| D47 | Persistent backlog: `.azoth/backlog.yaml` | Enforced operational queue — active items cannot be silently dropped |
| D48 | Versioned roadmap: `.azoth/ROADMAP.yaml` | Explicit deferral across versions eliminates squeeze-in scope creep |
| D49 | Intake 3-axis triage | M3/M2/backlog routing is simultaneous and independent, not sequential |
| D50 | Session scope card | Mechanical scope limiter — approved goals write scope-gate.json before session |
| D51 | Formalized M2→M1 promotion path | M1 changes are governed events between sessions; target_layer field routes delivery |
| D52 | Session Welcome UX: `/start` + `scripts/welcome.py` | Single entry point for session orientation — routes to /next, /intake, /promote, or custom goal; in **Codex**, `$azoth-start` is the calm-flow daily entry surface and raw slash tokens are compatibility fallback. **Claude Code** may also inject plain orientation via **SessionStart** (P5-007) and mirror to `.azoth/session-orientation.txt` (`CLAUDE.md` rule 9) |
| D53 | Auto-versioning policy | Version increments are delivery-triggered — 0.0.PHASE.PATCH pre-release, then 0.1.MILESTONE_PHASE.PATCH while shipping toward v0.2.0 |
| D54 | Branch model + worktree policy | Two permanent branches (`main`, `phase/vN-pN`); short-lived feature/patch branches deleted on merge; zero-worktree default to avoid scope-gate + run-ledger conflicts |

---

## 20. Auto-Versioning Policy (D53)

### Problem

Version numbers in `azoth.yaml` and `roadmap.yaml` require manual updates and drift from
actual delivery state. There is no signal connecting completed backlog items to version
progression, so the version number becomes decorative rather than informative.

### Decision

Version increments are **delivery-triggered**, governed by two bump classes:

```
M1 delivery complete (via /deliver-full)     → patch bump:  0.x.y → 0.x.y+1
Phase milestone complete (all phase items)   → minor bump:  0.x.y → 0.x+1.0
                                              + git tag proposed (user-confirmed)
```

### Version Format

#### Pre-release roadmap phases: `0.0.PHASE.PATCH`

```
0.0.PHASE.PATCH
│ │  │      └── delivery counter — increments every session, resets to 1 on phase bump
│ │  └───────── phase number — equals the current development phase (1–7)
│ └──────────── reserved: 0 during development
└────────────── reserved: 0 until public release
```

### Version Map

| Version | Scope | Phase |
|---------|-------|-------|
| v0.0.1 | Phases 1 + 1.5: kernel + sync + inbox | 1, 1.5 |
| v0.0.2 | Phase 2: core skills | 2 |
| v0.0.3 | Phase 3: agent archetypes + workflow loop | 3 |
| v0.0.4 | Phase 4: Distribution & Polish | 4 |
| v0.0.5 | Phase 5: Trust Layer | 5 |
| v0.0.6 | Phase 6: Meta-recursive | 6 |
| v0.0.7 | Phase 7: Publishing & public product | 7 |
| **v0.1.0** | **Public azoth release — full roadmap complete (Phases 1–7)** | — |
| v0.2.0 | Milestone target / container | Holds the roadmap specs, initiatives, and eventual release target |
| v0.2.0-p1 | Milestone phase 1 working slice | Active phase-1 queue under the v0.2.0 milestone |

### Bump Rules

- **PATCH** (`0.0.N.XX+1`): every delivery session in the pre-release roadmap. Counter resets
  to `.1` on each pre-release phase bump.
- **PATCH (post–v0.1.0)** (`0.1.P.M+1`): after `--release`, `azoth.yaml` stays four-part and
  `--patch` increments the fourth component; `roadmap.yaml` mirrors that in the active
  working slice `current_patch` (for example `v0.2.0-p1` phase 1 ↔ `0.1.1.M`).
- **PHASE** (`0.0.N+1` or `0.1.P+1.0`): phase completion. Pre-release phases continue the
  `0.0.*` line; post-release milestone work advances the milestone-local phase number and
  resets PATCH to `.0`.
- **Release** (`--release` from `v0.0.7` active): closes v0.0.7 + v0.1.0 roadmap blocks,
  proposes the public git tag **`v0.1.0`**, then moves the repo onto **`0.1.1.0`** with
  **`current_phase: 1`**, **`milestone: v0.2.0`**, **`lifecycle_phase: 8`**, milestone
  target block **`v0.2.0`**, and active working slice **`v0.2.0-p1`** at `current_patch: 0`.
  Git tag proposed — user-confirmed, never auto-pushed.

The PATCH counter provides agents with a reliable time-series signal: higher PATCH = later
in the phase. PHASE provides coarser orientation. Together they encode "where in development
are we" without requiring agents to read git history.

### Task IDs vs Working Slices

Post-v0.1.0 roadmap work has two separate axes:

- **Task id** (for example `P1-024`) = stable backlog/spec reference key
- **Working slice** (for example `v0.2.0-p2`) = milestone-local phase / delivery target

The current `v0.2.0` task set includes a legacy `P1-*` namespace because those ids were minted
when `v0.2.0-p1` opened. That namespace was carried into later working slices so existing spec
refs, backlog links, tests, memory episodes, and PR discussion references stayed stable.

Implications:

- Do **not** read the `P1` prefix as "phase 1" once a task is scheduled under `v0.2.0-p2+`
- Use `roadmap.yaml` `active_version`, the containing `versions[]` block, and backlog
  `target_version` to answer "what phase/slice is this in?"
- In human-facing summaries, prefer `P1-024 @ v0.2.0-p2` or `T-001 @ v0.2.0-p2` when ambiguity matters

### Namespace Rule Going Forward

- `v0.2.0` keeps existing `P1-*` ids as frozen legacy keys
- Historical `P1-*` ids are **not** renamed mid-stream just to match the current slice label
- New roadmap-backed task ids now mint in a neutral namespace:
  `T-{NNN}` (for example `T-001`, `T-002`)
- `T-*` ids are opaque task identifiers, not phase labels
- Milestone-local phase/slice semantics continue to come from `active_version`,
  the containing roadmap version block, and backlog `target_version`
- `roadmap.yaml` `task_id_policy` is the machine-readable source for this rule;
  `python scripts/roadmap_task_id.py` resolves the next available task id from that policy

This gives Azoth a clean future naming model without breaking the large body of existing
references to `P1-*` work across specs, tests, memory, and delivery history.

### Implementation (BL-009)

- `scripts/version-bump.py` — reads `azoth.yaml`, applies `--patch` or `--phase` bump,
  writes `azoth.yaml` and updates `roadmap.yaml` `active_version` + `current_patch` fields.
  `--release` closes the v0.0.7 slice, marks v0.1.0 complete, sets the v0.2.0 milestone
  container to `target`, activates `v0.2.0-p1`, sets milestone-local `phase: 1` +
  `milestone` + `lifecycle_phase: 8`, writes `0.1.1.0`, and proposes the public v0.1.0 tag.
- `/session-closeout` integration — final step always calls `version-bump.py --patch`
  after W3 so every successful closeout advances the patch version.
- `/deliver-full` integration — calls `version-bump.py --patch` after builder stage
  completes successfully.

### Rules

- Version bumps are never silent — `version-bump.py` prints the old → new transition
- Git tags are proposed at `--release` only; patch/phase bumps update files only
- `azoth.yaml` `version` is the authoritative time-series field for agents
- `roadmap.yaml` `active_version` + `current_patch` mirror it for roadmap context; after v0.1.0
  they track the active **working slice** (`v0.2.0-p1`, `v0.2.0-p2`, …), not the milestone container
- On `--phase` bump: `version-bump.py` writes `final_patch: N` to the completing version
  entry in `roadmap.yaml` before advancing `active_version` — preserves the full time-series
  history for completed phases
- `target_version` in `backlog.yaml` uses the delivery-phase version (e.g. `v0.0.3` or
  post-v0.1.0 `v0.2.0-p1`), not the milestone container or a future release target — completed
  items record where they actually landed

---

## 21. Branch Model + Worktree Policy (D54)

### Problem

Multi-platform parity work (Gemini, Codex, Copilot) and overlapping sessions generate
parallel branches that accumulate silently. Azoth's scope gate, run-ledger write claim,
and `azoth-deploy.py` mirror enforcement are all repo-root-relative — multiple worktrees
create mechanical conflicts. Without codified rules, branch hygiene becomes reactive
cleanup work rather than a maintained invariant.

### Decision

#### Branch Structure

Two permanent branches exist at all times:

```
main                    ← stable releases only; tagged on squash-merge from phase branch
phase/v0.2.0-pN         ← active integration branch; all session work lands here
  └── patch/<bl-id>     ← one per backlog item (e.g. patch/bl-046); deleted on merge
  └── feat/<slug>       ← ad-hoc feature work (e.g. feat/gemini-cli-adapter); deleted on merge
```

- `main` never receives direct commits — only squash-merges from a completed phase branch.
- One phase branch is active at a time. When a phase closes: merge → `main`, tag, delete
  the phase branch, open `phase/v0.2.0-p(N+1)`.
- Feature/patch branches are opened on scope approval and deleted within the same session
  or the next. They must never outlive a phase.

#### Worktree Default: Zero

The scope gate (`.azoth/scope-gate.json`), run-ledger write claim
(`.azoth/run-ledger.local.yaml`), and deploy hook mirror enforcement share the repo root.
Running two worktrees simultaneously will produce claim conflicts and stale-mirror false
positives.

| Scenario | Policy |
|----------|--------|
| Normal BL work | Single checkout; switch branches with `git checkout` |
| Parallel exploration | `git stash` + branch switch — no worktree |
| Genuinely parallel builds | Worktree allowed; register a separate run-ledger write claim per worktree path; close before `/session-closeout` |

Worktrees are tracked in `.claude/worktrees/`; the `/worktree-sync` skill handles
checkpointing. If a worktree is open at closeout, `worktree-sync` must be invoked first.

#### Merge Hygiene

- Merge feature/patch branches into the phase branch with `--no-ff` (preserves history).
- Run `python3 scripts/azoth-deploy.py` before committing after any merge — the pre-commit
  hook enforces parity, but running it manually avoids the abort-fix-recommit cycle.
- After every merge run `git branch --merged <phase-branch>` and delete anything listed
  except `main` and the phase branch.

#### State File Conflict Resolution Order

State files (`.azoth/`, `azoth.yaml`, `.claude/settings.json`) always conflict on parallel
branches. Canonical resolution:

1. **Version numbers** — keep the higher value (destination branch wins).
2. **Backlog / decisions state** — keep HEAD (destination branch is authoritative).
3. **`episodes.jsonl`** — append-merge all new episodes from both sides, sorted by ID.
4. **`bootloader-state.md`** — keep HEAD; add a merge note capturing session context from
   the incoming branch if relevant.

### Implementation

- `CLAUDE.md` §Git Conventions (Branch Model, Worktree Policy, Merge Hygiene) — the
  machine-readable source agents read at session start.
- `.claude/worktrees/` registry + `/worktree-sync` skill — worktree lifecycle tracking.
- `scripts/run_ledger.py claim / release-claim` — write claim enforcement for parallel
  worktrees (BL-011 compliant).

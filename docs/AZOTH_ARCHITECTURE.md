# AZOTH Architecture Plan v0.1.0

> Finalized: 2026-04-03 | Session: SupplyGrowth Architect Session
> Status: APPROVED — ready for Phase 1 implementation

---

## 1. Problem Statement

Extract proven governance patterns, bootloader philosophy, and self-improvement
loops from a production agentic framework into a standalone, portable,
"drop-and-start" personal toolkit that:

- Works natively with Claude Code (primary) and is compatible with OpenCode + GitHub Copilot
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
   - File changes: max N files per turn without human approval
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

```
Goal → Architect decides agent needed → Agent Crafter designs agent
→ Evaluator scores → Prompt Engineer refines → Agent Crafter updates
→ Human approves → Agent becomes permanent

Meta-level: Agent Crafter improves itself (with human approval)
Entropy guard prevents unbounded self-modification
```

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

12 built-in slash commands ship with every Azoth installation:

| Command | Category | Purpose |
|---------|----------|---------|
| `/bootstrap` | Lifecycle | Day 0 guided kernel creation |
| `/session-closeout` | Lifecycle | Unified eval + close + sync |
| `/remember` | Lifecycle | Capture cross-session learning |
| `/auto` | Pipeline | Auto-compose and execute pipeline (default) |
| `/deliver` | Pipeline | Lean pipeline (pre-approved work) |
| `/deliver-full` | Pipeline | Full pipeline with governance gates |
| `/plan` | Pipeline | Structured planning without execution |
| `/eval` | Quality | Governance quality gate |
| `/test` | Quality | Unit test generation |
| `/promote` | Governance | Review promotion candidates |
| `/sync` | Infrastructure | Pattern extraction from source framework |
| `/worktree-sync` | Infrastructure | Git checkpoint and sync |

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

Default behavior when user doesn't specify a pipeline. The Architect classifies the
goal and composes a pipeline from presets.

```yaml
auto_pipeline:
  trigger: Any goal without explicit pipeline selection

  classification:
    scope: kernel | skills | agents | pipelines | docs | mixed
    risk: governance-change | breaking-change | additive | cosmetic
    complexity: simple | medium | complex
    knowledge: known-pattern | needs-research | novel

  composition_rules:
    - if risk == governance-change: ALWAYS full pipeline
    - if scope == kernel: ALWAYS full pipeline
    - if complexity == simple AND risk == cosmetic:
        pipeline: [planner, builder, architect-review]
    - if complexity == simple AND risk == additive:
        pipeline: [planner, test-builder, builder, architect-review]
    - if knowledge == needs-research:
        inject: research-phase into architect stage
    - if scope == docs:
        pipeline: [architect, builder, architect-review]
    - default: full pipeline

  declaration:
    format: visual-ui
    shows: [goal, classification, composed-stages, rationale]
    gate: human-approve  # Human can override composition
```

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
| `auto` | *Composed dynamically via D23* | **Default — always** |

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
    ├── GitHub Copilot ── reads CLAUDE.md + .github/ adapter files
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
  ├─ OpenCode detected?    → .opencode/ (agents/, commands/, opencode.json)
  ├─ Copilot detected?     → .github/ (agents/, prompts/, copilot-instructions.md)
  └─ Cursor (always in dev-sync) → .cursor/rules/*.mdc (from kernel/templates/platform-adapters/cursor/)
```

### Compatibility Matrix

| Component | Claude Code | OpenCode | Copilot | Cursor |
|-----------|-------------|----------|---------|--------|
| CLAUDE.md | ✅ Primary | ✅ Native | ✅ Reads | ✅ via toggle |
| AGENTS.md | ✅ Native | ✅ Native | ✅ Native | ✅ Native |
| Skills (SKILL.md) | ✅ .claude/skills/ | ✅ .opencode/skills/{name}/ | ✅ .github/skills/ | ✅ .claude + repo (toggle) |
| Agents | .claude/agents/ | .opencode/agents/ | .github/agents/ | .claude/agents/ (toggle) |
| Commands | .claude/commands/ | .opencode/commands/ | .github/prompts/ | .claude/commands/ (toggle) |
| `.cursor/rules/*.mdc` | — | — | — | ✅ from `azoth-deploy --platforms cursor` |
| Config | .claude/settings.json | opencode.json | VS Code settings | Cursor Settings + toggle |
| Hooks | ✅ Full hook system | ✅ Plugin system | ⚠️ Limited | ❌ (use `.mdc` parity rules) |
| MCP | .mcp.json | opencode.json `mcp` key | VS Code MCP | VS Code MCP |

### Cursor IDE (Claude) and Claude Code parity

Cursor can consume the **same** Azoth sources as Claude Code when **Settings → Rules → “Include third-party plugin skills and configs”** is enabled: `CLAUDE.md`, `.claude/commands/`, repo-level `agents/` and `skills/` (paths as laid out in this scaffold; consumer installs may mirror via `azoth-deploy`).

**Seamless parity** means: same slash-command semantics, same skills, same trust and pipeline **logic**. **Runtime parity** differs in one important way:

| Mechanism | Claude Code | Cursor (Claude) |
|-----------|-------------|-----------------|
| `CLAUDE.md` + commands + agents + skills | Loaded via product integration | Loaded via toggle above |
| **PreToolUse hooks** (`.claude/settings.json`) | Executed on every tool call | **Not executed** — Cursor does not run Claude Code’s hook binary |
| Scope / pipeline gate enforcement | **Mechanical** (deny Write/Edit) | **Behavioral** — enforced by always-applied **`.cursor/rules/*.mdc`** instructing the model to read `.azoth/scope-gate.json` and `.azoth/pipeline-gate.json` and refuse writes when invalid |
| **Subagent isolation (D21)** | `Agent(subagent_type=...)` | **`Task`** with matching `subagent_type` (Azoth archetypes) — orchestrator stays in main chat; **must not** inline all pipeline stages when `Task` is available (see `claude-code-parity.mdc`) |

**PreToolUse hook commands** in `.claude/settings.json` should use **paths relative to the repository root** (for example `python3 .claude/hooks/edit_pretooluse_orchestrator.py`) so clones and CI do not embed machine-specific absolute paths. Claude Code runs hooks with the **project workspace as the current working directory**. If a hook fails to resolve, use an absolute path only for local debugging.

**Entropy (Write/Edit, P5-002):** `kernel/TRUST_CONTRACT.md` §1 states per-*turn* limits for agents. The **PreToolUse** entropy hook runs **once per tool call**, not per LLM turn. In this toolkit, **cumulative entropy_delta** and file/line caps are **session-scoped**, keyed to `scope-gate.json` `session_id`, and reset when the scope card changes—mechanical alignment with an approved scope, not a literal per-tool-call interpretation of the §1 table alone.

**Alignment summary (Write/Edit, P5-003):** `kernel/TRUST_CONTRACT.md` §2 defines the human-facing Alignment Summary. For **machine-comparable** handoffs, pipeline stages emit typed YAML per **BL-012** (`pipelines/stage-summary.schema.yaml`). The **PreToolUse orchestrator** (`.claude/hooks/edit_pretooluse_orchestrator.py`) runs **after** the scope gate and **before** entropy: for **Write** and **Edit** targeting `.azoth/handoffs/**/*.yaml|yml`, it validates **one YAML document** per call using shared structural checks (`.claude/hooks/stage_summary_validate.py`). Invalid **handoff content** → deny with `[alignment-summary]`; **malformed JSON on stdin** remains fail-open (same rationale as scope/entropy hooks). **Edit** resolves `old_string`/`new_string` to candidate text (single match), then applies the same validation as **Write**.

**Malformed stdin (fail-open):** If the hook process receives **invalid JSON** on stdin (PreToolUse payload), the scope and orchestrator hooks **allow** the tool call—same posture as `scope-gate.py` and `pip-install-guard.py`. Rationale: without a parseable payload there is no reliable `tool_name` / `tool_input` to enforce; denying would block **all** Write/Edit on environmental or platform glitches. For the strictest threat model (deny when stdin is corrupt), that would require a separate product or hook contract change—not Azoth-only policy.

**Architectural rule:** Treat Cursor as **source-compatible, hook-soft**. The **kernel/templates/platform-adapters/cursor/** templates (`azoth-memory.mdc`, `claude-code-parity.mdc`) are the **minimum viable guardrails** so sessions honor scope gates, pipeline gates, `/next`, delivery pipelines, and **Task-based** subagent routing **without** relying on hooks. Duplicated policy in M2 patterns + rules is intentional (mechanical enforcement in Claude Code, instruction enforcement in Cursor). **`scripts/azoth-deploy.py --platforms cursor`** copies `*.mdc.template` → `.cursor/rules/*.mdc` so consumer workspaces stay coupled to kernel templates.

**When to use which IDE:** Cursor is appropriate for exploration, edits, and multi-stage delivery **when** the agent uses **`Task`** per `subagent-router` (same isolation contract as Claude Code). Prefer **Claude Code** when you need **binary** PreToolUse enforcement, not for subagent isolation alone. See `kernel/templates/platform-adapters/cursor/README.md`.

#### Cross-IDE session memory parity (`/session-closeout` W1–W4)

Azoth treats **repo-local state** as the **authoritative** narrative every platform must converge on. **Claude Code project memory** (`~/.claude/projects/<project-key>/memory/`) is a **supplemental mirror**, not a second source of truth.

Canonical checkpoint text lives in **`.claude/commands/session-closeout.md`** (D46 copies to **`.github/prompts/session-closeout.prompt.md`** and **`.opencode/commands/session-closeout.md`**).

| Checkpoint | What it writes | Claude Code | Cursor | OpenCode | GitHub Copilot |
|------------|----------------|-------------|--------|----------|----------------|
| **W1** | `.azoth/memory/episodes.jsonl` | ✅ | ✅ | ✅ | ✅ (same repo path) |
| **W2** | `.azoth/bootloader-state.md`, `.azoth/scope-gate.json` | ✅ | ✅ | ✅ | ✅ (same repo paths) |
| **W3** | `~/.claude/projects/<project-key>/memory/` (`project_status.md`, `MEMORY.md` index, optional `feedback_*.md`) | ✅ native | ⚠️ **attempt** with host FS access; else log `W3 deferred` | N/A | N/A |
| **W4** | `python scripts/version-bump.py --patch` | ✅ | ✅ | ✅ | ✅ |

**Session start (all IDEs):** **`azoth-memory.mdc`** (Cursor) / same paths in Claude Code — read **`.azoth/memory/patterns.yaml`**, **`.azoth/bootloader-state.md`**, **`.azoth/session-state.md`** when present. Handoff **`session-state.md`** is separate from the W2 bullets in `/session-closeout` (update it when you intentionally leave a cross-IDE capsule).

**Parity rule:** **W1 + W2 + W4** are the **shared contract** — every tool edits or commits the **same files in the repo**. **W3** exists only so Claude Code’s native project-memory layer stays aligned; **Cursor** must mirror that intent (attempt W3 or log deferral per **`kernel/templates/platform-adapters/cursor/claude-code-parity.mdc.template`**). **OpenCode** and **GitHub Copilot** do not consume `~/.claude/projects/.../memory/`; their parity is **committed W1/W2** (plus `azoth.yaml`). If W2 and W3 diverge, **W2 wins**; refresh W3 on the next closeout run from Claude Code or a Cursor session with access.

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
agents/**/*.agent.md  ─┬→ .claude/agents/<name>.md         (strip Azoth-specific fields)
                       ├→ .github/agents/<name>.agent.md   (remap tools, drop tier/skills)
                       └→ .opencode/agents/<name>.md       (posture→permission, infer mode)

.claude/commands/*.md ─┬→ .github/prompts/<name>.prompt.md (add agent binding)
                       └→ .opencode/commands/<name>.md     (add $ARGUMENTS support)

skills/**/ ────────────→ .opencode/skills/<name>/SKILL.md  (per-skill subdirectory)
kernel/templates/platform-adapters/cursor/*.mdc.template
                       → .cursor/rules/<name>.mdc           (Cursor always-on rules)
                         AGENTS.md                          (generated broadcast layer)
```

Prior art: Caliber (`caliber-ai-org/ai-setup`) uses a similar canonical→many approach
with a git pre-commit hook triggering regeneration.

---

## 9. Observability & Trust Enforcement

### Session Telemetry

```jsonl
{"session_id":"uuid","turn":3,"agent":"builder","tool":"edit","target":"src/main.py","outcome":"success","files_changed":1,"entropy_delta":0.1,"timestamp":"2026-04-03T19:00:00Z"}
```

Stored in `.azoth/telemetry/session-log.jsonl` (gitignored).

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
├── LICENSE                       # MIT
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
├── commands/                     # Dual-write command templates
│   ├── claude/
│   └── copilot/
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
| D23 | Auto-pipeline: LLM-as-router composition | Default behavior, 8 presets |
| D24 | Gate typing: human vs agent | Kernel/governance gates must be human |
| D25 | 12 seed slash commands | Essential lifecycle + pipeline + quality |
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
| D46 | Dev-sync script: workspace self-installation to platform directories | `scripts/azoth-deploy.py` translates canonical agents/skills/commands into Claude Code, Copilot, OpenCode platform-specific files + AGENTS.md broadcast layer |
| D47 | Persistent backlog system: `.azoth/backlog.yaml` | Operational work queue; items carry `target_layer` (M1/M2/M3/infrastructure) and `delivery_pipeline` (governed/standard); active items cannot be silently dropped — deferral requires `target_version` |
| D48 | Versioned roadmap: `.azoth/ROADMAP.yaml` | Supersedes D39; multi-version structure (active/planned/backlog/complete); tasks reference backlog items; CLAUDE.md becomes rendered summary; explicit deferral with reason |
| D49 | Intake 3-axis triage | Extends D33 step 3: for each integrated insight, human simultaneously decides (1) M3 action, (2) M2 candidate flag, (3) backlog item needed — three independent axes, any combination valid |
| D50 | Session scope card | `/next` outputs a scope card (1 primary + max 2 secondary goals); human approves → writes `.azoth/scope-gate.json`; validator rejects mixed M1+runtime sessions |
| D51 | Formalized M2→M1 promotion path | M1 changes are a governed event: `target_layer: M1` backlog item + `/deliver-full` pipeline; M1 changes happen between sessions only; scope card validator enforces isolation |
| D52 | Session Welcome UX: `/start` + `scripts/welcome.py` | Rich-rendered terminal dashboard at session open; `scripts/welcome.py` reads `azoth.yaml`, `backlog.yaml`, `scope-gate.json`, recent episodes and renders via Python `rich` library — `box.HEAVY` identity header, `box.MINIMAL` phase progress strip, `Columns([health, backlog])` 2-column body with `box.ROUNDED` panels, last-session strip, START options panel; Rich handles all Unicode/emoji width via wcwidth internally — zero manual padding; context-sensitive option menu (resume if gate active, else /next); `.claude/commands/start.md` runs the script via Bash then routes user option; UX entry point for D41 bootstrap loop; Phase 4 deliverable; Phase 5 adds hook-based auto-trigger |

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
| **5** | Trust Layer | Hooks, telemetry, checkpoints, phone-friendly output |
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

### 3-Tier Model

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

### D51: Formalized M2→M1 Promotion Path

D11 noted "M2→M1 pending" as a partial status. D51 formalizes it.

**Trigger:** A backlog item with `target_layer: M1` + `/deliver-full` pipeline.

**Rules:**
- M1 changes happen *between* sessions, never during an active session
- The scope card validator (D50) enforces this: M1 items cannot be mixed with runtime tasks
- `/deliver-full` is the required pipeline for all M1-targeted backlog items
- This applies to kernel/, skills/ (.claude/commands/), and agents/ equally

**Promotion chain:**

```
Observation (M3) --/promote--> Pattern (M2) --BL item + /deliver-full--> Procedure (M1)
    ^                              ^                                           ^
any insight                 reinforced >=2x                         governance-gated
m2_candidate=true flag      set at intake                           target_layer: M1
```

### Architecture Decisions (D47–D53)

| # | Decision | Rationale |
|---|----------|-----------|
| D47 | Persistent backlog: `.azoth/backlog.yaml` | Enforced operational queue — active items cannot be silently dropped |
| D48 | Versioned roadmap: `.azoth/ROADMAP.yaml` | Explicit deferral across versions eliminates squeeze-in scope creep |
| D49 | Intake 3-axis triage | M3/M2/backlog routing is simultaneous and independent, not sequential |
| D50 | Session scope card | Mechanical scope limiter — approved goals write scope-gate.json before session |
| D51 | Formalized M2→M1 promotion path | M1 changes are governed events between sessions; target_layer field routes delivery |
| D52 | Session Welcome UX: `/start` + `scripts/welcome.py` | Single entry point for session orientation — routes to /next, /intake, /promote, or custom goal |
| D53 | Auto-versioning policy | Version increments are delivery-triggered — 0.0.PHASE.PATCH scheme; PATCH per delivery, PHASE per phase completion |

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

### Version Format: `0.0.PHASE.PATCH`

```
0.0.PHASE.PATCH
│ │  │      └── delivery counter — increments every session, resets to 1 on phase bump
│ │  └───────── phase number — equals the current development phase (1–6)
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
| **v0.1.0** | **Public azoth release — full roadmap complete** | — |

### Bump Rules

- **PATCH** (`0.0.N.XX+1`): every delivery session — /deliver-full, /deliver, or any
  session that produces artifacts. Counter resets to `.1` on each phase bump.
- **PHASE** (`0.0.N+1`): phase completion; PHASE number equals the current phase (3→4→5→6).
  PATCH counter resets to `.1`.
- **Release** (`0.1.0`): full roadmap complete (Phase 6 done). Only non-sequential jump.
  Git tag proposed — user-confirmed, never auto-pushed.

The PATCH counter provides agents with a reliable time-series signal: higher PATCH = later
in the phase. PHASE provides coarser orientation. Together they encode "where in development
are we" without requiring agents to read git history.

### Implementation (BL-009)

- `scripts/version-bump.py` — reads `azoth.yaml`, applies `--patch` or `--phase` bump,
  writes `azoth.yaml` and updates `roadmap.yaml` `active_version` + `current_patch` fields.
  `--release` flag triggers the `0.1.0` jump and proposes a git tag.
- `/session-closeout` integration — final step calls `version-bump.py --patch` after
  confirming at least one artifact was written this session.
- `/deliver-full` integration — calls `version-bump.py --patch` after builder stage
  completes successfully.

### Rules

- Version bumps are never silent — `version-bump.py` prints the old → new transition
- Git tags are proposed at `--release` only; patch/phase bumps update files only
- `azoth.yaml` `version` is the authoritative time-series field for agents
- `roadmap.yaml` `active_version` + `current_patch` mirror it for roadmap context
- On `--phase` bump: `version-bump.py` writes `final_patch: N` to the completing version
  entry in `roadmap.yaml` before advancing `active_version` — preserves the full time-series
  history for completed phases
- `target_version` in `backlog.yaml` uses the delivery-phase version (e.g. `v0.0.3`),
  not a future release target — completed items record where they actually landed

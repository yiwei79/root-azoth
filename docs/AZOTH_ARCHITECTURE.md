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
    └── GitHub Copilot ── reads CLAUDE.md + .github/ adapter files
```

### Platform Adapter Pattern

The installer generates platform-specific files at init time.
Azoth's kernel stays platform-agnostic.

```
azoth init
  ├─ ALWAYS: CLAUDE.md, kernel/, skills/, .azoth/
  ├─ Claude Code detected? → .claude/ (commands, agents, settings)
  ├─ OpenCode detected?    → .opencode/ (agent, command, config)
  └─ Copilot detected?     → .github/ (agents, prompts, instructions)
```

### Compatibility Matrix

| Component | Claude Code | OpenCode | Copilot |
|-----------|-------------|----------|---------|
| CLAUDE.md | ✅ Primary | ✅ Native | ✅ Reads |
| Skills (SKILL.md) | ✅ .claude/skills/ | ✅ .claude/skills/ | ✅ .github/skills/ |
| Agents | .claude/agents/ | .opencode/agent/ | .github/agents/ |
| Commands | .claude/commands/ | .opencode/command/ | .github/prompts/ |
| Config | .claude/settings.json | opencode.jsonc | VS Code settings |
| Hooks | ✅ Full hook system | ✅ Plugin system | ⚠️ Limited |
| MCP | .mcp.json | opencode.jsonc mcp key | VS Code MCP |

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
| D42 | Path duality convention: kernel/ vs .azoth/kernel/ | Dual-path awareness for scaffold vs consumer context |
| D43 | Commit-time governance enforcement hooks | Pre-commit hooks that mechanically enforce CLAUDE.md git rules (no Co-Authored-By, format validation) — moves governance from agent memory (driftable) to tool execution (deterministic) |
| D44 | Pipeline Stage 6 quality rubric for structured content | Stage 6 (Architect Review) must score generated structured content against minimum depth thresholds before passing the delivery gate — prevents shallow first-pass output |

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
| **4** | Distribution | README, `azoth init` onboarding, CI, publish |
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

### Architecture Decisions (D29–D38)

| # | Decision | Rationale |
|---|----------|-----------|
| D29 | Inbox format: `.azoth/inbox/*.jsonl` | Append-only, machine-parseable, git-friendly |
| D30 | Trusted source registry | Governance boundary for external data |
| D31 | SURVEY auto-detect + `/intake` | Passive awareness + explicit processing |
| D32 | 12-field insight schema | Structured enough to triage, flexible enough to extend |
| D33 | 4-step intake protocol | Validate → Classify → Human Triage → Integrate/Archive |
| D34 | root-azoth = personal root scaffold | Private workshop, not consumer product |
| D35 | azoth = public deployable product | Extracted via sync, consumer-ready |
| D36 | `--scaffold` vs `--project` modes | Phase 4 product differentiation |
| D37 | root-azoth (private) / azoth (public) | Naming convention for clarity |
| D38 | Scaffold infra now, extraction later | Build the workshop, extract the product when ready |
| D39 | Roadmap tracking: `.azoth/roadmap.yaml` | Machine-readable task backlog for agent self-direction |
| D40 | Repo rename: root-azoth (private) | Clear distinction from azoth (public product) |
| D41 | Bootstrap loop: 4 artifacts | Roadmap + /next + preflight gate + decisions index |

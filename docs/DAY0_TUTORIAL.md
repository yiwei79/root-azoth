# 🧪 AZOTH — Day 0 Tutorial & Development Guide

> **For the human alchemist.** This file is documentation — agents don't read it
> unless instructed. It won't affect development sessions.

---

## Table of Contents

- [Pre-Flight](#pre-flight)
- [Step 1: Environment Setup](#step-1-environment-setup-macos)
- [Step 2: Launch Day 0 Bootstrap](#step-2-launch-day-0-bootstrap)
- [Step 3: Phase 1 — Kernel Extraction](#step-3-phase-1--what-gets-built)
- [Step 4: Phase 1.5 — Sync Infrastructure](#step-4-phase-15--sync-infrastructure)
- [Phase 2–6 Development Guide](#phase-26-development-guide)
- [Tips for Ongoing Development](#tips-for-ongoing-development)
- [Day 0 Checklist](#day-0-checklist)

---

## Pre-Flight

**Your repo is ready.** 4 commits on `main`, pushed to GitHub.
Everything needed for Day 0 is already in place.

```
AZOTH repo state:
├── CLAUDE.md                      ← Agent reads this first (auto)
├── docs/AZOTH_ARCHITECTURE.md     ← 28 decisions, full blueprint
├── .claude/commands/bootstrap.md  ← The Day 0 command
├── .claude/settings.json          ← Kernel write-protection active
├── .github/AGENTIC_BOOTLOADER.md  ← Tracks artifact progress
├── azoth.yaml                     ← Manifest with pipeline presets
├── tests/                         ← 71 tests already passing
└── .gitignore                     ← Runtime state excluded
```

### What You Already Have

| Artifact | Status | Purpose |
|----------|--------|---------|
| Architecture plan (28 decisions) | ✅ Complete | Blueprint for all 6 phases |
| 7-stage pipeline design | ✅ Designed | Full / lean / auto composition |
| Auto-pipeline with 8 presets | ✅ Designed | Dynamic pipeline selection |
| Proactive Agent Posture (3 tiers) | ✅ Designed | always-do / ask-first / never-auto |
| 12 seed slash commands | ✅ Designed | Lifecycle + pipeline + quality |
| Kernel write protection | ✅ Active | `settings.json` denies `Edit(kernel/**)` |
| 71 validation tests | ✅ Passing | Architecture + governance + consistency |
| Governance review findings | ✅ Documented | B1 fixed, B2-B3 tracked |

---

## Step 1: Environment Setup (macOS)

```bash
# ── Clone ──────────────────────────────────────────────
git clone https://github.com/yiwei79/AZOTH.git
cd AZOTH

# ── Python environment ─────────────────────────────────
python3 -m venv .venv
source .venv/bin/activate
pip install pytest pyyaml ruff

# ── Verify everything works ────────────────────────────
python -m pytest tests/ -v
# Expected: 71 passed, 1 xfail ✅

# ── Install Claude Code (if not already) ───────────────
npm install -g @anthropic-ai/claude-code
```

### 💡 Tips

- **Kernel protection timing**: `.claude/settings.json` denies `Edit(kernel/**)`.
  During Day 0 bootstrap, this won't block creation since `kernel/` doesn't exist
  yet. After bootstrap completes, the directory becomes protected automatically.

- **Python version**: 3.11+ required. Verify with `python3 --version`.

- **Windows validation** (later): The `install.ps1` script should be tested on
  Windows after macOS is confirmed working. Cross-platform is a Phase 1 goal.

---

## Step 2: Launch Day 0 Bootstrap

```bash
# Start Claude Code in the AZOTH directory
claude

# Claude Code reads CLAUDE.md automatically
# It sees Phase 1 🎯 CURRENT
# Now invoke the bootstrap command:
/bootstrap
```

### What Happens

Claude Code reads `.claude/commands/bootstrap.md` — a guided 8-step Phase 1
plus 3-step Phase 1.5 workflow. It presents a welcome banner and waits for `go`.

```
╔══════════════════════════════════════════════════╗
║           🧪 AZOTH — Day 0 Bootstrap            ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  Welcome. This is the first bootstrap of Azoth.  ║
║  I'll guide you through creating the kernel.     ║
║                                                  ║
║  Ready? Type 'go' or ask questions first.        ║
╚══════════════════════════════════════════════════╝
```

### Your Role During Bootstrap

| You Say | What Happens |
|---------|-------------|
| `go` / `continue` / `looks good` | Advances to next step |
| `adjust: [feedback]` | Modifies current step before proceeding |
| `show me` / `explain` | Agent explains its plan before executing |
| `wait` / `hold` | Pauses pipeline, agent presents alignment summary |
| `skip` | Skips optional step (use sparingly) |

The bootstrap **stops after EACH step** for your signal.
This is the Trust Contract in action — PULL-based alignment.

---

## Step 3: Phase 1 — What Gets Built

### Kernel Extraction (8 Steps)

| Step | Creates | What It Does | ⚠️ Review Focus |
|------|---------|-------------|-----------------|
| **1.1** | `kernel/BOOTLOADER.md` | 4-phase boot sequence template (Activate → Survey → Operate → Harden) | Extracted pattern — should feel familiar |
| **1.2** | `kernel/TRUST_CONTRACT.md` | Entropy ceiling, alignment protocol, drift detection, recovery | **NEW design — read carefully** |
| **1.3** | `kernel/GOVERNANCE.md` | HITL gates, promotion flow, append-only rules, gate typing | Distilled from D24, D26 |
| **1.4** | `kernel/PROMOTION_RUBRIC.md` | 4-question decision tree for pattern routing | Direct extraction from SupplyGrowth |
| **1.5** | `kernel/templates/` | CLAUDE.md.template, settings.json.template, etc. | What consumer projects receive |
| **1.6** | `kernel/templates/platform-adapters/` | claude/, opencode/, copilot/ configs | Per-platform file generation |
| **1.7** | `install.sh` + `install.ps1` | Cross-platform installer with interactive options | **Test on macOS immediately** |
| **1.8** | *Validation* | Structural tests, architecture drift check | All tests must pass before moving on |

### 💡 Phase 1 Tips

> **Step 1.2 is the most important.** The Trust Contract is a new design, not an
> extraction. Read it like a contract you're signing with your future agent swarms.
> It defines what they CAN'T do without you.

> **Test the installer immediately** (Step 1.7):
> ```bash
> mkdir /tmp/test-azoth && cd /tmp/test-azoth
> bash ~/AZOTH/install.sh
> # Verify: CLAUDE.md created, kernel/ copied, memory dir initialized
> rm -rf /tmp/test-azoth  # cleanup
> ```

> **After Step 1.8 completes, kernel is LOCKED.** The `settings.json` deny rules
> activate because `kernel/` now exists. Future kernel changes require:
> 1. Human proposes change
> 2. Governance review
> 3. Human approves
> 4. Promotion via rubric

---

## Step 4: Phase 1.5 — Sync Infrastructure

| Step | Creates | What It Does |
|------|---------|-------------|
| **1.5.1** | `scripts/azoth-sync.py` | 5-phase extraction: SCAN → DIFF → PROPOSE → ALIGN → SANITIZE |
| **1.5.2** | `sync-config.yaml` | Sanitization rules — org patterns to strip |
| **1.5.3** | `.claude/commands/sync.md` | `/sync` command for agent-driven extraction |

### 💡 Phase 1.5 Tips

> **Configure sanitization BEFORE first sync:**
> ```yaml
> # sync-config.yaml — replace these with YOUR org patterns
> sanitize:
>   strip_patterns: ["YourOrg", "InternalProject", "internal-url.com"]
>   strip_paths: ["Projects/", "workspace/SESSION_MEMORY.md"]
> ```

> **Test with dry-run first:**
> ```bash
> python scripts/azoth-sync.py \
>   --source ~/path/to/SupplyGrowth/Agentic\ Framework \
>   --dry-run
> # Shows what WOULD be extracted — no files touched
> ```

> **Sync is bidirectional awareness, one-directional flow:**
> Patterns flow FROM SupplyGrowth → INTO Azoth. Never the reverse.
> The sanitization step ensures no org content leaks.

---

## Phase 2–6 Development Guide

After Day 0, sessions follow a natural rhythm:

```
┌──────────────────────────────────────────┐
│  Session Lifecycle                       │
│                                          │
│  1. Open Claude Code in AZOTH/           │
│  2. Claude reads CLAUDE.md → sees phase  │
│  3. State your goal                      │
│  4. Auto-pipeline composes stages        │
│  5. Review pipeline → approve            │
│  6. Work through stages                  │
│  7. /session-closeout at end             │
└──────────────────────────────────────────┘
```

### Phase 2: Core Skills *(1-2 sessions)*

| Task | Pipeline | Notes |
|------|----------|-------|
| Extract 5 skills via `/sync` | `/deliver` | Pre-approved via sync |
| Design 3 new skills | `/deliver-full` | Governance review needed |
| Skill drift tests | Included in `/deliver` | Each skill gets structural tests |

**Skills to extract:** context-map, structured-autonomy-plan, agentic-eval, remember, prompt-engineer

**Skills to create:** entropy-guard, alignment-sync, self-improve

**Done when:** Each skill has `SKILL.md` with valid frontmatter + at least 1 reference/script

---

### Phase 3: Agent Archetypes *(2-3 sessions)*

> **Recommended split:**
> - **3a**: T1 core agents (architect, planner, builder, reviewer) + pipeline YAML schema
> - **3b**: T2-T4 agents (6 remaining) + dual-format templates

| Task | Pipeline | Notes |
|------|----------|-------|
| T1 core agents (4) | `/deliver-full` | Agents ARE the governance surface |
| Pipeline YAML schema | `/deliver-full` | Implements D21-D28 design |
| T2-T4 agents (6) | `/deliver` | Lower risk, follow T1 pattern |
| Dual-format templates | `/deliver` | `.agent.md` + `.prompt.md` |

**Done when:** Each agent has `.agent.md` with posture tier assignment (D26)

---

### Phase 4: Distribution & Polish *(1 session)*

| Task | Pipeline | Notes |
|------|----------|-------|
| README (philosophy + quickstart) | `/docs` | Documentation only |
| `azoth init` onboarding | `/deliver-full` | User-facing, needs review |
| CI for drift detection | `/deliver` | GitHub Actions workflow |
| Publish to GitHub | Manual | Push + create release |

**Validation:** Fresh clone → `install.sh` → run tests → all pass

---

### Phase 5: Trust Layer *(1-2 sessions)*

| Task | Pipeline | Notes |
|------|----------|-------|
| entropy-check hook | `/deliver-full` | Core governance |
| alignment-summary hook | `/deliver-full` | Core governance |
| Session telemetry | `/deliver` | `.azoth/telemetry/session-log.jsonl` |
| Git-based checkpoints | `/deliver` | Auto-snapshot before risky ops |
| Phone-friendly output | `/deliver` | <500 word summaries |

**Validation:** Trigger entropy ceiling → verify agent stops and requests alignment

---

### Phase 6: Meta-Recursive *(2+ sessions)*

| Task | Pipeline | Notes |
|------|----------|-------|
| Agent Crafter | `/deliver-full` | **Always** full — meta-recursive is governance |
| L2 prompt optimization | `/deliver-full` | Auto-refine from evidence |
| L3 architecture proposals | `/deliver-full` | Human-gated by design |

**Validation:** Agent Crafter creates a simple agent → Evaluator scores → human approves

---

## Tips for Ongoing Development

### 🎯 Session Rhythm

```
Start:  Claude reads CLAUDE.md + bootloader state
Work:   Goal → auto-pipeline → execute stages
Close:  /session-closeout (captures episodes + syncs)
```

### 📱 Phone-Friendly Workflow

After starting a pipeline, you can walk away. Come back, read the alignment
summary (<500 words), then:

| Signal | Meaning |
|--------|---------|
| `✅` or `approve` | Continue to next stage |
| `🔄 [feedback]` | Adjust and retry current stage |
| `⛔` | Stop pipeline, preserve state |

The proactive posture (D26) means agents checkpoint before risky actions
and surface decisions to you — you don't have to watch constantly.

### 🔄 Sync Regularly

After significant improvements in your source framework:

```bash
# Agent-driven (recommended):
/sync

# Or manual:
python scripts/azoth-sync.py --source ~/path/to/framework
```

This is how Azoth stays alive and evolving. Patterns flow in, get sanitized,
and enrich the toolkit over time.

### 🧠 Memory Builds Over Time

```
Session 1-2:   M3 episodes accumulate (what worked, what didn't)
Session 3-5:   Patterns emerge → propose M2 promotion (human approves)
Session 5+:    M2 patterns prove durable → promote to M1 (skills/agents)
```

**Don't rush promotions.** Let patterns prove themselves across multiple sessions
before they become permanent. Quality > speed.

### ⚡ Pipeline Selection Shortcuts

The auto-pipeline (D23) selects based on your goal:

| You Say | Auto-Selects |
|---------|-------------|
| "fix the typo in README" | `hotfix` |
| "add context-map skill" | `deliver` |
| "redesign memory system" | `full` |
| "how does the sync work?" | `research` |
| "review the governance doc" | `review` |
| "refactor the installer" | `refactor` |

Or specify directly: `/deliver`, `/deliver-full`, etc.

### 🔧 When Things Go Wrong

| Problem | Solution |
|---------|----------|
| Tests fail | `python -m pytest tests/ -v --tb=long` |
| Kernel drift suspected | `python scripts/kernel-integrity.py` *(Phase 1)* |
| Architecture question | Read `docs/AZOTH_ARCHITECTURE.md` |
| Pipeline stuck | `/eval` to diagnose, then resume or restart |
| Agent ignoring rules | Check `.claude/settings.json` deny rules |
| Memory too noisy | Review M3 episodes, adjust auto-classify threshold |

### 📊 Version Milestones

```
v0.1.0-dev    ← You are here (architecture + handoff artifacts)
v0.1.0-alpha  ← After Phase 2 (kernel + skills working)
v0.1.0-beta   ← After Phase 4 (installable, documented)
v0.1.0        ← After Phase 5 (trust enforcement active)
v0.2.0        ← After Phase 6 (meta-recursive, self-improving)
```

---

## Day 0 Checklist

```
Pre-Flight
  □  Clone AZOTH on MacBook
  □  Set up Python venv + dependencies (pytest, pyyaml, ruff)
  □  Run existing 71 tests — verify all green

Bootstrap
  □  Launch Claude Code: claude
  □  Run /bootstrap
  □  Complete Phase 1 steps 1.1–1.7 (kernel + installer)
  □  Step 1.8: Run validation — all tests pass

Sync Setup
  □  Complete Phase 1.5 steps 1.5.1–1.5.3
  □  Configure sync-config.yaml with real sanitization patterns
  □  Test sync against source framework: --dry-run
  □  Run first real sync (if satisfied with dry-run)

Session Close
  □  /session-closeout — first episode captured in M3
  □  Push to GitHub
  □  Verify: python -m pytest tests/ → 100+ tests passing

Done
  □  🍵 Azoth is alive.
```

---

## Architecture Quick Reference

### The Water Molecule Model

```
Layer 3: CURRENT ── Orchestration (ephemeral, per-goal)
Layer 2: WAVE ───── Agents (10 archetypes, 4 tiers)
Layer 1: MINERAL ── Skills, memory, instructions (stable)
Layer 0: MOLECULE ─ Kernel (immutable without human approval)
```

### Full Pipeline (D21)

```
Stage 0: Goal Clarification  → human approves pipeline
Stage 1: Architect (+explore) → human approves design
Stage 2: Governance Review    → architect dispositions
Stage 3: Planner              → architect reviews plan
Stage 4: Test Builder         → architect reviews tests
Stage 5: SWE/Builder          → auto-test gate
Stage 6: Architect Review     → human approves delivery
```

### Proactive Posture (D26)

```
always-do:   Context map, test discovery, checkpoint suggestions
ask-first:   Scope expansion, agent routing, refactoring
never-auto:  Kernel changes, governance, dependencies, M2→M1
```

---

*This tutorial was generated during the Azoth architecture session on 2026-04-03.
For the source of truth on all design decisions, see `docs/AZOTH_ARCHITECTURE.md`.*

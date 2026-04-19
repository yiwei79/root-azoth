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

**Your repo is ready.** This is root-azoth — your private development scaffold.
Early phases through skills and infrastructure are complete. **Phase 6 (Meta-Recursive)** is **current** per `azoth.yaml` (Phase 7 = publishing / public product before v0.1.0). For sprint and roadmap detail, load **`skills/orientation/SKILL.md`** on demand.

```
root-azoth repo state:
├── CLAUDE.md                      ← Agent reads this first (auto)
├── docs/AZOTH_ARCHITECTURE.md     ← 53 decisions, full blueprint
├── docs/DECISIONS_INDEX.md        ← D1–D53 status tracking
├── commands/                      ← 15 neutral command contracts (live deploy input)
├── .claude/commands/              ← generated command mirrors for the current Azoth surface
├── .claude/settings.json          ← Kernel write-protection active
├── .azoth/roadmap.yaml            ← Phase goals + task backlog
├── .azoth/inbox/                  ← Governed insight intake channel
├── .azoth/memory/                 ← M3 episodes + M2 patterns
├── .azoth/trusted-sources.yaml    ← External source registry
├── azoth.yaml                     ← Manifest (name: root-azoth)
├── kernel/                        ← 4 governance files (immutable)
├── skills/                        ← 14 skills (see CLAUDE.md skill index)
├── tests/                         ← 865 tests collected (full suite)
└── .gitignore                     ← Runtime state excluded
```

### Scaffold vs Product (D34–D38)

> **This repo (root-azoth) is the root scaffold** — your private development workshop.
> It's where you design, build, and test the toolkit. The public product (`azoth`,
> lowercase) will be extracted from here via `sync-config.yaml` when ready.
> Think of it as: root-azoth is the lab, azoth is the medicine.
>
> See `docs/AZOTH_ARCHITECTURE.md` Section 18 for the full 3-tier model.

### What You Already Have

| Artifact | Status | Purpose |
|----------|--------|---------|
| Architecture plan (53 decisions) | ✅ Complete | Blueprint for all 6 phases |
| Kernel (4 files, immutable) | ✅ Active | BOOTLOADER, GOVERNANCE, TRUST_CONTRACT, PROMOTION_RUBRIC |
| Shared skills | ✅ Active | context-map, orientation, subagent-router, etc. (see CLAUDE.md) |
| 15 neutral command contracts | ✅ Active | `commands/<name>/command.yaml` is the live authored contract layer; `start`, `next`, `resume`, and `session-closeout` already author their bodies in `commands/`, while some other families still bridge through `legacy_claude_markdown` |
| Generated workflow entries | ✅ Active | Claude/Cursor use generated command mirrors directly; Codex uses `$azoth-start` as the calm-flow daily surface and exposes compatibility wrappers through `/skills` |
| Insight Inbox Protocol (D29-D33) | ✅ Active | Governed channel for external insights |
| Root scaffold identity (D34-D38) | ✅ Active | Private root-azoth → public azoth split |
| Bootstrap loop (D39-D41) | ✅ Active | Roadmap + /next + preflight + decisions index |
| Kernel write protection | ✅ Active | `settings.json` denies `Edit(kernel/**)` |
| 865 validation tests (collected) | ✅ CI baseline | Architecture + governance + inbox + identity — full suite expected green per CI; local runs may show skips/xpass |
| Development roadmap | ✅ Active | `.azoth/roadmap.yaml` — machine-readable task queue |

---

## Step 1: Environment Setup (macOS)

```bash
# ── Clone ──────────────────────────────────────────────
git clone https://github.com/yiwei79/root-azoth.git
cd root-azoth

# ── Python environment ─────────────────────────────────
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# ── Verify everything works ────────────────────────────
python -m pytest tests/ -q
# ~865 tests collected (pytest --collect-only); expect full suite green per CI
# (local runs may differ: e.g. skips, xpass — use -v or --tb=long to inspect)

# ── Install Claude Code (if not already) ───────────────
npm install -g @anthropic-ai/claude-code
```

### 💡 Tips

- **Kernel protection timing**: `.claude/settings.json` denies `Edit(kernel/**)`.
  During Day 0 bootstrap, this won't block creation since `kernel/` doesn't exist
  yet. After bootstrap completes, the directory becomes protected automatically.

- **Python version**: 3.9+ required. Verify with `python3 --version`.

- **Windows validation** (later): The `install.ps1` script should be tested on
  Windows after macOS is confirmed working. Cross-platform is a Phase 1 goal.

---

## Step 2: Launch Day 0 Bootstrap

```bash
# Start Claude Code in the root-azoth directory
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
> bash ~/root-azoth/install.sh
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
│  1. Open Claude Code in root-azoth/      │
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
| Stage 6 quality rubric (D44) | `/deliver-full` | Minimum depth thresholds for structured content; embedded in pipeline YAML schema |

**Done when:** Each agent has `.agent.md` with posture tier assignment (D26), and Stage 6 has a scored quality rubric that gates delivery

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
| Commit governance hooks (D43) | `/deliver-full` | `commit-msg` git hook + `scripts/git_commit_policy.py` **rejects** `Co-Authored-By:` trailers; run `python3 scripts/azoth_install_git_hooks.py` to set `core.hooksPath` — complements BL-002 (write-time) with VCS-time enforcement |
| entropy-check hook | `/deliver-full` | Core governance |
| alignment-summary hook | `/deliver-full` | Core governance |
| Session telemetry | `/deliver` | `.azoth/telemetry/session-log.jsonl` |
| Git-based checkpoints | `/deliver` | Auto-snapshot before risky ops |
| Phone-friendly output | `/deliver` | <500 word summaries |

**Validation:** Trigger entropy ceiling → verify agent stops and requests alignment; attempt a Co-Authored-By commit → verify hook blocks it

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
v0.1.0-dev    ← You are here (kernel + skills + infrastructure complete)
v0.1.0-alpha  ← After Phase 3 (agents + pipelines working)
v0.1.0-beta   ← After Phase 4 (installable, documented)
v0.1.0        ← After Phase 5 (trust enforcement active)
v0.2.0        ← After Phase 6 (meta-recursive, self-improving)
```

---

## Day 0 Checklist

```
Pre-Flight
  ☑  Clone root-azoth on MacBook
  ☑  Set up Python venv + `pip install -r requirements-dev.txt`
  ☑  Run full validation suite (`python -m pytest tests/ -q`) — ~865 tests collected; expect green per CI

Phase 1: Kernel ✅ COMPLETE
  ☑  4 kernel files created (BOOTLOADER, GOVERNANCE, TRUST_CONTRACT, PROMOTION_RUBRIC)
  ☑  Platform adapters + templates
  ☑  Installer (install.sh + install.ps1)
  ☑  Kernel write protection active

Phase 1.5: Infrastructure ✅ COMPLETE
  ☑  Sync pipeline (azoth-sync.py + sync-config.yaml)
  ☑  Insight Inbox Protocol (D29-D33)
  ☑  Root scaffold identity (D34-D38)
  ☑  Bootstrap loop: roadmap + /next + preflight + decisions index (D39-D41)

Phase 2: Skills ✅ COMPLETE
  ☑  14 skills (see `azoth.yaml` / CLAUDE.md skill index)
  ☑  Skill drift tests

Phase 3–5: Agents, distribution, trust ✅ COMPLETE (repo baseline: `agents/`, `pipelines/`, CI, hooks)

Phase 6: Meta-Recursive 🎯 CURRENT
  □  Run /next to see current priority task
  □  Phase / roadmap: `skills/orientation/SKILL.md`

Session Workflow
  □  Start: claude → agent reads CLAUDE.md → runs BOOTLOADER → loads roadmap
  □  Work: /next → goal → auto-pipeline → execute
  □  Close: /session-closeout → episode captured → push
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

*This tutorial was last updated 2026-04-08.
Phase 1, 1.5, and 2 complete; Phase 6 Meta-Recursive current per `azoth.yaml`. 53 architecture decisions (`docs/DECISIONS_INDEX.md`). 865 tests collected (`python3 -m pytest tests/ --collect-only`).
For the source of truth on all design decisions, see `docs/AZOTH_ARCHITECTURE.md`
and `docs/DECISIONS_INDEX.md`.*

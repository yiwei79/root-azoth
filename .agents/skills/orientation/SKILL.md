---
name: orientation
description: |
  Load the v0.2.0 slice roadmap, backlog alignment, per-task specs under
  `.azoth/roadmap-specs/v0.2.0/`, and expanded workflow when planning or editing
  `.azoth/roadmap.yaml` / backlog — not for routine implementation work.
---

# Orientation

## Overview

Root `CLAUDE.md` stays small: identity, routing, core rules, and pointers. This skill
holds the **historical phase roadmap** (Phases 1–7 → v0.1.0), the **active v0.2.0-p2 working slice**
(Phase 8 in `azoth.yaml`), and the **expanded development workflow** so agents load it
only when planning, roadmap edits, or phase alignment—not on every session.

## When to Use

- Before editing `.azoth/backlog.yaml` or `.azoth/roadmap.yaml` for phase alignment.
- When answering “what phase are we in?” with checklist detail beyond one line.
- When implementing or reviewing Phase 4–7 backlog items (welcome UX, trust layer, meta, publish).
- After reading root `CLAUDE.md`, when you need the same six-step workflow the scaffold
used before BL-013.

## Expanded Development Workflow

1. Read root `CLAUDE.md` (always-loaded behavior and rules).
2. Read `docs/AZOTH_ARCHITECTURE.md` for full context before structural changes.
3. Check current phase and roadmap **in this skill** (section below) and `.azoth/bootloader-state.md` if present.
4. Work within the approved scope (`.azoth/scope-gate.json` when active).
5. Validate changes against architecture decisions (D1–D53) as applicable.
6. Capture lessons in `.azoth/memory/episodes.jsonl` when the session produces durable insight.

## v0.1.0 Phase Roadmap

### Phase 1: Kernel Extraction ✅ COMPLETE

- kernel/BOOTLOADER.md
- kernel/TRUST_CONTRACT.md
- kernel/GOVERNANCE.md
- kernel/PROMOTION_RUBRIC.md
- kernel/templates/ (CLAUDE.md.template, settings.json.template, etc.)
- kernel/templates/platform-adapters/ (claude/, opencode/, copilot/)
- azoth.yaml manifest
- install.sh + install.ps1

### Phase 1.5: Sync Infrastructure ✅ COMPLETE

- scripts/azoth-sync.py
- sync-config.yaml
- .claude/commands/sync.md

### Phase 2: Core Skills ✅ COMPLETE

- 5 extracted skills (context-map, structured-autonomy-plan, agentic-eval, remember, prompt-engineer)
- 3 new skills (entropy-guard, alignment-sync, self-improve)
- Skill drift detection tests

### Phase 3: Agent Archetypes ✅ COMPLETE (v0.0.3)

- 10 agent archetypes, 8 pipeline presets, workflow loop (D47–D51), auto-router, subagent-router, stage6-rubric, context-recall, `/start` + `scripts/welcome.py` (BL-007; P5-007 SessionStart builds on this in Phase 5), token-optimization tracks (BL-011–BL-015), Cursor adapter (BL-016)

### Phase 4: Distribution & Polish ✅ COMPLETE (v0.0.4)

- D52 (Phase 4): Session Welcome — `.claude/commands/start.md` + `scripts/welcome.py` + template note (BL-007); **Phase 5** extends D52 with `hooks.SessionStart` (P5-007), see below
- P4-001: README (philosophy + quickstart) — D16 — **backlog priority 1**
- P4-002: `azoth init` interactive onboarding (`scripts/azoth_init.py`) — D5, D36 — **backlog priority 2**
- D42: Path duality convention (kernel/ vs `.azoth/kernel/`) — P4-005
- Update kernel docs for dual-path awareness — P4-006
- Add Edit(.azoth/kernel/**) to settings.json.template deny list (when that template is next revised for consumer installs)

### Phase 5: Trust Layer ✅ COMPLETE (v0.0.5)

- **P5-007 / D52 (Claude Code):** `hooks.SessionStart` in `.claude/settings.json` runs `.claude/hooks/session_start_welcome.py`, which invokes `scripts/welcome.py --plain` with repo `cwd`, mirrors stdout to `**.azoth/session-orientation.txt`** (gitignored), and injects the same text into model context. Matchers `startup|resume`; optional per-hook `timeout` (seconds). **Policy:** root `CLAUDE.md` rules 8–9 — default on injected context; `**Read`** for verbatim plain; **Bash** `welcome.py` (Rich) allowed — expand IDE output for full UI. **Cursor:** no SessionStart — **integrated terminal** `welcome.py` for full Rich UI; Bash in chat + expand; parity rules + `/start`.
- D43 / P5-001: Commit-time governance hooks (Co-Authored-By rejection, install path) — optional format rules still open in bootloader
- P5-002: entropy-check hook
- P5-003: alignment-summary hook
- P5-004: Session telemetry
- P5-005: Git-based checkpoints
- P5-006: Phone-friendly output — **deferred to v0.2.0** (post–v0.1.0), backlog `status: deferred`

### Phase 6: Meta-Recursive ✅ COMPLETE (v0.0.6)

- P6-001: Agent Crafter
- P6-002: L2 prompt optimization
- P6-003: L3 human-gated architecture proposals — **done** (`/arch-proposal`, `pipelines/architecture-proposal.schema.yaml`, `scripts/architecture_proposal_validate.py`)

### Phase 7: Publishing & public product ✅ COMPLETE (v0.0.7 → v0.1.0)

- P4-003: CI for drift detection — **shipped** (Phase 7)
- P4-004: Publish to GitHub (public azoth) — **shipped**; **D35**, **D37**; v0.1.0 release gate met

### Milestone v0.2.0 (milestone phase 2) — memory · declarative swarm depth · platform strategy 🎯 CURRENT

- **Canonical state:** `azoth.yaml` `version: 0.1.<phase>.<patch>`, `phase: 2`, `milestone: v0.2.0`, `lifecycle_phase: 8` (welcome strip); `.azoth/roadmap.yaml` `active_version: v0.2.0-p2` for the phase-2 working slice, `current_phase: 2`, `lifecycle_phase: 8`; per-task specs `.azoth/roadmap-specs/v0.2.0/<id>.yaml`; research/explore swarm aggregate **`SWARM_RESEARCH_DIGEST.yaml`** (DYNAMIC-FULL-AUTO+ planning pass).
- **Execution queue:** `.azoth/backlog.yaml` currently leaves **P1-020** (verbatim-first M3) and **P1-021** (memory operation parity) deferred in `v0.2.0-p2`, while **P1-022** and **P1-023** landed the co-primary platform blueprint, neutral command contract, and initiative execution plan for **INI-PLT-006**. **P1-024** (D46 command projection compiler refactor) is now the queued follow-on slice for a fresh scoped session under the same initiative. High-priority initiatives now include **INI-RST-001**, **INI-MEM-004**, **INI-RST-003**, and **INI-PLT-006**; **P5-006** remains **deferred** (phone-friendly / narrow terminal UX).
- **Workstreams (roadmap task ids / initiatives):**
  - **P1-020 / INI-MEM-001** — verbatim-first M3 storage strategy; keep full signal before downstream indexing or compression policy.
  - **P1-021 / INI-PLT-001** — memory operation parity across Claude Code, Cursor, and Copilot adapter paths.
  - **P1-022 / INI-PLT-006** — completed: codified Claude Code + Codex as co-primary command surfaces and made the adapter contract explicit for the rest.
  - **P1-023 / INI-PLT-006** — completed: defined the neutral canonical command contract, `commands/` source path, and initiative execution plan without refactoring D46 yet.
  - **P1-024 / INI-PLT-006** — queued next compiler slice: pilot command projection from the neutral contract while bridging legacy Claude markdown bodies.
  - **P1-015 / INI-RST-003** — true multi-writer safety remains staged behind the platform/bootstrap path.
  - **P1-002 / INI-RST-001** — declarative swarm / eval-wave specification remains the run-state depth track after ledger foundations.
  - **P1-009 / INI-PLT-002** — Cursor session-open parity remains a medium-priority adapter-hardening slice.
  - **P1-011 / INI-EFF-001** — token and inference efficiency remains available once platform/memory triage settles.
  - **P5-006 / INI-UX-001** — deferred narrow-terminal UX polish.

## Planning Sources

- **Canonical phase source for planning:** this file + `azoth.yaml` (`phase` = milestone-local, `lifecycle_phase` = welcome strip) + `.azoth/roadmap.yaml` `active_version` + matching `current_phase` / `lifecycle_phase`.
- **Root `CLAUDE.md`:** always-loaded; points here for roadmap and expanded workflow.
- **Session cockpit (D52):** Rich dashboard and routing via `/start` → `scripts/welcome.py` (BL-007). On **Claude Code**, **P5-007** adds automatic plain orientation at session open via **SessionStart** + `**.azoth/session-orientation.txt`** mirror; see rule 9. **Cursor:** run `welcome.py` in the **integrated terminal** for the full Rich UI; **Bash** in chat + expand is an alternative. **Codex:** use `/skills` or `$azoth-start` / `$azoth-next`; raw slash tokens are compatibility fallback, not native repo command registration. **Other IDEs without hooks:** `/start` or terminal `welcome.py`; do not assume hook injection.
- **DYNAMIC-FULL-AUTO+:** `skills/dynamic-full-auto/SKILL.md` — parallel research + explore swarms, queen merge to **`SWARM_RESEARCH_DIGEST.yaml`**, helper `scripts/swarm_research_digest.py` (`init` / `append-pack` / `validate`). Use before gated `/auto` delivery, not as a substitute for scope/pipeline gates.
- **Maintenance:** When phase checklists change, update **this skill**, not the root file,
unless the change is a one-line “current phase” pointer in `CLAUDE.md`.

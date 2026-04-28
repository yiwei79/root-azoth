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
holds the **historical phase roadmap** (Phases 1–7 → v0.1.0), the **active v0.2.0-p4
stabilization and rollout slice** (lifecycle Phase 8 in `azoth.yaml`), and the
**expanded development workflow** so agents load it
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

### Milestone v0.2.0 (milestone phase 4) — stabilization · release · control plane 🎯 CURRENT

- **Canonical state:** `azoth.yaml` `version: 0.1.4.0`, `phase: 4`, `milestone: v0.2.0`, `lifecycle_phase: 8` (welcome strip); `.azoth/roadmap.yaml` `active_version: v0.2.0-p4`, `current_phase: 4`, `lifecycle_phase: 8`; per-task specs `.azoth/roadmap-specs/v0.2.0/<id>.yaml`; rollout plan **`.azoth/roadmap-specs/v0.2.0/V0.2.0-P4-ROLLOUT-PLAN.md`**.
- **Phase policy:** v0.2.0-p4 is a stabilization freeze. Do not schedule new feature initiatives. New autonomy, memory, planning-bank, platform, or product ideas stay as proposal, inbox, or initiative-bank evidence until release readiness closes.
- **Execution queue:** p3 carry-forward and autonomous-auto feature work are complete through **T-033**. The live p4 queue is task-backed rather than initiative-backed:
  - **T-034** — freeze milestone baseline and release-readiness gate.
  - **T-035** — generated surface and planning-truth stabilization.
  - **T-036** — product extraction release candidate and consumer smoke test.
  - **T-037** — public azoth publishing pipeline and release automation.
  - **T-038** — personal root control-plane deployment model.
  - **T-039** — release candidate validation and rollout closeout.
- **Operating model:** keep three planes separate: `root-azoth` as private development workshop, `azoth` as clean extracted public product, and the operator personal root as an installed Azoth deployment for project and knowledge control.

## Planning Sources

- **Canonical phase source for planning:** this file + `azoth.yaml` (`phase` = milestone-local, `lifecycle_phase` = welcome strip) + `.azoth/roadmap.yaml` `active_version` + matching `current_phase` / `lifecycle_phase`.
- **Root `CLAUDE.md`:** always-loaded; points here for roadmap and expanded workflow.
- **Session cockpit (D52):** Rich dashboard and routing via `/start` → `scripts/welcome.py` (BL-007). On **Claude Code**, **P5-007** adds automatic plain orientation at session open via **SessionStart** + `**.azoth/session-orientation.txt`** mirror; see rule 9. **Cursor:** run `welcome.py` in the **integrated terminal** for the full Rich UI; **Bash** in chat + expand is an alternative. **Codex:** use `/skills` or `$azoth-start` / `$azoth-next`; raw slash tokens are compatibility fallback, not native repo command registration. **Other IDEs without hooks:** `/start` or terminal `welcome.py`; do not assume hook injection.
- **DYNAMIC-FULL-AUTO+:** `skills/dynamic-full-auto/SKILL.md` — parallel research + explore swarms, queen merge to **`SWARM_RESEARCH_DIGEST.yaml`**, helper `scripts/swarm_research_digest.py` (`init` / `append-pack` / `validate`). Use before gated `/auto` delivery, not as a substitute for scope/pipeline gates.
- **Maintenance:** When phase checklists change, update **this skill**, not the root file,
unless the change is a one-line “current phase” pointer in `CLAUDE.md`.

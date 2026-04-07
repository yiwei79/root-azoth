---
name: orientation
description: |
  Load the v0.1.0 phase roadmap, backlog vs roadmap alignment, and expanded development
  workflow when planning or editing `.azoth/roadmap.yaml` / backlog — not for routine
  implementation work.
---

# Orientation

## Overview

Root `CLAUDE.md` stays small: identity, routing, core rules, and pointers. This skill
holds the **full phase roadmap** (Phases 1–6 toward v0.1.0) and the **expanded
development workflow** so agents load it only when planning, roadmap edits, or phase
alignment—not on every session.

## When to Use

- Before editing `.azoth/backlog.yaml` or `.azoth/roadmap.yaml` for phase alignment.
- When answering “what phase are we in?” with checklist detail beyond one line.
- When implementing or reviewing Phase 4–6 backlog items (welcome UX, trust layer, meta).
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
- [x] kernel/BOOTLOADER.md
- [x] kernel/TRUST_CONTRACT.md
- [x] kernel/GOVERNANCE.md
- [x] kernel/PROMOTION_RUBRIC.md
- [x] kernel/templates/ (CLAUDE.md.template, settings.json.template, etc.)
- [x] kernel/templates/platform-adapters/ (claude/, opencode/, copilot/)
- [x] azoth.yaml manifest
- [x] install.sh + install.ps1

### Phase 1.5: Sync Infrastructure ✅ COMPLETE
- [x] scripts/azoth-sync.py
- [x] sync-config.yaml
- [x] .claude/commands/sync.md

### Phase 2: Core Skills ✅ COMPLETE
- [x] 5 extracted skills (context-map, structured-autonomy-plan, agentic-eval, remember, prompt-engineer)
- [x] 3 new skills (entropy-guard, alignment-sync, self-improve)
- [x] Skill drift detection tests

### Phase 3: Agent Archetypes ✅ COMPLETE (v0.0.3)
- [x] 10 agent archetypes, 8 pipeline presets, workflow loop (D47–D51), auto-router, subagent-router, stage6-rubric, context-recall, `/start` + `scripts/welcome.py` (BL-007; P5-007 SessionStart builds on this in Phase 5), token-optimization tracks (BL-011–BL-015), Cursor adapter (BL-016)

### Phase 4: Distribution & Polish ✅ COMPLETE (v0.0.4)
- [x] D52 (Phase 4): Session Welcome — `.claude/commands/start.md` + `scripts/welcome.py` + template note (BL-007); **Phase 5** extends D52 with `hooks.SessionStart` (P5-007), see below
- [x] P4-001: README (philosophy + quickstart) — D16 — **backlog priority 1**
- [x] P4-002: `azoth init` interactive onboarding (`scripts/azoth_init.py`) — D5, D36 — **backlog priority 2**
- [x] D42: Path duality convention (kernel/ vs `.azoth/kernel/`) — P4-005
- [x] Update kernel docs for dual-path awareness — P4-006
- [ ] Add Edit(.azoth/kernel/**) to settings.json.template deny list (when that template is next revised for consumer installs)

### Phase 5: Trust Layer 🎯 CURRENT (v0.0.5)
- [x] **P5-007 / D52 (Claude Code):** `hooks.SessionStart` in `.claude/settings.json` runs `.claude/hooks/session_start_welcome.py`, which invokes `scripts/welcome.py --plain` with repo `cwd`, mirrors stdout to **`.azoth/session-orientation.txt`** (gitignored), and injects the same text into model context. Matchers `startup|resume`; optional per-hook `timeout` (seconds). **Policy:** root `CLAUDE.md` rules 8–9 — default on injected context; **`Read`** for verbatim plain; **Bash** `welcome.py` (Rich) allowed — expand IDE output for full UI. **Cursor:** no SessionStart — **integrated terminal** `welcome.py` for full Rich UI; Bash in chat + expand; parity rules + `/start`.
- [ ] D43: Commit-time governance hooks (Co-Authored-By stripping, commit format validation)
- [ ] entropy-check hook
- [ ] alignment-summary hook
- [ ] Session telemetry
- [ ] Git-based checkpoints
- [ ] Phone-friendly output

### Phase 6: Meta-Recursive (v0.0.6 — last 0.0.x before v0.1.0)
- [ ] P4-003: CI for drift detection — **deferred from Phase 4**; schedule here with public-repo readiness
- [ ] P4-004: Publish to GitHub (public azoth) — **deferred from Phase 4**; **D35**, **D37**; pairs with v0.1.0 gate
- [ ] Agent Crafter
- [ ] L2 prompt optimization
- [ ] L3 human-gated architecture proposals

## Integration

- **Canonical phase source for planning:** this file + `azoth.yaml` `phase` + `.azoth/roadmap.yaml` `active_version`.
- **Root `CLAUDE.md`:** always-loaded; points here for roadmap and expanded workflow.
- **Session cockpit (D52):** Rich dashboard and routing via `/start` → `scripts/welcome.py` (BL-007). On **Claude Code**, **P5-007** adds automatic plain orientation at session open via **SessionStart** + **`.azoth/session-orientation.txt`** mirror; see rule 9. **Cursor:** run `welcome.py` in the **integrated terminal** for the full Rich UI; **Bash** in chat + expand is an alternative. **Other IDEs without hooks:** `/start` or terminal `welcome.py`; do not assume hook injection.
- **Maintenance:** When phase checklists change, update **this skill**, not the root file,
  unless the change is a one-line “current phase” pointer in `CLAUDE.md`.

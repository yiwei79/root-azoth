---
name: orientation
description: |
  Use this skill when: you need the v0.1.0 phase roadmap, sprint planning against
  backlog vs roadmap, current phase checklist, or the expanded development workflow
  (steps that were moved out of root CLAUDE.md for progressive disclosure). Use this
  skill when: onboarding to Azoth workshop work after reading root CLAUDE.md. Use this
  skill when: updating phase status or deciding what belongs in Phase 3–6.
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

### Phase 3: Agent Archetypes 🎯 CURRENT
- [~] T1: architect, planner, builder, reviewer (initial draft + External Analysis refinements done; online research refinement pending)
- [~] T2: researcher, research-orchestrator (same)
- [~] T3: prompt-engineer, evaluator, agent-crafter (same)
- [~] T4: context-architect (same)
- [ ] Pipeline YAML schema
- [ ] Dual-format agent templates
- [ ] D44: Stage 6 quality rubric for structured content in delivery pipelines
- [ ] D45: Context-recall skill (memory read interface)

### Phase 4: Distribution & Polish
- [ ] D52: Session Welcome UX — `skills/session-start/` + `.claude/commands/start.md`
- [ ] D52: Add `/start` instruction to `kernel/templates/CLAUDE.md.template`
- [ ] D42: Document path duality convention (kernel/ scaffold vs .azoth/kernel/ consumer)
- [ ] Update kernel docs for dual-path awareness (BOOTLOADER.md, GOVERNANCE.md, TRUST_CONTRACT.md)
- [ ] Add Edit(.azoth/kernel/**) to settings.json.template deny list
- [ ] README (philosophy + quickstart)
- [ ] `azoth init` interactive onboarding
- [ ] CI for drift detection
- [ ] Publish to GitHub

### Phase 5: Trust Layer
- [ ] D43: Commit-time governance hooks (Co-Authored-By stripping, commit format validation)
- [ ] entropy-check hook
- [ ] alignment-summary hook
- [ ] Session telemetry
- [ ] Git-based checkpoints
- [ ] Phone-friendly output

### Phase 6: Meta-Recursive
- [ ] Agent Crafter
- [ ] L2 prompt optimization
- [ ] L3 human-gated architecture proposals

## Integration

- **Canonical phase source for planning:** this file + `azoth.yaml` `phase` + `.azoth/roadmap.yaml` `active_version`.
- **Root `CLAUDE.md`:** always-loaded; points here for roadmap and expanded workflow.
- **Maintenance:** When phase checklists change, update **this skill**, not the root file,
  unless the change is a one-line “current phase” pointer in `CLAUDE.md`.

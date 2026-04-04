# AZOTH — The Universal Agentic Toolkit

> *"Be water, my friend."* — Azoth is the alchemist's universal solvent:
> it dissolves into any project and transforms how agents work within it.

## What Is Azoth

A personal "drop-and-start" agentic toolkit for AI-assisted development.
You clone it, run the installer, and any project gets: disciplined agents,
auto-improving memory, trusted autonomous pipelines, and a single human
alignment point.

**Version**: v0.1.0-dev (pre-release)
**Primary platform**: Claude Code (CLI + VS Code extension)
**Also compatible**: OpenCode (reads CLAUDE.md natively), GitHub Copilot (via adapter)
**License**: MIT

## Project Routing

| Area | Path | Purpose |
|------|------|---------|
| Kernel | `kernel/` | Layer 0 — immutable governance core |
| Skills | `skills/` | Layer 1 — portable capabilities |
| Agents | `agents/` | Layer 2 — agent archetypes |
| Pipelines | `pipelines/` | Layer 3 — orchestration templates |
| Scaffold | `scaffold/` | Coded agent/swarm templates |
| Docs | `docs/` | Architecture, ADRs, design |
| Scripts | `scripts/` | Automation (sync, validate, install) |
| Tests | `tests/` | Drift detection, kernel integrity |
| Platform adapters | `kernel/templates/platform-adapters/` | Per-platform file templates |

## Architecture Reference

Full architecture: `docs/AZOTH_ARCHITECTURE.md` (28 decisions, 4 layers, all components).

### The Water Molecule Model (Quick Reference)

```
Layer 3: CURRENT ── Orchestration (ephemeral, per-goal)
Layer 2: WAVE ───── Agents (10 archetypes, 4 tiers)
Layer 1: MINERAL ── Skills, memory, instructions (stable, refinable)
Layer 0: MOLECULE ─ Kernel (immutable without human approval)
```

### Memory System (3-Layer)

```
M3: EPISODIC  ── .azoth/memory/episodes.jsonl (append-only, auto-classified)
M2: SEMANTIC  ── .azoth/memory/patterns.yaml (promoted from M3, human-approved)
M1: PROCEDURAL ─ kernel/ + skills/ + agents/ (promoted from M2 via governance)
```

## Development Instructions

### Core Rules

1. **Quality > speed**. Every output passes evaluation before delivery. No AI slop.
2. **Kernel immutability**. Files in `kernel/` change ONLY via human-approved promotion.
3. **Cross-platform**. All scripts in Python (not PowerShell). Paths via `pathlib`.
4. **macOS primary, Windows validated**. Test on macOS first, verify Windows compat.
5. **Claude Code primary**. `.claude/` is the development surface. Other platforms via adapters.
6. **Architecture-first**. Read `docs/AZOTH_ARCHITECTURE.md` before making structural changes.

### Development Workflow

1. Read this file (you're doing it)
2. Read `docs/AZOTH_ARCHITECTURE.md` for full context
3. Check current phase status below
4. Work within the current phase scope
5. Validate changes against architecture decisions (D1–D28)
6. Capture lessons in `.azoth/memory/episodes.jsonl`

### Coding Standards

- **Language**: Python 3.11+ for all scripts, tests, and automation
- **Tests**: pytest (not unittest, not Pester)
- **Formatting**: ruff format + ruff check
- **Types**: Type hints on all public functions
- **Paths**: `pathlib.Path`, never string concatenation
- **OS**: `os.sep` and `shutil` for cross-platform file ops
- **Errors**: Explicit error messages, fail loudly
- **Comments**: Only for "why", never for "what"

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
- [ ] T1: architect, planner, builder, reviewer
- [ ] T2: researcher, research-orchestrator
- [ ] T3: prompt-engineer, evaluator, agent-crafter
- [ ] T4: context-architect
- [ ] Pipeline YAML schema
- [ ] Dual-format agent templates

### Phase 4: Distribution & Polish
- [ ] README (philosophy + quickstart)
- [ ] `azoth init` interactive onboarding
- [ ] CI for drift detection
- [ ] Publish to GitHub

### Phase 5: Trust Layer
- [ ] entropy-check hook
- [ ] alignment-summary hook
- [ ] Session telemetry
- [ ] Git-based checkpoints
- [ ] Phone-friendly output

### Phase 6: Meta-Recursive
- [ ] Agent Crafter
- [ ] L2 prompt optimization
- [ ] L3 human-gated architecture proposals

## Origin

Azoth was distilled from the SupplyGrowth Agentic Framework (v0.2.20),
a production governance system with 129 tests, 16 agents, and 3-tier
HITL governance. The patterns that proved generic across projects were
extracted, sanitized, and crystallized into this toolkit.

The name comes from alchemy: Azoth is the universal solvent — it encodes
A-to-Z (completeness), dissolves into anything (be water), and transforms
what it touches (the animating spirit).

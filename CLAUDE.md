# AZOTH — The Universal Agentic Toolkit

> *"Be water, my friend."* — Azoth is the alchemist's universal solvent:
> it dissolves into any project and transforms how agents work within it.

## What Is Azoth

**root-azoth** (private) is the personal root scaffold and development
workshop for the Azoth toolkit. This repo is where the toolkit is designed,
built, tested, and evolved. It is NOT a consumer project — it IS the source.

The public deployable product **azoth** (lowercase) will be mechanically
extracted from this scaffold via `sync-config.yaml` product extraction profiles.
See `docs/AZOTH_ARCHITECTURE.md` Section 18 for the 3-tier model.

**As a toolkit**: A personal "drop-and-start" agentic toolkit for AI-assisted
development. You clone it, run the installer, and any project gets: disciplined
agents, auto-improving memory, trusted autonomous pipelines, and a single human
alignment point.

**Version**: v0.0.3.28
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

Full architecture: `docs/AZOTH_ARCHITECTURE.md` (53 decisions, 4 layers, all components).

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
7. **Cursor (Claude)**: Enable Settings → Rules → third-party plugin configs; run `python3 scripts/azoth-deploy.py` (includes `--platforms cursor`) after changing `kernel/templates/platform-adapters/cursor/*.mdc.template` so `.cursor/rules/` stays coupled. Hooks do not run in Cursor; parity rules simulate scope/pipeline gates. For delivery pipelines (`/auto`, `/deliver`, `/deliver-full`), use the **`Task`** tool with `subagent_type` matching each stage per `skills/subagent-router/SKILL.md` — do not inline all stages in main chat when `Task` is available. See `docs/AZOTH_ARCHITECTURE.md` Cursor parity.

### Development Workflow

1. Read this file, then `docs/AZOTH_ARCHITECTURE.md` for structural work.
2. For **phase / roadmap / sprint alignment**, read `skills/orientation/SKILL.md` (lazy-loaded).
3. Work within approved scope; validate against D1–D53; capture durable lessons in `.azoth/memory/episodes.jsonl`.

### Skill index (drift checks)

`context-map`, `structured-autonomy-plan`, `agentic-eval`, `remember`, `prompt-engineer`, `entropy-guard`, `alignment-sync`, `self-improve`, `subagent-router`, `auto-router`, `stage6-rubric`, `context-recall`, `orientation`

### Coding Standards

- **Language**: Python 3.11+ for all scripts, tests, and automation
- **Tests**: pytest (not unittest, not Pester)
- **Formatting**: ruff format + ruff check
- **Types**: Type hints on all public functions
- **Paths**: `pathlib.Path`, never string concatenation
- **OS**: `os.sep` and `shutil` for cross-platform file ops
- **Errors**: Explicit error messages, fail loudly
- **Comments**: Only for "why", never for "what"

### Git Conventions

- **No Co-Authored-By**: NEVER add Co-Authored-By tags or trailers to any commit, PR
  description, or output. No exceptions. This is a governance rule, not a preference.
- **Scope-limited fixes**: When asked to fix a specific artifact (e.g. a PR description or
  a commit message), operate only on that artifact. Do NOT rebase, amend, or rewrite other
  commits unless explicitly asked. Expansion of scope to git history is always ask-first (D26).
- **First-pass quality**: When generating structured content from a source framework (agent
  archetypes, skills, pipeline schemas), match the depth and richness of the source on the
  first pass. Simplified stubs that require a second enrichment pass are a quality failure.

## Orientation & roadmap

**Current phase:** Phase 3 (Agent Archetypes). **Release target:** v0.1.0 — full phase checklist,
expanded workflow, and Phases 4–6 detail live in **`skills/orientation/SKILL.md`** (load on
demand for planning and roadmap edits).

## Origin

Azoth was distilled from the SupplyGrowth Agentic Framework (v0.2.20),
a production governance system with 129 tests, 16 agents, and 3-tier
HITL governance. The patterns that proved generic across projects were
extracted, sanitized, and crystallized into this toolkit.

The name comes from alchemy: Azoth is the universal solvent — it encodes
A-to-Z (completeness), dissolves into anything (be water), and transforms
what it touches (the animating spirit).

## Context Management
Compact at natural task boundaries — end of pipeline stage, after receiving subagent results, between unrelated tasks.
Preserve on compact: active file list, current task state, pending decisions, approved scope.
Discard on compact: exploration file reads, intermediate reasoning steps, subagent raw outputs.

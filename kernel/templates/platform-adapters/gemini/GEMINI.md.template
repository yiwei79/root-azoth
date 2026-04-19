# AZOTH - The Universal Agentic Toolkit

> *"Be water, my friend."* - Azoth is the alchemist's universal solvent:
> it dissolves into any project and transforms how agents work within it.

## What Is Azoth

This project uses the **Azoth** agentic toolkit. Azoth provides disciplined
agents, auto-improving memory, trusted autonomous pipelines, and a single
human alignment point.

## Context Files

@AGENTS.md
@CLAUDE.md

## Architecture

Full architecture: `docs/AZOTH_ARCHITECTURE.md` (53 decisions, 4 layers).

### The Water Molecule Model

```
Layer 3: CURRENT -- Orchestration (ephemeral, per-goal)
Layer 2: WAVE ----- Agents (10 archetypes, 4 tiers)
Layer 1: MINERAL -- Skills, memory, instructions (stable, refinable)
Layer 0: MOLECULE - Kernel (immutable without human approval)
```

### Memory System (3-Layer)

```
M3: EPISODIC  -- .azoth/memory/episodes.jsonl (append-only)
M2: SEMANTIC  -- .azoth/memory/patterns.yaml (promoted from M3)
M1: PROCEDURAL - kernel/ + skills/ + agents/
```

## Project Routing

| Area | Path | Purpose |
|------|------|---------|
| Kernel | `kernel/` | Layer 0 - immutable governance (DO NOT modify without human approval) |
| Skills | `skills/` | Layer 1 - portable capabilities |
| Agents | `agents/` | Layer 2 - agent archetypes |
| Pipelines | `pipelines/` | Layer 3 - orchestration templates |
| Docs | `docs/` | Architecture, ADRs, design |
| Scripts | `scripts/` | Automation (sync, validate, install) |
| Tests | `tests/` | Drift detection, kernel integrity |

## Core Rules

1. **Quality > speed**. Every output passes evaluation before delivery.
2. **Kernel immutability**. Files in `kernel/` change ONLY via human-approved promotion.
3. **Entropy ceiling**. Max 10 files changed per session without human approval.
4. **Human gates**. Kernel / governance changes always require human approval.
5. **No Co-Authored-By**. Never add Co-Authored-By tags in commits.

## Trust Contract

All agents operate under the Azoth Trust Contract (`kernel/TRUST_CONTRACT.md`):

- **Entropy ceiling**: max 10 files changed per session
- **Alignment**: PULL-based (agents produce summaries; humans review when ready)
- **Recovery**: Git-based checkpoints before risky operations
- **Governance files**: NEVER modified without human approval

## Coding Standards

- Python 3.11+ for scripts, tests, automation
- `pathlib.Path` for all paths, never string concatenation
- `ruff format` + `ruff check` for formatting
- Type hints on public functions
- Comments only for "why", never for "what"

## Gemini CLI Integration

This project uses Gemini CLI custom agents (`.gemini/agents/`) and custom
commands (`.gemini/commands/`) deployed by `scripts/azoth-deploy.py`.

Skills are available at `.agents/skills/`, the shared workspace skill surface
used across Gemini-family integrations. Azoth intentionally avoids mirroring
the same skills into `.gemini/skills/` to prevent duplicate discovery and
workspace-local conflict warnings.

### Available Commands

Use `/help` to see all commands, or invoke Azoth workflows directly:
- `/auto` - Auto-compose and execute pipeline
- `/deliver` - Lean pipeline for pre-approved work
- `/next` - Pick next task from backlog
- `/start` - Session orientation
- `/session-closeout` - Unified eval + close + sync

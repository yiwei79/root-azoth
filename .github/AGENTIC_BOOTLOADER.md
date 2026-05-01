# Azoth — Agentic Bootloader State

> This file tracks the project-specific operating picture for the Azoth toolkit itself.
> Azoth eats its own dog food — this bootloader follows the pattern defined in `kernel/BOOTLOADER.md`.

## Boot Phase: PHASE 1 — ACTIVATE + SURVEY

### Project Objective
Build the Azoth Universal Agentic Toolkit — a personal "drop-and-start" overlay
for AI agents that is mutatable to do anything, with governance, memory, and trust.

### Canonical Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Architecture plan | `docs/AZOTH_ARCHITECTURE.md` | ✅ Created |
| Project instructions | `CLAUDE.md` | ✅ Created |
| Toolkit manifest | `azoth.yaml` | ✅ Created |
| Claude Code config | `.claude/settings.json` | ✅ Created |
| Bootstrap command | `.claude/commands/bootstrap.md` | ✅ Created |
| Kernel: Bootloader | `kernel/BOOTLOADER.md` | ⬜ Phase 1 |
| Kernel: Trust Contract | `kernel/TRUST_CONTRACT.md` | ⬜ Phase 1 |
| Kernel: Governance | `kernel/GOVERNANCE.md` | ⬜ Phase 1 |
| Kernel: Promotion Rubric | `kernel/PROMOTION_RUBRIC.md` | ⬜ Phase 1 |
| Installer | `install.sh` + `install.ps1` | ⬜ Phase 1 |
| Sync script | `scripts/azoth-sync.py` | ⬜ Phase 1.5 |

### Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Kernel bloat beyond 2K LOC | High | Hard cap, architect review |
| Platform drift (Claude Code ↔ Copilot) | Medium | Dual-write pattern, adapters |
| Sync leaks org-specific content | High | Sanitization script, strip patterns |
| Meta-recursive loop diverges | Medium | Evaluator scoring + human gate |

### Validation Surfaces

- Python pytest for all tests (cross-platform)
- `ruff check` + `ruff format` for Python code
- Kernel integrity validation script
- Architecture drift check (structure vs AZOTH_ARCHITECTURE.md)

### Major Commands

| Command | Purpose |
|---------|---------|
| `/bootstrap` | Day 0 guided kernel creation |
| `/auto` | Auto-compose and execute explicit governed delivery |
| `/deliver` | Lean pipeline for pre-approved work |
| `/deliver-full` | Full pipeline with governance gates |
| `/plan` | Structured planning without execution |
| `/eval` | Governance quality gate |
| `/remember` | Capture cross-session learning |
| `/promote` | Review M2→M1 promotion candidates |
| `/sync` | Sync patterns from source framework (Phase 1.5) |
| `/worktree-sync` | Git checkpoint and sync |
| `/session-closeout` | Unified eval + close + sync |

### Missing Overlays (to be created during Phase 1)

- [ ] Memory directory (`.azoth/memory/`)
- [ ] Telemetry directory (`.azoth/telemetry/`)
- [ ] `.gitignore` for runtime state
- [ ] Tests directory with pytest configuration

## Origin

This project was architected in a SupplyGrowth SE: Architect session on 2026-04-03.
5 rounds of refinement produced 28 architecture decisions and a complete v0.1.0 plan.
The handoff artifacts were created at session close to enable seamless Day 0 bootstrap
via Claude Code on macOS.

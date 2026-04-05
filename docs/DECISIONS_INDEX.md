# Architecture Decisions Index

Machine-readable index of all architecture decisions (D1–D41).
Agents use this to check compliance and track implementation status.

See `docs/AZOTH_ARCHITECTURE.md` for full rationale and context.

## Status Legend

- ✅ **implemented** — Decision is fully realized in code/config
- 🔧 **partial** — Decision exists but not all aspects are implemented
- 📋 **planned** — Decision is approved but implementation is deferred
- 🔄 **superseded** — Replaced by a later decision

## Decisions

| # | Title | Status | Location | Phase |
|---|-------|--------|----------|-------|
| D1 | Name: Azoth | ✅ implemented | CLAUDE.md, azoth.yaml | 1 |
| D2 | Kernel: 10 files / 2000 LOC cap | ✅ implemented | kernel/ | 1 |
| D3 | Trust Contract: entropy ceiling | ✅ implemented | kernel/TRUST_CONTRACT.md | 1 |
| D4 | Repo: isolated from org repos | ✅ implemented | Repository setup | 1 |
| D5 | Distribution: git clone + installer | ✅ implemented | install.sh | 1 |
| D6 | Pipelines: YAML-declarative | 📋 planned | pipelines/ (Phase 3) | 3 |
| D7 | Agents: 10 archetypes, 4 tiers | 📋 planned | agents/ (Phase 3) | 3 |
| D8 | Coded scaffold: included | ✅ implemented | scaffold/ | 1 |
| D9 | Sync extraction: Python script | ✅ implemented | scripts/azoth-sync.py | 1.5 |
| D10 | Session scope per session | ✅ implemented | kernel/TRUST_CONTRACT.md | 1 |
| D11 | Memory: 3-layer auto-improving | 🔧 partial | .azoth/memory/ (M3 works, M2→M1 pending) | 1 |
| D12 | Claude Code Extension: full compat | ✅ implemented | .claude/ config | 1 |
| D13 | Skills: shared between platforms | ✅ implemented | skills/ | 2 |
| D14 | Observability: session telemetry | 🔧 partial | kernel/GOVERNANCE.md Section 6 | 1 |
| D15 | Rollback: git-based checkpoints | ✅ implemented | kernel/TRUST_CONTRACT.md | 1 |
| D16 | README: Phase 4 deliverable | 📋 planned | — | 4 |
| D17 | Pipeline schema: Phase 3 deliverable | 📋 planned | pipelines/ | 3 |
| D18 | OpenCode: compatible via CLAUDE.md | ✅ implemented | CLAUDE.md | 1 |
| D19 | Platform adapter pattern | ✅ implemented | kernel/templates/platform-adapters/ | 1 |
| D20 | No multi-platform layers in kernel | ✅ implemented | kernel/ | 1 |
| D21 | Full pipeline: 7 stages with typed gates | 📋 planned | pipelines/ (Phase 3) | 3 |
| D22 | Goal Clarification Protocol (Stage 0) | 📋 planned | pipelines/ (Phase 3) | 3 |
| D23 | Auto-pipeline: LLM-as-router | 📋 planned | pipelines/ (Phase 3) | 3 |
| D24 | Gate typing: human vs agent | ✅ implemented | kernel/GOVERNANCE.md | 1 |
| D25 | 12 seed slash commands | ✅ implemented | .claude/commands/ | 1 |
| D26 | Proactive Agent Posture: 3 tiers | ✅ implemented | kernel/TRUST_CONTRACT.md | 1 |
| D27 | Explore/Research as Architect tools | ✅ implemented | Design decision | 1 |
| D28 | 8 pipeline presets | 📋 planned | pipelines/ (Phase 3) | 3 |
| D29 | Inbox format: `.azoth/inbox/*.jsonl` | ✅ implemented | .azoth/inbox/ | 1.5 |
| D30 | Trusted source registry | ✅ implemented | .azoth/trusted-sources.yaml | 1.5 |
| D31 | SURVEY auto-detect + `/intake` | ✅ implemented | kernel/BOOTLOADER.md, .claude/commands/intake.md | 1.5 |
| D32 | 12-field insight schema | ✅ implemented | kernel/GOVERNANCE.md Section 7 | 1.5 |
| D33 | 4-step intake protocol | ✅ implemented | .claude/commands/intake.md | 1.5 |
| D34 | root-azoth = personal root scaffold | ✅ implemented | azoth.yaml, CLAUDE.md | 1.5 |
| D35 | azoth = public deployable product | 📋 planned | Phase 4 extraction | 4 |
| D36 | `--scaffold` vs `--project` modes | 📋 planned | Phase 4 installer | 4 |
| D37 | root-azoth (private) / azoth (public) | ✅ implemented | Naming convention | 1.5 |
| D38 | Scaffold infra now, extraction later | ✅ implemented | sync-config.yaml | 1.5 |
| D39 | Roadmap tracking: `.azoth/roadmap.yaml` | ✅ implemented | .azoth/roadmap.yaml | 1.5 |
| D40 | Repo rename: root-azoth | ✅ implemented | Repository naming | 1.5 |
| D41 | Bootstrap loop: 4 artifacts | ✅ implemented | roadmap + next + preflight + decisions index | 1.5 |
| D42 | Path duality convention: kernel/ vs .azoth/kernel/ | 📋 planned | — (Phase 4) | 4 |
| D43 | Commit-time governance enforcement hooks | 📋 planned | hooks/ (Phase 5) | 5 |
| D44 | Pipeline Stage 6 quality rubric for structured content | 📋 planned | pipelines/ (Phase 3) | 3 |

## Summary

| Status | Count |
|--------|-------|
| ✅ implemented | 27 |
| 🔧 partial | 2 |
| 📋 planned | 15 |
| 🔄 superseded | 0 |
| **Total** | **44** |

# Architecture Decisions Index

Machine-readable index of all architecture decisions (D1–D52).
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
| D6 | Pipelines: YAML-declarative | 🔧 partial | pipelines/pipeline.schema.yaml + preset files in pipelines/ | 3 |
| D7 | Agents: 10 archetypes, 4 tiers | 📋 planned | agents/ (Phase 3) | 3 |
| D8 | Coded scaffold: included | ✅ implemented | scaffold/ | 1 |
| D9 | Sync extraction: Python script | ✅ implemented | scripts/azoth-sync.py | 1.5 |
| D10 | Session scope per session | ✅ implemented | kernel/TRUST_CONTRACT.md | 1 |
| D11 | Memory: 3-layer auto-improving | 🔧 partial | .azoth/memory/ (M3 works, M2→M1 pending) | 1 |
| D12 | Claude Code Extension: full compat | ✅ implemented | .claude/ config | 1 |
| D13 | Skills: shared between platforms | ✅ implemented | skills/ | 2 |
| D14 | Observability: session telemetry | ✅ implemented | kernel/GOVERNANCE.md §6; `.claude/hooks/session_telemetry.py`; `.azoth/telemetry/session-log.jsonl` (gitignored) | 1 |
| D15 | Rollback: git-based checkpoints | ✅ implemented | kernel/TRUST_CONTRACT.md | 1 |
| D16 | README: Phase 4 deliverable | 📋 planned | — | 4 |
| D17 | Pipeline schema: Phase 3 deliverable | 🔧 partial | pipelines/pipeline.schema.yaml + pipeline.template.yaml | 3 |
| D18 | OpenCode: compatible via CLAUDE.md | ✅ implemented | CLAUDE.md | 1 |
| D19 | Platform adapter pattern | ✅ implemented | kernel/templates/platform-adapters/ | 1 |
| D20 | No multi-platform layers in kernel | ✅ implemented | kernel/ | 1 |
| D21 | Full pipeline: 7 stages with typed gates | 🔧 partial | pipelines/full.pipeline.yaml | 3 |
| D22 | Goal Clarification Protocol (Stage 0) | 🔧 partial | pipelines/full.pipeline.yaml goal-clarification stage | 3 |
| D23 | Auto-pipeline: LLM-as-router | ✅ implemented | skills/auto-router/SKILL.md + pipelines/auto.pipeline.yaml | 3 |
| D24 | Gate typing: human vs agent | ✅ implemented | kernel/GOVERNANCE.md | 1 |
| D25 | Seed slash commands (minimum table + scaffold e.g. `/next`, `/arch-proposal`) | ✅ implemented | .claude/commands/ + docs § Seed Commands (D25) | 1 |
| D26 | Proactive Agent Posture: 3 tiers | ✅ implemented | kernel/TRUST_CONTRACT.md | 1 |
| D27 | Explore/Research as Architect tools | ✅ implemented | Design decision | 1 |
| D28 | 8 pipeline presets | 📋 planned | pipelines/ (Phase 3) | 3 |
| D29 | Inbox format: `.azoth/inbox/*.jsonl` | ✅ implemented | .azoth/inbox/ | 1.5 |
| D30 | Trusted source registry | ✅ implemented | .azoth/trusted-sources.yaml | 1.5 |
| D31 | SURVEY auto-detect + `/intake` | ✅ implemented | kernel/BOOTLOADER.md, .claude/commands/intake.md | 1.5 |
| D32 | 12-field insight schema | ✅ implemented | kernel/GOVERNANCE.md Section 7 | 1.5 |
| D33 | 4-step intake protocol | ✅ implemented | .claude/commands/intake.md (step 3 extended to 3-axis by D49) | 1.5 |
| D34 | root-azoth = personal root scaffold | ✅ implemented | azoth.yaml, CLAUDE.md | 1.5 |
| D35 | azoth = public deployable product | 📋 planned | Phase 4 extraction | 4 |
| D36 | `--scaffold` vs `--project` modes | 📋 planned | Phase 4 installer | 4 |
| D37 | root-azoth (private) / azoth (public) | ✅ implemented | Naming convention | 1.5 |
| D38 | Scaffold infra now, extraction later | ✅ implemented | sync-config.yaml | 1.5 |
| D39 | Roadmap tracking: `.azoth/roadmap.yaml` | 🔄 superseded | Superseded by D48 (roadmap.yaml versioned) | 1.5 |
| D40 | Repo rename: root-azoth | ✅ implemented | Repository naming | 1.5 |
| D41 | Bootstrap loop: 4 artifacts | ✅ implemented | roadmap + next + preflight + decisions index | 1.5 |
| D42 | Path duality convention: kernel/ vs .azoth/kernel/ | ✅ implemented | `docs/AZOTH_ARCHITECTURE.md` §18 Path duality | 4 |
| D43 | Commit-time governance enforcement hooks | 🔧 partial | `scripts/git_commit_policy.py`, `scripts/git-hooks/commit-msg`, `scripts/azoth_install_git_hooks.py` (Co-Authored-By); optional format rules TBD — BL-002 is write-time subset | 5 |
| D44 | Pipeline Stage 6 quality rubric for structured content | 🔧 partial | skills/stage6-rubric/SKILL.md | 3 |
| D45 | Context-sensitive memory retrieval | 🔧 partial | skills/context-recall/SKILL.md | 3 |
| D46 | Dev-sync script: workspace self-installation to platform directories | ✅ implemented | scripts/azoth-deploy.py | 3 |
| D47 | Persistent backlog: `.azoth/backlog.yaml` | ✅ implemented | .azoth/backlog.yaml | 3 |
| D48 | Versioned roadmap: `.azoth/roadmap.yaml` | ✅ implemented | .azoth/roadmap.yaml (v0.0.1–v0.0.7 + v0.1.0 target; /next reads versioned structure) | 3 |
| D49 | Intake 3-axis triage (extends D33) | ✅ implemented | .claude/commands/intake.md | 3 |
| D50 | Session scope card | 🔧 partial | `.claude/commands/next.md` + `.azoth/scope-gate.json` (BL-004 delivered; hook enforcement Claude Code–only) | 3 |
| D51 | Formalized M2→M1 promotion path | ✅ implemented | kernel/GOVERNANCE.md + kernel/PROMOTION_RUBRIC.md | 3 |
| D52 | Session Welcome UX: `/start` + `scripts/welcome.py` | ✅ implemented | `scripts/welcome.py` + `.claude/commands/start.md` (BL-007); Phase 5: `.claude/hooks/session_start_welcome.py`, `.azoth/session-orientation.txt` (runtime), `CLAUDE.md` rule 9 | 4 |
| D53 | Auto-versioning policy: delivery-triggered version increments | 📋 planned | scripts/version-bump.py + /session-closeout integration (BL-009) | 4 |

## Summary

| Status | Count |
|--------|-------|
| ✅ implemented | 32 |
| 🔧 partial | 9 |
| 📋 planned | 11 |
| 🔄 superseded | 1 |
| **Total** | **53** |

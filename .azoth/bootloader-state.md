# Azoth Bootloader State

## Current Phase
v0.1.1.37 · Phase 1 — v0.2.0 · swarm · memory · UX (milestone phase 1) · active_version: v0.2.0-p1

## Last Session
- **Session**: 2026-04-12-p1-013-orchestrator-default
- **Platform**: Copilot CLI (Opus 4.6)
- **Delivered**: P1-013 — Explicit main-session orchestrator default (Claude Code + Copilot role parity)
- **Pipeline**: deliver-full (7-stage governed)
- **Eval**: eval-swarm PASS (0.961 aggregate, 0.90 bar)
- **Episodes**: ep-133 (delivery), ep-134 (self-improvement meta-observations)
- **Version bump**: 0.1.1.36 → 0.1.1.37

## Key Changes This Session
1. CLAUDE.md rule 10: Orchestrator as default session persona with yield + inline-fallback clauses
2. .github/copilot-instructions.md: Default agent persona section with scope note
3. agents/tier1-core/orchestrator.agent.md: Stale DFA e2e friction branch ref → P1-013 resolved
4. docs/platform-guides/orchestrator-default-entry.md: §Deferred Work superseded by P1-013
5. Backlog + roadmap closed P1-013; added P1-018, P1-019 from eval-swarm

## Open Decisions
- None from this session

## Next Action
- P1-018: Mechanically enforce azoth-deploy after source agent changes (priority 14, infrastructure/standard)
- P1-019: Add ambiguous-case examples to CLAUDE.md rule 10 (priority 15, infrastructure/standard)
- P1-008: auto-router L2 / self-improve lane (priority 13, M1/governed — timing: let auto-router rules bake first)

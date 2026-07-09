# Azoth Simplification Research Findings

**Purpose:** Persist the deep research and critique from the 2026-06-23 simplification session so future planning does not depend on chat context.

**Research basis:** Five parallel deep explorations covered architecture/philosophy, Python tooling, skills/agents/pipelines/commands, multi-platform sync, and memory/repo hygiene. Several high-risk findings were re-verified directly in the workspace during the session.

**Planning relationship:** This file is evidence. The executable roadmap is `docs/superpowers/plans/2026-06-23-azoth-simplification-roadmap.md`.

---

## Executive Thesis

Azoth is a serious governance-first agentic toolkit with real engineering strengths: Trust Contract, entropy budgeting, runtime guards, memory promotion, deploy parity, and a broad test suite. Its main failure mode is **accretion without subtraction**: every improvement tends to add a new named layer, D-number, adapter, mirror, rule, or script while old surfaces remain active.

The simplification strategy should therefore preserve the load-bearing core and remove duplicate truth, contradictory posture, and personal-workshop residue before any broad refactor.

## What Azoth Is Trying To Be

- A portable agentic toolkit that installs into projects and gives agents disciplined workflows.
- A governed autonomy system: bounded changes, human gates, recoverable state, and PULL-based alignment.
- A layered memory/promote system: M3 episodic records, M2 approved patterns, M1 procedural assets.
- A multi-host adapter layer for Claude Code, Codex, OpenCode, Copilot, Cursor, Gemini, Antigravity, and Hermes.
- A root workshop (`root-azoth`) that extracts a public product (`azoth`) via configured sync/extraction.

## What Azoth Does Right

### Trust and Governance

- The Trust Contract contains a computable entropy formula and explicitly bounds blast radius.
- PULL-based alignment summaries are the correct default for asynchronous human-agent work.
- `azoth_effect: read | write | mixed` makes command side effects legible.
- External insights are treated as untrusted data, not instructions, which aligns with prompt-injection safety practice.

### Runtime Guard Direction

- The FD-003/004/005/008 guard family is small, deterministic, and subprocess-based.
- `scripts/azoth_guards.py` is a clean runner pattern and better than relying on prompt prose for safety invariants.
- This is the architectural direction worth expanding: mechanical checks over narrative constraints.

### Memory System

- Memory is real, not purely write-only theater.
- `.azoth/memory/episodes.jsonl` contains 588 episodes; `.azoth/memory/patterns.yaml` contains 29 promoted patterns.
- Production readers exist: `context_recall_quality.py`, `do_closeout.py`, `welcome.py`, `autonomous_campaign_audit.py`, `reinforcement_count.py`, `worktree_sync.py`, and related surfaces.
- `episode_store.py` has meaningful append/merge invariants and worktree-aware reconciliation.

### Tests and Engineering Discipline

- The test suite is unusually broad for a personal/workshop toolkit: over 2,000 collected tests in current runs.
- `test_autonomous_loop.py`, `test_azoth_deploy.py`, and `test_run_ledger.py` pin behavior for major high-risk surfaces.
- The test suite is the main reason structural simplification is possible without blind rewrites.

### Deploy Compiler

- `scripts/azoth-deploy.py` is a real projection compiler, not a pure copy script.
- It transforms agents, commands, skills, and host adapters across multiple platforms.
- `--check` provides a mechanical parity gate and should remain central.

## What Azoth Gets Wrong

### Accretion Without Subtraction

Evidence:
- 57 D-numbered decisions plus BL, FD, P, W, F, M, L, Layer, and Tier vocabularies.
- Multiple active names for related concepts: Layer 0-3, M1-M3, Tier 1-4, L1-L3.
- Legacy command bodies coexist with canonical `commands/<name>/command.yaml` contracts.
- Superseded roadmap concepts remain active instead of being retired.

Planning implication:
- Simplification work must enforce subtraction discipline. Do not add new D-numbers, command names, layers, or adapter surfaces unless an old surface is removed or clearly frozen.

### Loss of Conceptual Integrity

Evidence:
- The water-molecule names are evocative but not mechanically load-bearing.
- The kernel can mean four hashed files, five root `kernel/*.md` files, or kernel docs plus templates depending on the context.
- Platform posture has conflicting stories: Claude/Codex as co-primary in some docs; Hermes/Codex/OpenCode as trust-bearing in D55/kernel docs.

Planning implication:
- Resolve vocabulary and authority contradictions before large code refactors. Otherwise refactors will preserve or multiply the ambiguity.

### Documentation Drift

Directly re-verified during the session:
- `CLAUDE.md` and `GEMINI.md` said 53 decisions.
- `docs/DECISIONS_INDEX.md` header said D1-D54 while the table ended at D57 and total said 57.
- `AGENTS.md` advertised `.claude/skills/` even though that directory does not exist.
- `azoth-deploy.py --check` initially reported 4 stale generated orchestrator files.
- `kernel/TRUST_HOSTS.md` declared itself Layer 0 but was outside `.azoth/kernel-checksums.sha256` and `scripts/kernel-integrity.py` checksum coverage.

Planning implication:
- Treat source-of-truth inventory and deploy/checksum parity as first-class stabilization work.

### Declarative Theatre

Evidence:
- `pipelines/pipeline.schema.yaml` is not the runtime validator; `pipeline_lint.py` re-implements constraints in Python.
- `auto.pipeline.yaml` and `skills/auto-router/SKILL.md` duplicate routing logic.
- `autonomous_loop.py` does not consume pipeline YAML as a runtime source of truth.

Planning implication:
- Pick one narrow declarative surface and make it mechanically checked before attempting a broad pipeline redesign.

### Tooling God-Files and Implicit Library

Evidence:
- `scripts/autonomous_loop.py` is about 6,305 LOC and contains candidate selection, decision policy, alignment packet handling, proposal hydration, self-capture, strategy preflight, and YAML/lock wrappers.
- `scripts/run_ledger.py`, `worktree_sync.py`, `do_closeout.py`, and `autonomous_campaign_audit.py` are also large subsystem files.
- There is no real package boundary; tests and scripts rely on path insertion patterns.
- YAML helpers exist but duplicated `_load_yaml` / `_dump_yaml` helpers remain across multiple scripts.

Planning implication:
- Do not start with a whole-package rewrite. First extract one tiny duplicated helper path under test, then repeat.

### Multi-Platform Sync Complexity

Evidence:
- Generated mirrors span 277 files across host surfaces.
- `install.sh` and `install.ps1` are separate hand-written install paths that do not call `azoth-deploy.py`.
- OpenCode install paths use singular `.opencode/agent` and `.opencode/command` while generated repo paths use `.opencode/agents` and `.opencode/commands`.
- Gemini/Cursor are accepted by installer parsing but not fully handled by installer branches.

Planning implication:
- Eventually make installers call the deploy compiler instead of maintaining a parallel copy path. Do this after Phase 0 stabilization, not during it.

### Personal Workshop vs Portable Product

Evidence:
- The repo contains personal cockpit/harness scripts: `personal_harness_*`, `personal_knowledge_*`, `cockpit_*`, and `welcome.py` dashboard code.
- `docs/personal-control-plane/` includes author-specific operator onboarding.
- `.azoth/` contains tracked campaigns, handoffs, inbox items, research, and roadmap state from one operator/workshop.
- PolyForm Noncommercial licensing conflicts with broad commercial adoption of a drop-in toolkit.

Planning implication:
- Scope separation must be a proposal and decision gate before deletion. Classify surfaces as `core-toolkit`, `operator-extension`, or `local-state`.

## Industry and Academic Anchors

- **Lehman's Laws of Software Evolution:** Azoth shows increasing complexity from continuous growth without equivalent simplification work.
- **Brooks, conceptual integrity:** Azoth contains many good ideas but too many overlapping vocabularies and authorities.
- **Sweller, Cognitive Load Theory:** bespoke terms and layered numbering systems create extraneous cognitive load for users and contributors.
- **Leidy Klotz, Subtract:** the project repeatedly solves problems by adding surfaces instead of removing or merging existing ones.
- **Parnas information hiding / Fowler refactoring:** god-files and implicit libraries make safe change expensive.
- **Infrastructure-as-code drift practice:** generated mirrors require mechanical parity gates in CI; optional local hooks are insufficient.
- **Agent safety practice:** prompt-only safety rules are weaker than deterministic subprocess/runtime checks.

## Revised Phase 0 Changes Currently Kept In Worktree

- `azoth-deploy.py --check` was added to CI.
- Deploy was re-run; stale orchestrator mirrors were regenerated.
- Generated agents no longer reference phantom `skills/azoth-route-decision`, `skills/azoth-assumption-checkpoint`, `skills/azoth-eval-dispatch`, or `skills/azoth-fd-guard` paths.
- Deploy now validates generated agent skill references against known skills.

## Findings Deferred Or Resolved After The Revised Phase 0 Patch

- Decision count references still need a later consistency cleanup.
- `kernel/TRUST_HOSTS.md` self-declared Layer 0 while sitting outside the checksum manifest; this is resolved by the five-file kernel checksum task.
- `AGENTS.md` still advertises `.claude/skills/`; fix this in a separate generated-doc truth task.

## Current Verification Reality

Targeted revised Phase 0 verification should cover:
- `tests/test_azoth_deploy.py::test_agent_outputs_report_missing_skill_references`
- `tests/test_azoth_deploy.py::test_canonical_agent_outputs_reference_existing_skills`
- `scripts/azoth-deploy.py --check`
- Focused Ruff lint/format on changed Python files.

Repo-wide verification still has blockers outside the Phase 0 slice:
- Full pytest had 16 failures, primarily around orchestrator contract/test mismatch, Codex adapter fixture imports, and legacy `azoth.yaml` platform-shape assumptions.
- Repo-wide Ruff check failed on unused imports in `tests/test_trust_hosts_contract.py`.
- Repo-wide Ruff format reported 30 pre-existing files needing formatting.

## Minimum Viable Planning Principles

1. Stabilize the current Phase 0 patch before starting new simplification work.
2. Create a source-of-truth inventory before editing strategic docs.
3. Resolve platform/trust posture contradictions before touching installers or host projections deeply.
4. Fix one duplicate truth at a time with a targeted regression test.
5. Prefer tiny utility consolidation over package-wide rewrites.
6. Treat personal-workshop separation as a classification/decision problem before deletion.
7. Keep generated mirrors generated; never hand-edit them as source.
8. Record repo-wide blockers honestly instead of claiming global green.

## Recommended Roadmap Sequence

1. Stabilize/review Phase 0 change set.
2. Write source-of-truth inventory.
3. Resolve primary platform/trust-bearing terminology.
4. Add mechanical parity for one duplicated declarative surface, starting with auto routing.
5. Consolidate one duplicated YAML helper path.
6. Produce a scope-separation brief for cockpit/personal/local-state surfaces.

## Non-Goals For The Next Slice

- Do not split `autonomous_loop.py` yet.
- Do not rewrite installer architecture yet.
- Do not delete `.azoth/` tracked state yet.
- Do not introduce a new architecture decision number unless the human explicitly asks.
- Do not normalize all formatting repo-wide as a drive-by change.

## Open Human Decisions

1. Should the current Phase 0 patch be kept, revised, or parked?
2. Which platform story is authoritative: Hermes/Codex/OpenCode trust-bearing, Claude/Codex co-primary, or an explicit split between trust-bearing and user-facing support?
3. Is the portable product meant to be commercially adoptable, or is PolyForm Noncommercial intentional for the foreseeable future?
4. Should personal cockpit/harness surfaces move out, stay marked as non-product, or remain first-class?

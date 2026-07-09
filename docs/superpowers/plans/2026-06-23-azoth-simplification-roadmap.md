# Azoth Simplification Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify and refactor Azoth toward efficiency, conceptual integrity, and maintainability without breaking the trust, memory, and multi-host intent that make the project valuable.

**Architecture:** Treat Azoth as a governance-first agent toolkit, not a prompt-library grab bag. Preserve the small load-bearing core: Trust Contract, runtime guards, deploy parity, memory promotion, and tests. Remove drift and duplicate surfaces before adding features or broad refactors.

**Tech Stack:** Python 3.11+, pytest, ruff, PyYAML, Rich, generated host mirrors via `scripts/azoth-deploy.py`, kernel checks via `scripts/kernel-integrity.py`.

## Global Constraints

- Do not start broad refactors while repo-wide tests and source-of-truth drift are unresolved.
- Treat `opencode/GLM5.2_refactor` as the integration branch for this work; do not assume `main` is the active target branch.
- Preserve the intent: bounded autonomous work, human alignment, memory read/write discipline, multi-host portability, and mechanical guardrails.
- Prefer subtraction and consolidation over new terminology, new commands, new D-numbers, or new host surfaces.
- Every task must have a fresh targeted verification command; repo-wide failures must be recorded, not hidden.
- Generated mirrors are not source: edit canonical sources, then run `python3 scripts/azoth-deploy.py`.
- Kernel/governance changes require explicit human approval and checksum updates.
- Stop if a task touches more than 10 files or enters an unrelated subsystem; split the roadmap instead.

---

## Current State Snapshot

- A Phase 0 stop-the-bleeding change set is currently in the worktree.
- Targeted Phase 0 verification passed before revision; after option 2, Phase 0 is narrowed to deploy parity, regenerated orchestrator mirrors, and missing-skill-reference validation.
- Repo-wide verification is not green: full pytest has existing failures around orchestrator contract drift, Codex adapter fixture imports, and legacy platform assumptions; repo-wide Ruff also has unrelated lint/format drift.
- Untracked local state exists and must not be modified unless explicitly requested: `.claude/state/`, `tests/fixtures/_round1_clean.json`, `tests/fixtures/_round1_fail.json`.

## Research Findings Artifact

The deep session findings are persisted in `docs/superpowers/plans/2026-06-23-azoth-simplification-research-findings.md`. Treat that file as the evidence base for this roadmap. If future work discovers contradictory evidence, update the findings file first, then adjust this roadmap.

## Alignment Thesis

Azoth's best parts are real: the Trust Contract, subprocess guards, memory promotion discipline, deploy compiler, and test suite. The simplification target is not to shrink everything blindly; it is to protect those load-bearing ideas by removing contradiction, duplicate truth, and personal-workshop residue.

## Minimum Viable Roadmap

### Task 1: Stabilize the Phase 0 Change Set

**Files:**
- Review: current git diff
- Modify only if needed: files already touched in the Phase 0 change set
- Test: targeted Phase 0 tests and deploy/kernel checks

**Interfaces:**
- Consumes: current worktree state from the Phase 0 stop-the-bleeding pass
- Produces: a clean, reviewable Phase 0 patch that either lands or is intentionally revised

- [ ] **Step 1: Review the current tracked diff**

Run: `git diff --stat && git diff --name-only`

Expected: only Phase 0 files are modified; no unrelated source edits are present.

- [ ] **Step 2: Re-run Phase 0 targeted verification**

Run:

```bash
python3 -m pytest tests/test_decisions_index_consistency.py tests/test_kernel_integrity.py tests/test_kernel_contract_doc_consistency.py tests/test_install_sh_kernel_checksums.py tests/test_hermes_manifest_check.py tests/test_azoth_deploy.py::test_agent_outputs_report_missing_skill_references tests/test_azoth_deploy.py::test_canonical_agent_outputs_reference_existing_skills -q
python3 scripts/kernel-integrity.py
python3 scripts/kernel-integrity.py --verify-checksums
python3 scripts/azoth-deploy.py --check
```

Expected: targeted tests pass, kernel checks return exit 0, deploy reports all files in sync.

- [ ] **Step 3: Record repo-wide blockers without expanding scope**

Run:

```bash
python3 -m pytest -q
python3 -m ruff check .
python3 -m ruff format --check .
```

Expected: if failures remain, summarize them as existing blockers. Do not fix unrelated orchestrator/Codex/platform-test drift inside Task 1.

- [ ] **Step 4: Human decision gate**

Present options:

```text
1. Keep Phase 0 patch and continue to Task 2.
2. Revise Phase 0 patch before continuing.
3. Park Phase 0 patch and start a fresh simplification branch/scope.
```

Expected: no further implementation until the human chooses one option.

### Task 2: Create One Source-of-Truth Inventory

**Files:**
- Create: `docs/superpowers/plans/2026-06-23-azoth-source-of-truth-inventory.md`
- Read: `README.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `docs/DECISIONS_INDEX.md`, `kernel/TRUST_HOSTS.md`, `scripts/azoth-deploy.py`, `sync-config.yaml`

**Interfaces:**
- Consumes: review findings from this session
- Produces: a concise inventory that says which file owns each major truth

- [ ] **Step 1: Write the inventory skeleton**

Create sections:

```markdown
# Azoth Source-of-Truth Inventory

## Canonical Truths
| Topic | Canonical Source | Generated Mirrors | Validation Gate |
|---|---|---|---|

## Contradictions To Resolve
| Topic | Conflicting Files | Proposed Owner | Decision Needed |
|---|---|---|---|

## Do Not Add New Owners
```

- [ ] **Step 2: Fill only the minimum viable rows**

Include rows for: decisions count, trust-bearing hosts, kernel checksum set, agents, skills, commands, pipelines, installer/deployer, memory tiers, public-product extraction.

- [ ] **Step 3: Verify no new authority is invented**

Run: `grep -n "Canonical Source\|Generated Mirrors\|Validation Gate" docs/superpowers/plans/2026-06-23-azoth-source-of-truth-inventory.md`

Expected: the file is an index to existing authorities, not a replacement architecture doc.

### Task 3: Resolve Strategy Contradictions Before Refactoring

**Files:**
- Modify only after human choice: `README.md`, `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, `docs/CO_PRIMARY_PLATFORM_BLUEPRINT.md`, `kernel/TRUST_HOSTS.md`, `docs/HERMES_SUBSTRATE.md`
- Test: `python3 scripts/azoth-deploy.py --check`, relevant doc tests

**Interfaces:**
- Consumes: Task 2 inventory
- Produces: one coherent platform/trust story

- [ ] **Step 1: Present the strategic choice**

Ask the human to choose exactly one:

```text
1. Trust-bearing story: Hermes + Codex + OpenCode are primary; Claude/Copilot/Cursor/Gemini/Antigravity are best-effort mirrors.
2. Product-adoption story: Claude Code + Codex are co-primary; Hermes becomes a personal operator appendix.
3. Transitional story: keep both, but explicitly separate "trust-bearing" from "user-facing supported" in every top-level doc.
```

- [ ] **Step 2: Edit only the chosen story**

Expected: all top-level docs use the same terms for platform posture. Do not add D58 unless the human explicitly requests a new architecture decision.

- [ ] **Step 3: Regenerate generated surfaces**

Run: `python3 scripts/azoth-deploy.py`

Expected: generated docs match the chosen story.

- [ ] **Step 4: Verify targeted doc/deploy gates**

Run: `python3 scripts/azoth-deploy.py --check && python3 -m pytest tests/test_agents_md_parity.py tests/test_trust_hosts_contract.py -q`

Expected: deploy parity clean; trust-host tests pass or fail only for intentionally updated expectations.

### Task 4: Stop Declarative Theatre in One Narrow Place

**Files:**
- Modify: `pipelines/auto.pipeline.yaml` or `skills/auto-router/SKILL.md`
- Modify or create: a small generator/test only if needed
- Test: focused routing-table parity test

**Interfaces:**
- Consumes: existing `auto-router` 11-rule routing table and `auto.pipeline.yaml`
- Produces: one canonical source for the auto routing table

- [ ] **Step 1: Choose the canonical routing-table source**

Recommended: `skills/auto-router/SKILL.md` remains human/agent-facing, but its table is checked against `pipelines/auto.pipeline.yaml` until a generator exists.

- [ ] **Step 2: Add a failing parity test**

Test should extract rule IDs or route labels from both files and fail if one contains a rule missing from the other.

- [ ] **Step 3: Make the minimum edit to pass**

Expected: no pipeline redesign; only parity enforcement.

- [ ] **Step 4: Verify**

Run: `python3 -m pytest <new-test-file> -q && python3 scripts/pipeline_lint.py`

Expected: parity test and pipeline lint pass.

### Task 5: Extract the First Tiny Shared Utility, Not a Big Package Rewrite

**Files:**
- Modify: one or two scripts with duplicated YAML helpers
- Reuse: `scripts/yaml_helpers.py`
- Test: existing focused tests for the touched scripts

**Interfaces:**
- Consumes: `safe_load_yaml_path` / `safe_load_yaml` from `scripts/yaml_helpers.py`
- Produces: one deleted duplicated YAML helper pattern

- [ ] **Step 1: Pick one duplicated pair**

Recommended first pair: `scripts/initiative_scaffold.py` and `scripts/roadmap_scaffold.py`, because their `_load_yaml`/`_dump_yaml` helpers were identified as byte-for-byte duplicated.

- [ ] **Step 2: Write or identify a focused test before editing**

Run: `python3 -m pytest tests/test_roadmap_scaffold.py tests/test_initiative_scaffold.py -q`

Expected: if either test file does not exist, stop and add the smallest behavior test for the helper path before production edits.

- [ ] **Step 3: Replace only the duplicated helper calls**

Expected: no package restructure, no CLI behavior changes, no broad import changes.

- [ ] **Step 4: Verify focused behavior**

Run the exact focused tests identified in Step 2 plus `python3 -m ruff check <touched-files>`.

Expected: tests pass; touched files lint clean.

### Task 6: Decide What Leaves the Portable Toolkit

**Files:**
- Create: `docs/superpowers/plans/2026-06-23-azoth-scope-separation-brief.md`
- Read: `docs/personal-control-plane/`, `scripts/personal_*`, `scripts/cockpit_*`, `.azoth/campaigns/`, `.azoth/handoffs/`, `.azoth/inbox/`

**Interfaces:**
- Consumes: strategic choice from Task 3
- Produces: a removal/move proposal, not immediate deletion

- [ ] **Step 1: Classify each candidate surface**

Use exactly three labels:

```text
core-toolkit
operator-extension
local-state
```

- [ ] **Step 2: Produce a move/delete proposal**

Expected: no files are deleted in this task. The output is a proposal with risk and migration notes.

- [ ] **Step 3: Human decision gate**

Present options:

```text
1. Move operator-extension files to a separate repo later.
2. Keep them but mark them explicitly non-product.
3. Delete or gitignore local-state surfaces after archival.
```

## Roadmap Maintenance Rules

- Update this file after each task with: status, verification command, residual risk, and next recommended task.
- If new evidence invalidates the sequence, edit this roadmap instead of starting a new undocumented plan.
- Keep each task under 10 changed files. If a task exceeds that, split it and add a note here.
- Do not add new roadmap levels, codenames, phases, or D-numbers for this simplification track unless the human asks.

## Recommended Next Action

Do Task 1 only. Stabilize or revise the current Phase 0 patch before any further simplification work.

## Progress Log

### 2026-06-23 — Task 1 Stabilization Check

Status: reached human decision gate.

Revision decision: human chose option 2, revise before continuing. Phase 0 was narrowed to avoid bundling kernel/install/governance changes with deploy drift prevention.

Revised Phase 0 keeps:
- CI deploy parity check.
- Regenerated stale orchestrator mirrors.
- Deploy-side missing-skill-reference validation and regression tests.

Deferred from Phase 0 into later roadmap tasks:
- Decision-count consistency cleanup.
- `.claude/skills/` platform table cleanup in `AGENTS.md`.
- `kernel/TRUST_HOSTS.md` checksum coverage and installer/kernel-governance updates.

Verification before revision:
- Targeted tests passed: 18 tests.
- Kernel checks and deploy parity passed.

Verification after revision:
- `python3 -m pytest tests/test_azoth_deploy.py::test_agent_outputs_report_missing_skill_references tests/test_azoth_deploy.py::test_canonical_agent_outputs_reference_existing_skills -q` passed: 2 tests.
- `python3 scripts/azoth-deploy.py --check` passed; deploy reports all 277 files in sync.
- `python3 -m ruff check scripts/azoth-deploy.py tests/test_azoth_deploy.py && python3 -m ruff format --check scripts/azoth-deploy.py tests/test_azoth_deploy.py` passed.

Residual repo-wide blockers recorded, not fixed in Task 1:
- `python3 -m pytest -q` fails with 16 failures: orchestrator contract/test mismatch, Codex adapter fixture import failures, legacy `azoth.yaml` platform-shape assumptions, and the ruff-smoke failure.
- `python3 -m ruff check .` fails on unused imports in `tests/test_trust_hosts_contract.py`.
- `python3 -m ruff format --check .` reports 29 pre-existing files needing formatting.

Next decision: keep, revise, or park the current Phase 0 patch before proceeding to Task 2.

### 2026-06-23 — Task 2 Source-of-Truth Inventory

Status: complete.

Created `docs/superpowers/plans/2026-06-23-azoth-source-of-truth-inventory.md` as an index to existing authorities, not a new authority.

Verification:
- `grep -n "Canonical Source\|Generated Mirrors\|Validation Gate" docs/superpowers/plans/2026-06-23-azoth-source-of-truth-inventory.md` found the expected table header.
- Placeholder scan across the three planning artifacts found no placeholder markers.

Next recommended target: decision-count references, because the canonical owner is clear and the fix can be guarded by a small test without choosing the broader platform strategy.

### 2026-06-23 — Decision Count Consistency Cleanup

Status: complete.

Changed:
- Added `tests/test_decisions_index_consistency.py`.
- Aligned decision references to 57 / D1-D57 in `docs/DECISIONS_INDEX.md`, `CLAUDE.md`, and `kernel/templates/platform-adapters/gemini/GEMINI.md.template`.
- Regenerated `GEMINI.md` through `scripts/azoth-deploy.py`.

Verification:
- Red state confirmed first: `tests/test_decisions_index_consistency.py` failed on `D1-D54` while actual decisions ended at D57.
- `python3 -m pytest tests/test_decisions_index_consistency.py -q` passed.
- `python3 scripts/azoth-deploy.py --check` passed; deploy reports all 277 files in sync.
- `python3 -m ruff check tests/test_decisions_index_consistency.py && python3 -m ruff format --check tests/test_decisions_index_consistency.py` passed.

Next recommended target: `.claude/skills/` generated path cleanup or `TRUST_HOSTS.md` checksum coverage. Prefer `.claude/skills/` first because it is non-kernel and smaller.

### 2026-06-23 — AGENTS.md Claude Skills Path Cleanup

Status: complete.

Changed:
- Added `tests/test_agents_md_parity.py::test_claude_code_platform_row_does_not_claim_missing_skills_dir`.
- Updated `scripts/azoth-deploy.py` so the Claude Code platform row no longer advertises `.claude/skills/`.
- Regenerated `AGENTS.md` through `scripts/azoth-deploy.py`.

Verification:
- Red state confirmed first: the new test failed while `AGENTS.md` advertised `.claude/skills/`.
- `python3 -m pytest tests/test_agents_md_parity.py::test_claude_code_platform_row_does_not_claim_missing_skills_dir -q` passed.
- `python3 scripts/azoth-deploy.py --check` passed; deploy reports all 277 files in sync.
- `python3 -m ruff check scripts/azoth-deploy.py tests/test_agents_md_parity.py && python3 -m ruff format --check scripts/azoth-deploy.py tests/test_agents_md_parity.py` passed after formatting `tests/test_agents_md_parity.py`.

Next recommended target: `TRUST_HOSTS.md` checksum coverage, because it is a real Layer 0 coherence issue. Treat it as a separate kernel/governance task with checksum, installer, and tests updated together.

### 2026-06-23 — TRUST_HOSTS.md Checksum Coverage

Status: complete.

Changed:
- Added `kernel/TRUST_HOSTS.md` to `scripts/kernel-integrity.py` checksum coverage.
- Updated `scripts/hermes_manifest_check.py` to check five kernel files.
- Updated `kernel/GOVERNANCE.md` Integrity Check Mechanism to document the five-file root kernel set.
- Updated `install.sh` and `install.ps1` so consumer checksum generation includes `TRUST_HOSTS.md`.
- Updated `.azoth/kernel-checksums.sha256` with the five-file hash set.
- Updated targeted tests for installer, Hermes manifest, kernel contract docs, and kernel integrity.

Verification:
- Red state confirmed first: targeted tests failed because current code checked four files and omitted `TRUST_HOSTS.md`.
- `python3 -m pytest tests/test_install_sh_kernel_checksums.py tests/test_hermes_manifest_check.py tests/test_kernel_contract_doc_consistency.py tests/test_kernel_integrity.py -q` passed: 15 tests.
- `python3 scripts/kernel-integrity.py && python3 scripts/kernel-integrity.py --verify-checksums` passed.
- `python3 -m ruff check scripts/kernel-integrity.py scripts/hermes_manifest_check.py tests/test_install_sh_kernel_checksums.py tests/test_hermes_manifest_check.py tests/test_kernel_contract_doc_consistency.py && python3 -m ruff format --check scripts/kernel-integrity.py scripts/hermes_manifest_check.py tests/test_install_sh_kernel_checksums.py tests/test_hermes_manifest_check.py tests/test_kernel_contract_doc_consistency.py` passed after formatting `tests/test_hermes_manifest_check.py`.

Next recommended target: installer/deployer divergence inventory or a tiny YAML-helper consolidation. Prefer installer/deployer divergence only as a plan/design slice; prefer YAML-helper consolidation for executable code simplification.

### 2026-06-23 — Ruff Lint Hygiene

Status: complete.

Changed:
- Removed unused `pytest` and `yaml` imports from `tests/test_trust_hosts_contract.py`.
- Renamed the best-effort mirrors test/comment to match the current 3 trust-bearing + 5 best-effort host model.

Verification:
- `python3 -m ruff check .` passed.
- `python3 -m pytest tests/test_trust_hosts_contract.py -q` passed: 5 tests.
- `python3 -m ruff format --check tests/test_trust_hosts_contract.py` passed after formatting the file.

Residual repo-wide blocker:
- `python3 -m ruff format --check .` is still expected to report unrelated pre-existing formatting drift across many files unless those are addressed in a dedicated formatting-only slice.

## Self-Review

- Spec coverage: covers simplification, preservation of intent, critique-to-roadmap conversion, and context-rot avoidance.
- Placeholder scan: no placeholder markers are present.
- Type consistency: roadmap uses existing commands and file paths only; new files are planning artifacts under `docs/superpowers/plans/`.

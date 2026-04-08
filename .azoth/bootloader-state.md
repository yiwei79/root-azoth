# Bootloader State

Last updated: 2026-04-09 (session closeout ep-095 — eval-swarm + extract follow-up)

## Current Phase

Phase 7 — Publishing & public product  
**Toolkit version:** **0.0.7.6** (`azoth.yaml`) · **Roadmap:** `active_version: v0.0.7` · **current_patch:** **6** (`.azoth/roadmap.yaml`, D53)

## Session outcome (ep-095) — session-closeout

- **Delivered / refined:** **`/eval-swarm`** Wave C on extract + license + governance (0.90); extract **FAIL** then **Wave D** (`.git/` guard, tests, `--out` help) + **re-eval PASS**; **follow-up** **`test_extract_removes_pre_existing_out_directory`**, module doc + **destructive `--out`** argparse text (**staging / rsync**). **`AZOTH_VERSION`** in **`.claude/settings.json`** synced **0.0.7.6** (**BL-018**).
- **Closeout:** W1 **ep-095**; W2 bootloader + scope gate closed; W3 Claude memory (attempt); W4 patch **0.0.7.5 → 0.0.7.6**; **M3** **episodes: 95**.
- **Next:** **`git push`** **`origin`** **`phase-7-v0.0.7-publishing`**; **`/intake`** for **3** queued inbox JSONL; **`/next`** for post–Phase 7 scope; merge **PR #6** when CI green.

## Session outcome (ep-094) — session-closeout

- **Delivered / refined:** **GitHub PR #6** metadata aligned with full Phase 7 branch; **ready for review**; **`@copilot`** review comment; **D32** inbox — `.azoth/inbox/cursor-review-2026-04-08.jsonl` (appended) + **`.azoth/inbox/pr-code-review-pr6-phase7-2026-04-08.jsonl`**. **`azoth_extract_product.py`** — defense-in-depth **never copy `.git/`** even if `exclude_paths` misconfigured; **`test_copy_tree_always_skips_dot_git`** + minimal-tree assertion; **`--out` help** documents rmtree behavior.
- **Closeout:** W1 **ep-094**; W2 bootloader + scope gate closed; W3 Claude memory (attempt); W4 patch **0.0.7.4 → 0.0.7.5**; **M3** **episodes: 94**.
- **Next:** **`git push`** **`origin`** **`phase-7-v0.0.7-publishing`** (closeout commit + prior **35be673** if not pushed); **`/next`** for post–Phase 7 scope; **`/intake`** for **3** queued inbox JSONL; merge **PR #6** when CI green.

## Session outcome (ep-093) — session-closeout

- **Delivered / refined:** **P4-004** **complete** — public **`yiwei79/azoth`** populated via **`azoth_extract_product.py`** + staging rsync; **`sync-config.yaml`** excludes **`.git/`**; **PolyForm Noncommercial 1.0.0** `LICENSE` + docs/README alignment + public README license block; **`kernel/templates/README.public.azoth.md`** for future extracts.
- **Closeout:** W1 **ep-093**; W2 bootloader + scope gate closed; W3 Claude memory (attempt); W4 patch **0.0.7.3 → 0.0.7.4**; **BL-018** settings **`AZOTH_VERSION`** synced; **M3** **episodes: 93**.
- **Next:** **`git push`** **`origin`** (branch **`phase-7-v0.0.7-publishing`**); **`/next`** for post–Phase 7 scope; **`/intake`** if inbox queued; verify **public** GitHub Actions on **`main`**.

## Session outcome (ep-092) — session-closeout

- **Delivered / refined:** **`/eval-swarm`** command; **`/eval`** intelligent routing **E1–E6**; **`/auto`** Execution §6 + **`/deliver`** / **`/deliver-full`** eval–swarm wiring; **`tests/test_eval_pipeline_wiring.py`**; **`/intake`** — inbox empty (nothing to triage). **`python3 scripts/azoth-deploy.py`** after command edits.
- **Closeout:** W1 **ep-092**; W2 bootloader + scope gate closed; W3 Claude memory (deferred in Cursor — mirror manually if needed); W4 patch **0.0.6.8 → 0.0.6.9**; **M3** **episodes: 92**.
- **Next:** **`git push`** **`origin main`**; **`/next`** when backlog seeded; **`/promote`** for M2 candidates if any.

## Session outcome (ep-090) — BL-024–BL-026

- **Delivered:** **BL-024** — `/session-closeout` W2 field checklist + W2b (post-W4 refresh) in `.claude/commands/session-closeout.md`; **`azoth-deploy`** mirrors (Copilot/OpenCode prompts). **BL-025** — `tests/test_governance_never_auto_parity.py` (GOVERNANCE §5 Never-Auto vs `UNIVERSAL_NEVER_AUTO`). **BL-026** — `install.sh` Step 7 explicit four-file §4 order; `tests/test_install_sh_kernel_checksums.py`.
- **Swarm:** parallel architect wave (prior session) + parallel **reviewer** verification wave on acceptance criteria.
- **Next:** **`/next`** for next backlog row; **`/intake`** if inbox queued.

## Session outcome (ep-088) — session-closeout

- **Delivered / refined:** **`main`** merged **`patch/bl-023-azoth-deploy-parity`** (**`78be4fa`**) — backlog deliveries **BL-018**–**BL-023** on default branch (settings sync, pip/requirements-dev, runtime gate JSON policy, DAY0 + UTF-8 + session-state example, roadmap dashboard hardening, **D46** deploy parity tests). **`python3 scripts/azoth-deploy.py`** — 84 files reported written; **working tree clean** (mirrors already matched).
- **Closeout:** W1 **ep-088**; W2 bootloader + session-state; W3 Claude memory (attempt); W4 patch **0.0.6.7 → 0.0.6.8**; **M3** **episodes: 88**.
- **Next:** **`git push`** **`origin main`**; **`/next`** **BL-024** (bootloader alignment on closeout); **`/intake`** if new inbox lines.

## Session outcome (ep-086) — session-closeout

- **Delivered / refined:** **Copilot PR workflow** — `.github/pull_request_template.md`, `.github/copilot-instructions.md`, `tests/test_github_pr_template.py`. **Cursor review → inbox** — `skills/cursor-review-insights/SKILL.md`, `.claude/commands/review-insights.md`, `kernel/templates/platform-adapters/cursor/code-review-insights.mdc.template` → `.cursor/rules/code-review-insights.mdc`; **`.azoth/trusted-sources.yaml`** `cursor-review`; `README.md` / **`CLAUDE.md`** skill index; **`azoth.yaml`** skills **14**; **`tests/test_skills.py`**, **`tests/test_cursor_adapter_templates.py`**, **`tests/test_cursor_review_insights.py`**. **`azoth-deploy`** (84 files). PR **#5** created; Copilot inbox comment posted earlier in session.
- **Closeout:** W1 **ep-086**; W2 bootloader + session-state; W3 Claude memory (attempt); W4 patch **0.0.6.6 → 0.0.6.7**; **M3** **episodes: 86**.
- **Next:** **`/intake`** queued insights (inbox + any Copilot/Cursor JSONL); merge **PR #5** when CI green; continue **Phase 7** planning when ready.

## Session outcome (ep-085) — session-closeout

- **Delivered / refined:** **BL-017** **complete** — `scripts/kernel-integrity.py` (D2 on `kernel/*.md`; `--verify-checksums` for GOVERNANCE §4); **`.azoth/kernel-checksums.sha256`** committed; **`.gitignore`** documents golden manifest; **`.github/workflows/ci.yml`** (ruff stack, kernel-integrity, pytest); **`tests/test_kernel_integrity.py`**; **`tests/test_ruff_smoke.py`** includes new script; B2 xfail removed. **`azoth-deploy`** dry-run verified (80 files); live deploy no-op (already synced). Git **`084f722`**.
- **Closeout:** W1 **ep-085**; W2 bootloader + scope gate **closed** (`approved: false`, `closed_at`); W3 Claude memory (attempt); W4 patch **0.0.6.5 → 0.0.6.6**; **M3** **episodes: 85**.
- **Next:** **`/intake`** inbox (**5** JSONL in **`.azoth/inbox/`**, excluding **`processed/`**); plan **Phase 7** (**v0.0.7**) / **P4-003**–**P4-004** when ready; add backlog rows if **`/next`** should surface new work.

## Session outcome (ep-084) — session-closeout

- **Delivered / refined:** **P6-003** **complete** (governed `/auto`): `pipelines/architecture-proposal.schema.yaml`, `scripts/architecture_proposal_validate.py`, `/arch-proposal` (mixed, Cursor parity, Task + `prior_stage_summaries`), pytest suite, `.gitignore` + installers for `.azoth/proposals/`, architect cue, orientation, `azoth-deploy`. Reviewer **request-changes** cleared via human **revise-then-continue** + revision architect pass before planner. **P6-003-OPT** **complete** (standard): architect → reviewer **approve** → evaluator plan PASS → builder → evaluator post PASS; **`/next` step 8b** read-only proposal footer (scope-gate + `.azoth/proposals/*.yaml`); **`docs/AZOTH_ARCHITECTURE.md`** D25 + **`/arch-proposal`** row; **`docs/DECISIONS_INDEX.md`** D25 nuance; **`pyproject.toml`** `[tool.ruff]`; **`tests/test_next_arch_proposal_footer.py`**, **`tests/test_ruff_smoke.py`**; removed **stale expired** **`pipeline-gate.json`**.
- **Closeout:** W1 **ep-084**; W2 bootloader + scope gate **closed** (`approved: false`, `closed_at`); W3 Claude **project_status.md** mirror; W4 patch **0.0.6.4 → 0.0.6.5**; **M3** **episodes: 84**.
- **Next:** **`/next`** **BL-017**; **`/intake`** inbox (**5** JSONL in **`.azoth/inbox/`**, excluding **`processed/`**).

## Session outcome (ep-083) — session-closeout

- **Delivered / refined:** **P6-002** **complete** — L2 evidence **JSONL** (`pipelines/l2-evidence-record.schema.yaml`), **`scripts/l2_evidence_validate.py`**, **`l2_evidence_append.py`** (scope + pipeline gates), **pytest**, **`.gitignore`** for store; **skills** (prompt-engineer, agentic-eval, self-improve, auto-router, subagent-router), **`agents/tier3-meta/prompt-engineer.agent.md`** `pipeline_stages`, **`.claude/commands/eval.md`**; **`azoth-deploy`**. **Tests:** `test_phase_consistent` cross-checks **roadmap `current_phase`**; **`test_azoth_checkpoint`** `git init -b main` + skip. **Backlog:** **BL-017** (GOV-B2 **`scripts/kernel-integrity.py`**); xfail reason points to BL-017. **Skill frontmatter:** repaired **`## name:`** corruption on multiple **`SKILL.md`** files (was blocking deploy).
- **Closeout:** W1 **ep-083**; W2 bootloader + scope/pipeline gates **closed**; W3 Claude memory (attempt); W4 patch **0.0.6.3 → 0.0.6.4**; **M3** **episodes: 83**.
- **Next:** **`/next`** **P6-003** or **BL-017**; **`/intake`** inbox (**5** JSONL in **`.azoth/inbox/`**, excluding **`processed/`**).

## Session outcome (ep-082) — session-closeout

- **Delivered / refined:** **Roadmap** — **Phase 7** (**v0.0.7** backlog) holds **P4-003/P4-004** publishing; **v0.0.6** meta-only (**P6-001–003**). **version-bump.py** — `--phase` from **v0.0.6→v0.0.7**; **`--release`** requires **v0.0.7**; tests updated. **welcome.py** — phase strip **[7] Publish**. **Backlog** — **P6-001–003** seeded; **P6-001** **complete** (Agent Crafter meta-loop hardening: `agents/tier3-meta/agent-crafter.agent.md`, `docs/AZOTH_ARCHITECTURE.md`, `skills/subagent-router`, `tests/test_agents.py`, `azoth-deploy`). **Evaluator** — PASS threshold **0.85** (evaluator agent, `skills/agentic-eval`, `/eval`, patterns, `pipeline.template`). **subagent-router** — repaired broken YAML frontmatter (`## name:` → valid `---` block) that blocked **azoth-deploy**.
- **Closeout:** W1 **ep-082**; W2 bootloader + scope/pipeline gates **closed**; W3 Claude memory (attempt); W4 **patch** bump.
- **M3:** **ep-082** appended (`episodes: 82`).
- **Next:** **`/next`** for **P6-002** or **P6-003**; **`/intake`** inbox (**5** JSONL in `.azoth/inbox/`, excluding **processed/**).

## Session outcome (ep-081) — session-closeout

- **Delivered / refined:** **P5→P6** phase advance (**D53**): `scripts/version-bump.py` **--phase** with **backlog→active** activation for next version slice; **v0.0.5** **complete** **final_patch** **14**; **v0.0.6** **active**; **azoth.yaml** **phase** **6**; legacy **current_phase** / **orientation** / **CLAUDE.md** / **tests** / **azoth-deploy**; scope gate opened then **closed** this closeout. **UX:** user meant **closeout** when saying **option 2** after a separate earlier **option 2** (phase close)—**ordinal reuse** across menus; captured **ep-081** + **`skills/self-improve`** note.
- **Closeout:** W1 **ep-081**; W2 bootloader + scope gate **`closed_at`**; W3 Claude Code **project_status** mirror; W4 patch **0.0.6.1 → 0.0.6.2**.
- **M3:** **ep-081** appended (`episodes: 81`).
- **Next:** Seed **`.azoth/backlog.yaml`** from roadmap **P6-001…P6-003** / **P4-003** / **P4-004** so **`/next`** can run; **`/intake`** for inbox (**5** queued files, see closeout).

## Session outcome (ep-080) — session-closeout

- **Delivered / refined:** **P5-006** deferred to **v0.2.0** (post–**v0.1.0**): backlog `status: deferred` + `target_version`; roadmap **v0.2.0** bucket added; P5-006 removed from v0.0.5/v0.0.6 slices; `scripts/welcome.py` + **`/next`** exclude `deferred`; `tests/test_welcome.py::test_filter_excludes_deferred`; scope gate closed; session-state/bootloader pointers. Earlier in session: `/start`, `/next` + approval for P5-006, `/auto` declaration only (not executed).
- **Closeout:** W1 **ep-080**; W2 bootloader + scope gate **`closed_at`** refresh; W3 Claude Code memory mirror (attempt); W4 patch **0.0.5.13 → 0.0.5.14**.
- **M3:** **ep-080** appended (`episodes: 80`).
- **Next:** v0.0.5 Phase 5 backlog has **no pending** items (P5-006 is deferred past v0.1.0). Plan **phase close / v0.0.6** work, **`/intake`** for inbox, or add new backlog. **`/next`** returns no candidates until new items.

## Session outcome (ep-079) — session-closeout

- **Delivered / refined:** **P5-005** (D15) — `scripts/azoth_checkpoint.py` (create / tag / list), `tests/test_azoth_checkpoint.py`, `kernel/TRUST_CONTRACT.md` §4 (human-invoked checkpoints), `.claude/hooks/entropy_check.py` RED recovery hint, `skills/entropy-guard` + `azoth-deploy`; backlog **P5-005** **complete**; deliver-full mid-session **0.0.5.11 → 0.0.5.12**; evaluator **PASS** 0.88; follow-ups — **lightweight tag** wording, `tag`/`list` tests, `tag` subparser `description=` for Python 3.9 `--help`.
- **Closeout:** W1 **ep-079**; W2 bootloader + **scope gate closed** (`approved: false`, `closed_at`); W3 Claude Code memory mirror (attempt); W4 patch bump **0.0.5.12 → 0.0.5.13**.
- **M3:** **ep-079** appended (`episodes: 79`).
- **Next:** **`/next`** for **P5-006**; **`/intake`** for inbox queue.

## Session outcome (ep-078) — session-closeout

- **Delivered / refined:** P5-004 telemetry hardening (`session_telemetry.py` never-raise contract, `_safe_seq` / `_read_seq_state`); evaluator re-run **PASS** 0.91; follow-up docs — `kernel/GOVERNANCE.md` §6 outcome vocabulary, `docs/AZOTH_ARCHITECTURE.md` §9, `skills/entropy-guard`, module docstring; test `telemetry_seq` rewrite after corrupt read; `azoth-deploy`. Episodes **ep-076** (scope-goal binding), **ep-077** (initial P5-004 delivery) precede this closeout slice.
- **Closeout:** W1 **ep-078**; W2 bootloader + **scope gate closed** (`approved: false`, `closed_at`); W3 Claude Code memory mirror (attempt); W4 patch bump **0.0.5.10 → 0.0.5.11**.
- **M3:** **ep-078** appended (`episodes: 78`).
- **Next:** **`/next`** for **P5-005** or **P5-006**; **`/intake`** for inbox queue.

## Session outcome (ep-075) — session-closeout

- **Delivered / refined:** P5-007 SessionStart path (`session_start_welcome.py`, settings, tests), welcome plain + file mirror, policy for **Bash Rich** (expand) and **Cursor integrated terminal** for full ANSI/Rich; `CLAUDE.md` rules 8–9; kernel/cursor templates; orientation skill; `start.md`; README; architecture/decisions index where touched; `azoth-deploy` parity.
- **Closeout:** W1 **ep-075**; W2 bootloader + **scope gate closed** (`approved: false`, `closed_at`); W3 Claude Code memory mirror; W4 patch bump **0.0.5.9 → 0.0.5.10**.
- **M3:** **ep-075** appended (`episodes: 75`).
- **Next:** **`/next`** for new scope before governed M1 writes; **`/intake`** for inbox queue; Rich welcome: **Terminal** panel, not agent chat widget.

## Session outcome (ep-074) — session-closeout

- **Closeout:** Part A evaluation (Phase 5 alignment, tests, kernel untouched, decisions count 53); W1 **ep-074**; W2 bootloader refresh, scope gate remains **closed** (`approved: false`); W3 Claude Code memory — see log below; W4 **`0.0.5.8 → 0.0.5.9`**. Part D: **5** insight files queued in `.azoth/inbox/` (run **`/intake`**; do not triage during closeout).
- **M3:** **ep-074** appended (`episodes: 74`).
- **Next:** **`/next`** for **P5-007** or **P5-004**; **`/intake`** for inbox queue.

## Session outcome (ep-073)

- **Delivered:** P5-003 — `stage_summary_validate.py`, `alignment_summary_gate.py` (`evaluate_alignment_handoff`), orchestrator integration **after** scope allow **before** entropy; `.azoth/handoffs/` convention; `tests/test_p5_003_alignment_summary_gate.py` (gate + orchestrator + Edit edge cases + relative path + malformed stdin); `docs/AZOTH_ARCHITECTURE.md` (P5-003); `kernel/templates/platform-adapters/cursor/claude-code-parity.mdc.template` + deploy; **evaluator** rubric **PASS** 0.92. Backlog **P5-003** **complete**.
- **Pipeline:** `/deliver-full` — Goal Clarification → Architect → Governance Review → Planner → Test Builder → Builder → Step 7 + `version-bump.py --patch`.
- **M3:** **ep-073** appended.
- **Scope gate:** **closed** (`approved: false`, `closed_at` set) — run **`/next`** before the next scoped write session.
- **W4 (delivery):** `0.0.5.7 → 0.0.5.8`.

## Session outcome (ep-072) — historical snapshot

- **Delivered:** P5-002 — PreToolUse orchestrator (scope then entropy), entropy_state/check, tests; relative hook paths; AZOTH_ARCHITECTURE; **M2** pattern evaluator-subagent. Backlog **P5-002** **complete**.
- **W4:** `0.0.5.6 → 0.0.5.7`.

## Open decisions

- **Phase 7 wrap:** v0.1.0 readiness, extraction cadence, and public-repo hygiene (Actions on **`yiwei79/azoth`**).
- **settings.json.template** deny list for `.azoth/kernel/**` (optional consumer hardening) still open in orientation.
- **D43 remainder:** optional commit-format rules beyond Co-Authored-By (human sign-off before expansion).

## Next action

**Phase 7 (v0.0.7)** — **`P4-003`** / **`P4-004`** **complete**. **`git push`** **`phase-7-v0.0.7-publishing`**; **`/intake`** — **3** JSONL in **`.azoth/inbox/`** (cursor-review + pr-code-review); **`/next`** toward **v0.1.0** when ready. **P5-006** **deferred** **v0.2.0**.

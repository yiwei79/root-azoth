# AZOTH — The Universal Agentic Toolkit

> *"Be water, my friend."* — Azoth is the alchemist's universal solvent:
> it dissolves into any project and transforms how agents work within it.

## What Is Azoth

**root-azoth** (private) is the personal root scaffold and development
workshop for the Azoth toolkit. This repo is where the toolkit is designed,
built, tested, and evolved. It is NOT a consumer project — it IS the source.

The public deployable product **azoth** (lowercase) will be mechanically
extracted from this scaffold via `sync-config.yaml` product extraction profiles.
See `docs/AZOTH_ARCHITECTURE.md` Section 18 for the 3-tier product flow and
the 4-plane operating model used by the personal cockpit and controlled
project repos.

**As a toolkit**: A personal "drop-and-start" agentic toolkit for AI-assisted
development. You clone it, run the installer, and any project gets: disciplined
agents, auto-improving memory, trusted autonomous pipelines, and a single human
alignment point.

**Version**: v0.1.4.0
**Primary platform**: Claude Code (CLI + VS Code extension)
**Also compatible**: Codex (skill-routed via `.codex/` + `.agents/skills/azoth-*` adapters), OpenCode (reads CLAUDE.md natively), GitHub Copilot (via adapter)
**License**: [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — source-available; commercial use requires a separate written license from the copyright holder (see `LICENSE`).

## Project Routing

| Area | Path | Purpose |
|------|------|---------|
| Kernel (scaffold) | `kernel/` | Layer 0 — authoritative in this repo |
| Kernel (consumer) | `.azoth/kernel/` | Read-only copy after install (D42 — see architecture §18) |
| Skills | `skills/` | Layer 1 — portable capabilities |
| Agents | `agents/` | Layer 2 — agent archetypes |
| Pipelines | `pipelines/` | Layer 3 — orchestration templates |
| Scaffold | `scaffold/` | Coded agent/swarm templates |
| Docs | `docs/` | Architecture, ADRs, design |
| Scripts | `scripts/` | Automation (sync, validate, install) |
| Tests | `tests/` | Drift detection, kernel integrity |
| Platform adapters | `kernel/templates/platform-adapters/` | Per-platform file templates |

## Architecture Reference

Full architecture: `docs/AZOTH_ARCHITECTURE.md` (57 decisions, 4 layers, all components).

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
M1: PROCEDURAL ─ `kernel/` + skills/ + agents/ in scaffold; `.azoth/kernel/` is the governance read path in consumer installs (D42)
```

## Development Instructions

### Core Rules

1. **Quality > speed**. Every output passes evaluation before delivery. No AI slop.
2. **Kernel immutability**. Files in `kernel/` change ONLY via human-approved promotion.
3. **Cross-platform**. All scripts in Python (not PowerShell). Paths via `pathlib`.
4. **macOS primary, Windows validated**. Test on macOS first, verify Windows compat.
5. **Claude Code primary**. `.claude/` is the development surface. Other platforms via adapters.
6. **Architecture-first**. Read `docs/AZOTH_ARCHITECTURE.md` before making structural changes.
7. **Effect labels**. Every `.claude/commands/*.md` file declares `azoth_effect: read | write | mixed` in its frontmatter (`kernel/GOVERNANCE.md`). If a prompt can trigger **Write/Edit** (build path), it must be clearly marked — never hide implementation behind read-only wording.
8. **Cursor (Claude)**: Enable Settings → Rules → third-party plugin configs; run `python3 scripts/azoth-deploy.py` (includes `--platforms cursor`) after changing `kernel/templates/platform-adapters/cursor/*.mdc.template` so `.cursor/rules/` stays coupled. Hooks do not run in Cursor; parity rules simulate scope/pipeline gates. For delivery pipelines (`/auto`, `/autonomous-auto`, `/dynamic-full-auto`, `/deliver`, `/deliver-full`), use the **`Task`** tool with `subagent_type` matching each stage per `skills/subagent-router/SKILL.md` — do not inline all stages in main chat when `Task` is available. See `docs/AZOTH_ARCHITECTURE.md` Cursor parity. **Rich welcome UI in Cursor:** run `python3 scripts/welcome.py` in the **integrated terminal** (Terminal panel) for the full designed layout (ANSI colors, box drawing). **Bash** tool output for the same command may appear collapsed—**expand** the block to see the Rich layout in chat.
   **Codex:** Azoth's custom command UX in Codex is skill-routed. In the **Codex app**, enabled `azoth-*` skills can appear in the slash list. In **Codex CLI/IDE**, use `/skills` or `$azoth-auto`, `$azoth-next`, `$azoth-start`, etc.; the generated `.agents/skills/azoth-*` wrappers are the discoverable command surface there. Raw `/auto`-style tokens are a compatibility fallback only. The default Codex adapter is **instruction-first, skill-routed**, with a single narrow `UserPromptSubmit` compatibility hook; governance and non-Bash tool discipline remain behavioral in `.codex/config.toml`.
9. **SessionStart orientation (Claude Code):** `hooks.SessionStart` runs **`.claude/hooks/session_start_welcome.py`**, which invokes **`welcome.py --plain`** with correct repo `cwd`, mirrors stdout to **`.azoth/session-orientation.txt`** (gitignored), and **injects** the same text into model context. Treat that as the **single mechanical source**; avoid duplicating the full blob with **`Read`** unless the user needs verbatim output in chat.
   - **Default (token-efficient):** Use the injected SessionStart text as-is. Short proactive routing (e.g. “try `/next` for P5-004”) is **OK** without re-pasting the entire dashboard.
   - **Verbatim in chat:** When the user asks for the **full** snapshot, **verbatim** orientation, or **paste the file**, then **`Read` `.azoth/session-orientation.txt`** and put the **entire file** in one fenced code block — **or** quote the injected block exactly. **Do not** answer those requests with only a bullet summary.
   - **Rich UI via Bash:** **Bash** to run `python3 scripts/welcome.py` (no `--plain`) is **allowed** when the user wants the **designed Rich dashboard** in the IDE tool surface. Output may appear **collapsed or summarized** at first; **expand** the Bash output to see the full layout (panels, colors, spacing). For **plain-text** facts in chat without re-running, use **`Read`** of `.azoth/session-orientation.txt` or the injected SessionStart text.
   - **Cursor — Rich UI:** SessionStart does not run. For the **full Rich dashboard** as the UI was designed, run `python3 scripts/welcome.py` in Cursor’s **integrated terminal** (renders ANSI/Rich correctly). **Bash** in chat is an alternative—**expand** tool output if collapsed. Plain snapshot: **`Read`** `.azoth/session-orientation.txt` (if present) or `welcome.py --plain`.
   - **Token efficiency:** Prefer **injected** SessionStart text for the model when nothing new is needed; avoid redundant Bash runs when the same facts are already in context unless the user wants the Rich view.

10. **Orchestrator as default session persona (Claude Code and Copilot):** In freeform chat — any message that is not a pipeline slash command and does not arrive via a BL-011 spawn contract — treat the **Orchestrator** (`agents/tier1-core/orchestrator.agent.md`) as the active session persona: classify goal intent, apply pipeline conventions, and manage scope before responding.
   - **Yield to `agent:` frontmatter:** When a slash command (e.g. `/auto`, `/deliver`, `/deliver-full`) is invoked, the command's `agent:` field governs the active persona. Do not re-impose orchestrator classification on top of an already-bound command handler.
   - **Yield to BL-011 spawn contracts:** When this session was spawned by an upstream orchestrator via a BL-011 contract, the `role_hint` in that contract governs (e.g. `planner`, `builder`, `evaluator`). Suppress orchestrator persona and fulfil the assigned subagent role instead.
   - **No overhead on direct coding requests:** If the user's intent is unambiguously a direct coding or implementation request (e.g. "fix this function", "explain this error", "write a unit test"), skip pipeline classification and respond directly. The orchestrator persona governs goal-level navigation and pipeline entry — not routine code assistance.
   - **Gray-zone requests (ambiguous scope):** When intent falls between clearly direct and clearly multi-stage — e.g. "improve this function" (one-line rename or cross-file refactor?), or "update the auth module" (targeted patch or unknown blast radius?) — apply the Goal Clarification protocol: ask one focused question to resolve scope before acting. Default to **Orchestrate** if scope remains unclear after one clarification. See `agents/tier1-core/orchestrator.agent.md` §Goal Clarification.
   - **Normative source:** `agents/tier1-core/orchestrator.agent.md`; platform binding details in `docs/platform-guides/orchestrator-default-entry.md`.
11. **BL-051 human-facing response style.**
   - Default to paragraph-led, information-dense explanations for human-facing non-operational responses; use bullets only when the content is inherently list-shaped.
   - Use contrastive reasoning to make tradeoffs explicit instead of presenting disconnected facts in human-facing explanations.
   - Preserve terse operational modes for status updates, approvals, gates, and explicit short-output requests.
   - Keep agent-to-agent artifacts optimized for determinism and parseability, including BL-011 spawn payloads, BL-012 stage summaries, evaluator scorecards, planner task tables, reviewer findings blocks, and schema-bound YAML/JSON/TOML outputs.

### Karpathy Behavioral Layer

1. **Think Before Coding.** Discover before editing: read the relevant files, map the local context, and use `context-map` when the blast radius is unclear before changing anything.
2. **Simplicity First.** Choose the smallest sufficient solution that satisfies the approved goal; do not add speculative abstraction, extra layers, or just-in-case machinery.
3. **Surgical Changes.** Keep diffs minimal, local, and reversible. Preserve unrelated work, limit blast radius, and touch adjacent files only when the approved scope or validation truly requires it.
4. **Goal-Driven Execution.** Work backward from the approved goal and concrete validation checks. Use lightweight plans for non-trivial work, verify the result, and use bounded replay only at the lowest legitimate corrective stage when review finds a real gap.

### Development Workflow

1. Read this file, then `docs/AZOTH_ARCHITECTURE.md` for structural work (including **Long-running sessions (P1-005)** when scope may span waves or TTL).
2. For **phase / roadmap / sprint alignment**, read `skills/orientation/SKILL.md` (lazy-loaded).
3. Work within approved scope; validate against D1–D53; capture durable lessons in `.azoth/memory/episodes.jsonl`.

### Skill index (drift checks)

`context-map`, `structured-autonomy-plan`, `agentic-eval`, `remember`, `prompt-engineer`, `entropy-guard`, `alignment-sync`, `self-improve`, `subagent-router`, `auto-router`, `autonomous-auto`, `stage6-rubric`, `context-recall`, `cursor-review-insights`, `dynamic-full-auto`, `orientation`

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

#### Branch Model (D54)

Two permanent branches; all other branches are short-lived:

```
main                  ← stable releases only (tagged on squash-merge from phase branch)
phase/v0.2.0-p4       ← active integration branch; receives all merges for current phase
  └── patch/<bl-id>   ← one branch per backlog item; deleted immediately after merge
  └── feat/<slug>     ← ad-hoc feature work; deleted immediately after merge
```

Rules:
- **Never commit directly to `main`** — it only receives squash-merges from a completed
  phase branch, accompanied by a version tag.
- **One active phase branch at a time** — when a phase closes, the phase branch merges to
  `main` and is deleted; the next phase opens a new `phase/v0.2.0-pN` branch.
- **Short-lived feature/patch branches** — open on scope approval, merge (or squash) within
  the same session or next, delete immediately. Never let stale branches accumulate.
- **Merge with `--no-ff`** into the phase branch to preserve feature history.
- **Tag phases** with `git tag v0.2.0-p3-close` before the squash to `main` (user-confirmed,
  never auto-pushed).

#### Worktree Policy (D54)

The scope gate, run-ledger write claim, and deploy hooks are all repo-root-relative —
multiple worktrees create mechanical conflicts. Default: **zero worktrees**.

- **Normal BL work**: single checkout, switch branches with `git checkout`.
- **Parallel exploratory sessions**: `git stash` + branch switch, not a worktree.
- **Genuinely parallel builds** (e.g. testing platform X while implementing Y): a worktree
  is acceptable, but the writer token stays singleton across sibling worktrees. Azoth now
  coordinates that lease through a shared cross-worktree claim keyed by the repo's git
  common-dir and mirrored into each local `.azoth/run-ledger.local.yaml`. In practice:
  one worktree may hold the live write claim, while other worktrees should stay in
  discovery/review mode until the claim is released or handed off; close the worktree
  before `/session-closeout`.
- **Worktrees must be closed before closeout** — the `/worktree-sync` skill handles the
  checkpoint; the `.claude/worktrees/` registry tracks open ones.

#### Merge Hygiene (D54)

- **Run `azoth-deploy.py` before committing after any merge** — the pre-commit hook
  enforces mirror parity; running it manually avoids the abort-fix-recommit cycle.
- **State file conflict resolution order** (`.azoth/`, `azoth.yaml`, `.claude/settings.json`):
  1. Version numbers: keep the higher value (HEAD wins on the destination branch).
  2. Backlog/decisions state: keep HEAD (destination branch has the authoritative record).
  3. `episodes.jsonl`: append-merge all new episodes from both sides, sorted by ID.
  4. `bootloader-state.md`: keep HEAD; add a merge note if session context from the
     incoming branch is worth recording.
- **Stale branch audit**: after any merge, run `git branch --merged <phase-branch>` and
  delete anything that appears (except `main` and the phase branch itself).

## Orientation & roadmap

**Current phase:** Phase 4 (milestone **v0.2.0**); **v0.1.0** shipped (historical Phases 1–7 on the pre-1.0 roadmap). Roadmap `active_version: v0.2.0-p4` for the stabilization, rollout, product extraction, and personal control-plane deployment slice under the `v0.2.0` milestone. Phase 3 is closed after the autonomous-auto campaign reached Green with T-033. See **`skills/orientation/SKILL.md`** for expanded workflow (load on demand).

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

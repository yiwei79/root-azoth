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

**Version**: v0.0.6.3
**Primary platform**: Claude Code (CLI + VS Code extension)
**Also compatible**: OpenCode (reads CLAUDE.md natively), GitHub Copilot (via adapter)
**License**: MIT

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
8. **Cursor (Claude)**: Enable Settings → Rules → third-party plugin configs; run `python3 scripts/azoth-deploy.py` (includes `--platforms cursor`) after changing `kernel/templates/platform-adapters/cursor/*.mdc.template` so `.cursor/rules/` stays coupled. Hooks do not run in Cursor; parity rules simulate scope/pipeline gates. For delivery pipelines (`/auto`, `/deliver`, `/deliver-full`), use the **`Task`** tool with `subagent_type` matching each stage per `skills/subagent-router/SKILL.md` — do not inline all stages in main chat when `Task` is available. See `docs/AZOTH_ARCHITECTURE.md` Cursor parity. **Rich welcome UI in Cursor:** run `python3 scripts/welcome.py` in the **integrated terminal** (Terminal panel) for the full designed layout (ANSI colors, box drawing). **Bash** tool output for the same command may appear collapsed—**expand** the block to see the Rich layout in chat.
9. **SessionStart orientation (Claude Code):** `hooks.SessionStart` runs **`.claude/hooks/session_start_welcome.py`**, which invokes **`welcome.py --plain`** with correct repo `cwd`, mirrors stdout to **`.azoth/session-orientation.txt`** (gitignored), and **injects** the same text into model context. Treat that as the **single mechanical source**; avoid duplicating the full blob with **`Read`** unless the user needs verbatim output in chat.
   - **Default (token-efficient):** Use the injected SessionStart text as-is. Short proactive routing (e.g. “try `/next` for P5-004”) is **OK** without re-pasting the entire dashboard.
   - **Verbatim in chat:** When the user asks for the **full** snapshot, **verbatim** orientation, or **paste the file**, then **`Read` `.azoth/session-orientation.txt`** and put the **entire file** in one fenced code block — **or** quote the injected block exactly. **Do not** answer those requests with only a bullet summary.
   - **Rich UI via Bash:** **Bash** to run `python3 scripts/welcome.py` (no `--plain`) is **allowed** when the user wants the **designed Rich dashboard** in the IDE tool surface. Output may appear **collapsed or summarized** at first; **expand** the Bash output to see the full layout (panels, colors, spacing). For **plain-text** facts in chat without re-running, use **`Read`** of `.azoth/session-orientation.txt` or the injected SessionStart text.
   - **Cursor — Rich UI:** SessionStart does not run. For the **full Rich dashboard** as the UI was designed, run `python3 scripts/welcome.py` in Cursor’s **integrated terminal** (renders ANSI/Rich correctly). **Bash** in chat is an alternative—**expand** tool output if collapsed. Plain snapshot: **`Read`** `.azoth/session-orientation.txt` (if present) or `welcome.py --plain`.
   - **Token efficiency:** Prefer **injected** SessionStart text for the model when nothing new is needed; avoid redundant Bash runs when the same facts are already in context unless the user wants the Rich view.

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

**Current phase:** Phase 6 (Meta-Recursive); Phase 7 (publishing / public product) follows before v0.1.0. **Release target:** v0.1.0 — full phase checklist,
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

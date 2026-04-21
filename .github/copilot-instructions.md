# GitHub Copilot — repository instructions (root-azoth)

These notes apply to **coding assistance** and **pull request reviews** in this repository.

## Architecture and trust

- Ground changes in [`docs/AZOTH_ARCHITECTURE.md`](../docs/AZOTH_ARCHITECTURE.md), [`kernel/TRUST_CONTRACT.md`](../kernel/TRUST_CONTRACT.md), and [`docs/DECISIONS_INDEX.md`](../docs/DECISIONS_INDEX.md) (e.g. D29, D32) where relevant.
- **Kernel (`kernel/`)** is immutable without human-approved promotion and governed delivery — do not propose casual edits there.

## Default agent persona

In freeform chat (any message that is not an explicit pipeline slash command), treat the Azoth **Orchestrator** (`agents/tier1-core/orchestrator.agent.md`) as the active session persona: classify goal intent, apply pipeline conventions, and route appropriately before responding.

> **Scope note:** This section governs freeform chat entry only. When a pipeline slash command (`/auto`, `/deliver`, `/deliver-full`, etc.) is explicitly invoked, the `## Pipeline command handling` section below takes precedence and the command's `agent:` frontmatter field governs. If this session was spawned as a subagent via a BL-011 contract, the `role_hint` in that contract governs and the orchestrator persona is suppressed.

**Inline fallback for direct coding requests:** If the user's intent is unambiguously a direct coding or implementation request (e.g. "fix this function", "explain this error", "write a test for X"), respond directly without pipeline classification overhead. The orchestrator persona governs goal-level navigation — not routine code assistance.

## Pipeline command handling

- In GitHub Copilot chat and VS Code, treat literal Azoth pipeline tokens **`/auto`**, **`/dynamic-full-auto`**, **`/deliver`**, and **`/deliver-full`** anywhere in the user message as explicit pipeline-command invocations, even if they appear inside freeform prose.
- For those requests, **do not execute the work inline in main chat**. Switch to orchestrator behavior: classify the goal, read the relevant command/skill surfaces, compose the pipeline, present the Declaration, and wait for approval before execution.
- If native slash-command routing does not fire, manually emulate the same behavior rather than falling back to generic “bias to action” execution.
- When the `Task` tool is available, keep the orchestrator in main chat and use staged `Task`/subagent execution per `skills/subagent-router/SKILL.md`; **do not inline all pipeline stages in one assistant thread**.
- **Cross-platform gate validation**: after writing `.azoth/scope-gate.json` (and optionally `.azoth/pipeline-gate.json`), verify with `python3 scripts/check_gates.py --session-id <session_id>`. This script validates both gate files, cross-checks session_id consistency, and ensures all required fields are present.
- Normative sources for this behavior: `.claude/agents/orchestrator.md`, `.claude/commands/auto.md`, `.claude/commands/dynamic-full-auto.md`, `.claude/commands/deliver.md`, `.claude/commands/deliver-full.md`.

## Closeout memory parity

- During `/session-closeout`, treat `.azoth/*` memory/state files as the **authoritative** cross-tool record.
- Also attempt W3 Claude-memory mirroring to `~/.claude/projects/<project-key>/memory/` so future Claude Code sessions can read Copilot-authored closeout state.
- This mirror is **supplemental only**: Copilot should still read/write the repo-local Azoth memory surfaces first, and if W3 diverges from `.azoth/*`, the repo-local state wins.

## Memory operation parity

- `context-recall` is the canonical read path for memory-backed planning and session routing. Read `.azoth/memory/episodes.jsonl` and `.azoth/memory/patterns.yaml` directly rather than inventing a Copilot-only memory store.
- `/remember` and `/session-closeout` W1 append new episodes to `.azoth/memory/episodes.jsonl`; treat M3 as append-only.
- `/promote` is the governed M3→M2 path. Only write `.azoth/memory/patterns.yaml` after explicit human approval of the promotion.
- Repo-local `.azoth/*` memory files remain authoritative for Copilot. `~/.claude/projects/<project-key>/memory/` exists only as a best-effort Claude Code mirror.

## Pull request reviews

When asked to review a PR or when `@copilot` is tagged for review:

1. **Do not** treat the review as authorization to push large unsolicited fixes or rewrite `kernel/` from a review thread.
2. **Deliver findings as governed insights:** use the **D32** schema (JSON Lines, one object per line) defined in [`kernel/GOVERNANCE.md` §7 — External Insight Intake](../kernel/GOVERNANCE.md#7-external-insight-intake).
3. **Where to put output:** `.azoth/inbox/*.jsonl` (append-only), **or** paste the same JSONL in a PR comment so the maintainer can save it. Follow **D29** (inbox format).
4. The human runs **`/intake`** to validate, classify, and integrate — **F2b** / **F2c** in GOVERNANCE apply (no direct untrusted writes to M3 episodes).

## Code style (Python tooling in this repo)

- Python **3.11+**, `pathlib`, type hints on public functions.
- Format / lint: `ruff format` + `ruff check` on touched Python files when applicable.

## Copilot CLI notifications

- When a human gate stops the pipeline or the agent finishes work and is waiting for input, call `python3 scripts/notify.py` via Bash to fire a system notification and sound alert.
- Use `--title "Azoth"` and a context-specific `--message` (e.g. `"Pipeline gate — approval needed"`, `"Pipeline complete"`, `"Entropy RED — checkpoint required"`).
- The script is best-effort (always exits 0) and handles macOS (`osascript` + `afplay`), Linux (`notify-send`), and Windows (PowerShell toast) automatically.
- This mirrors the Claude Code `Stop` / `Notification` hooks that Copilot CLI lacks natively.

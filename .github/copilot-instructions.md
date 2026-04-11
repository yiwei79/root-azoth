# GitHub Copilot — repository instructions (root-azoth)

These notes apply to **coding assistance** and **pull request reviews** in this repository.

## Architecture and trust

- Ground changes in [`docs/AZOTH_ARCHITECTURE.md`](../docs/AZOTH_ARCHITECTURE.md), [`kernel/TRUST_CONTRACT.md`](../kernel/TRUST_CONTRACT.md), and [`docs/DECISIONS_INDEX.md`](../docs/DECISIONS_INDEX.md) (e.g. D29, D32) where relevant.
- **Kernel (`kernel/`)** is immutable without human-approved promotion and governed delivery — do not propose casual edits there.

## Pipeline command handling

- In GitHub Copilot chat and VS Code, treat literal Azoth pipeline tokens **`/auto`**, **`/dynamic-full-auto`**, **`/deliver`**, and **`/deliver-full`** anywhere in the user message as explicit pipeline-command invocations, even if they appear inside freeform prose.
- For those requests, **do not execute the work inline in main chat**. Switch to orchestrator behavior: classify the goal, read the relevant command/skill surfaces, compose the pipeline, present the Declaration, and wait for approval before execution.
- If native slash-command routing does not fire, manually emulate the same behavior rather than falling back to generic “bias to action” execution.
- When the `Task` tool is available, keep the orchestrator in main chat and use staged `Task`/subagent execution per `skills/subagent-router/SKILL.md`; **do not inline all pipeline stages in one assistant thread**.
- Normative sources for this behavior: `.claude/agents/orchestrator.md`, `.claude/commands/auto.md`, `.claude/commands/dynamic-full-auto.md`, `.claude/commands/deliver.md`, `.claude/commands/deliver-full.md`.

## Closeout memory parity

- During `/session-closeout`, treat `.azoth/*` memory/state files as the **authoritative** cross-tool record.
- Also attempt W3 Claude-memory mirroring to `~/.claude/projects/<project-key>/memory/` so future Claude Code sessions can read Copilot-authored closeout state.
- This mirror is **supplemental only**: Copilot should still read/write the repo-local Azoth memory surfaces first, and if W3 diverges from `.azoth/*`, the repo-local state wins.

## Pull request reviews

When asked to review a PR or when `@copilot` is tagged for review:

1. **Do not** treat the review as authorization to push large unsolicited fixes or rewrite `kernel/` from a review thread.
2. **Deliver findings as governed insights:** use the **D32** schema (JSON Lines, one object per line) defined in [`kernel/GOVERNANCE.md` §7 — External Insight Intake](../kernel/GOVERNANCE.md#7-external-insight-intake).
3. **Where to put output:** `.azoth/inbox/*.jsonl` (append-only), **or** paste the same JSONL in a PR comment so the maintainer can save it. Follow **D29** (inbox format).
4. The human runs **`/intake`** to validate, classify, and integrate — **F2b** / **F2c** in GOVERNANCE apply (no direct untrusted writes to M3 episodes).

## Code style (Python tooling in this repo)

- Python **3.11+**, `pathlib`, type hints on public functions.
- Format / lint: `ruff format` + `ruff check` on touched Python files when applicable.

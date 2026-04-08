# GitHub Copilot — repository instructions (root-azoth)

These notes apply to **coding assistance** and **pull request reviews** in this repository.

## Architecture and trust

- Ground changes in [`docs/AZOTH_ARCHITECTURE.md`](../docs/AZOTH_ARCHITECTURE.md), [`kernel/TRUST_CONTRACT.md`](../kernel/TRUST_CONTRACT.md), and [`docs/DECISIONS_INDEX.md`](../docs/DECISIONS_INDEX.md) (e.g. D29, D32) where relevant.
- **Kernel (`kernel/`)** is immutable without human-approved promotion and governed delivery — do not propose casual edits there.

## Pull request reviews

When asked to review a PR or when `@copilot` is tagged for review:

1. **Do not** treat the review as authorization to push large unsolicited fixes or rewrite `kernel/` from a review thread.
2. **Deliver findings as governed insights:** use the **D32** schema (JSON Lines, one object per line) defined in [`kernel/GOVERNANCE.md` §7 — External Insight Intake](../kernel/GOVERNANCE.md#7-external-insight-intake).
3. **Where to put output:** `.azoth/inbox/*.jsonl` (append-only), **or** paste the same JSONL in a PR comment so the maintainer can save it. Follow **D29** (inbox format).
4. The human runs **`/intake`** to validate, classify, and integrate — **F2b** / **F2c** in GOVERNANCE apply (no direct untrusted writes to M3 episodes).

## Code style (Python tooling in this repo)

- Python **3.11+**, `pathlib`, type hints on public functions.
- Format / lint: `ruff format` + `ruff check` on touched Python files when applicable.

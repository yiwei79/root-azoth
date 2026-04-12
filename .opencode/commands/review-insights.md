---
description: Run Cursor-oriented blindspot review and write D32 insights to .azoth/inbox/
agent: orchestrator
---

# /review-insights

Run a structured **code review / bug sweep** aligned with **`skills/cursor-review-insights/SKILL.md`**, then **write** D32 JSONL insights to **`.azoth/inbox/`** (trusted source **`cursor-review`**).

## When to use

- You want **blindspot coverage** (silent failures, parity, tests, security, paths) in **Cursor**
- You want findings as **governed inbox insights** for **`/intake`**, not only chat prose

## Steps

1. **Read** `skills/cursor-review-insights/SKILL.md`.
2. **Scope:** Ask the human which paths, diff, or commits to review (default: recent change set or open files).
3. **Analyze** using the skill checklist; dedupe findings.
4. **Write** one JSON object per line to `.azoth/inbox/cursor-review-YYYY-MM-DD.jsonl` (append if the file exists).
5. **Report** path written and count of insights; remind: **`/intake`** for triage.

## Rules

- Each line must satisfy **D32** in `kernel/GOVERNANCE.md` §7; `source` must be **`cursor-review`**.
- Do not write to M3 episodes from this command unless the human explicitly asks.

## Arguments

Optional: `$ARGUMENTS` — space-separated paths or glob hint for scope (e.g. `scripts/ .github/workflows/`).

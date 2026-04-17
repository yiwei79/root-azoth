---
type: review-request
source: session-2026-04-17-next-active-filter
pr: https://github.com/yiwei79/root-azoth/pull/11
pr_number: 11
date: 2026-04-17
reviewers: [github-copilot, codex]
status: pending
---

# Review Request — PR #11: fix(next) multi-session coordination

Please ask **GitHub Copilot** and **Codex** to review PR #11:
https://github.com/yiwei79/root-azoth/pull/11

## What to review

Primary file: `.claude/commands/next.md` (and its platform mirrors)

Key questions for reviewers:

1. **Step 0b logic** — Does the run-ledger cross-check correctly handle all session
   states (`active`, `parked`, absent file, YAML parse error)? Any edge cases missed?

2. **Step 10c write-back** — Is it appropriate to write `status: active` to `backlog.yaml`
   as a side effect of scope approval? Risk of stale `active` items if session is abandoned?

3. **Lag window** — Is the two-layer defence (Step 0b run-ledger + Step 3 status filter)
   sufficient to prevent races, or is there a scenario that slips through?

4. **Platform mirror parity** — Do the `.gemini/commands/next.toml`, `.agents/workflows/next.md`,
   `.github/prompts/next.prompt.md`, and `.opencode/commands/next.md` mirrors correctly
   reflect all six changes?

5. **Recovery guidance** — Is the Step 10c recovery note (abandoned scope) actionable enough?
   The eval flagged "prior value" ambiguity and missing session_id hint.

## How to file insights

Append each insight as a new `.md` or `.jsonl` file in `.azoth/inbox/` using the naming
convention `<reviewer>-review-pr11-<date>.md`. The next `/intake` session will triage them.

Or use this file — append findings directly below the `---` separator.

---

## Copilot review findings
<!-- GitHub Copilot: append findings here -->

## Codex review findings
<!-- Codex: append findings here -->

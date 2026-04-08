## Summary

<!-- What does this PR change and why? Link backlog IDs or roadmap items if helpful. -->

## Testing

<!-- e.g. `python3 -m pytest -q` — note any skipped/xfail expectations. -->

## Checklist

- [ ] Aligns with [`docs/AZOTH_ARCHITECTURE.md`](../docs/AZOTH_ARCHITECTURE.md) and current phase
- [ ] No unauthorized [`kernel/`](../kernel/) edits (unless this PR is an approved promotion / scope card)
- [ ] After changing canonical `skills/`, `agents/`, or `.claude/commands/`, ran `python3 scripts/azoth-deploy.py` (parity)

---

## GitHub Copilot review — inbox-only (Azoth)

**Easy path:** PR sidebar → **Reviewers** → request **Copilot** → paste the **one-liner** below as a comment (or rely on [`.github/copilot-instructions.md`](copilot-instructions.md)).

**Contract**

1. Findings are **insights**, not substitute for `/deliver` or direct kernel writes.
2. **Output format:** **D29 / D32** — **JSON Lines**, one object per line, **12-field schema** in [`kernel/GOVERNANCE.md` §7](../kernel/GOVERNANCE.md#7-external-insight-intake) (`id`, `source`, `source_type`, `timestamp`, `category`, `severity`, `target`, `summary`, `evidence`, `recommended_action`, `auto_applicable`, `requires_human_gate`). See also [`docs/DECISIONS_INDEX.md`](../docs/DECISIONS_INDEX.md) (D29, D32).
3. **Drop path:** add file(s) under `.azoth/inbox/*.jsonl` **or** paste the same JSONL in a PR comment for the maintainer to save.
4. Maintainer runs **`/intake`** — no automatic M3/M2 promotion from Copilot output.

**One-liner for Copilot (copy into a PR comment after requesting review)**

```text
@copilot Review for Azoth alignment (`docs/AZOTH_ARCHITECTURE.md`, trust/governance as relevant). Output **only** D32 JSONL insights per `kernel/GOVERNANCE.md` §7 for `.azoth/inbox/` (or paste JSONL here). No drive-by commits or kernel edits from this review; human `/intake` triages.
```

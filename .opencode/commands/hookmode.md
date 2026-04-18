---
description: Inspect or switch the local Codex hook profile
agent: orchestrator
---

# /hookmode $ARGUMENTS

Inspect or switch the local Codex hook mode.

This command manages the local Codex hook profile in this worktree. It is mainly
for Codex UX tuning and writes only local Codex adapter state:
- `.codex/hooks.json`
- `.codex/hooks.mode.local`

## Arguments

- No argument or `status`: show the current mode and sync state
- `calm`: restore the default low-noise Codex hook profile
- `verbose` or `verbo`: enable the fuller automatic Codex hook profile

If the argument is anything else, do not guess. Tell the human the accepted values:
`status`, `calm`, `verbose`, `verbo`.

## Execution

1. Normalize `$ARGUMENTS`:
   - empty → `status`
   - `verbo` → `verbose`
2. Run the local switcher:

```bash
python3 scripts/codex_hooks_mode.py $ARGUMENTS
```

For `status`, run:

```bash
python3 scripts/codex_hooks_mode.py status
```

## Reporting

After the script runs, report:
- active mode
- whether `.codex/hooks.json` is in sync with the selected template
- that `verbose` is a local override, not the canonical repo default

## Notes

- `calm` is the canonical Azoth default for Codex.
- `verbose` is an opt-in local profile for people who want more automatic hooks and accept more UI noise.
- This command does not change the Trust Contract. It only changes which Codex hook template is active locally.

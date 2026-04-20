---
description: Inspect or switch the local Codex operating mode
agent: orchestrator
---

# /hookmode $ARGUMENTS

Inspect or switch the local Codex operating mode.

This command manages two local Codex knobs in this worktree:
- the active permission profile (`calm` or `seamless`)
- the active hook overlay (`calm` or `verbose`)

Tracked Codex adapter artifacts stay stable under deploy:
- `.codex/config.toml` is the calm tracked default
- `.codex/config.seamless.toml` is the tracked seamless companion
- `.codex/hooks.json` is the calm tracked default
- `.codex/hooks.verbose.json` is the tracked verbose companion

This command applies a local override on top of those tracked artifacts and writes
only local Codex adapter state:
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/permission_profile.local`
- `.codex/hooks.mode.local`

## Arguments

- No argument or `status`: show the current mode and sync state
- `calm`: restore the calm permission profile and calm hooks
- `seamless`: enable the seamless permission profile with calm hooks
- `verbose` or `verbo`: enable the verbose hook overlay while preserving the current permission profile

If the argument is anything else, do not guess. Tell the human the accepted values:
`status`, `calm`, `seamless`, `verbose`, `verbo`.

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
- active permission profile
- active hook mode
- whether `.codex/config.toml`, `.codex/hooks.json`, and `.codex/rules/azoth-seamless.star` are in sync with the selected local mode
- that `seamless` and `verbose` are local overrides layered over tracked repo artifacts, not a replacement for the repo default

## Notes

- `calm` is the canonical Azoth default for Codex.
- `seamless` is the tracked opt-in permission companion, but local activation still happens through this command.
- `verbose` is a hook overlay only. It preserves whichever permission profile is currently selected.
- `python3 scripts/azoth-deploy.py` refreshes the tracked calm defaults and companion artifacts. Re-run `/hookmode` afterward if you want to re-apply a local override.
- This command does not change the Trust Contract. It only changes which Codex adapter surfaces are active locally.

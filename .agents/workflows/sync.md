# /sync — Pattern Extraction

You are running the Azoth sync pipeline. This extracts proven patterns from a
source framework and proposes them for inclusion in Azoth.

## Pre-Flight

1. Read `sync-config.yaml` for sanitization rules
2. Confirm the source path with the human (ask if not provided as argument)

## Execution

Run the sync script:

```bash
python scripts/azoth-sync.py --source $ARGUMENTS
```

If the human didn't provide a source path, ask for it first.

## Modes

- **Default**: Interactive — presents proposals for human approval
- **Dry run**: Add `--dry-run` to see what would be synced without changes
- **Auto-approve**: Add `--yes` to skip human alignment (use with caution)

## Post-Sync

After sync completes:

1. Review the sync log: `.azoth/sync-log.jsonl`
2. Run tests to verify nothing broke: `python -m pytest tests/ -v`
3. If new skills/agents were synced, verify they follow Azoth conventions
4. Update `azoth.yaml` if new components were added
5. Present alignment summary to human:
   - Files synced
   - Sanitization applied
   - Any manual review needed

## Governance

- Synced files that touch `kernel/` require full governance review
- Synced files are always sanitized before writing
- The human approves each proposal (unless `--yes` flag is used)
- Sync direction is ONE-WAY: source → Azoth (never reverse)

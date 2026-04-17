# Canonical Commands

This directory is the future neutral source-of-truth for Azoth commands.

Design source:

- `docs/CANONICAL_COMMAND_CONTRACT.md`

Target layout:

```text
commands/<name>/command.yaml
commands/<name>/body.md
```

Current migration status:

- This directory is partially runtime-active for pilot contracts consumed by `scripts/azoth-deploy.py`
- Commands without a canonical contract still compile from `.claude/commands/*.md`
- individual command contracts may temporarily point back to legacy Claude command files
  through `body.mode: legacy_claude_markdown`

Prototype coverage in this slice:

- `commands/next/command.yaml` is the active pilot contract

Rules:

- Keep user-facing terminology command-first
- Do not treat files here as live deploy input until `P1-024`
- Prefer adding one representative pilot at a time rather than bulk-copying every command

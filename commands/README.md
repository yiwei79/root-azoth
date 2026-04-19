# Command Contracts

This directory is the neutral authored source-of-truth for Azoth commands.

Design source:

- `docs/CANONICAL_COMMAND_CONTRACT.md`

Target layout:

```text
commands/<name>/command.yaml
commands/<name>/body.md
```

Current migration status:

- `scripts/azoth-deploy.py` consumes these contracts directly for deployed platform surfaces
- Migrated commands such as `/start`, `/next`, `/resume`, and `/session-closeout` already use canonical `commands/<name>/body.md`
- Some commands still bridge through `body.mode: legacy_claude_markdown`; that bridge remains documented until the final body migration lands

Rules:

- Keep user-facing terminology command-first
- Treat files here as the live authored command input for migrated commands
- Keep command-first wording and make any remaining legacy bridge explicit in the contract
- Treat `body.mode: legacy_claude_markdown` as a mixed bridge: the contract here stays
  canonical, while the markdown body is still sourced from `.claude/commands/<name>.md`
- `azoth-deploy --check` only permits semantic parity on the deployed Claude output for
  that legacy bridge, defined as parsed frontmatter equality plus exact body equality
- Keep every non-Claude projection and every canonical Claude projection byte-exact under
  `azoth-deploy --check`

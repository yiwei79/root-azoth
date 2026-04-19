# Canonical Command Contract

## 1. Purpose

This document defines the neutral, command-first source-of-truth model for Azoth
commands after the shift to a protocol-first platform model.

The goal is not to make every harness look identical.

The goal is to author command semantics once, preserve Azoth's user-facing
`/command` convention, and project those semantics into:

- Claude Code
- Codex
- GitHub Copilot
- OpenCode
- Cursor
- other adapter surfaces when useful

This is the design artifact for `P1-023`.

Initiative sequencing and advancement criteria live in:

- `.azoth/roadmap-specs/v0.2.0/INI-PLT-006-execution-plan.md`

## 2. Chosen Canonical Path

Canonical command contracts live under:

```text
commands/<name>/command.yaml
commands/<name>/body.md        # eventual canonical markdown body
```

For the transition period, `command.yaml` may point at a legacy body source under
`.claude/commands/<name>.md` instead of requiring `body.md` immediately.

That gives Azoth a neutral command root now without forcing the `D46`
projection/compiler refactor in the same slice.

This is a mixed bridge, not a second canonical source-of-truth:

- `commands/<name>/command.yaml` remains the authored contract
- `body.mode: legacy_claude_markdown` reuses only the legacy markdown body source
- deployed `.claude/commands/*.md` outputs stay generated artifacts, even when the
  legacy body path matches the Claude projection path

## 3. Contract Shape

Each command contract is a YAML document with these required top-level fields:

| Field | Purpose |
| --- | --- |
| `schema_version` | Contract version for future compiler changes |
| `name` | Stable Azoth command id without the slash |
| `display_name` | User-facing command token, usually `/<name>` |
| `description` | One-line purpose |
| `agent` | Default execution owner / routing hint |
| `azoth_effect` | `read`, `mixed`, or `write` |
| `execution` | Command shape such as `orientation`, `scope_card`, `pipeline`, `utility`, `closeout` |
| `arguments` | Whether the command accepts `$ARGUMENTS` and how |
| `state` | Files/artifacts read, written, or emitted |
| `governance` | Approval, gate, and human-stop behavior |
| `body` | Where the markdown execution body comes from |
| `projection` | Platform-specific deployment targets |
| `migration` | Transition status while D46 still compiles from legacy sources |

Recommended optional fields:

- `references`
- `aliases`
- `notes`

## 4. Body Rules

The body remains markdown because Azoth commands are still instruction-rich, with:

- ordered execution steps
- inline examples
- tables
- cross-links to skills, agents, and state files

`command.yaml` defines the machine-readable contract; the body remains the
human-readable instruction payload.

Allowed `body.mode` values:

- `legacy_claude_markdown`
  - Transitional mode. Runtime source still lives at `.claude/commands/<name>.md`.
- `canonical_markdown`
  - Final mode. Runtime source lives at `commands/<name>/body.md`.

Design rule:

- the compiler may transform formatting per platform
- it must not change command semantics, gate semantics, or stage semantics

## 5. Projection Rules

### Claude Code

- Output: `.claude/commands/<name>.md`
- Projection type: native command markdown
- Render frontmatter from the contract fields needed by Claude:
  - `description`
  - `azoth_effect`
  - `agent`
- Body source: markdown body from `body`
- `azoth-deploy --check` is byte-exact for canonical Claude outputs
- Narrow exception: when `body.mode: legacy_claude_markdown`, Claude check mode
  accepts parsed frontmatter equality plus exact body equality for that deployed
  output only

### Cursor

- Output: same `.claude/commands/<name>.md` surface when the toggle is enabled
- Projection type: Claude-compatible command mirror
- Cursor-specific guardrails remain in `.cursor/rules/*.mdc`
- Cursor does not redefine the command contract; it consumes the Claude-shaped projection

### GitHub Copilot

- Output: `.github/prompts/<name>.prompt.md`
- Projection type: prompt markdown
- Required frontmatter:
  - `mode: agent`
  - `description`
  - `agent`
- Body source: same semantic body, with only platform wrapper differences

### OpenCode

- Output: `.opencode/commands/<name>.md`
- Projection type: native command markdown
- Preserve `$ARGUMENTS` semantics
- Frontmatter remains minimal:
  - `description`
  - `agent`

### Codex

- Output:
  - `.agents/skills/azoth-<name>/SKILL.md`
  - `.agents/skills/azoth-<name>/openai.yaml`
- Projection type: explicit skill wrapper
- The wrapper should read the canonical command contract, not `.claude/commands/*`,
  once `P1-024` lands
- Literal `/name` text remains compatibility fallback, not the primary Codex-native surface

### Other adapters

- Gemini / Antigravity and future adapters should consume the same contract through thin
  projection layers
- Adapter-specific UX is allowed
- adapter-specific semantics are not

## 6. Worked Example: `/next`

`/next` is the first prototype because it is representative without being the
largest command:

- it is command-first, not pipeline-first
- it reads roadmap/backlog state
- it emits a structured scope card
- it writes governed state only after human approval

Its prototype contract lives at:

```text
commands/next/command.yaml
```

Key modeling choices in the pilot:

- `execution.kind: scope_card`
- `arguments.accepts_arguments: false`
- `state.reads` captures roadmap/backlog/memory inputs
- `state.writes_on_approval` captures the gated write set
- `body.mode: legacy_claude_markdown` kept `.claude/commands/next.md` as the
  temporary body source during the pilot projection slice

This was deliberate for the pilot: the design slice created a real neutral
contract without forcing dual maintenance of every command body yet.

Current status after `T-002` batch-1 migration:

- `/next`, `/start`, and `/resume` now move under `commands/<name>/`
- their `.claude/commands/*.md` files are deployed outputs again
- `legacy_claude_markdown` remains supported as a transition mode for later batches,
  but it is no longer required for the batch-1 command family

## 7. Migration Plan

### Phase 0: design

- Define the contract shape
- Create `commands/` root
- Add one prototype contract
- Keep D46 unchanged

### Phase 1: dual-source bridge

- Teach `scripts/azoth-deploy.py` to load `commands/<name>/command.yaml`
- Allow `body.mode: legacy_claude_markdown`
- Prefer the contract for metadata and projection rules
- Continue reading legacy Claude markdown for body text
- In `--check`, allow scoped semantic parity only for the contract-backed Claude
  output of legacy-body commands; all other projections stay byte-exact

### Phase 2: canonical body migration

- Move selected commands to `commands/<name>/body.md`
- Flip `body.mode` to `canonical_markdown`
- Keep legacy `.claude/commands/*.md` generated, not authored

### Phase 3: full D46 projection

- Generate all command surfaces from `commands/*`
- Remove `.claude/commands/*` as an authored source
- Keep `.claude/commands/*` only as deployed output

## 8. Non-Goals

- Refactoring `scripts/azoth-deploy.py` in this design slice
- Migrating every existing command immediately
- Flattening command bodies into pure YAML
- Renaming commands to workflows
- Forcing all adapters to mimic Claude-native enforcement

## 9. Decision

Azoth's canonical command source should become:

- structured contract in `commands/<name>/command.yaml`
- markdown body in `commands/<name>/body.md` when migrated
- temporary legacy-body import allowed during transition

That gives Claude Code and Codex a neutral shared design center while preserving
reasonable adapter compatibility for the rest of the supported platforms.

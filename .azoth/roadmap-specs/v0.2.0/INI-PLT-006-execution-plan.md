# INI-PLT-006 Execution Plan

## Purpose

This is the initiative-level execution plan for:

- `INI-PLT-006 — Co-primary platform model (Claude Code + Codex; stable adapters)`

It exists to keep the initiative scoped at the right level:

- strong enough to guide multiple slices coherently
- light enough to avoid over-specifying `D46` implementation details too early

## Initiative Goal

Azoth should evolve from:

- Claude-first with adapters

to:

- protocol-first with two co-primary command surfaces and a stable adapter layer

The target is not perfect harness parity.

The target is:

- low-stress operation
- anti-slop defaults
- high-quality output
- command-first user experience
- unified governance semantics
- honest adapter compatibility for non-co-primary platforms

## Done Means

`INI-PLT-006` is done when all of the following are true:

1. Azoth's platform model is explicitly protocol-first in roadmap, architecture, and planning surfaces.
2. Claude Code and Codex are treated as co-primary command surfaces in the canonical design.
3. A neutral canonical command contract exists outside `.claude/commands/`.
4. `scripts/azoth-deploy.py` can project at least one pilot command family from the neutral contract into:
   - Claude Code
   - Codex
   - GitHub Copilot
   - OpenCode
   - Cursor-compatible Claude projection
5. Codex wrappers no longer depend on `.claude/commands/*.md` as the semantic source of truth.
6. Adapter platforms remain on an explicit, documented compatibility contract rather than silently inheriting co-primary status.

## Slice Plan

### Slice 1 — `P1-022`

Objective:

- codify the co-primary platform model in roadmap, backlog, orientation, and blueprint surfaces

Proof provided by this slice:

- the initiative exists as active roadmap work
- co-primary and adapter-tier language is explicit
- command-first terminology is preserved

### Slice 2 — `P1-023`

Objective:

- define the neutral canonical command contract
- choose the on-disk source path
- add one representative prototype command contract
- define the migration bridge from legacy Claude-authored bodies

Proof provided by this slice:

- the contract shape is documented
- the `commands/` path is real
- at least one prototype command exists
- transition rules are explicit enough to start `P1-024`

### Slice 3 — `P1-024`

Objective:

- refactor `D46` command projection so deployed command surfaces are generated from the neutral command contract

Proof provided by this slice:

- one pilot command family is projected end-to-end from the neutral source
- generated Claude, Codex, Copilot, and OpenCode command surfaces stay behaviorally aligned
- drift/parity tests cover the new path

### Follow-on migration batches

After `P1-024`, remaining command migration should proceed in small batches rather than a repo-wide cutover.

Preferred order:

1. scope/orientation commands
   - `/start`
   - `/next`
   - `/resume`
2. lean delivery commands
   - `/deliver`
   - `/plan`
   - `/test`
3. governed and orchestration-heavy commands
   - `/auto`
   - `/deliver-full`
   - `/eval`
   - `/eval-swarm`
4. closeout / memory / maintenance commands
   - `/session-closeout`
   - `/remember`
   - `/sync`
   - `/roadmap`

## Advancement Evidence

### Evidence required before moving from `P1-022` to `P1-023`

- the co-primary model is stable in planning language
- no unresolved disagreement remains on command-vs-pipeline terminology

### Evidence required before moving from `P1-023` to `P1-024`

- canonical command path and format are chosen
- projection rules are explicit for Claude Code, Codex, Copilot, OpenCode, and Cursor
- one prototype command contract is present
- transition strategy from legacy Claude bodies is documented
- no open ambiguity remains about whether Codex should consume the canonical contract or Claude files after the refactor

### Evidence required before broad migration after `P1-024`

- one pilot command family works end-to-end from the neutral source
- parity/drift tests stay green
- generated Codex wrappers read the canonical contract path rather than `.claude/commands/*`
- no adapter-specific regression forces a redesign of the contract

## Failure Signals

Revise the contract before broad migration if any of these happen:

1. The canonical contract needs platform-specific semantic fields to describe ordinary command behavior.
2. Codex requires materially different command semantics rather than only a different native surface.
3. Copilot or OpenCode projections require command meaning to be changed instead of merely wrapped.
4. The contract cannot represent large orchestration commands like `/auto` or `/deliver-full` without leaking compiler-specific logic into authored content.
5. The transition bridge (`legacy_claude_markdown`) becomes permanent rather than transitional.

## Non-Goals

- full deterministic governance parity across all platforms
- eliminating all harness-specific UX differences
- migrating every command in one initiative slice
- changing command semantics just to make deployment easier
- promoting Copilot, Cursor, OpenCode, or Gemini / Antigravity to co-primary status

## Review Rule

If `P1-024` exposes structural problems in the command contract, revise `P1-023`
and this initiative plan before continuing with wider migration. Do not brute-force
through the mismatch by hardcoding more adapter-specific exceptions into the compiler.

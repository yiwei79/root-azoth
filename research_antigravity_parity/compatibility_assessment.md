# Final Compatibility Assessment: Azoth On Antigravity

## Bottom line

Antigravity is a credible compatible-platform candidate for Azoth.

Practical parity looks achievable with an Antigravity-specific adapter.
Exact Claude Code parity does not.

## Recommendation

Conditional go.

Proceed only as an adapter project, not as a claim that Antigravity natively understands Azoth's current Claude Code surfaces.

## Calibration: Copilot-Level Parity

If the target is "works well at the same level as Copilot" rather than "near-total Claude Code parity", the outlook improves materially.

Under that calibration, this is closer to a plain go than a cautious go.

The success bar becomes:

- Azoth guidance loads reliably through Antigravity-native rules rather than `CLAUDE.md`.
- Azoth command equivalents are usable through Antigravity workflows rather than `.claude/commands/` or `.github/prompts/`.
- Azoth skills work well through `.agents/skills/`.
- `.azoth/` remains the repo-authoritative state layer for session continuity and governance.
- Multi-agent work, artifacts, browser usage, terminal usage, and MCP-backed workflows feel operationally strong.
- Governance is acceptably enforced through permissions, strict mode, sandboxing, artifact review, and workflow discipline, even if it is not implemented through executable Claude-style hooks.

That is a substantially easier target than Claude-equivalent runtime behavior.

## Why this is a go

Antigravity has first-party support for the primitives Azoth most needs:

- local IDE plus workspace editing,
- slash-triggered workflows,
- progressive-disclosure skills,
- multiple asynchronous agents and task groups,
- browser, terminal, and editor execution,
- artifact-centered review,
- MCP integration,
- permissions, strict mode, and sandboxing,
- persistent knowledge across sessions.

That is enough to support an Azoth-native operating style.

## Why this is only conditional

Antigravity does not show first-party evidence for two Claude-specific assumptions:

1. Repo-local executable hooks equivalent to Claude Code PreToolUse.
2. User-defined custom agent persona files equivalent to Azoth's current agent archetype files.

These are the two areas where parity becomes translation rather than reuse.

## Recommended adapter scope

### Direct mappings

- Azoth command surfaces -> Antigravity Workflows in `.agents/workflows/`
- Azoth skills -> Antigravity Skills in `.agents/skills/`
- Core session guidance -> Antigravity Rules in `.agents/rules/`
- Tool integrations -> Antigravity MCP config and MCP Store usage
- Repo state -> keep `.azoth/` authoritative inside the workspace

### Behavioral translations

- `CLAUDE.md` behavior -> one or more Always On rules instead of direct file loading
- custom agent archetypes -> workflow plus rule plus skill combinations instead of separate agent-definition files
- hook enforcement -> permissions, strict mode, sandboxing, artifact review policies, and workflow-level checks instead of executable repo hooks

## Recommended first prototype

Build a minimum Antigravity adapter with only:

1. `azoth-core` Always On workspace rule
2. `/auto` workflow equivalent
3. one transported Azoth skill in `.agents/skills/`
4. strict-mode and permission recommendations for governed sessions
5. proof that workflows can read `.azoth/scope-gate.json` and stop when invalid

If that prototype works, extend D46 to add an Antigravity deploy target.

## Behaviors That Can Stay Claude-Only

These do not need to port for Antigravity to be considered successful at the Copilot level:

- executable PreToolUse hook parity from `.claude/settings.json`
- SessionStart hook behavior and automatic orientation injection
- direct loading of `.claude/commands/`
- direct loading of file-defined Azoth agent archetypes as custom personas
- Claude project-memory mirror behavior under `~/.claude/projects/.../memory/`

If Antigravity delivers the same practical outcomes through its own native surfaces, those Claude-specific mechanisms can remain platform-specific rather than universal.

## Non-portable or not-yet-proven behaviors

- direct consumption of `CLAUDE.md`
- direct consumption of `.claude/commands/`
- direct consumption of `.claude/agents/`
- direct consumption of `.github/prompts/`
- programmable repo-local hook scripts with Claude-style PreToolUse semantics

## Confidence

Medium-high for practical compatibility.

Medium for governed-workflow parity until a prototype proves that permissions, strict mode, and workflow discipline are sufficient in place of executable hooks.

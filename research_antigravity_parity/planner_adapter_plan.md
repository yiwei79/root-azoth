# Planner Output: Antigravity Adapter Strategy

## Goal

Define the minimum Antigravity-native surfaces Azoth would need to target in order to achieve practical parity with its current Claude Code behavior where parity is possible, and isolate the behaviors that can only be approximated.

## Recommended adapter shape

### 1. Core always-on guidance

Deploy Azoth's core session and governance guidance into Antigravity Rules:

- Workspace rule: `.agents/rules/azoth-core.md`
- Optional global rule: `~/.gemini/GEMINI.md` as a user-level pointer or umbrella instruction file

Recommended activation:

- Core governance rule: Always On
- Narrow helper rules: Model Decision or Glob, depending on surface

### 2. Command equivalents

Deploy Azoth command surfaces as Antigravity Workflows:

- `.claude/commands/*.md` and `.github/prompts/*.md` map to `.agents/workflows/*.md`
- Preserve slash-triggered entry points where possible so `/auto`, `/deliver`, `/next`, `/session-closeout`, and `/eval` remain recognizable behaviors
- Use nested workflows where Antigravity supports calling one workflow from another

### 3. Skills

Deploy Azoth skills into Antigravity-native skill folders:

- Workspace skills: `<workspace-root>/.agents/skills/`
- Optional global skills: `~/.gemini/antigravity/skills/`

This is the cleanest mapping because Antigravity already uses SKILL.md with progressive disclosure.

### 4. Agent-archetype translation

Do not assume user-defined custom agent files exist.

Instead, express Azoth archetypes behaviorally through:

- workflow entry points,
- rule bundles,
- skill sets,
- planning vs fast mode,
- Antigravity task groups and Manager-surface agent instances.

This should preserve most architect/planner/builder/reviewer/evaluator behavior, but not as one-to-one file-defined agent personas.

### 5. Governance and safety mapping

Map Claude Code's mechanical enforcement into Antigravity's native controls where possible:

- command safety -> Agent Permissions Allow/Deny/Ask
- browser safety -> Browser URL Allowlist/Denylist + strict mode
- workspace boundary -> strict mode workspace isolation + Agent Non-Workspace File Access off
- terminal containment -> sandbox mode
- artifact review gates -> Artifact Review Policy set to Request Review when appropriate

### 6. Repo-authoritative state

Keep `.azoth/` as the authoritative repo-local state layer.

Antigravity-native rules and workflows should read and write:

- `.azoth/scope-gate.json`
- `.azoth/pipeline-gate.json`
- `.azoth/session-state.md`
- `.azoth/bootloader-state.md`
- `.azoth/memory/*`

Antigravity Knowledge Items can be treated as supplemental platform memory rather than the source of truth.

### 7. MCP and tools

Antigravity has first-party MCP support. Azoth should treat this as a direct mapping opportunity:

- document required MCP servers,
- provide Antigravity config examples for `~/.gemini/antigravity/mcp_config.json`,
- keep repo workflows tool-agnostic where possible.

## Direct mappings

- Skills -> direct
- Slash workflows -> direct
- Multi-agent planning and task groups -> direct
- Browser/terminal/editor execution -> direct
- MCP integration -> direct
- Artifact review and walkthroughs -> direct

## Approximate mappings

- `CLAUDE.md` always-on contract -> Antigravity Rules, not direct file reuse
- custom agent archetype files -> workflows + rules + skills, not direct file reuse
- PreToolUse hook logic -> permissions + strict mode + sandbox + workflow discipline, not direct file reuse

## Highest-risk gap

The highest-risk gap is mechanical hook parity.

Antigravity has strong built-in permissions and sandboxing, but first-party docs do not show repo-local executable hook scripts comparable to Claude Code PreToolUse. That means the exact Azoth hook model probably cannot be ported verbatim.

## Validation plan

1. Build a minimal Antigravity adapter prototype with one Always On rule, one slash workflow, and one skill.
2. Verify that a workflow can read `.azoth/scope-gate.json` and stop itself when scope is invalid.
3. Verify that strict mode plus permissions can reproduce acceptable safety for standard, non-governed work.
4. Verify that a governed workflow can require artifact review and request-review command execution before edits.
5. Decide whether any remaining Claude-only behaviors are acceptable as documented non-parity.

## Recommendation to evaluator

Assess this as a practical-compatibility question, not a zero-adapter question. The evidence already supports a likely yes for practical compatibility, but only a partial yes for exact Claude Code parity.

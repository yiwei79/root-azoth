# Antigravity Capability Matrix For Azoth Parity

| Azoth / Claude Code assumption | Antigravity first-party evidence | Parity status | Notes |
| --- | --- | --- | --- |
| Always-on instruction surface | Global Rules in `~/.gemini/GEMINI.md`; workspace Rules in `.agents/rules/` with activation modes including Always On | Partial parity | Equivalent behavior exists, but not via `CLAUDE.md`; requires an Antigravity adapter or mirrored rule files. |
| Slash-command style reusable prompts | Workflows are markdown files invoked as `/workflow-name` | Confirmed parity | This maps cleanly to Azoth command prompts, but file locations differ from `.github/prompts/` and `.claude/commands/`. |
| Skill loading with progressive disclosure | Skills live in `.agents/skills/` or `~/.gemini/antigravity/skills/`, discovered by name/description and loaded on demand | Confirmed parity | This is a very strong fit for Azoth skills and may require less translation than Copilot or Cursor. |
| Multi-agent or subagent isolation | Agent Manager spawns dedicated agent instances; Browser Subagent is a specialized subagent; Planning/Fast modes documented | Confirmed parity | D21-style stage isolation appears achievable and may be more native than in Claude Code. |
| User-defined custom agent personas or agent files | No first-party evidence of custom named agent-definition files; docs describe one Agent surface with customization through modes, rules, workflows, skills, permissions, and task groups | Partial parity | Azoth's archetypes likely need to be expressed behaviorally through rules, workflows, and skills rather than direct custom-agent file mirrors. |
| Editor + terminal + browser action loop | Antigravity agents operate across editor, terminal, and browser; browser subagent has DOM and video tooling | Confirmed parity | This matches Azoth's end-to-end delivery assumptions well. |
| Reviewable artifacts instead of raw logs only | Task lists, implementation plans, walkthroughs, screenshots, browser recordings, code diffs | Confirmed parity | Aligns strongly with Azoth's artifact and trust model. |
| Repo-local programmable hooks / pre-tool interception | No first-party evidence of repo-local executable hooks; instead Antigravity provides permissions, allow/deny/ask, strict mode, and sandboxing | Partial parity | Strong safety controls exist, but they are settings-driven rather than script-hook-driven like Claude Code PreToolUse. |
| Fine-grained command and file permissions | Agent Permissions supports `command`, `read_file`, `write_file`, `read_url`, and `mcp` resource strings | Confirmed parity | Stronger built-in permission grammar than basic allow/deny lists. |
| Workspace-only or out-of-workspace file control | Agent Non-Workspace File Access setting and strict mode workspace isolation | Confirmed parity | Good match for Azoth scope boundaries. |
| Browser safety controls | Browser URL allowlist/denylist and strict mode; browser JS execution request-review mode | Confirmed parity | Stronger documented browser controls than Claude Code alone. |
| Sandboxed terminal execution | Terminal sandboxing with file-system and network restrictions on macOS/Linux | Confirmed parity | Useful analogue for governed or high-trust sessions, though not identical to Azoth's repo-specific hook logic. |
| Persistent memory across sessions | Knowledge Items automatically capture and reuse summaries and artifacts | Partial parity | Memory exists, but first-party docs do not show a repo-authoritative handoff file equivalent to `.azoth/session-state.md`. |
| Portable custom tool integration | MCP Store and custom MCP config in `~/.gemini/antigravity/mcp_config.json` | Confirmed parity | Strong fit for Azoth MCP-dependent workflows. |
| Direct loading of existing Azoth Claude surfaces (`CLAUDE.md`, `.claude/commands/`, `.github/prompts/`) | No first-party evidence | No parity | Azoth cannot expect zero-config compatibility; dedicated deployment or mirroring is required. |

## Preliminary verdict

Antigravity appears capable of supporting most of Azoth's behavioral model, but not by directly reusing the current Claude Code file surfaces. The likely path is a dedicated Antigravity adapter that deploys:

- always-on rules for core Azoth governance and orientation,
- slash-triggered workflows for command equivalents,
- `.agents/skills/` mirrors or symlinks for Azoth skills,
- optional MCP and permission presets,
- repo-local state files that Azoth already owns under `.azoth/`.

The main hard gap is programmable hook parity. Antigravity has strong built-in security and permission controls, but no first-party evidence of repo-local executable hook scripts equivalent to Claude Code PreToolUse. That means some Azoth behaviors can be mapped, but some of the current mechanical enforcement would need to be re-expressed through permissions, strict mode, sandboxing, rules, or human review policies rather than direct hook execution.

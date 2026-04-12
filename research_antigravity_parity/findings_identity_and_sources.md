# Antigravity Identity And First-Party Sources

## Product identity

Antigravity is a first-party Google product: an agentic development platform and local IDE built on a fork of the open-source VS Code foundation.

## First-party sources used

- [antigravity.google](https://antigravity.google/)
- [Google Developers Blog announcement](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)
- [Google Codelab](https://codelabs.developers.google.com/getting-started-google-antigravity)
- [Agent modes and settings](https://antigravity.google/docs/agent-modes-settings)
- [Browser subagent](https://antigravity.google/docs/browser-subagent)
- [Rules and workflows](https://antigravity.google/docs/rules-workflows)
- [Skills](https://antigravity.google/docs/skills)
- [Agent permissions](https://antigravity.google/docs/agent-permissions)
- [Knowledge](https://antigravity.google/docs/knowledge)
- [MCP](https://antigravity.google/docs/mcp)
- [Strict mode](https://antigravity.google/docs/strict-mode)
- [Sandbox mode](https://antigravity.google/docs/sandbox-mode)

## Confirmed first-party facts

- Antigravity is available as a local install for macOS, Windows, and specific Linux distributions.
- The product is in public preview for personal Gmail accounts and requires Chrome for the browser agent flow.
- Antigravity splits the UI into an Editor and an Agent Manager (Mission Control) and can spawn multiple dedicated agents asynchronously across workspaces.
- Agents can act across editor, terminal, and browser surfaces.
- Antigravity includes a specialized browser subagent with DOM capture, screenshots, console-log access, typing, clicking, scrolling, markdown parsing, and video capture.
- Antigravity produces artifacts such as task lists, implementation plans, walkthroughs, screenshots, browser recordings, and code diffs, and users can comment on them.
- Rules and workflows are first-class customizations stored as markdown files.
- Skills are first-class directory-based packages with `SKILL.md`, optional scripts, and optional resources.
- Agent permissions are configurable through Allow, Deny, and Ask lists over commands, file reads and writes, URL reads, and MCP tools.
- Strict mode and terminal sandboxing provide stronger built-in security controls than a pure prompt-only model.
- Antigravity supports MCP through an MCP Store and custom `mcp_config.json` in `~/.gemini/antigravity/`.
- Antigravity has a persistent memory system called Knowledge Items.

## Key source excerpts mapped to parity

- Instruction and workflow surfaces: `~/.gemini/GEMINI.md`, `~/.gemini/antigravity/global_workflows/`, `<workspace-root>/.agents/rules/`, `<workspace-root>/.agents/workflows/`.
- Skill surfaces: `~/.gemini/antigravity/skills/` and `<workspace-root>/.agents/skills/`.
- Permissions surface: Allow/Deny/Ask resource strings for `command`, `read_file`, `write_file`, `read_url`, and `mcp`.
- Memory surface: Knowledge Items stored and surfaced by Antigravity; app-managed data lives under `~/.antigravity/` for artifacts and knowledge items, and under `~/.gemini/antigravity/` for customizations and MCP config.

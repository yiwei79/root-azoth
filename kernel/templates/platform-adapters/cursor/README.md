# Cursor Platform Adapter

## Setup (one toggle)

1. Open Cursor → Settings → Rules
2. Enable **"Include third-party plugin skills and configs"**
3. Restart the chat

Cursor will now load:
- `CLAUDE.md` as an always-applied rule (identity + governance)
- `.claude/commands/` as slash commands
- `agents/` as subagents
- `skills/` as skills

The toggle gives ~90% of Claude Code compatibility for free.

## What This Adapter Adds

Two **always-applied** Cursor rules (`.mdc`) complement the toggle:

| File | Purpose |
|------|---------|
| `azoth-memory.mdc` | Session start: read M2 patterns, bootloader state, optional `session-state.md` handoff |
| `claude-code-parity.mdc` | **Claude Code parity**: simulate scope-gate + pipeline-gate checks before writes (hooks do not run in Cursor), mandate `.claude/commands/` workflows, `azoth-deploy` after canonical edits |

Without `claude-code-parity.mdc`, agents may assume `.claude/settings.json` PreToolUse hooks will block bad writes — **they will not run in Cursor**.

## Installation

**Preferred:** deploy from kernel templates with Azoth dev-sync (D46 extension):

```bash
python3 scripts/azoth-deploy.py --platforms cursor
```

This copies every `*.mdc.template` under this directory to `.cursor/rules/<name>.mdc`.

**Manual** (equivalent):

```bash
mkdir -p .cursor/rules
cp kernel/templates/platform-adapters/cursor/azoth-memory.mdc.template .cursor/rules/azoth-memory.mdc
cp kernel/templates/platform-adapters/cursor/claude-code-parity.mdc.template .cursor/rules/claude-code-parity.mdc
```

Re-run **`azoth-deploy`** (full default includes `cursor`) whenever these templates change.

## Cross-IDE Session Handoff

To hand off a session from Claude Code to Cursor (or vice versa):

1. Run `/session-closeout` in the current IDE — it writes `.azoth/session-state.md`
2. Switch to the other IDE in the same workspace
3. Start a new chat — `azoth-memory.mdc` auto-loads the handoff capsule

## Capability Delta

| Workflow | Claude Code | Cursor |
|---|---|---|
| Exploration, edits, Q&A | ✓ | ✓ |
| Slash commands, skills | ✓ | ✓ via toggle |
| `CLAUDE.md` + repo layout parity | ✓ | ✓ with toggle + `.cursor/rules` |
| PreToolUse hooks (scope / pipeline gate) | ✓ mechanical | ✗ — **simulate** via `claude-code-parity.mdc` |
| `/deliver`, `/plan`, `/eval`, `/eval-swarm` | ✓ | ✓ follow command docs; use **`Task`** per stage when the command assigns subagents (`/eval-swarm` = stricter 0.90 swarm gate) |
| `/deliver-full` / `/auto` (subagent isolation) | ✓ `Agent(subagent_type=...)` | ✓ **`Task(subagent_type=...)`** per `subagent-router` — same D21 contract when parity rule is followed |
| Governed pipelines with stage isolation | ✓ hooks + commands | ✓ hooks simulated + **`Task`** for workers — risky only if orchestrator inlines stages |
| `/session-closeout` **W3** (Claude Code `~/.claude/.../memory/`) | ✓ native | ✓ attempt or log `W3 deferred` (see `claude-code-parity.mdc`) — **not** a substitute for repo W1/W2 |

**GitHub Copilot / OpenCode:** They do not load `.cursor/rules/*.mdc`; they use D46-deployed commands under `.github/prompts/` and `.opencode/commands/`. **`/session-closeout` W1/W2/W4** apply the same way in-repo; **W3** (Claude Code project memory under `~/.claude/`) does not apply — parity is **committed** episodes, bootloader, and `azoth.yaml`.

**Rule of thumb:** Install both `.mdc` rules. Use **`Task`** with Azoth archetype names for each pipeline stage that requires isolation (see `claude-code-parity.mdc`). Prefer **Claude Code** when you need **mechanical** PreToolUse enforcement (not behavioral).

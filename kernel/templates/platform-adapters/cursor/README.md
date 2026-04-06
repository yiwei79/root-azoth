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

`azoth-memory.mdc` (always-applied, installed by `azoth-sync`) bridges the one gap the toggle does not cover: M2 semantic memory and cross-IDE session state. It instructs the model to read at session start:

- `.azoth/memory/patterns.yaml` — approved architectural patterns (M2)
- `.azoth/bootloader-state.md` — current task state
- `.azoth/session-state.md` — cross-IDE handoff capsule (if present)

## Installation

`azoth-sync` writes `azoth-memory.mdc` to `.cursor/rules/` automatically. To install manually:

```bash
cp kernel/templates/platform-adapters/cursor/azoth-memory.mdc.template .cursor/rules/azoth-memory.mdc
```

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
| `/deliver`, `/plan`, `/eval` | ✓ | ✓ single-agent |
| `/deliver-full` (parallel subagents) | ✓ | Degraded — use Claude Code |
| Governed pipelines with stage isolation | ✓ | Not available |

**Rule of thumb**: Cursor for exploration and quick edits; Claude Code for governed delivery pipelines.

# 📘 Azoth Playbook

> Practical guides for using the Azoth agentic toolkit.  
> For architecture details, see [`AZOTH_ARCHITECTURE.md`](../AZOTH_ARCHITECTURE.md).

## Guides

| Guide | What you'll learn |
|-------|-------------------|
| [Pipeline Overview](./01-pipeline-overview.md) | How pipelines work, when to use which one |
| [Your First /auto](./02-first-auto.md) | Step-by-step walkthrough of the `/auto` command |
| [Session Lifecycle](./03-session-lifecycle.md) | Start → work → closeout flow |
| [Command Reference](./04-command-reference.md) | Quick-reference for Azoth commands across platforms |
| [Parallel Sessions](./05-parallel-sessions.md) | Safe single-integrator protocol for parallel branches/worktrees |

## Quick Start

```
Claude/OpenCode/Cursor: /start
Codex: $azoth-start                       ← orient and choose the next move

Claude/OpenCode/Cursor: /auto fix the login bug
Codex: $azoth-start pipeline_command=auto fix the login bug
                                           ← pipeline composes, you approve, it runs

Claude/OpenCode/Cursor: /session-closeout
Codex: $azoth-start closeout              ← save learnings, bump version, done
```

In Codex, raw slash tokens like `/auto` and `/next` are compatibility fallback, not the primary daily path. They normalize back through the calm-flow `$azoth-start` controller.

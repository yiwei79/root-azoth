# 📘 Azoth Playbook

> Practical guides for using the Azoth agentic toolkit.  
> For architecture details, see [`AZOTH_ARCHITECTURE.md`](../AZOTH_ARCHITECTURE.md).

## Guides

| Guide | What you'll learn |
|-------|-------------------|
| [Pipeline Overview](./01-pipeline-overview.md) | How pipelines work, when to use which one |
| [Your First /auto](./02-first-auto.md) | Step-by-step walkthrough of the `/auto` command |
| [Session Lifecycle](./03-session-lifecycle.md) | Start → work → closeout flow |
| [Command Reference](./04-command-reference.md) | Quick-reference for all slash commands |
| [Parallel Sessions](./05-parallel-sessions.md) | Safe single-integrator protocol for parallel branches/worktrees |

## Quick Start

```
You: /start                    ← see dashboard, pick next task
You: /auto fix the login bug   ← pipeline composes, you approve, it runs
You: /session-closeout          ← save learnings, bump version, done
```

That's it. Three commands for a full governed session.

# Gemini Platform Guide

> How to use Azoth in Gemini CLI, with a newcomer walkthrough for this repository.

## Classification

Gemini CLI is source-compatible with Azoth's generated adapter surfaces.

| Property | Value |
|----------|-------|
| Instruction file | `GEMINI.md` + `AGENTS.md` |
| Settings | `.gemini/settings.json` |
| Agents | `.gemini/agents/*.md` |
| Commands | `.gemini/commands/*.toml` |
| Skills | `.agents/skills/` (shared Gemini-family skill surface) |
| Canonical generator | `scripts/azoth-deploy.py` |

## Quick Start

1. From the repo root, regenerate platform surfaces if you changed canonical agents, commands, or skills:
   ```bash
   python3 scripts/azoth-deploy.py
   python3 scripts/azoth-deploy.py --check
   ```
2. Start Gemini from the repo root:
   ```bash
   gemini
   ```
3. Let Gemini load `GEMINI.md`, `AGENTS.md`, workspace commands, agents, and shared skills.
4. Use `/help` once per session to confirm the currently active command names.
5. Start with `/start` for orientation or `/next` to open a scoped task.

## What Gemini Loads In This Repo

At startup, Gemini reads the repo-local adapter surfaces that Azoth deploys:

| Surface | Role |
|--------|------|
| `GEMINI.md` | Primary Gemini-specific repo instructions |
| `AGENTS.md` | Cross-platform manifest |
| `.gemini/agents/` | Azoth agent archetypes for Gemini |
| `.gemini/commands/` | Azoth command entry points |
| `.agents/skills/` | Shared skill surface used by Gemini-family integrations |

The shared skill surface matters because Gemini should not use a second mirrored `.gemini/skills/` tree. In Azoth, that mirror is intentionally retired to avoid duplicate discovery and runtime warnings.

## Gemini-Specific Command Names

Azoth now deploys stable Gemini command names for the collision-prone workflows while keeping canonical source command names unchanged in `.claude/commands/`.

| Canonical Azoth command | Gemini command |
|--------|--------|
| `/plan` | `/workspace.plan` |
| `/remember` | `/workspace.remember` |
| `/dynamic-full-auto` | `/workspace.dynamic-full-auto` |

All other commands keep their canonical names on the Gemini surface.

Gemini can still rename other commands in future if a built-in or discovered skill conflicts. If startup output shows a rename notice, trust the runtime alias printed by Gemini for that session.

## Tutorial 1: Start a Safe Gemini Session

Goal: open Gemini in the repo, confirm it loaded Azoth context, and orient yourself before changing anything.

1. Open a terminal in the repo root.
   ```bash
   cd C:\Github\AZOTH
   gemini
   ```
2. Watch the startup banner for three things:
   - The current workspace path is this repo.
   - `GEMINI.md` and `AGENTS.md` are part of the loaded context.
   - Any unexpected command rename notices are visible.
3. Run `/help` to inspect the active command surface for this session.
4. Ask Gemini to ground itself in the repo before you do real work. Example:
   ```text
   Read GEMINI.md and summarize the first thing a contributor should do in this repo.
   ```
5. Run `/start` to get the repo orientation flow.
   - If you only want the dashboard outside Gemini, use:
     ```bash
     python3 scripts/welcome.py
     ```
6. Decide your path:
   - `/next` if you want Azoth to pick the next scoped task.
   - `/auto <goal>` if you already know your goal.
   - `/roadmap` if you need roadmap context first.

Expected outcome: Gemini is attached to the repo, you know the active command surface, and you have either an orientation snapshot or a scoped next step.

## Tutorial 2: Use the Core Azoth Workflow From Gemini

Goal: run a normal Azoth work session from Gemini without bypassing scope or closeout.

### Path A: Standard contributor flow

1. Start orientation:
   ```text
   /start
   ```
2. Open or refresh scope:
   ```text
   /next
   ```
3. Ask Gemini to execute a concrete goal through the default pipeline:
   ```text
   /auto update the Gemini platform guide with one more troubleshooting note
   ```
4. Review the declaration or informational pipeline card Gemini presents.
5. Let Gemini complete the work.
6. Close the session correctly:
   ```text
   /session-closeout
   ```

### Path B: Pre-approved small work

If the task is already approved and does not need `/auto` classification:

```text
/deliver add a short README link to the Gemini guide
```

### Path C: Planning only

```text
/workspace.plan write a small onboarding improvement for Gemini users
```

Core commands worth learning first:

| Intent | Command |
|--------|---------|
| Orient session | `/start` |
| Pick next scoped work | `/next` |
| Auto-classify and route | `/auto <goal>` |
| Pre-approved delivery | `/deliver <goal>` |
| Quality gate | `/eval` |
| Roadmap snapshot | `/roadmap` |
| Session closeout | `/session-closeout` |

Expected outcome: you can run a normal Azoth session in Gemini from orientation through scoped execution to closeout.

## Tutorial 3: Maintain the Gemini Adapter

Goal: understand what to change when Gemini behavior in this repo needs to evolve.

1. Edit canonical sources, not generated Gemini files, unless you are intentionally debugging deployment output.
   - Agents: `agents/**/*.agent.md`
   - Commands: `.claude/commands/*.md`
   - Skills: `skills/**/SKILL.md`
   - Gemini templates: `kernel/templates/platform-adapters/gemini/`
2. Regenerate deployed surfaces:
   ```bash
   python3 scripts/azoth-deploy.py
   ```
3. Verify nothing drifted:
   ```bash
   python3 scripts/azoth-deploy.py --check
   ```
4. Smoke-test Gemini non-interactively:
   ```bash
   gemini -p "Reply in one line: Gemini adapter smoke test."
   ```
5. Smoke-test Gemini interactively:
   ```bash
   gemini
   ```
   Then check for:
   - startup loads without skill-surface warnings
   - expected command names, or explicit rename notices
   - working `/start`, `/next`, and `/auto`

### Troubleshooting

| Symptom | What to check |
|--------|---------------|
| Skill conflict warnings | Confirm `.agents/skills/` is the only Gemini-family skill surface and rerun `python3 scripts/azoth-deploy.py` |
| Missing Gemini command | Check `.gemini/commands/` and rerun deploy |
| Wrong command name in session | Use `/help` and the runtime alias Gemini printed at startup |
| Generated file drift | Run `python3 scripts/azoth-deploy.py --check` |

Expected outcome: you know which files are canonical, how to regenerate the Gemini adapter, and how to verify that Gemini sees the repo the way Azoth intends.

## Recommended First Session

If you only want one short practice loop, use this exact sequence:

1. `gemini`
2. `/help`
3. `/start`
4. `/next`
5. `/auto explain the current top Gemini-related backlog item in this repo`
6. `/session-closeout`

That sequence exercises the core Azoth session lifecycle in Gemini without requiring you to start with a risky code change.

## References

- `GEMINI.md`
- `AGENTS.md`
- `README.md`
- `docs/DAY0_TUTORIAL.md`
- `scripts/azoth-deploy.py`
- `kernel/templates/platform-adapters/gemini/`
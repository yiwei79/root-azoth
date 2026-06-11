# Hermes as Azoth Operating Substrate

> Status: implemented in phase/v0.2.0-p5-hermes-substrate (workshop branch `hermes/azoth-improvements`).
> Decision: D56.

## Why

The 2026-05-01 meta-research concluded that the meta-harness target shape is:

> one strategic brain, explicit side-effectful hands, durable session/event log,
> context views instead of always-loaded doctrine, progressive-disclosure skills,
> permission gates, and trace grading.

Hermes Agent's primitive surface maps onto this shape more directly than per-IDE
adapter engineering. The kernel becomes **profile-level state** in Hermes, not
**repo-level state** in every consumer install.

This is the long-promised `meta-harness-experimental` direction from the
comparison profiles — the one Azoth should move toward if migration is approved.

## Mapping

| Azoth construct | Hermes primitive | Where |
|---|---|---|
| Kernel (BOOTLOADER + TRUST_CONTRACT + GOVERNANCE + PROMOTION_RUBRIC + TRUST_HOSTS) | Profile state + AGENTS.md shim | `~/.hermes/profiles/azoth-personal-cockpit/` |
| M3 episodic memory | `session_search` (FTS5 + bookends) | Hermes session DB |
| M2 human-approved patterns | `memory` tool, target=`memory` + target=`user` | auto-loaded each turn |
| M1 procedural knowledge | `skill_manage` + profile skills | `~/.hermes/profiles/azoth-personal-cockpit/skills/` |
| Pipeline orchestration | `delegate_task` (tasks array, role: leaf) | isolated subagent context |
| Scheduled watchdog | `cronjob` (script: true, no_agent: true) | drift detection, receipt digest |
| Long-running delivery | `terminal(background=True, notify_on_complete=True)` | test runs, release builds |
| 4-panel authority firewall | Hermes profile isolation | each panel is a profile |
| Friction-event guards | subprocess via `terminal` | `scripts/azoth_guards.py` (FD-003/004/005/008) |
| Manifest drift check | subprocess via `terminal` + `cronjob` | `scripts/hermes_manifest_check.py` |

## Operating model

The kernel is installed **once per profile**, not per project. Projects reference
the kernel via their own AGENTS.md shim (read-only pointer). This collapses the
manifest-vs-reality drift: the kernel is wherever the profile is.

Trust-bearing hosts (Codex + Hermes + OpenCode) all share the kernel checksum.
A drift run on any one detects drift on the others. The other four platforms
(Copilot, Cursor, Gemini, Antigravity) ship best-effort mirrors with explicit
"instructional, not mechanical" warnings — see `kernel/TRUST_HOSTS.md`.

## Daily operator flow

```
1. Open Hermes cockpit profile (active: azoth-personal-cockpit)
2. `python3 scripts/cockpit_menu.py --check`   # validates cockpit state
3. `python3 scripts/cockpit_menu.py`           # renders safe-open menu
4. Choose a project; the cockpit prints a switch-into-project prompt
5. cd to the project repo; project-local AGENTS.md loads
6. Run /next or `python3 scripts/personal_harness_context.py --json`
7. Use `delegate_task` for any subagent fan-out (FD-003 guard)
8. Use `session_search` to recall prior sessions (FD-005 guard)
9. Close with /session-closeout; receipt written
10. Drift check (cronjob) verifies kernel integrity overnight
```

## Hermes-visible shim layer

Hermes's `terminal` tool runs in a sandboxed shell whose `PATH` does not include
the operator's standard install locations. The fix is a shim layer at
`~/.hermes/profiles/azoth-personal-cockpit/bin/` that execs the real binary by
absolute path. Currently shipped shims:

- `opencode` → `/Users/yiwei/.opencode/bin/opencode` (override: `AZOTH_OPENCODE_PATH`)
- `codex` → `/Users/yiwei/.npm-global/bin/codex` (override: `AZOTH_CODEX_PATH`)
- `tirith` → direct binary (pre-existing)

Hermes must invoke these by absolute path (e.g.
`~/.hermes/profiles/azoth-personal-cockpit/bin/opencode ...`); by-name
invocation does not work because the profile bin dir is not on Hermes's PATH.

## Anti-patterns

- Do not install the kernel per-project; install once per profile.
- Do not bulk-copy root-azoth memory into the cockpit (Wrong #4 from the
  2026-06-11 review — knowledge management literature says small + cited beats
  richly-typed).
- Do not rely on per-IDE adapter enforcement for trust; the trust-bearing hosts
  run the runtime guards as subprocesses.
- Do not inline architect/builder/reviewer work; spawn via `delegate_task`.
- Do not invoke shim binaries by name; use absolute paths.

## Migration note

A consumer project that wants trust-bearing behavior must:

1. Be operated from one of the three trust-bearing hosts.
2. Reference the kernel via AGENTS.md (read-only pointer).
3. Run `python3 scripts/hermes_manifest_check.py` before any session that
   touches governed state.
4. Use `scripts/azoth_guards.py` before marking any scope complete.

If the operator is on a best-effort mirror host, the kernel is documented but
not enforced. Drift detection runs in CI; runtime guards run when invoked
manually.

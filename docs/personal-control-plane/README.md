# Personal Control Plane

This directory is the workshop-side reference for the Azoth personal control
plane. The control plane itself lives in **Hermes profile state**, not in
workshop files.

## Where the personal control plane lives now

The personal control plane is governed by Hermes profile state:

- **Profile kernel**: `~/.hermes/profiles/azoth-personal-cockpit/`
- **Operating skill** (loads on demand): `~/.hermes/profiles/azoth-personal-cockpit/skills/azoth-substrate/SKILL.md`
- **Substrate doc**: `docs/HERMES_SUBSTRATE.md` (workshop)
- **Trust-bearing hosts**: `kernel/TRUST_HOSTS.md` (workshop)
- **Cockpit user surface**: `yiwei-azoth-cockpit/scripts/cockpit_menu.py`
- **Personal cockpit onboarding**: `docs/personal-control-plane/YIWEI-AZOTH-COCKPIT-OPERATOR-ONBOARDING.md`
- **Multi-control-panel UX anchor**: `docs/personal-control-plane/MULTI-CONTROL-PANEL-UX-ANCHOR.md`
- **Deployment procedure**: `docs/personal-control-plane/PERSONAL-CONTROL-PLANE-DEPLOYMENT-PROCEDURE.md`

## Why the K0–K7 architecture was retired (2026-06-11)

The previous `PERSONAL-KNOWLEDGE-ARCHITECTURE.md` defined 8 knowledge classes
(K0–K7), a 13-required-field card contract, a 7-step import flow, and a 7-phase
rollout. That schema was heavier than a single operator with three or four
projects needs.

Knowledge management literature (PARA, Zettelkasten, Luhmann) consistently
shows that **small, cited, linked notes beat richly-typed, centrally-curated
notes**. Anthropic's multi-agent-research post says the same about retrieval:
"relevant context is few and cited."

The replacement:

- **M2 semantic memory** (was `patterns.yaml` with 13 required fields) → Hermes `memory` tool, target=`memory` (project facts) or target=`user` (operator preferences). Auto-loaded into every turn, profile-scoped, durable.
- **M3 episodic memory** (was `episodes.jsonl` bulk) → Hermes `session_search` over the session DB. FTS5 + bookends + role filter. Retrieval shape matches the kernel's D45 context-sensitive-retrieval intent.
- **Knowledge cards** (was 13-field YAML) → `~/.hermes/profiles/azoth-personal-cockpit/memories/` plus a flat `NOTES.md` per project. No central curator, no enum-on-type, no freshness policy.
- **Import flow** (was 8 steps) → `session_search` for retrieval; direct write for capture. No inbox draining.
- **7-phase rollout** → single install: `~/.hermes/profiles/azoth-personal-cockpit/` is the personal root, set up once.

The retired spec lives at `_retired/PERSONAL-KNOWLEDGE-ARCHITECTURE.md` for
historical reference (and the original rollout plan at
`_retired/2026-04-29-personal-knowledge-architecture-rollout.md`). Historical
roadmap entries (`.azoth/roadmap-specs/v0.2.0/T-040..T-053`) reference the
retired doc by path — those pointers are now stale but the entries themselves
are historical evidence of the 7-phase plan that was superseded.

## Operator daily flow

1. Open Hermes cockpit profile.
2. Run `python3 scripts/cockpit_menu.py --check` (validates cockpit state).
3. Run `python3 scripts/cockpit_menu.py` (renders safe-open menu).
4. Choose a project pointer; the cockpit prints a switch-into-project prompt.
5. `cd` to the project repo; project-local AGENTS.md governs from there.
6. Run `/next` or `python3 scripts/personal_harness_context.py --json` to get the route.
7. Use `delegate_task` for subagent fan-out (FD-003 guard).
8. Use `session_search` to recall prior sessions (M3 replacement).
9. `/session-closeout` writes the receipt.
10. Drift check (cronjob) verifies kernel integrity overnight.

## Authority firewall (unchanged from UX anchor)

- **Developer panel** (`root-azoth`): toolkit source, tests, governance, roadmap, release evidence.
- **Product panel** (public `azoth`): clean extracted release surface.
- **Personal control panel** (cockpit): operator inventory, knowledge, project pointers, releases.
- **Project panel** (per-project repo): project-local code, project memory, project gates.

The panels cooperate through explicit handoffs and never inherit each
other's authority.

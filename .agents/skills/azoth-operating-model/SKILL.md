---
name: azoth-operating-model
description: |
  Cold-start Azoth orientation for Antigravity sessions. Use when starting work,
  choosing a workflow, checking scope, or deciding whether work fits the
  bootstrap adapter boundary.
---

# Azoth Operating Model

## Read First

- `AGENTS.md`
- `CLAUDE.md`
- `.azoth/backlog.yaml`
- `.azoth/roadmap.yaml`
- `.azoth/scope-gate.json` when present

## Workflow Routing

- `/next`: choose the next queue item and open scope
- `/auto`: classify a goal and compose a standard-work pipeline
- `/deliver`: execute pre-approved additive infrastructure work
- `/session-closeout`: checkpoint W1, W2, and W4 at the end of the session

## Repo Authority

- `.azoth/` is canonical for scope, pipeline gates, handoffs, memory, and session state.
- `AGENTS.md` and `CLAUDE.md` define broad behavior.
- Platform memory is supplemental, not authoritative.

## Antigravity Bootstrap Limits

- Supported here: standard infrastructure, docs, and adapter work.
- Not supported here: governed M1 or kernel delivery, direct Claude hook parity, or D46 deploy-target integration.
- If the user asks for kernel or governance changes, stop and redirect to a governed path.

## Delivery Expectations

- Prefer isolated planning and review stages when critique must not share context with implementation.
- Preserve typed YAML handoffs when downstream stages depend on prior critique.
- Validate touched files and run focused tests.
- Keep file count and change scope bounded.
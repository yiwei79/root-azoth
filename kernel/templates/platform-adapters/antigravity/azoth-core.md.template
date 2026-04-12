# Azoth Core

Apply this rule as Always On for the workspace.

This repository uses Azoth. Treat the repo-local `.azoth/` state as authoritative.

## Read path

- Read `AGENTS.md` and `CLAUDE.md` for project identity and global operating rules.
- Read `.azoth/backlog.yaml` and `.azoth/roadmap.yaml` for queue and phase context.
- Read `.azoth/scope-gate.json` before write work. If it is missing, unapproved, or expired, stop and ask the user to run `/next` or otherwise approve scope.
- Read `.azoth/pipeline-gate.json` when the selected workflow requires a delivery gate.

## Workflow routing

- Use `/next` to pick the next task and open scope.
- Use `/auto` to classify a goal and compose a standard-work pipeline.
- Use `/deliver` for pre-approved additive infrastructure work.
- Use `/session-closeout` before ending a session.

## Antigravity bootstrap boundary

- This bootstrap path covers standard infrastructure, docs, and adapter work only.
- If work touches `kernel/`, `kernel/templates/`, governance docs, or any backlog item with `target_layer: M1`, stop and redirect to the governed Claude Code, Copilot, or Cursor path.
- Do not claim Claude hook parity. Re-express safety through workflow checks, strict mode, permissions, sandboxing, and human review.

## Execution posture

- Prefer isolated planning and review stages when critique should not share context with implementation.
- Keep writes inside the workspace. Prefer strict mode and disable non-workspace file access.
- Preserve BL-012 typed YAML handoffs when a workflow spans multiple gated stages.
- Prefer repo-local state over platform memory for scope, session, and handoff facts.

## Session close

- W1, W2, and W4 under `.azoth/` remain the shared cross-IDE contract.
- Treat Claude-only project-memory mirroring as out of scope for this bootstrap adapter.

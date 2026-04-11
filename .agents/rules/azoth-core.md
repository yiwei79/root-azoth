# Azoth Core

Apply this rule as Always On for the workspace.

This repository uses Azoth. Treat the repo-local `.azoth/` state as authoritative.

## Compliance Checklist (P1-016)

Before **any** write work in a session, verify every item. If any item fails, **STOP**.

1. **Scope gate valid?** — Read `.azoth/scope-gate.json`. Require `approved: true` and
   `expires_at` in the future. If missing, expired, or unapproved, stop and ask the user
   to run `/next`.
2. **Workflow file read?** — Before executing a workflow (`/auto`, `/deliver`, `/deliver-full`,
   `/session-closeout`), read the full workflow file first. Do not paraphrase from memory.
3. **Classification/declaration complete?** — For `/auto`: Stage 0 classification must be
   output as a visible YAML block and the composed pipeline Declaration must be presented
   to the human before any implementation begins.
4. **Human approval received?** — For any pipeline: the human must explicitly approve the
   pipeline composition or scope card before the build stage runs. "Pipeline started" does
   not override a missing approval.
5. **Pipeline gate written?** — For governed work (`delivery_pipeline: governed` or
   `target_layer: M1`), `.azoth/pipeline-gate.json` must exist per `docs/GATE_PROTOCOL.md`
   before any Write/Edit.

## STOP Conditions

Immediately halt and present the issue to the human if:

- Scope gate is missing, expired, or `approved: false`
- A review/audit stage returns `request-changes`, `BLOCKED`, or `CRITICAL` findings
- Entropy enters RED zone (≥ 25 delta or ≥ 10 files in a single turn)
- Work would touch `kernel/`, governance docs, or any `target_layer: M1` item (redirect to governed path)
- Pipeline composition has not been approved but build stage is about to start
- Write-claim conflict detected in `.azoth/run-ledger.local.yaml`

## Read Path

- Read `AGENTS.md` and `CLAUDE.md` for project identity and global operating rules.
- Read `.azoth/backlog.yaml` and `.azoth/roadmap.yaml` for queue and phase context.
- Read `.azoth/scope-gate.json` before write work (see Compliance Checklist §1).
- Read `.azoth/pipeline-gate.json` when the selected workflow requires a delivery gate.

## Memory System Integration

- **Session start:** `/start` must invoke the `context-recall` skill after showing the
  welcome dashboard, before routing to a workflow. Surface relevant M3 episodes and M2
  patterns for the goal domain.
- **Session close:** `/session-closeout` must invoke the `remember` skill during W1 to
  structure and capture the episode. Do not skip M3 capture.
- **Entropy tracking:** At each pipeline stage boundary, perform a self-check using the
  `entropy-guard` skill: count files changed, lines changed, and classify the zone
  (GREEN/YELLOW/RED). Include the zone in any alignment summary output.

## Workflow Routing

- Use `/next` to pick the next task and open scope.
- Use `/auto` to classify a goal and compose a standard-work pipeline.
- Use `/deliver` for pre-approved additive infrastructure work.
- Use `/session-closeout` before ending a session.

## Antigravity Bootstrap Boundary

- This bootstrap path covers standard infrastructure, docs, and adapter work only.
- If work touches `kernel/`, `kernel/templates/`, governance docs, or any backlog item
  with `target_layer: M1`, stop and redirect to the governed Claude Code, Copilot, or
  Cursor path.
- Do not claim Claude hook parity. Re-express safety through workflow precondition checks,
  strict mode, permissions, sandboxing, and human review.

### Antigravity Limitations (honest)

- **No subagent isolation.** Antigravity does not support `Agent()` or `Task()` spawning.
  Pipeline stages run inline in the same context. Review stages cannot be context-isolated
  from the stages they review. This is an accepted degradation — document it in alignment
  summaries.
- **No PreToolUse blocking.** Scope-gate and pipeline-gate checks are instruction-only.
  A sufficiently confused agent can bypass them. The Compliance Checklist above makes the
  correct path explicit but cannot mechanically block writes.
- **No SessionStart injection.** Orientation context is not auto-injected. The `/start`
  workflow must be invoked manually or the agent must read `.azoth/scope-gate.json` and
  backlog context explicitly.

## Execution Posture

- Prefer isolated planning and review stages when critique should not share context with
  implementation (even though Antigravity cannot enforce isolation mechanically, maintain
  the stage separation in workflow output).
- Keep writes inside the workspace. Prefer strict mode and disable non-workspace file access.
- Preserve BL-012 typed YAML handoffs when a workflow spans multiple gated stages.
- Prefer repo-local state over platform memory for scope, session, and handoff facts.

## Session Close

- W1, W2, and W4 under `.azoth/` remain the shared cross-IDE contract.
- W3 (platform memory) maps to Gemini Knowledge Items on Antigravity — update if
  the platform supports it; otherwise log `W3 skipped (no Antigravity KI write path)`.
- Treat Claude-only project-memory mirroring as out of scope for this bootstrap adapter.

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

## Compliance Checklist

Before writing any file, verify:

1. `.azoth/scope-gate.json` exists, is approved, and has not expired.
2. Target files are inside the approved scope (not `kernel/`, not governance).
3. Entropy delta stays in GREEN zone (< 12). Checkpoint if approaching YELLOW.
4. Use `entropy-guard` skill to track blast radius during multi-file changes.
5. Use `context-recall` skill at session start to surface relevant M3 episodes and M2 patterns.
6. Use `remember` skill at session close to capture durable lessons.

## STOP Conditions

Halt immediately and redirect to the governed Claude Code / Copilot / Cursor path if:

- Work touches `kernel/`, `kernel/templates/`, or any governance doc.
- A backlog item has `target_layer: M1` or `delivery_pipeline: governed`.
- Entropy delta reaches RED zone (≥ 25).
- A pipeline gate fails or returns `BLOCKED` / `CRITICAL`.

## Memory System Integration

- Use `context-recall` at SURVEY / Stage 0 to read M3 episodes and M2 patterns by goal tags.
- Use `remember` at session closeout to append structured episodes to `.azoth/memory/episodes.jsonl`.
- Use `entropy-guard` during pipeline execution to monitor and bound blast radius.
- Memory promotion (M2→M1) is always out of scope for this bootstrap adapter — governed path only.

## Antigravity Limitations

This bootstrap adapter does NOT have parity with Claude Code or Cursor:

- **No subagent isolation**: Antigravity lacks `Task` tool or equivalent. Multi-stage pipelines run sequentially in the same context. Critique stages may share context with implementation.
- **No PreToolUse blocking**: There are no mechanical hooks to enforce scope-gate or entropy limits. Compliance is instruction-based only — the agent must self-check before every write.
- **No SessionStart hooks**: `welcome.py` must be invoked manually; there is no automatic session orientation injection.
- **No native slash-command routing**: Pipeline tokens (`/auto`, `/deliver`, etc.) are recognized by instruction, not by platform mechanics.

## Session close

- W1, W2, and W4 under `.azoth/` remain the shared cross-IDE contract.
- Treat Claude-only project-memory mirroring as out of scope for this bootstrap adapter.

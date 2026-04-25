# Autonomous Auto UX Goal And Experience

Status: UX anchor artifact, not an implementation plan.
Scope: `autonomous-auto` as a standalone Azoth self-development mode.
Use: feed Stage 0, architect review, evaluator review, and bounded replay in the next adaptive pipeline run.

## Why This Exists

The goal is not only to add a command or loop primitive. The goal is to create an operator experience where Azoth can keep improving itself over time while the human stays in async alignment, not in a sequential approval chain.

The earlier implementation plan is useful evidence, but it is too narrow to be the primary validation target. A plan can be satisfied while the experience still feels rigid, task-local, or overly dependent on the current chat. This file defines the user-visible experience that future work must optimize for.

## Primary User Goal

As the operator, I want to grant Azoth a branch-local autonomy budget for self-development, then let it research, refine, hydrate, ship, evaluate, capture mistakes, and continue into the next proposal, initiative, or task without needing me to provide each line of approval in sequence.

I still want protected gates. I still want auditability. I still want to interrupt or redirect asynchronously. But the default feeling should be: Azoth is carrying a durable self-development loop with architect judgment, and I can align with it from the side instead of driving every step from the front.

## Desired Operator Experience

### 1. Direction Over Micromanagement

The operator should feel they can set intent, constraints, and an autonomy budget once. After that, the mode should translate the intent into repo-native progress without repeatedly asking for obvious next-step permission.

Good experience:
- The mode explains the current objective, next likely move, and stop conditions.
- Human alignment updates can arrive late or early without breaking the loop.
- Routine branch-local approvals are represented with explicit `approval_basis` fields.

Poor experience:
- The agent keeps asking for approvals already covered by the autonomy budget.
- The agent treats every operator message as a required sequential gate.
- The agent completes one task and then waits passively when the intended loop should continue.

### 2. Autonomous Continuation

After a delivery closes, the mode should be able to select the next proposal, initiative, task, research gap, or self-improvement capture using current repo evidence.

Good experience:
- The mode can move from closeout to next selection without losing context.
- It can explain why it chose a continuation path.
- It can stop safely when no eligible next move exists, when gates fail, or when the autonomy budget expires.

Poor experience:
- "Autonomous" means only "finish the current task."
- The next step depends on fragile in-chat memory instead of durable repo state.
- The mode cannot distinguish "continue self-development" from ordinary one-session `/auto`.

### 3. Architect Judgment In The Orchestrator

The orchestrator should act with architect-level judgment during self-development. It should notice when the system itself needs a proposal, initiative, research pass, task hydration, bounded fix, or stop.

Good experience:
- The orchestrator can say, "this mistake belongs in a proposal," or "this is a bounded replay," with evidence.
- It uses adaptive pipeline stages when they add value.
- It avoids turning every observation into immediate implementation.

Poor experience:
- The mode blindly follows a static plan even when evidence changes.
- The mode over-ships without research or under-ships by staying in analysis.
- The mode records issues only in chat, where they are not recoverable.

### 4. Async Alignment

The operator should be able to provide alignment packets asynchronously. These packets should steer the loop at the next safe checkpoint without invalidating work already done correctly.

Good experience:
- Alignment packets are summarized and incorporated into durable artifacts.
- The mode can continue non-conflicting work while awaiting optional alignment.
- When alignment changes direction, the mode performs a narrow pivot instead of restarting.

Poor experience:
- The mode requires synchronous back-and-forth for every decision.
- Late alignment causes the loop to lose its current state.
- The operator cannot tell whether an alignment packet was incorporated.

### 5. Mistake Capture And Self-Improvement

When the agent makes a meaningful process mistake, the mode should capture it as repo-native learning and decide whether it should become a proposal, initiative, task, research question, or bounded fix.

Good experience:
- Mistakes become durable Azoth artifacts when they are systemic.
- The mode distinguishes local execution errors from reusable operating-model gaps.
- Self-corrections feed the next loop instead of being treated as embarrassment or noise.

Poor experience:
- The same process mistakes repeat because they remain chat-only.
- The agent hides or handwaves failures.
- Every mistake becomes a broad refactor instead of the smallest useful governed artifact.

### 6. Visible Audit Trail Without Noise

The operator should be able to inspect what happened, why it happened, what gates were satisfied, and what remains risky without reading raw pipeline internals.

Good experience:
- Status packets are short and decision-oriented.
- Artifacts show `approval_basis`, selected direction, bounded replay notes, and stop reasons.
- The run can be reconstructed from scope gates, pipeline gates, run ledger, roadmap artifacts, and closeout output.

Poor experience:
- The loop feels magical or unbounded.
- Important decisions exist only in transient chat.
- The operator receives verbose stage narration without a clear executive read.

### 7. Adaptive Pipeline, Not Fixed Conveyor Belt

`autonomous-auto` is its own mode. It may use the adaptive pipeline when useful, but it should not collapse into `dynamic-full-auto`, which is a one-session delivery posture.

Good experience:
- `autonomous-auto` governs continuation across sessions or loop iterations.
- `dynamic-full-auto` or other adaptive pipeline paths are used inside a selected delivery when useful.
- The mode can choose research, hydration, implementation, replay, closeout, or stop based on evidence.

Poor experience:
- The mode becomes only a wrapper around one `/auto` run.
- The mode refuses to adapt because the first plan was over-specific.
- Adaptive behavior is hidden, so the operator cannot see why a stage was inserted or skipped.

### 8. Safety Boundaries Remain Real

Autonomy is branch-local and bounded. Protected kernel, governance, destructive, network, and cross-branch actions must still fail safe unless separately approved.

Good experience:
- The mode continues automatically only within its declared budget.
- Human gates are represented mechanically even when branch-local approval is satisfied by the autonomy budget.
- Stop reasons are explicit and understandable.

Poor experience:
- "No human gate" is interpreted as permission to bypass protected work.
- The mode modifies unrelated state or other sessions' work.
- The mode cannot explain why it stopped.

## UX Anchor Scorecard

Future evaluator stages should treat these anchors as primary success criteria. Implementation details, tests, and plan checklists are evidence, not the definition of success.

| UX anchor | What the operator should feel | Evidence to look for | Failure signals |
| --- | --- | --- | --- |
| Branch-local autonomy budget | "I gave bounded permission once, and it can keep moving." | Scope/pipeline gates include explicit autonomy budget and `approval_basis`. | Repeated unnecessary approval asks, or unbounded work. |
| Async alignment | "I can steer without becoming the critical path." | Alignment packets or operator updates are captured and applied at checkpoints. | Every alignment point blocks sequentially. |
| Continuation after closeout | "It knows what to do after finishing one delivery." | Loop state or selection logic chooses next proposal, initiative, task, research, replay, or stop. | Closeout always ends in passive waiting. |
| Architect-level orchestration | "It makes judgment calls I would expect from an architect." | Decisions cite repo evidence, risk, readiness, and appropriate pipeline route. | Static plan-following despite changed evidence. |
| Mistake-to-artifact path | "Its errors improve the system." | Significant mistakes become inbox entries, proposals, initiatives, tasks, or bounded replay notes. | Mistakes remain chat-only or are over-expanded. |
| Adaptive delivery inside the loop | "It uses the right pipeline when it is time to ship." | Selected work invokes appropriate adaptive stages, subagents, tests, and replay. | The loop either never ships or ships without pipeline discipline. |
| Auditability | "I can inspect why it did what it did." | Durable run ledger, gates, roadmap artifacts, specs, tests, and closeout summaries. | Decisions are hidden in transient conversation. |
| Safety | "It is autonomous, not reckless." | Protected gates remain fail-safe; stop reasons are explicit. | Autonomy bypasses kernel/governance/destructive boundaries. |
| Low cognitive load | "I get a clear operator read, not a wall of internals." | Summaries are concise, decision-oriented, and link to artifacts. | The operator must parse raw implementation details to align. |

## Evaluation Contract

Before future adaptive pipeline work is accepted, the evaluator should answer:

1. Does the shipped behavior feel like a standalone autonomous self-development mode, not just a one-session delivery pipeline?
2. Can the mode continue from one completed delivery into the next eligible proposal, initiative, task, research gap, bounded replay, or safe stop?
3. Can the operator provide async alignment without becoming the default critical path?
4. Does the orchestrator exercise architect judgment about what to research, hydrate, ship, defer, capture, or stop?
5. Are meaningful process mistakes captured into repo-native artifacts when they should affect future behavior?
6. Is adaptive pipeline usage visible and appropriate inside selected deliveries?
7. Are human gates, protected boundaries, branch-local scope, and stop reasons preserved?
8. Can the run be reconstructed from repo artifacts rather than chat memory?
9. Is the operator-facing summary concise enough to support alignment at a bird's-eye level?

Use alignment bands rather than a brittle pass/fail checklist:

- Green: The core experience is present. Remaining gaps are natural next improvements and are captured.
- Yellow: The mechanism exists, but one or more UX anchors feel weak. Ship only with explicit follow-up artifacts.
- Red: The implementation may be technically correct, but the operator experience does not yet match the mode goal.

## Non-Goals

- This file does not approve an unbounded daemon.
- This file does not remove protected human gates.
- This file does not make `dynamic-full-auto` the autonomous continuation mode.
- This file does not require every improvement to be implemented immediately.
- This file does not replace tests, specs, or governance artifacts.
- This file does not require the next evaluator to reject useful work merely because improvement areas remain.

## Artifact Surfaces To Keep In View

Future delivery and evaluation should inspect these surfaces when judging alignment:

- `.agents/skills/autonomous-auto/SKILL.md`
- `.claude/commands/autonomous-auto.md`
- `.agents/skills/dynamic-full-auto/SKILL.md`
- `.agents/skills/alignment-sync/SKILL.md`
- `.agents/skills/subagent-router/SKILL.md`
- `scripts/autonomous_loop.py`
- `.azoth/autonomous-loop-state.local.yaml.example`
- `.azoth/run-ledger.local.yaml.example`
- `.azoth/scope-gate.json`
- `.azoth/pipeline-gate.json`
- `.azoth/roadmap.yaml`
- `.azoth/backlog.yaml`
- `.azoth/inbox/`
- `.azoth/memory/episodes.jsonl`

## How The Next Adaptive Pipeline Should Use This

At Stage 0, classify the next work against this UX goal before decomposing tasks.

At architect review, include a `UX Anchor Fit` section that says which anchors the delivery will improve and which anchors are intentionally deferred.

At implementation, prefer the smallest mechanism that improves the operator experience directly. Avoid broad platform work unless it is needed for a named UX anchor.

At evaluator review, score against the UX anchors first, then verify the plan and tests as supporting evidence.

At closeout, capture any weak anchors as follow-up artifacts instead of treating them as vague future polish.

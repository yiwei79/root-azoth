# Autonomous Auto UX Goal And Experience

Status: UX anchor artifact, not an implementation plan.
Scope: `autonomous-auto` as a standalone Azoth self-development mode.
Use: feed Stage 0, architect review, evaluator review, and bounded replay in the next adaptive pipeline run.

## Why This Exists

The goal is not only to add a command or loop primitive. The goal is to create an operator experience where Azoth can keep improving itself over time while the human stays in async alignment, not in a sequential approval chain.

The earlier implementation plan is useful evidence, but it is too narrow to be the primary validation target. A plan can be satisfied while the experience still feels rigid, task-local, or overly dependent on the current chat. This file defines the user-visible experience that future work must optimize for.

The calibrated bar is campaign-level autonomy. When the operator says to open a campaign, the expected behavior is not "pick the next task." It is: discover the roadmap system, identify a vision-driven campaign that can span multiple sessions and tasks, run a strategy layer that makes route decisions, and automate as much of the development work as can be safely governed by repo-native state.

## Primary User Goal

As the operator, I want to grant Azoth a branch-local autonomy budget for a vision-driven campaign, then let it discover the roadmap system, interpret my intent, choose a strategic route, research, refine, hydrate, ship, evaluate, capture mistakes, and continue across multiple sessions or tasks without needing me to provide each line of approval in sequence.

I still want protected gates. I still want auditability. I still want to interrupt or redirect asynchronously. But the default feeling should be: Azoth is carrying a durable self-development campaign with architect judgment, and I can align with it from the side instead of driving every step from the front.

The intended operator feeling is relaxed, low-pressure coding. I should be able to give goals, visions, corrections, or taste signals at non-fixed intervals, then trust the autonomous layer to interpret them, maintain campaign state, and work through Azoth-native discovery, strategy, research, hydration, delivery, evaluation, and learning loops without turning my messages into an ad hoc task queue.

## Campaign Definition

An autonomous-auto campaign is a strategy object over the roadmap system, not a single scoped delivery.

A valid campaign:

- starts from roadmap/proposal/initiative/backlog discovery, not chat memory alone
- defines a vision-level objective and success anchor before opening child work
- may encompass multiple sessions, child scopes, tasks, research passes, hydration steps, delivery runs, evaluations, and closeouts
- owns a strategy layer that can reassess route, budget, readiness, risk, and next move after each checkpoint
- self-identifies operator intent and decomposes it into smaller native work units when the goal is broad
- decides when initiative-level research or task-level research is sufficiently complete to hydrate or ship
- opens child scopes as execution moves inside the campaign, not as the campaign itself
- records why it chose the current route and why rejected alternatives were not opened
- closes the learning loop by updating code, tests, instructions, initiative/proposal state, or governed lesson artifacts when the system itself needs to improve

A campaign is not valid if it merely selects one task, runs `/auto`, and calls that "autonomous" without strategy, continuation, repo-native discovery, or learning closure.

## Desired Operator Experience

### 1. Direction Over Micromanagement

The operator should feel they can set intent, constraints, and an autonomy budget once at the campaign level. After that, the mode should translate the intent into repo-native progress without repeatedly asking for obvious next-step permission.

Good experience:
- The mode explains the current objective, next likely move, and stop conditions.
- The mode explains the campaign strategy, not only the immediate child task.
- Human alignment updates can arrive late or early without breaking the loop.
- The operator can send goals or corrections irregularly, without needing to babysit the next action.
- Routine branch-local approvals are represented with explicit `approval_basis` fields.

Poor experience:
- The agent keeps asking for approvals already covered by the autonomy budget.
- The agent treats every operator message as a required sequential gate.
- The agent completes one task and then waits passively when the intended loop should continue.
- The agent narrows a campaign into a task-local plan without showing why that is the right strategic move.

### 2. Roadmap-Discovered Campaign Strategy

Before opening work, the mode should discover the roadmap system and choose a campaign shape that is vision-driven, not merely the next visible item.

Good experience:
- The mode reads initiative banks, proposals, backlog, roadmap specs, gates, loop state, and recent lessons before selecting a route.
- The campaign declaration names the vision, selected seed, strategy-preflight verdict, route authority, allowed action classes, and protected boundaries.
- The route decision distinguishes stale old-loop authority from fresh campaign authority.
- The campaign can say "research first," "hydrate next," "ship this task," "repair the router," "capture the lesson," or "stop" with evidence.
- The campaign decomposes broad intent into smaller roadmap-native slices instead of asking the operator to pre-split everything.

Poor experience:
- The mode opens the first available task without roadmap-level discovery.
- The mode treats a recommendation packet as open authority instead of advisory strategy input.
- The operator cannot tell whether the campaign is broad enough, too narrow, or blocked by route conflict.

### 3. Autonomous Continuation

After a delivery closes, the mode should be able to select the next proposal, initiative, task, research gap, or self-improvement capture using current repo evidence.

Good experience:
- The mode can move from closeout to next selection without losing context.
- It can explain why it chose a continuation path.
- It can stop safely when no eligible next move exists, when gates fail, or when the autonomy budget expires.

Poor experience:
- "Autonomous" means only "finish the current task."
- The next step depends on fragile in-chat memory instead of durable repo state.
- The mode cannot distinguish "continue self-development" from ordinary one-session `/auto`.

### 4. Campaign Strategy Layer

The orchestrator should act with architect-level judgment at the campaign layer. It should notice when the system itself needs a proposal, initiative, research pass, task hydration, bounded fix, subagent wave, or stop.

Good experience:
- The orchestrator can say, "this mistake belongs in a proposal," or "this is a bounded replay," with evidence.
- The orchestrator can spend strategy budget before opening delivery, then adjust after each checkpoint.
- It treats child scopes as moves inside a larger campaign strategy.
- It self-identifies whether the current need is intent clarification, initiative research, task research, hydration, implementation, evaluation, replay, or closeout.
- It uses adaptive pipeline stages when they add value.
- It avoids turning every observation into immediate implementation.

Poor experience:
- The mode blindly follows a static plan even when evidence changes.
- The mode over-ships without research or under-ships by staying in analysis.
- The mode records issues only in chat, where they are not recoverable.
- The mode has no explicit strategy-preflight verdict before init or open-next.

### 5. Async Alignment

The operator should be able to provide alignment packets asynchronously. These packets should steer the loop at the next safe checkpoint without invalidating work already done correctly.

Good experience:
- Alignment packets are summarized and incorporated into durable artifacts.
- The mode can continue non-conflicting work while awaiting optional alignment.
- When alignment changes direction, the mode performs a narrow pivot instead of restarting.
- Corrections are interpreted as campaign strategy signals first, then translated into repo-native action through the loop.

Poor experience:
- The mode requires synchronous back-and-forth for every decision.
- Late alignment causes the loop to lose its current state.
- The operator cannot tell whether an alignment packet was incorporated.
- Corrections trigger one-off quick fixes instead of entering a governed strategy and learning loop.

### 6. Research, Readiness, Hydration, And Shipping Judgment

The mode should know how to move from fuzzy goal to researched initiative, from researched initiative to hydrated task, and from hydrated task to shipping work using native readiness evidence.

Good experience:
- Broad goals become initiative-level research questions, candidate slices, and readiness criteria.
- Task-level work gets its own focused research when the task knowledge base is not sufficient.
- The mode can explain why knowledge is enough to hydrate, why hydration should wait, or why shipping can begin.
- Hydration into roadmap/backlog/spec state happens only when readiness, approval scope, and scaffold evidence are explicit.
- Shipping starts only after the selected task has enough context, acceptance criteria, tests, and safe execution boundaries.

Poor experience:
- The mode hydrates a task because the operator sounded enthusiastic rather than because readiness is green.
- The mode ships from shallow knowledge when initiative or task research is still open.
- The mode stays in endless research because it cannot decide when evidence is sufficient.
- The mode asks the operator to manually decide every readiness transition that the system should infer from native artifacts.

### 7. Mistake Capture And Self-Improvement

When the agent makes a meaningful process mistake, the mode should capture it as repo-native learning and decide whether it should become a proposal, initiative, task, research question, or bounded fix.

Good experience:
- Mistakes become durable Azoth artifacts when they are systemic.
- The mode distinguishes local execution errors from reusable operating-model gaps.
- Self-corrections feed the next loop instead of being treated as embarrassment or noise.
- Operator corrections are converted into reusable policy, tests, proposals, initiative updates, or skill changes when they reveal a pattern.

Poor experience:
- The same process mistakes repeat because they remain chat-only.
- The agent hides or handwaves failures.
- Every mistake becomes a broad refactor instead of the smallest useful governed artifact.
- The agent patches the current symptom without updating the loop that produced it.

### 8. Visible Audit Trail Without Noise

The operator should be able to inspect what happened, why it happened, what gates were satisfied, and what remains risky without reading raw pipeline internals.

Good experience:
- Status packets are short and decision-oriented.
- Artifacts show `approval_basis`, campaign vision, route authority, strategy-preflight verdict, selected direction, bounded replay notes, and stop reasons.
- The run can be reconstructed from scope gates, pipeline gates, run ledger, roadmap artifacts, and closeout output.
- The operator receives calm executive reads that preserve the chill coding experience while still exposing the important decisions.

Poor experience:
- The loop feels magical or unbounded.
- Important decisions exist only in transient chat.
- The operator receives verbose stage narration without a clear executive read.
- Campaign-level decisions are mixed together with child-task implementation details.

### 9. Adaptive Pipeline, Not Fixed Conveyor Belt

`autonomous-auto` is its own mode. It may use the adaptive pipeline when useful, but it should not collapse into `dynamic-full-auto`, which is a one-session delivery posture.

Good experience:
- `autonomous-auto` governs continuation across sessions or loop iterations.
- `dynamic-full-auto` or other adaptive pipeline paths are used inside a selected delivery when useful.
- The mode can choose research, hydration, implementation, replay, closeout, or stop based on evidence.
- Subagents are staged as execution capacity for the campaign, with clear ownership and review boundaries.
- The pipeline adapts to the current knowledge state: discovery when intent is fuzzy, research when evidence is thin, hydration when readiness is green, delivery when task truth is executable, and replay when review/eval finds gaps.

Poor experience:
- The mode becomes only a wrapper around one `/auto` run.
- The mode refuses to adapt because the first plan was over-specific.
- Adaptive behavior is hidden, so the operator cannot see why a stage was inserted or skipped.
- Subagents are omitted or used decoratively when the campaign requires staged strategy, research, implementation, or evaluation.

### 10. Safety Boundaries Remain Real

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
| Relaxed async operator experience | "I can drop goals or corrections when I have them, and the system keeps working." | Alignment packets, status reads, and campaign state show irregular operator input being incorporated at checkpoints. | The operator has to babysit each next step or convert ideas into task instructions. |
| Campaign-level strategy | "It is running a vision-driven development campaign, not a task picker." | Campaign declaration names vision, selected seed, route authority, strategy-preflight verdict, allowed actions, budget, and stop conditions. | The mode selects one task without roadmap discovery or strategic rationale. |
| Roadmap-system discovery | "It knows the system it is operating inside." | Decisions inspect initiative banks, proposals, backlog, roadmap specs, gates, loop state, and lesson artifacts. | The campaign depends on chat memory or a stale recommendation packet. |
| Intent interpretation and decomposition | "I can give a broad vision, and it finds the smaller native work units." | Broad goals become initiative questions, candidate slices, hydration plans, task research, or scoped delivery moves. | The operator must manually split the work or the mode opens an oversized scope. |
| Async alignment | "I can steer without becoming the critical path." | Alignment packets or operator updates are captured and applied at checkpoints. | Every alignment point blocks sequentially. |
| Continuation after closeout | "It knows what to do after finishing one delivery." | Loop state or selection logic chooses next proposal, initiative, task, research, replay, or stop. | Closeout always ends in passive waiting. |
| Architect-level orchestration | "It makes judgment calls I would expect from an architect." | Decisions cite repo evidence, risk, readiness, and appropriate pipeline route. | Static plan-following despite changed evidence. |
| Strategy-preflight route authority | "Before it opens work, it proves this is the right kind of work." | Recommendation packets and declarations include route/preflight verdict, selected route, route state, approval scope, and blocked alternatives. | Advisory recommendations are treated as open authority, or route conflicts are ignored. |
| Research-to-readiness judgment | "It knows when to research, hydrate, or ship." | Readiness reports, task research, acceptance criteria, scaffold commands, and route decisions explain the transition. | Hydration/ship starts from shallow evidence, or research never converges. |
| Mistake-to-artifact path | "Its errors improve the system." | Significant mistakes become inbox entries, proposals, initiatives, tasks, or bounded replay notes. | Mistakes remain chat-only or are over-expanded. |
| Multi-session execution | "It can carry a campaign across sessions and child scopes." | Loop state, closeout, history, and route decisions preserve campaign continuity across child work. | Each session behaves as an unrelated one-off delivery. |
| Adaptive delivery inside the loop | "It uses the right pipeline when it is time to ship." | Selected work invokes appropriate adaptive stages, subagents, tests, and replay. | The loop either never ships or ships without pipeline discipline. |
| Auditability | "I can inspect why it did what it did." | Durable run ledger, gates, roadmap artifacts, specs, tests, and closeout summaries. | Decisions are hidden in transient conversation. |
| Safety | "It is autonomous, not reckless." | Protected gates remain fail-safe; stop reasons are explicit. | Autonomy bypasses kernel/governance/destructive boundaries. |
| Low cognitive load | "I get a clear operator read, not a wall of internals." | Summaries are concise, decision-oriented, and link to artifacts. | The operator must parse raw implementation details to align. |

## Evaluation Contract

Before future adaptive pipeline work is accepted, the evaluator should answer:

1. Does the shipped behavior feel like a standalone autonomous self-development mode, not just a one-session delivery pipeline?
2. Did the campaign discover roadmap/proposal/initiative/backlog/gate state before selecting a route?
3. Is the campaign vision-driven, with a strategy layer that can span multiple sessions, child scopes, and tasks?
4. Does the mode preserve a relaxed async operator experience where goals and corrections can arrive at non-fixed intervals?
5. Can the mode interpret broad intent and decompose it into roadmap-native initiatives, candidate slices, task research, hydration, delivery, or capture work?
6. Does the declaration include route authority, strategy-preflight verdict, selected route, route state, approval scope, blocked alternatives, budget, and protected boundaries?
7. Can the mode continue from one completed delivery into the next eligible proposal, initiative, task, research gap, bounded replay, or safe stop?
8. Can the operator provide async alignment without becoming the default critical path?
9. Does the orchestrator exercise architect judgment about what to research, hydrate, ship, defer, capture, or stop?
10. Does the mode decide when initiative or task knowledge is sufficient for hydration or shipping using native readiness evidence?
11. Are meaningful process mistakes and operator corrections captured into repo-native artifacts when they should affect future behavior?
12. Is adaptive pipeline usage visible and appropriate inside selected deliveries?
13. Are human gates, protected boundaries, branch-local scope, and stop reasons preserved?
14. Can the campaign be reconstructed from repo artifacts rather than chat memory?
15. Is the operator-facing summary concise enough to support alignment at a bird's-eye level?

Use alignment bands rather than a brittle pass/fail checklist:

- Green: The core experience is present. Remaining gaps are natural next improvements and are captured.
- Yellow: The mechanism exists, but one or more UX anchors feel weak. Ship only with explicit follow-up artifacts.
- Red: The implementation may be technically correct, but the operator experience does not yet match the mode goal.

## Campaign-Level Green Bar

Green autonomous-auto behavior means:

- the campaign starts with repo-native discovery and a vision declaration
- the strategy layer owns route selection before delivery opens
- broad operator intent is interpreted and decomposed into native campaign moves
- async corrections update strategy through checkpoints rather than ad hoc quick fixes
- advisory recommendations remain advisory until route/preflight and approval agree
- initiative and task research converge into explicit readiness judgments before hydration or shipping
- child scopes are opened as deliberate campaign moves with staged subagents where useful
- closeout is a campaign checkpoint, not automatically the end of the campaign
- meaningful lessons change future behavior through code, tests, skills, proposals, initiative state, or governed inbox artifacts
- the operator can understand the current campaign from one concise executive read

## Non-Goals

- This file does not approve an unbounded daemon.
- This file does not remove protected human gates.
- This file does not make `dynamic-full-auto` the autonomous continuation mode.
- This file does not define a campaign as a single task or a single `/auto` run.
- This file does not require the operator to provide input on a fixed schedule.
- This file does not allow "autonomy" to mean ad hoc quick fixes outside the closed loop.
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
- `.azoth/initiative-banks/`
- `.azoth/proposals/`
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

Before opening a campaign, perform roadmap-system discovery and produce a campaign declaration with vision, route authority, strategy-preflight verdict, selected seed, allowed action classes, budget, stop conditions, protected boundaries, and evidence links.

During the campaign, treat operator input as asynchronous alignment. Classify whether it changes vision, constraints, route, acceptance, taste, or stop conditions; then apply it at the next safe checkpoint through the same strategy and readiness loop.

At architect review, include a `UX Anchor Fit` section that says which anchors the campaign will improve, which anchors are intentionally deferred, and why the current child scope is the right move inside the larger campaign.

At implementation, prefer the smallest mechanism that improves the operator experience directly. Avoid broad platform work unless it is needed for a named UX anchor.

At evaluator review, score against the UX anchors first, then verify the plan and tests as supporting evidence.

At closeout, capture any weak anchors as follow-up artifacts instead of treating them as vague future polish.

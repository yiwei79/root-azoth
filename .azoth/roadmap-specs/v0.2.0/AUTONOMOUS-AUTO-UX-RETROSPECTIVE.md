# Autonomous Auto UX Retrospective

Status: retrospective capture
Session: `2026-04-25-adhoc-autonomous-auto-ux-retro`
Mode used: `dynamic-full-auto`
Anchor: `.azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md`

## Executive Read

Alignment band: Yellow.

`autonomous-auto` is not just a renamed `/auto` run. The repo now has a standalone command/skill surface, a deterministic loop governor, explicit `approval_basis` propagation, bounded next-scope opening, stale-decision refusal, protected-gate stops, and tests for core continuation paths.

The feature is not yet Green against the UX anchor because the strongest operator-experience promises are still thin or mostly declarative:

- Async alignment has packet classes in instructions, but no durable packet queue, classifier, disposition record, or checkpoint application path.
- Mistake-to-artifact capture can be selected through `self_capture_queue`, but there is no materializer that writes inbox, proposal, initiative, backlog, or bounded replay artifacts.
- Architect judgment is currently a deterministic first/sorted candidate selector with generic rationale, not a readiness/risk/opportunity comparison.
- The operator read is still JSON/dict-shaped rather than a short alignment packet.
- UX-anchor evaluation is not yet wired into the autonomous-auto command or skill, so future runs can still validate against a too-strict or too-mechanical plan.

The right next move is not a rewrite. The robust path is to keep the safety core and add the missing UX mechanisms in small Azoth-native slices.

## Dynamic-Full-Auto Route

Stage 0 classification:

- `scope: docs/planning`
- `risk: additive`
- `complexity: medium`
- `knowledge: known-pattern/local-evidence`

Adaptive route:

- Wave A external research skipped. Current external facts were not material, and Codex network is restricted.
- Wave B local implementation-surface explore ran with an isolated explorer.
- Wave C UX-anchor evaluation ran with an independent evaluator because the target crosses command, skill, loop, tests, and operator experience surfaces.
- Capture stage wrote this retrospective and inbox follow-up entries.

## Strengths To Preserve

| UX anchor | Current evidence | Why it matters |
| --- | --- | --- |
| Standalone mode identity | `skills/autonomous-auto/SKILL.md` defines the mode as not a `dynamic-full-auto` submode; `.claude/commands/autonomous-auto.md` routes it through `pipeline_command=autonomous-auto`. | The operator can distinguish autonomous self-development from one-session delivery. |
| Branch-local autonomy budget | `.azoth/autonomous-loop-state.local.yaml.example` includes `autonomy_budget.approval_basis`, max iterations, and allowed actions; `scripts/autonomous_loop.py` refuses missing approval basis. | Autonomy is bounded and auditable. |
| Continuation after closeout | `scripts/autonomous_loop.py decide_next` can choose queue, self-capture, backlog, ready initiative hydration, research initiative, proposal refinement, or safe stop. | The mode can move beyond passive closeout. |
| Safety boundaries | Protected layers, governed pipelines, credentials, network, destructive flags, stale decisions, active scope, and active session conflicts all stop continuation. | The loop is autonomous, not reckless. |
| Staged pipeline compatibility | `subagent-router` includes `autonomous-auto` in BL-011/BL-012 contracts. | The mode can use adaptive pipeline discipline inside selected deliveries. |

## Gaps

### G1 - Async Alignment Is Mostly Declarative

Evidence:

- `skills/autonomous-auto/SKILL.md` defines alignment packet classes and checkpoint behavior.
- `.claude/commands/autonomous-auto.md` repeats the same operator-line semantics.
- `.azoth/autonomous-loop-state.local.yaml.example` has no `alignment_packets`, `alignment_dispositions`, or checkpoint fields.
- `scripts/autonomous_loop.py` writes `alignment_mode: async` into opened scopes but has no ingest, classify, apply, or audit path for packets.

UX impact:

The operator can say alignment is async, but cannot inspect whether a late packet was captured, classified, applied, deferred, or rejected.

Capture:

Add a durable alignment-packet path with packet id, packet type, source, received_at, applies_at_checkpoint, disposition, affected artifact, and replay requirement. Add tests for advisory, override, stop, and approval-basis packets.

### G2 - Mistake Capture Does Not Yet Materialize Artifacts

Evidence:

- The skill says the loop should reflect on mistakes and capture self-improvement signals as inbox, proposal, initiative, or backlog candidates.
- `scripts/autonomous_loop.py` prioritizes `self_capture_queue` and can select `capture_self_improvement`.
- There is no code path that writes an inbox JSONL entry, proposal draft, initiative-bank candidate, backlog item, or bounded replay note from that selection.

UX impact:

The mode can decide that a mistake should be captured, but the operator still depends on the agent to perform a separate manual artifact-writing step.

Capture:

Add a self-capture materializer that turns a selected capture candidate into a repo-native artifact and records the materialization in loop history.

### G3 - UX Anchor Is Not Wired Into The Mode

Evidence:

- The UX anchor says Stage 0, architect review, evaluator review, and closeout should use UX anchors.
- The autonomous-auto skill and command do not reference `AUTONOMOUS-AUTO-UX-EXPERIENCE.md` or require a `UX Anchor Fit` section.
- Existing tests assert presence of autonomous-auto markers, but do not assert UX-anchor evaluation behavior.

UX impact:

Future work can regress into plan-compliance validation and miss the actual operator experience.

Capture:

Update autonomous-auto stage contracts so architect and evaluator stages explicitly read the UX anchor and produce `UX Anchor Fit` / `UX Anchor Scorecard` sections when the work affects the autonomous mode.

### G4 - Architect Judgment Is Too Shallow

Evidence:

- Candidate selection scans queue, self-capture, backlog, initiative banks, research initiatives, and proposals in fixed order.
- Backlog selection sorts by priority and picks the first ready candidate.
- Ready initiative and proposal selection use first eligible file ordering.
- Rationale strings are generic, such as "Selected the highest-priority ready backlog task."

UX impact:

The mode may continue, but it does not yet feel like the orchestrator is acting with the user's architect judgment about readiness, compounding value, risk, or opportunity cost.

Capture:

Add an architect-decision scoring capsule for each continuation choice. It should compare at least readiness, UX-anchor value, risk, dependency state, and stop cost, then persist why the selected next action won.

### G5 - Operator Read Is Too Raw

Evidence:

- `scripts/autonomous_loop.py status` prints a JSON/dict-shaped payload with state, can_continue, active scope/session, and stop reason.
- The UX anchor asks for short decision-oriented status packets with objective, next likely move, approval basis, stop conditions, and residual risk.

UX impact:

The operator still has to parse implementation state to understand whether the loop is aligned.

Capture:

Add an operator-read command or status mode that emits a concise alignment packet distinct from raw JSON.

## Overengineering Risks

### O1 - Loop Governor Reimplements A Mini Next Router

`scripts/autonomous_loop.py` scans backlog, initiative banks, proposal files, and self-capture queues directly. This is useful as a deterministic governor, but it can drift from existing `/next`, planning-bank readiness, proposal promotion, and roadmap routing semantics.

Preferred direction:

Keep deterministic safety checks in the governor, but either route candidate discovery through existing Azoth readiness surfaces or record explicit divergence when the governor chooses a local fallback.

### O2 - Protected Flag Taxonomy Is Broader Than UX Mechanisms

The protected flag detection is intentionally conservative and well-tested, but the safety taxonomy is more developed than async alignment, mistake capture, and operator-read mechanisms.

Preferred direction:

Do not remove safety. Bring UX mechanisms up to the same maturity level.

### O3 - `next_candidate` Is In The Example But Not Used

The loop state example includes `next_candidate`, and `open_next` clears it, but no audited read path uses it.

Preferred direction:

Either implement `next_candidate` as an explicit preview/hold field for async alignment, or remove it from the example to reduce misleading affordances.

## Misalignments

| Misalignment | Evidence | Correction |
| --- | --- | --- |
| UX anchor not part of autonomous-auto execution contract | UX anchor requires future stages to use it, but autonomous-auto skill/command do not reference it. | Add UX-anchor read and scorecard obligations to autonomous-auto when the work affects autonomous mode behavior. |
| Continuation feels deterministic, not architect-grade | Selection chooses first/sorted candidates with generic rationale. | Add a scoring/rationale capsule and persist rejected alternatives. |
| Mistake capture is a queue, not artifact materialization | `self_capture_queue` selection exists; no writer exists. | Add materializer for inbox/proposal/initiative/backlog/bounded replay capture. |
| Async alignment lacks durable state | Packet classes exist only in instruction text. | Add packet ledger/state and checkpoint application logic. |
| Operator read is not yet low cognitive load | Status is raw JSON/dict output. | Add concise status packet output for alignment. |

## Recommended Follow-Up Slices

1. `alignment-packet-ledger`
   - Add durable packet schema/state and classifier/apply behavior.
   - Tests: advisory, override, stop, approval-basis; packet disposition visible in status.

2. `self-capture-materializer`
   - Convert selected self-capture candidates into `.azoth/inbox` JSONL entries first.
   - Later slices can promote to proposal, initiative, or backlog.

3. `ux-anchor-fit-contract`
   - Require autonomous-auto architect/evaluator stages to read the UX anchor and output UX fit/scorecard sections.
   - Add deploy/parity tests for command and skill surfaces.

4. `architect-next-decision-capsule`
   - Add readiness/risk/value scoring for continuation choices.
   - Persist selected and rejected alternatives in loop history.

5. `operator-read-status`
   - Add a concise status output for objective, current loop state, next likely move, approval basis, stop reason, and residual risk.

## Acceptance Bar For Green

The mode should be considered Green only when a future evaluator can verify:

- Async alignment packets are durable and visibly incorporated.
- Mistakes can become repo-native artifacts without a manual chat-only step.
- Continuation choices include architect-grade rationale and rejected alternatives.
- The UX anchor participates in autonomous-auto stage contracts and tests.
- The operator can understand the loop state from a concise status packet.
- Existing safety and gate behavior remains fail-closed.

# Harness Rethink Deep Dive

Date: 2026-05-04
Campaign: `product-strategy-orchestrator-20260504`
Child scope: `2026-05-04-autonomous-auto-harness-rethink-deep-dive-4`
Action: `research_initiative`
Status: complete enough to route the next PM move

## Question

What should Azoth become before this campaign refines or productizes the
orchestrator's product-management workflow?

## Source Read

Primary source:

- `.azoth/proposals/azoth-harness-rethink-2026.yaml`

Supporting sources:

- `.azoth/campaigns/product-strategy-orchestrator-20260504/child-1-portfolio-inventory.md`
- `.azoth/campaigns/product-strategy-orchestrator-20260504/child-2-product-strategy-operating-model.md`
- `.azoth/campaigns/product-strategy-orchestrator-20260504/child-3-product-strategy-decision-surface.md`
- `.azoth/proposals/initiative-discovery-to-roadmap-hydration.yaml`
- `.azoth/proposals/autonomous-initiative-lifecycle-orchestration.yaml`
- `.azoth/roadmap-specs/v0.2.0/AUTONOMOUS-AUTO-UX-EXPERIENCE.md`
- `.azoth/roadmap-specs/v0.2.0/INI-PLT-006-execution-plan.md`

Referenced but absent in this checkout:

- `.azoth/research/azoth-harness-rethink-source-matrix-2026-05-01.yaml`
- `.azoth/roadmap-specs/v0.2.0/AZOTH-HARNESS-RETHINK-CONTRACT.yaml`

The absent artifacts matter because the proposal names them as source matrix
and contract evidence. Their absence lowers readiness for any implementation or
default-profile decision.

## What Harness Rethink Contributes

Harness Rethink is the right strategic frame. It argues that Azoth should become
a smaller durable meta-harness instead of accumulating more deterministic
machinery by default. Its stable interfaces are:

- Brain: one strategic model brain.
- Hands: execution capacity used when ownership, parallelism, or review
  independence is real.
- SessionLog: durable continuity and audit state.
- ContextView: generated, task-relevant views instead of raw context dumping.
- RouteCapsule: compact route, stop, and next-action state.
- HarnessProfile: stock-lite, azoth-lite, azoth-full, or experimental
  meta-harness.
- Skills: progressive-disclosure instructions instead of monolithic prompts.

This directly matches the operator's requested experience: smart product
management choices, not mechanical task selection.

## Readiness Gaps

Harness Rethink should not drive implementation yet.

- The proposal is `draft`.
- The referenced source matrix is absent.
- The referenced structured contract is absent.
- The proposal's own non-goals block immediate deletion of existing pipeline,
  kernel/governance edits, default-profile switches, and broad autonomous swarm
  changes.
- The proposal requires benchmark evidence before promoting simplification.
- Current campaign authority allows only `research_initiative`,
  `refine_proposal`, and `ship_task` strategy/report artifacts.

## Product Decision

**Decision:** fold Harness Rethink into the Product Strategy Orchestrator as a
strategic constraint, not as the next implementation lane.

**Do not simplify now.**

**Do not defer entirely.**

**Do fold into Initiative Discovery next.**

Reason: Harness Rethink answers "what Azoth should become," but the next safe
campaign move is to refine the practical PM workflow that can turn broad
initiatives into researched, challenged, gated slices. Initiative Discovery is
where the orchestrator's smart PM choices become repeatable without crossing
hydration or delivery boundaries.

## Implications For The PM Workflow

The next Initiative Discovery refinement should inherit these constraints:

- Prefer one campaign brain that makes explicit product choices.
- Treat execution hands as capacity, not ceremony.
- Keep route capsules compact and reusable at child boundaries.
- Preserve source-of-truth boundaries: strategy artifacts recommend, roadmap
  and backlog authorize.
- Make readiness visible before hydration.
- Keep protected gates fail-closed.
- Prefer generated context views and research banks over broad context dumping.
- Use evals and validators before changing default harness profiles.

## Rejected Routes

- `ship_task` for a harness contract: blocked because the named contract is a
  roadmap-spec artifact and campaign authority is limited to campaign reports.
- `hydrate_task`: blocked without fresh human approval.
- Harness implementation: blocked by readiness gaps and proposal non-goals.
- Public release parity: remains too close to protected public/release work.
- Memory recall adoption: useful, but narrower than the PM campaign spine.

## Next Child Recommendation

Action: `refine_proposal`

Candidate id: `initiative-discovery-pm-lane`

Title: `Initiative Discovery PM Lane`

Expected output:

- A campaign-local refinement that turns Initiative Discovery into the Product
  Strategy Orchestrator's practical operating lane.
- A staged sequence for discovery, challenge, readiness, plan-only hydration
  handoff, and human-gated hydration.
- Explicit Harness Rethink constraints folded into the workflow.
- No roadmap/backlog/spec writes.

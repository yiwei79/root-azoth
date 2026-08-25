# Product Strategy Operating Model

Date: 2026-05-04
Campaign: `product-strategy-orchestrator-20260504`
Child scope: `2026-05-04-autonomous-auto-product-strategy-operating-model-2`
Action: `refine_proposal`
Status: active strategy model for the remaining campaign

## Purpose

The Product Strategy Orchestrator is a campaign-bounded product-management
loop. Its job is not to execute the nearest artifact. Its job is to choose what
kind of product move Azoth should make next, explain why, and preserve the
authority boundary between strategy, roadmap truth, delivery, release, and
packaging.

## Core Model

Use three layers:

1. **Strategic Frame**

   Source: `azoth-harness-rethink-2026`

   Decide what Azoth should become before adding machinery. The current strategic
   frame is a small durable meta-harness: one strategic brain, explicit execution
   hands, durable session log, generated context views, progressive skills,
   runtime guards, and eval-backed profile choices.

2. **Product-Management Workflow**

   Source: `initiative-discovery-to-roadmap-hydration`

   Treat ideas as opportunities before treating them as delivery. Compare
   options, challenge assumptions, build readiness, and hydrate only when the
   first slice is smaller than the initiative and the authority gate is explicit.

3. **Autonomous Routing Substrate**

   Source: `autonomous-initiative-lifecycle-orchestration`

   Use `research_initiative`, `refine_proposal`, `hydrate_task`, `ship_task`,
   `capture_self_improvement`, and `stop` as route verbs. In this campaign,
   `hydrate_task` remains blocked until fresh human approval names the exact
   candidate and scaffold/write path.

## Product Choice Loop

At each child boundary, the orchestrator should answer:

- What product question are we answering?
- What are the candidate lanes?
- Which lane has the best ratio of leverage, readiness, PM fit, and bounded risk?
- Is the next safe action discovery, proposal refinement, strategy-board
  shipping, hydration, delivery, packaging, or stop?
- What protected gate would this choice cross?
- What evidence would change the decision?
- What must remain canonical outside this strategy artifact?

## Scoring Dimensions

Use the child-1 scorecard dimensions:

- `strategic_leverage`: Does this improve Azoth's core product direction?
- `readiness`: Is there enough repo-native evidence to act without guessing?
- `pm_fit`: Does this strengthen the orchestrator's product-management ability?
- `protected_risk`: How close is the lane to release, public, cockpit/project,
  governance, network, credential, destructive, or broad rephasing boundaries?

Derived route:

- High leverage + low readiness: `research_initiative`
- High PM fit + moderate readiness: `refine_proposal`
- Stable strategy artifact needed: `ship_task`
- Hydration/delivery desire but missing explicit gate: `stop_for_human_gate`
- Protected action required: `stop_for_human_gate`

## Current Strategy Decision

The campaign should not jump straight into public release parity or memory
recall adoption. Those are product lanes. The orchestrator needs one more
strategy surface first:

**Next child:** `ship_task`

**Candidate:** `product-strategy-decision-surface`

**Why:** The campaign now has an inventory and operating model. The next move is
to ship a non-authoritative decision surface that future child scopes can use to
compare lanes and choose the next safe action without replacing roadmap/backlog
truth.

## Candidate Lane Ordering

1. **Product Strategy Decision Surface**
   - Route: `ship_task`
   - Reason: Makes the PM loop concrete and reusable inside this campaign.
   - Authority: non-authoritative campaign artifact only.

2. **Harness Rethink Deep Dive**
   - Route: `research_initiative` or `refine_proposal`
   - Reason: Highest strategic leverage, but should be evaluated before defaults
     or implementation change.

3. **Initiative Discovery PM Lane**
   - Route: `refine_proposal`
   - Reason: Best workflow fit for product management. Likely the first lane to
     become a durable orchestrator capability after the decision surface exists.

4. **Public Release Root Feature Parity**
   - Route: `research_initiative`
   - Reason: High product value, but close to public release/protected gates.

5. **INI-MEM-003 Recall Quality**
   - Route: later `research_initiative` or gated `hydrate_task`
   - Reason: Bounded quality improvement, but less central to product strategy.

## Protected Gates

Stop for human intervention before:

- `hydrate_task`
- roadmap/backlog/spec writes
- public sync or release
- public checkout mutation
- cockpit or project writes
- backup/private remote or credential work
- network/dependency expansion
- destructive actions
- kernel/governance/M1 mutation
- broad roadmap/backlog rephasing
- commit or push

## Packaging Rule

A campaign can be strategically Green while the repo is still dirty. The
orchestrator must surface both truths separately:

- Campaign truth: did the approved objective reach its vision score?
- Packaging truth: are artifacts staged/committed or otherwise intentionally
  left dirty?

The current campaign still inherits uncommitted artifacts from the completed
INI-RST-006 campaign and new strategy artifacts from this campaign.

## Recommended Child 3

Action: `ship_task`

Candidate id: `product-strategy-decision-surface`

Title: `Product strategy decision surface`

Output:

- A non-authoritative campaign strategy board or decision capsule.
- A route table for product lanes.
- A selected next lane recommendation with rejected alternatives.
- No roadmap/backlog/spec hydration.

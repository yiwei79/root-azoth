# Product Strategy Decision Surface

Date: 2026-05-04
Campaign: `product-strategy-orchestrator-20260504`
Child scope: `2026-05-04-autonomous-auto-product-strategy-decision-surface-3`
Action: `ship_task`
Status: active non-authoritative strategy surface

## Authority Boundary

This surface is a campaign artifact. It helps the Product Strategy Orchestrator
choose and explain product-management moves, but it does not replace
`.azoth/roadmap.yaml`, `.azoth/backlog.yaml`, initiative banks, proposal banks,
or any protected governance/release gate.

It may recommend discovery, refinement, strategy-board shipping, or a human
stop. It may not silently hydrate tasks, mutate canonical roadmap/backlog state,
change public/cockpit/project checkouts, commit, push, or claim release
readiness.

## Current Inputs

- Child 1 produced the portfolio inventory and scorecard.
- Child 2 produced the operating model:
  - Harness Rethink supplies the strategic frame.
  - Initiative Discovery supplies the product-management workflow.
  - Autonomous Initiative Lifecycle supplies the routing substrate.
- The campaign remains branch-local and non-protected.
- INI-RST-006 is campaign-Green but still uncommitted; packaging truth remains
  separate from strategy truth.

## Decision Rule

At every child boundary, prefer the smallest route that answers the product
question without crossing an authority boundary:

| Situation | Preferred Route | Stop Condition |
| --- | --- | --- |
| Portfolio or evidence is missing | `research_initiative` | Stop if source truth is ambiguous or protected |
| Strategy frame is incomplete | `research_initiative` or `refine_proposal` | Stop before implementation defaults change |
| Product-management model is clear but not concrete | `ship_task` | Stop before roadmap/backlog/spec writes |
| Lane is valuable but assumption-heavy | `research_initiative` | Stop before hydration |
| Lane has enough evidence but needs sequencing | `refine_proposal` | Stop before task creation |
| Hydration or delivery becomes the next real move | `stop_for_human_gate` | Requires explicit human approval |
| Public release, public checkout, cockpit/project, backup/private remote, credentials, dependencies, destructive operations, kernel/governance/M1, commit, or push are needed | `stop_for_human_gate` | Always requires fresh human approval |

## Candidate Lane Board

| Rank | Lane | Product Question | Recommended Route | PM Judgment |
| ---: | --- | --- | --- | --- |
| 1 | Harness Rethink Deep Dive | What should Azoth become before we add more orchestration machinery? | `research_initiative` | Highest strategic leverage; ambiguity is still material. |
| 2 | Initiative Discovery PM Lane | How should ideas become researched, challenged, and eventually hydrated? | `refine_proposal` | Best workflow fit, likely next after strategic frame is clarified. |
| 3 | Autonomous Initiative Lifecycle | How should route verbs and stop conditions become a repeatable substrate? | `refine_proposal` | Useful mechanism, but it should serve product strategy. |
| 4 | Public Release Root Feature Parity | What belongs in a consumer-safe Full release? | `research_initiative` | High product value, but close to public/release gates. |
| 5 | INI-MEM-003 Recall Quality | How should recall quality improve operator/product decisions? | `research_initiative` | Bounded quality lane, not the central PM campaign spine. |

## Selected Next Lane

**Next child:** `research_initiative`

**Candidate id:** `harness-rethink-deep-dive`

**Why this wins now:** The user asked for a long-running intelligent campaign
where the orchestrator can make smart product-management choices. The first
smart choice is to clarify the strategic product shape before optimizing the
workflow around it. Harness Rethink has the highest leverage because it asks
whether Azoth should be a smaller durable meta-harness with one strong strategic
brain, explicit execution hands, durable session log, generated context views,
runtime guards, route capsules, harness profiles, and progressive skills.

This should be researched before any default-profile switch, governance edit,
public release implementation, dependency expansion, or roadmap/backlog
hydration.

## Rejected Alternatives

- **Jump directly to Initiative Discovery PM Lane:** good workflow fit, but it
  should be shaped by the strategic harness decision.
- **Open Public Release Parity:** strong product direction, but too close to
  protected public release and checkout boundaries for this ungated campaign.
- **Hydrate tasks now:** explicitly blocked; hydration requires a fresh human
  gate naming exact candidate and write paths.
- **Package or commit campaign artifacts now:** explicitly blocked unless the
  operator asks for packaging/commit work.
- **Adopt INI-MEM-003 as the main lane:** valuable, but narrower than the
  requested product-strategy capability.

## Evidence That Could Change The Decision

- If Harness Rethink proves too broad or under-evidenced, pivot to Initiative
  Discovery as the practical PM spine.
- If Initiative Discovery already contains enough strategic framing, child 5
  can refine it directly instead of extending the harness lane.
- If any next move requires canonical roadmap/backlog mutation, hydration,
  public/cockpit/project checkout writes, release, dependency/network work,
  credentials, destructive actions, kernel/governance/M1 mutation, commit, or
  push, the loop must stop for a human gate.

## Child 4 Recommendation

Action: `research_initiative`

Candidate id: `harness-rethink-deep-dive`

Expected outputs:

- A research brief comparing Harness Rethink against the current Azoth operating
  model.
- A product-shape decision: simplify meta-harness now, defer, or fold the
  insight into Initiative Discovery.
- Explicit non-goals and protected gates.
- No canonical roadmap/backlog/spec hydration.

# Product Strategy Orchestrator Child 1

Date: 2026-05-04
Campaign: `product-strategy-orchestrator-20260504`
Child scope: `2026-05-04-autonomous-auto-product-strategy-orchestrator-portfolio-inventory-1`
Action: `research_initiative`
Status: complete enough to proceed to proposal refinement

## Campaign Boundary

This campaign is a product-management and strategy campaign, not a direct
delivery campaign. It may compare, score, refine, and ship non-authoritative
strategy artifacts. It may not hydrate roadmap/backlog/spec work, mutate public
or cockpit/project checkouts, change kernel/governance/M1, expand dependencies
or network access, or commit/push without fresh approval.

Current packaging truth remains visible: the completed INI-RST-006 campaign is
Green, but its artifacts and closeout bookkeeping are still uncommitted.

## Portfolio Read

### A. Harness Rethink

Source: `.azoth/proposals/azoth-harness-rethink-2026.yaml`

This is the strategic umbrella. It asks whether Azoth should shift from a
deterministic workflow engine toward a smaller meta-harness with stable
interfaces: Brain, Hands, SessionLog, ContextView, RouteCapsule,
HarnessProfile, and Skills. It directly matches the operator's goal for smarter
orchestrator product judgment because it questions the whole control surface
before adding more machinery.

PM read: high leverage, high ambiguity, should guide the campaign's operating
model before implementation.

### B. Initiative Discovery Lane

Source: `.azoth/proposals/initiative-discovery-to-roadmap-hydration.yaml`

This is the product-management workflow proposal. It describes how phase-null
initiatives should move through discovery, research banks, challenge/refinement,
readiness, and only then hydration. It is the closest current artifact to a
real PM loop: compare opportunities, validate assumptions, then commit delivery.

PM read: strongest foundation for orchestrator choice-making; likely the next
proposal to refine into an operating model.

### C. Autonomous Initiative Lifecycle

Source: `.azoth/proposals/autonomous-initiative-lifecycle-orchestration.yaml`

This is the autonomous execution engine proposal. It defines the lifecycle
router that classifies whether an initiative needs research, proposal
refinement, hydration, shipping, capture, or stop. It supplies the routing
language this campaign should use, but it should not override product strategy.

PM read: essential mechanism, but it should serve the PM model rather than
become the product model by itself.

### D. Public Release Root Feature Parity

Source: `.azoth/proposals/public-release-root-feature-parity.yaml`

This is the most product-facing release lane. It argues that a public "Full"
Azoth release should include root-level capability classes transformed into
consumer-safe assets, not a narrow kernel-only subset. It is high product value
but also closer to protected public release and installer territory.

PM read: important candidate lane, but should follow a strategy model and likely
requires fresh gates before implementation.

### E. Memory Recall / INI-MEM-003

Source: `.azoth/initiative-banks/INI-MEM-003.yaml`

This is a focused product-quality lane for context recall and memory retrieval.
The bank already has useful readiness detail and a zero-dependency adoption path
for the recall-quality scorer. It is valuable and bounded, but less central to
the requested "proper smart product management choices" capability.

PM read: good candidate for a later selected lane after the orchestrator has a
portfolio and sequencing surface.

## Scorecard Summary

Scores are local product-management judgments for this campaign only. They are
not roadmap authority.

| Candidate | Strategic Leverage | Readiness | PM Fit | Protected Risk | Recommended Route |
| --- | ---: | ---: | ---: | ---: | --- |
| Harness Rethink | 10 | 6 | 9 | 6 | refine as strategic frame |
| Initiative Discovery Lane | 9 | 8 | 10 | 4 | refine as operating model |
| Autonomous Initiative Lifecycle | 8 | 8 | 8 | 5 | consume as routing substrate |
| Public Release Parity | 9 | 6 | 8 | 8 | defer implementation; keep as product lane |
| INI-MEM-003 Recall Quality | 6 | 8 | 5 | 5 | later focused lane |

## Product Strategy Judgment

The next child should refine a product strategy operating model that combines:

- Harness Rethink as the strategic frame: one strong brain, explicit execution
  hands, runtime guards, and profile-aware harnessing.
- Initiative Discovery Lane as the PM workflow: opportunity inventory,
  assumption challenge, readiness, and sequencing before delivery.
- Autonomous Initiative Lifecycle as the router: research/refine/hydrate/ship
  decisions with fail-closed protected gates.

This avoids jumping straight to public release parity or memory recall work.
Those are valuable product lanes, but the campaign first needs an orchestrator
decision model that can explain why one lane should beat another.

## Recommended Child 2

Action: `refine_proposal`

Candidate id: `product-strategy-operating-model`

Title: `Product strategy operating model`

Expected output:

- A refined strategy artifact under this campaign directory.
- A decision framework for orchestrator product choices.
- A next-lane recommendation that explicitly separates discovery, refinement,
  hydration, delivery, packaging, and protected gates.

## Stop Conditions

Stop for human intervention before:

- Any hydration or roadmap/backlog/spec write.
- Any public release or public checkout mutation.
- Any cockpit/project repo write.
- Any dependency/network/credential/destructive action.
- Any kernel/governance/M1 mutation.
- Any commit or push.

# Azoth

**A personal agent-engineering project about keeping intent connected to
outcomes across complex AI-assisted work.**

## Start with the work

I build software, data products and AI systems for operational teams. These
cases show the practical work that shaped Azoth:

| Work | What I delivered | Read the case |
|---|---|---|
| Production AI | Own a rider CRM from discovery and architecture through implementation and production operation; the platform has handled 41,000+ conversations. | [GloBuddy: engineering the system around the conversation](docs/case-studies/narrow-success-broad-failure.md#6-globuddy-a-later-agent-operations-system-in-its-own-right) |
| Operational data | Rebuilt fragmented reporting definitions into a BigQuery pipeline and decision dashboard used across 22 countries. | [SupplyOps: preserving meaning through delivery](docs/case-studies/narrow-success-broad-failure.md#1-operational-reporting-and-bigquery-migration-meaning-had-to-move-first) |
| Process and adoption | Redesigned logistics-partner administration and transferred the live workflow to another operations team. | [3PL: making an operating model transferable](docs/case-studies/narrow-success-broad-failure.md#2-3pl-administration-operational-knowledge-had-to-become-executable) |

Azoth is my independent engineering project. The systems above were delivered
at Glovo and helped shape its principles. For a technical walkthrough of
Azoth and its tested capabilities, see [Routing, Context, and Authority](docs/PERSONAL_HARNESS_OS.md).

Agent-assisted work can look successful until the larger outcome is checked. A
thread starts with a sound plan, discovers something important, follows the
detour, and produces a useful artifact—while the original intent, acceptance
boundary, evidence, or stopping condition quietly fades. The conversation
progressed; the work did not.

Longer prompts, larger context windows, and stronger models can improve an
individual thread. They do not by themselves make a transcript a durable plan,
evidence ledger, authority boundary, or outcome state.

```mermaid
flowchart TB
    subgraph C["Conversation-centred continuity"]
        direction LR
        C1["Intent lives mainly<br/>in one thread"] --> C2["Useful discovery<br/>changes the local plan"]
        C2 --> C3["Locally successful artifact"]
        C3 -.->|continuity was conversational| C4["Intent · evidence · authority<br/>must be reconstructed"]
    end

    subgraph O["Outcome-centred continuity"]
        direction LR
        O1["Durable intent anchor"] --> O2["Bounded work pulse"]
        O2 --> O3["Artifact · evidence<br/>· observed effect"]
        O3 -->|evaluate and update| O4["Durable outcome state<br/>next safe transition is explicit"]
    end

    C ~~~ O
```

Conversation remains useful as an interaction surface. The failure is asking a
bounded thread to also be the plan, memory, policy, evidence ledger, and history
of the whole effort.

> **A thread is a bounded work pulse. It reads from a durable intent anchor,
> changes or investigates a limited part of the work, and returns evidence for
> the next safe transition.**

Once that distinction is made, a harder question follows: if continuity and
useful intelligence are distributed across intent, state, people, tools,
evidence, and work pulses, where does the durable intelligence of the larger
effort live—and is any one thread really the agent?

Azoth explores that question by treating purpose, project meaning, evidence,
decisions, authority, recovery, and observed outcomes as persistent system
state. The intended experience is to state an outcome once, then let the system
expose missing knowledge, form and route bounded work, return evidence, and stop
at the decisions that still require human meaning or authority. “The system as
agent” is a useful analogy here, not a settled name for the durable whole.

## Azoth in one view

```mermaid
flowchart TB
    D["Durable continuity<br/>persistent intent anchor<br/>+ meaning · decisions · authority · evidence · outcome state"]
    P["Bounded work pulse<br/>model · tools · human collaboration"]
    E["Observed effect + evaluation<br/>artifact · changed state · next safe transition"]
    H["Human authority<br/>meaning · risk · consequential action"]

    D -->|scope + context| P
    P -->|artifact + evidence| E
    E -->|continue · correct · recover · stop · redefine| D
    H -.-> D
    H -.-> E
```

What propagates through this loop is not merely text or code. **Alignment
signal** is shorthand for the traceable relationship between current intent and
each intermediate representation, action, item of evidence, and observed
outcome. That relationship can strengthen, degrade, or reveal that the intent
anchor itself needs revision. It is a working engineering metaphor, not a
formal measurement.

## Explore the project

| If you want to understand… | Continue with… |
|---|---|
| **Experience and evidence** | [*Narrow Success, Broad Failure*](docs/case-studies/narrow-success-broad-failure.md), a braided account of the projects, engineering value, framework growth, and contraction that exposed the problem |
| **Engineering framework** | [*Intent-to-Outcome Engineering*](docs/INTENT_TO_OUTCOME_ENGINEERING.md), the evolving argument about work pulses, durable system intelligence, feedback, authority, and open research questions |
| **Executable proof** | [Routing, Context, and Authority](docs/PERSONAL_HARNESS_OS.md), the current operator experience and the exact boundary of the tested public slice |
| **Source and architecture history** | [Architecture overview](docs/AZOTH_ARCHITECTURE.md), [decision index](docs/DECISIONS_INDEX.md), and [current proof paths](#inspect-the-current-proof) |

## From intent to governed work

Across the wider Azoth workshop, an operator can assemble a sequence like this
from separate capabilities:

`intent intake → discovery seed → research sufficiency → initiative / roadmap /
task formation → routed work pulse → evidence ledger → independent evaluation
→ bounded replay or next safe transition → closeout`

This is neither one opaque autonomous pipeline nor one fully integrated public
product. Each transition can expose its inputs, evidence, authority, and
stopping reason. Research can be required before a task is hydrated. An
evaluator can reject incomplete stage evidence. A repair can replay within a
declared budget. Protected actions remain closed until a human authorizes the
specific effect.

The public story therefore has three evidence bands:

### Portable proof

The extracted `v{{PUBLIC_VERSION}}` candidate implements and tests deterministic
effect-aware routing, compact source-referenced context, explicit authority and
stopping state, and a four-case no-write rehearsal. Thirty portable tests cover
that selected surface.

### Root workshop evidence

The wider source repository contains separate, inspectable machinery for raw
initiative intake, research-sufficiency checks, proposal knowledge assessment,
initiative and roadmap scaffolding, durable run ledgers, campaign routing,
stage evidence, evaluation, and bounded replay. Root-only campaign receipts
show these parts being used in multi-stage product-strategy, operating-profile,
and route-repair work.

Those capabilities are real, but they are not exported as one validated public
product journey. The [executable proof](docs/PERSONAL_HARNESS_OS.md) keeps the
difference visible.

### Working direction

Azoth is moving toward a system that can carry an outcome across many work
pulses: refine intent, discover missing knowledge, form and re-form work,
select the smallest sufficient composition, evaluate what happened, learn
externally to any one model context, and stop honestly at human authority.

That direction is an evolving framework, not a completion claim.

## How this inquiry emerged

The starting point was operational-data work: fragmented reporting semantics
could not survive a mechanical platform migration. Recovering business meaning
required traceable evidence, explicit acceptance contracts, staged
publication, independent readback, and recovery.

Reusing that discipline for local data requests showed that the coordination
pattern could transfer while project meaning could not. A shared internal
framework then explored project-local learning, reviewed promotion,
specialized roles, typed handoffs, and adaptive pipelines. When the framework
began duplicating state and consuming more attention than some tasks required,
architectural contraction revealed which controls had actually earned their
place.

A later conversational-agent operations system applied related lessons to a
different problem: versioned business meaning, deterministic policy,
behavioral tests, provider projection, authority gates, continuity, and
reconciliation. It is an individual production-system case, not a deployment
or ideal realization of Azoth.

Azoth is the independent project where these recurring engineering questions
became an explicit inquiry. The [case study](docs/case-studies/narrow-success-broad-failure.md)
holds the grounded chronology; the [framework](docs/INTENT_TO_OUTCOME_ENGINEERING.md)
develops the broader model.

## Claim boundary

| Surface | Status | Inspect |
|---|---|---|
| Effect-aware routing and typed route state | **Portable proof:** implemented and tested in the candidate | [`scripts/harness_profile.py`](scripts/harness_profile.py) |
| Compact, provenance-preserving context assembly | **Portable proof:** implemented and tested in the candidate | [`scripts/context_view.py`](scripts/context_view.py), [`scripts/personal_harness_context.py`](scripts/personal_harness_context.py) |
| Read-only behavioral rehearsal | **Portable proof:** implemented and tested in the candidate | [runner](scripts/personal_harness_practice_rehearsal.py), [cases](examples/personal-harness/rehearsal-cases.yaml), [tests](tests/test_personal_harness_practice_rehearsal.py) |
| Initiative discovery, research sufficiency, roadmap formation, ledgers, and campaign control | **Root workshop evidence:** separate capabilities and observed campaigns; not one extracted product journey | [`scripts/initiative_intake.py`](scripts/initiative_intake.py), [`scripts/research_sufficiency.py`](scripts/research_sufficiency.py), [`scripts/roadmap_scaffold.py`](scripts/roadmap_scaffold.py), [`scripts/run_ledger.py`](scripts/run_ledger.py), [`scripts/autonomous_loop.py`](scripts/autonomous_loop.py) |
| Intent-to-outcome engineering | **Working direction:** qualified framework, not fully implemented | [framework](docs/INTENT_TO_OUTCOME_ENGINEERING.md) |
| Historical employer projects and internal framework | Experience and repository-grounded evidence; not Azoth deployment evidence | [case study](docs/case-studies/narrow-success-broad-failure.md) |
| External adoption or production deployment of Azoth | Not claimed | [preview boundary](docs/PERSONAL_HARNESS_OS.md#public-preview-boundary) |

## Inspect the current proof

- [Routing](scripts/harness_profile.py) — deterministic effect and authority
  classification.
- [Context assembly](scripts/personal_harness_context.py) — compact,
  source-referenced packets.
- [No-write rehearsal](scripts/personal_harness_practice_rehearsal.py) — shared
  code exercised against representative cases.
- [Portable tests](tests/test_personal_harness_practice_rehearsal.py) —
  behavioral and mutation-detection evidence.
- [Research sufficiency](scripts/research_sufficiency.py) and [knowledge
  richness](scripts/proposal_knowledge_richness.py) — wider root-workshop
  checks, outside the narrow portable claim.
- [Trust Contract](kernel/TRUST_CONTRACT.md) — protected authority and action
  boundaries.
- [Architecture decisions](docs/DECISIONS_INDEX.md) — decision records and
  implementation status.

The framework relies on Git for revision history rather than adding another
changelog. Installer completeness, cross-host parity, package distribution,
and production adoption remain outside the `v{{PUBLIC_VERSION}}` validation
boundary. Existing tags remain immutable. Publication requires review of the
exact extracted tree and explicit human approval for its public commit, tag,
push, and release.

## License

Licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).
Commercial use outside the licence's permitted noncommercial purposes requires
a separate written agreement. Contact [Yiwei Ye on GitHub](https://github.com/yiwei79).

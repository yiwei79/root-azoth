# Narrow Success, Broad Failure: A Control-Systems Lens for Agentic Engineering

## From Orchestration to the Minimum-Sufficient Harness

AI agents are easy to demonstrate and difficult to make dependable. A model can
produce a plausible answer through many paths, while an operational workflow may
accept only a narrow range of outcomes: the right action, on the right object, at
the right time, under the right authority, with enough evidence to explain and
recover it.

This case study presents the engineering model that emerged from building
production conversational AI, reconstructing an operational data foundation,
developing an internal agentic-delivery framework, and then distilling those
lessons into Azoth's Personal Harness OS. It is a practical design argument—not
a claim that software agents are literally electrical circuits, that their
behaviour has been reduced to formal control theory, or that one harness is
optimal for every environment.

The central idea is simpler: treat agents as programmable probabilistic
components inside an engineered system. Define success outside the model, make
state and authority legible, observe real outcomes, and design the feedback path
that makes useful trajectories more likely.

The portable implementation is documented in
[Personal Harness OS](../PERSONAL_HARNESS_OS.md).

## Project lineage

The work progressed through three connected stages:

- Production AI and operational-data systems exposed how failures enter through
  business meaning, context, tools, state, authority, and feedback—not only
  through model behaviour.
- A comprehensive internal Agentic Framework tested richer governance, memory,
  routing, and delivery patterns, including machinery whose state and ceremony
  later proved too costly.
- Azoth distils those lessons into an independent public preview centred on
  minimum-sufficient routing, context, authority, evaluation, and rehearsal
  contracts.

GloBuddy and SupplyOps appear later as design examples, not as Azoth
deployments. This release candidate claims the implementation and tests it
ships, not external adoption or a finished universal harness.

## 1. The narrow success envelope and broad failure surface

For a real workflow, “the model produced a good-looking response” is rarely the
success condition. Success is usually a conjunction:

- the request was interpreted against the correct business meaning;
- the agent received relevant, current, authorised context;
- tools acted on the intended scope and no wider;
- outputs satisfied deterministic policy and data contracts;
- uncertain or consequential cases reached the correct human decision;
- the outcome was measured against the operational purpose; and
- the system could stop, explain itself, or recover when any condition failed.

Each additional condition narrows the acceptable success envelope. Failure,
meanwhile, remains broad: stale context, semantically wrong data, ambiguous
authority, a locally sensible but globally harmful action, silent tool failure,
an unobserved outcome, or a feedback loop that rewards the wrong proxy.

The useful engineering objective is therefore to:

`increase estimated P(trajectory ∈ S | architecture, context)`

`subject to cost, latency, safety, and authority constraints.`

Here, `S` is the explicitly defined set of acceptable trajectories. This is a
design heuristic, not a calibrated probability model. Its purpose is to force a
better question: which architectural choices make the whole path to an
acceptable outcome more likely, and which merely make one model call look more
capable?

## 2. Agents as programmable probabilistic transitions

Conventional software components are usually expected to map an input to an
output according to code we can inspect directly. An agent component is
different: its next action is conditioned on instructions, tools, context,
model behaviour, and the state accumulated along the way. It is programmable,
but its transition is probabilistic.

That makes the surrounding system—not the prompt alone—the primary engineering
object:

```text
Business intent + success envelope → context/state → probabilistic component + deterministic tools → bounded action → observed outcome → evaluation/evidence → correction, stop, or recovery
```

Protected human authority spans consequential transitions and release decisions.

The agent can reason over ambiguity; deterministic code can enforce invariants;
an evaluator can compare behaviour with explicit criteria; and a human can own
the decisions whose consequences should not be delegated. None of these is the
system alone. Reliability comes from their composition.

This lens also changes what “programming an agent” means. The work includes:

- choosing the state the component may see;
- exposing tools whose effects are bounded and inspectable;
- defining what evidence a transition must produce;
- deciding which failures can retry and which must stop;
- separating execution from independent evaluation; and
- connecting technical behaviour to the business outcome it exists to improve.

## 3. Control flow versus employee-role simulation

One common starting point is to personify agents: researcher, developer,
reviewer, manager. Role-based agents can be useful when a role creates a real
boundary—for example, isolated context, different tools, independent
evaluation, or distinct authority. But copying an organisation chart is not a
reliability architecture by itself.

The stronger default is to decompose around control flow:

- What information is required for this transition?
- Which component may act, and through which tools?
- What must be true before the action begins?
- What evidence proves that it completed?
- Who or what evaluates the result independently?
- Which state is authoritative when two surfaces disagree?
- What happens on uncertainty, contradiction, timeout, or partial failure?

Under this model, a “reviewer agent” is valuable because it receives a fresh
evaluation context and cannot silently become the executor—not because it has a
reviewer persona. A multi-agent graph is valuable when it gives the system
parallelism, isolation, critique, or authority separation that a simpler loop
cannot provide.

This is not an argument against roles. It is an argument that roles should be a
consequence of system boundaries, rather than the boundaries being inferred
from human job titles.

## 4. Signal, noise, semantic integrity, and trustworthy context

The signal-processing analogy is useful if it remains disciplined. “Signal” is
evidence that helps move the system toward the defined success envelope:
accepted business definitions, relevant context, validated state changes,
observed user outcomes, or an evaluator's actionable finding. “Noise” is
anything that consumes attention or changes behaviour without reliably
improving that trajectory: stale instructions, duplicated state, conflicting
sources of truth, raw logs without selection, ambiguous metrics, and elaborate
memory that cannot establish freshness or authority.

The objective is not to eliminate uncertainty. Probabilistic components are
valuable precisely because they can work through ambiguity. The objective is to
prevent avoidable ambiguity from propagating through the system while
preserving evidence about the uncertainty that remains.

Business semantics are part of that signal path. An agent can retrieve a
perfectly current row and still make the wrong decision if the row's meaning,
grain, ownership, or exception rules are unclear. Data integrity therefore
includes semantic integrity—not only completeness and schema validity.

This is why context engineering and ontology work are closely connected in
production AI. The agent needs a compact view of what the business means, which
state is current, what good looks like, and where authority sits. OpenAI's
description of Frontier similarly emphasises shared business context, outcomes,
permissions, evaluation, and an enterprise semantic layer; the product framing
differs, but the operational prerequisites are recognisable
([OpenAI, *Introducing OpenAI Frontier*](https://openai.com/index/introducing-openai-frontier/)).

## 5. GloBuddy and SupplyOps as production manifestations

Two systems at Glovo made this philosophy concrete from opposite directions.

**GloBuddy** is a production conversational-AI Rider CRM system for daily
operations around rider onboarding and the funnel lifecycle. The difficult part
was not making a model converse. It was turning operational intent into a
dependable path from policy and context to interaction, bounded outcomes,
follow-up state, measurement, and human improvement.

The implementation joined a governed agent runtime with versioned agent-as-code
definitions, scoped tools, routing, contextual knowledge, a cloud backend,
operational state, observability, and a release path with verification, human
gates, rollback, and recovery. Conversation outcomes were reconciled into
structured state and connected to operational measures rather than treated as
isolated transcripts. This let the system answer a harder question than “did
the agent respond?”: did the workflow behave acceptably, and did it support the
operational result it was built for?

**SupplyOps** began with a different failure surface. Leadership reporting
depended on fragmented, undocumented logic whose meaning could not be preserved
through a mechanical data-platform translation. The necessary work was semantic
reconstruction: trace sources and lineage, test competing hypotheses, establish
accepted definitions, encode them as deterministic metric contracts, and build
a bounded operational ontology around them.

That semantic layer then supported a governed BigQuery pipeline and
business-facing decision dashboard with quality gates, staged publication,
rollback, and independent readback. The result was not merely converted SQL. It
was a maintainable operational-intelligence foundation connecting business
meaning, data, publication, and consumption.

Together, the systems exposed a recurring adoption problem. AI behaviour cannot
be made dependable only at the model layer. It depends on the meaning and
authority of the context below it, and on the outcome and feedback loop above
it.

## 6. The original comprehensive Agentic Framework

The internal Agentic Framework grew from repeated operational work rather than
from an abstract desire to build a universal platform. Its early versions
established project-local bootloaders, reusable instructions, role overlays,
promotion rules, and workspace-aware context. Later iterations added
append-only episodic evidence, deterministic classification, explicit retrieval
rules, separate architectural review, typed project-to-master signals, and
human-controlled promotion into durable policy.

Several decisions were deliberately conservative:

- experience was appended as evidence rather than allowed to rewrite policy;
- reflection and architectural diagnosis were separated from the executing
  session;
- one source owned each concern instead of several surfaces competing to be
  current;
- project-local context could emerge while a thin shared contract preserved
  trust and handoff semantics; and
- autonomous continuation remained bounded by scope, evidence, and protected
  human decisions.

The framework also included richer orchestration: specialised roles, routing,
model tiers, duplicated compatibility surfaces, and multi-stage delivery paths.
Those mechanisms were not mistakes simply because they were complex. They were
hypotheses about where additional structure would improve control.

## 7. What production use revealed about duplicated state and orchestration cost

Using the framework across real work made its failure modes observable. Some
layers improved safety or continuity. Others duplicated information already
available in live repositories, forced the same decision through multiple
representations, or made an agent spend more context reconstructing the harness
than solving the task.

The cost was not only code volume. Duplicated state creates semantic questions:
which copy is authoritative, which is stale, and which update path is allowed?
More orchestration creates more transitions that can lose intent, omit evidence,
or stop for the wrong reason. More instructions can reduce guidance when every
rule competes for attention.

The response was architectural contraction, not indiscriminate deletion. In one
scoped operational-data redesign, 88 files changed, with 464 insertions and
4,835 deletions (net -4,371). The diff size is evidence of a substantial
contraction, not a claim that every deleted line was redundant or that line
count alone proves quality. The redesign preserved domain-specific validation,
release controls, live truth, and human authorisation. The principle was to keep
the control that earned its operating cost and remove machinery whose state
burden had become a new source of noise.

This conclusion has useful external calibration. OpenAI describes replacing a
large instruction manual with a short map into repository-owned knowledge
([OpenAI, *Harness engineering*](https://openai.com/index/harness-engineering/)).
Anthropic describes context as finite and recommends progressive disclosure,
allowing agents to discover relevant information while retaining only what is
needed in working memory
([Anthropic, *Effective context engineering for AI agents*](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
These sources do not prove that the earlier implementation was uniquely correct;
they provide current external calibration for the same class of trade-off.

## 8. Personal Harness OS and the minimum-sufficient governed path

Personal Harness OS distilled the contraction into a small executable API and
packet contract:

- **HarnessRequest** captures the goal, intended actions, planned paths, and
  the signals needed to reason about effects and traceability.
- **classify_harness_request** returns a **HarnessDecision**. Its selected
  `profile` field places the request on the mode ladder without inventing a
  separate profile object.
- **RouteCapsule** states the route, required authority, required inputs, next
  safe action, and stop reason in a compact typed packet.
- **build_context_view** creates a compact context-view packet from approved
  summaries and pointers, filters raw memory, and keeps advisory context
  separate from governing instruction.
- **build_personal_harness_context** provides the read-only integration path
  across routing, bounded recall, optional approved context, and project
  readback.

The mode ladder is explicit:

| Mode | Promise | Boundary |
|---|---|---|
| Guide | Orientation and decision support | No project mutation or autonomy claim |
| Assisted | Skills, tools, and focused checks | No hidden project-management ownership |
| Managed | Project-local operating state | Fresh local authority required |
| Governed autonomy | Campaign-bounded continuation | Budget, ledger, write authority, stop conditions, and protected decisions required |

The portable rehearsal surface keeps those promises testable without turning
examples into a second operating system. A generic runner consumes
`examples/personal-harness/rehearsal-cases.yaml`, evaluates representative
routes without writing to the target repository, and reports profile, route,
authority, warning, and stop-condition results. A command-line wrapper may be
added around that runner, but its final name is not part of this contract.

The June 2026 implementation began with pure, deterministic routing contracts
and focused tests before integration into wider control surfaces. It later
assembled route-aware context from compact memory results, optional personal
knowledge, and project receipts, while treating missing or stale sources as
warnings instead of inventing current truth.

“Minimum sufficient” does not mean no harness. It means the lightest path that
still makes the relevant context, evidence, authority, stop conditions, and
recovery visible. Ordinary work should not pay the ceremony cost of governed
autonomy. Consequential work should not be disguised as an ordinary task to
avoid that ceremony.

Recent platform direction reinforces the viability of simple primitives. The
OpenAI Responses API exposes shell execution, files as working context, bounded
tool output, native compaction, and progressively discovered skills
([OpenAI, *From model to agent*](https://openai.com/index/equip-responses-api-computer-environment/)).
That does not remove the need for application memory or retrieval; it raises the
bar for custom infrastructure by making a capable minimum path available.

## 9. When RAG, memory, and multi-agent coordination earn their cost

The correct conclusion is not “RAG, memory, and multi-agent systems are bad.”
It is that each should answer a demonstrated failure mode.

**Retrieval earns its cost when:**

- the relevant corpus cannot fit or be navigated reliably through ordinary
  files and tools;
- the query pattern and freshness requirements are understood;
- provenance, permissions, and ranking can be preserved; and
- retrieval quality can be evaluated against representative tasks.

**Memory earns its cost when:**

- information must survive beyond the current working context;
- recomputing it is expensive or would lose important evidence;
- freshness and authority can be represented;
- experience is append-only by default; and
- promotion into durable behaviour is reviewed separately from capture.

**Multi-agent coordination earns its cost when:**

- separable work can run in parallel;
- context or tool isolation materially reduces interference;
- an evaluator must remain independent of the executor;
- different authority boundaries are real; or
- the quality or latency gain exceeds the handoff and reconciliation overhead.

Otherwise, shell commands, files, a bounded loop, deterministic tools, and one
well-instrumented probabilistic component may be the more capable architecture
because fewer transitions can lose intent.

Native compaction does not make durable memory disappear. Progressive file
discovery does not make retrieval obsolete. Better models do not remove
permissions, evaluation, or semantic integrity. These advances change the
build-versus-buy and simple-versus-custom boundary; they do not abolish the
underlying requirements.

## 10. Transferable principles and explicit boundaries

The transferable method is:

1. Define the success envelope in operational terms outside the model.
2. Model agents as probabilistic transitions inside an explicit control flow.
3. Give each transition the minimum context, tools, and authority it needs.
4. Keep business meaning and data provenance inside the reliability boundary.
5. Make consequential effects bounded, observable, and recoverable.
6. Evaluate outcomes independently and connect behaviour to the purpose of the
   workflow.
7. Preserve evidence by addition; promote durable policy through a separate
   decision.
8. Let project-specific harnesses emerge while keeping the shared contract thin.
9. Add retrieval, memory, or coordination when evidence identifies the failure
   they solve.
10. Remove machinery when its state and maintenance cost exceed the control it
    provides.

The boundaries matter as much as the thesis:

- This is an engineering lens, not a formal control-theory result.
- The probability expression is a decision heuristic, not a measured model.
- GloBuddy and SupplyOps show where the lens was shaped in production; they do
  not prove that every business has the same adoption problem.
- The Agentic Framework records an evidence-led evolution, including complexity
  that was later reduced; it was not minimal from the beginning.
- The selected Personal Harness routing, context, and rehearsal contracts are
  implemented and tested in the `v0.3.0-rc.1` executable candidate. The wider
  operating profile remains under development; it is not a finished universal
  harness.
- Role-based agents, RAG, memory, and multi-agent graphs remain valid when their
  boundaries and value are demonstrated.
- No claim is made here of external Azoth adoption, causal business lift, or
  having invented the broader industry concepts used to explain the work.

The practical contribution is therefore not a claim to possess a universal
recipe. It is a way of engineering under uncertainty: make success explicit,
keep the signal path trustworthy, expose authority and feedback, and let the
smallest system that satisfies those conditions emerge from evidence.
